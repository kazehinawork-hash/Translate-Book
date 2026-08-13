"""Điều phối batch chunk cho workflow dịch bằng AI Agent."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_VERSION = 1
BATCH_DIR_NAME = "batches"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp, path)


def chunk_number(path: Path) -> int:
    match = re.search(r"(\d+)", path.stem)
    return int(match.group(1)) if match else -1


def progress_done(progress_dir: Path, chunk_id: int) -> bool:
    path = progress_dir / f"chunk_{chunk_id:03d}.json"
    if not path.exists():
        return False
    try:
        return bool(read_json(path).get("translated_text", "").strip())
    except (OSError, json.JSONDecodeError):
        return False


def load_chunks(chunks_dir: Path) -> list[dict]:
    chunks = []
    for path in sorted(chunks_dir.glob("chunk-*.json"), key=chunk_number):
        try:
            data = read_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data.get("chunk_id"), int):
            chunks.append(data)
    return chunks


def batch_path(manifest_dir: Path, batch_id: int) -> Path:
    return manifest_dir / f"batch-{batch_id:03d}.json"


def load_batches(manifest_dir: Path) -> list[dict]:
    batches = []
    if not manifest_dir.exists():
        return batches
    for path in sorted(manifest_dir.glob("batch-*.json"), key=chunk_number):
        try:
            data = read_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data.get("batch_id"), int):
            batches.append(data)
    return batches


def _group_chunks(chunks: list[dict], progress_dir: Path, batch_size: int) -> list[list[dict]]:
    pending = [c for c in chunks if not progress_done(progress_dir, c["chunk_id"])]
    groups: list[list[dict]] = []
    current: list[dict] = []
    current_chapter = None

    for chunk in pending:
        chapter = chunk.get("chapter", "") or ""
        if current and (len(current) >= batch_size or chapter != current_chapter):
            groups.append(current)
            current = []
        current.append(chunk)
        current_chapter = chapter
    if current:
        groups.append(current)
    return groups


def create_batches(slug: str, chunks_dir: Path, progress_dir: Path,
                   batch_size: int = 3, force: bool = False) -> list[dict]:
    if batch_size < 1:
        raise ValueError("batch_size phải lớn hơn 0")
    chunks = load_chunks(chunks_dir)
    if not chunks:
        raise ValueError(f"Không tìm thấy chunk JSON trong {chunks_dir}")

    manifest_dir = progress_dir / BATCH_DIR_NAME
    existing = load_batches(manifest_dir)
    if existing and not force:
        return existing
    if force and manifest_dir.exists():
        for path in manifest_dir.glob("batch-*.json"):
            path.unlink()

    groups = _group_chunks(chunks, progress_dir, batch_size)
    result = []
    total = len(chunks)
    for index, group in enumerate(groups):
        ids = [c["chunk_id"] for c in group]
        result.append({
            "manifest_version": MANIFEST_VERSION,
            "slug": slug,
            "batch_id": index,
            "chunk_ids": ids,
            "chapter": group[0].get("chapter", "") or "",
            "total_chunks": total,
            "status": "pending",
            "claimed_by": "",
            "claimed_at": "",
            "completed_at": "",
            "error": "",
            "created_at": now_iso(),
        })
        write_json_atomic(batch_path(manifest_dir, index), result[-1])
    return result


@contextmanager
def _claim_lock(manifest_dir: Path):
    lock_path = manifest_dir / ".claim.lock"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    owns_lock = False
    try:
        handle = open(lock_path, "x", encoding="utf-8")
        handle.write(str(os.getpid()))
        handle.close()
        owns_lock = True
        yield True
    except FileExistsError:
        yield False
    finally:
        if owns_lock and lock_path.exists():
            try:
                lock_path.unlink()
            except OSError:
                pass




def claim_batch(manifest_dir: Path, worker: str = "agent") -> dict | None:
    with _claim_lock(manifest_dir) as locked:
        if locked is False:
            return None
        for path in sorted(manifest_dir.glob("batch-*.json"), key=chunk_number):
            try:
                data = read_json(path)
            except (OSError, json.JSONDecodeError):
                continue
            if data.get("status") not in {"pending", "failed"}:
                continue
            data["status"] = "claimed"
            data["claimed_by"] = worker
            data["claimed_at"] = now_iso()
            data["error"] = ""
            write_json_atomic(path, data)
            return read_json(path)
    return None


def update_batch(manifest_dir: Path, batch_id: int, status: str, error: str = "") -> dict:
    if status not in {"pending", "claimed", "complete", "failed"}:
        raise ValueError(f"Trạng thái không hợp lệ: {status}")
    path = batch_path(manifest_dir, batch_id)
    data = read_json(path)
    data["status"] = status
    data["error"] = error
    if status == "complete":
        data["completed_at"] = now_iso()
    write_json_atomic(path, data)
    return read_json(path)


def verify_manifest(manifest_dir: Path, progress_dir: Path) -> dict:
    batches = load_batches(manifest_dir)
    ids: list[int] = []
    duplicate_ids: list[int] = []
    incomplete_batches: list[int] = []
    for batch in batches:
        for cid in batch.get("chunk_ids", []):
            if cid in ids and cid not in duplicate_ids:
                duplicate_ids.append(cid)
            ids.append(cid)
        if batch.get("status") != "complete":
            incomplete_batches.append(batch.get("batch_id"))
    missing_progress = sorted(cid for cid in set(ids) if not progress_done(progress_dir, cid))
    return {
        "batch_count": len(batches),
        "chunk_count": len(ids),
        "duplicate_chunk_ids": sorted(duplicate_ids),
        "missing_progress_ids": missing_progress,
        "incomplete_batch_ids": incomplete_batches,
        "ok": not duplicate_ids and not missing_progress and not incomplete_batches,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Tạo và quản lý manifest batch dịch AI Agent")
    parser.add_argument("--slug", required=True)
    parser.add_argument("--chunks-dir", type=Path, required=True)
    parser.add_argument("--progress-dir", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=3)
    parser.add_argument("--worker", default="agent")
    parser.add_argument("--batch-id", type=int)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("action", choices=["create", "status", "claim", "complete", "fail", "verify"])
    args = parser.parse_args()
    manifest_dir = args.progress_dir / BATCH_DIR_NAME

    if args.action == "create":
        result = create_batches(args.slug, args.chunks_dir, args.progress_dir, args.batch_size, args.force)
    elif args.action == "status":
        result = load_batches(manifest_dir)
    elif args.action == "claim":
        result = claim_batch(manifest_dir, args.worker)
    elif args.action in {"complete", "fail"}:
        if args.batch_id is None:
            parser.error("complete/fail cần --batch-id")
        result = update_batch(manifest_dir, args.batch_id, "complete" if args.action == "complete" else "failed")
    else:
        result = verify_manifest(manifest_dir, args.progress_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
