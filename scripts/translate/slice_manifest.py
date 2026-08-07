"""Điều phối slice cho workflow Dual-Agent — checkpoint tiến độ từng slice để resume.

Pattern theo batch_manifest.py (dùng cho dịch sách). Mỗi slice là một phần
của master plan, được giao riêng cho executor, đánh dấu pending/claimed/
complete/failed để nếu dừng giữa chừng có thể resume từ slice còn thiếu.
"""

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

# Console Windows mặc định cp1252 — cần UTF-8 để in tiếng Việt
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_VERSION = 1


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp, path)


def slice_number(path: Path) -> int:
    match = re.search(r"(\d+)", path.stem)
    return int(match.group(1)) if match else -1


def slice_path(manifest_dir: Path, slice_id: int) -> Path:
    return manifest_dir / f"slice-{slice_id:03d}.json"


def load_slices(manifest_dir: Path) -> list[dict]:
    slices = []
    if not manifest_dir.exists():
        return slices
    for path in sorted(manifest_dir.glob("slice-*.json"), key=slice_number):
        try:
            data = read_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data.get("slice_id"), int):
            slices.append(data)
    return slices


def create_slices(slug: str, manifest_dir: Path, slice_names: list[str],
                  force: bool = False) -> list[dict]:
    """Tạo manifest các slice từ danh sách tên. Mỗi slice là pending."""
    if not slice_names:
        raise ValueError("slice_names không được rỗng")
    if force and manifest_dir.exists():
        for path in manifest_dir.glob("slice-*.json"):
            path.unlink()

    result = []
    total = len(slice_names)
    for index, name in enumerate(slice_names):
        result.append({
            "manifest_version": MANIFEST_VERSION,
            "slug": slug,
            "slice_id": index,
            "name": name,
            "total_slices": total,
            "status": "pending",
            "claimed_by": "",
            "claimed_at": "",
            "completed_at": "",
            "error": "",
            "created_at": now_iso(),
        })
        write_json_atomic(slice_path(manifest_dir, index), result[-1])
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


def claim_slice(manifest_dir: Path, worker: str = "agent") -> dict | None:
    """Claim slice pending/failed đầu tiên (theo thứ tự slice_id)."""
    with _claim_lock(manifest_dir) as locked:
        if locked is False:
            return None
        for path in sorted(manifest_dir.glob("slice-*.json"), key=slice_number):
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


def update_slice(manifest_dir: Path, slice_id: int, status: str, error: str = "") -> dict:
    if status not in {"pending", "claimed", "complete", "failed"}:
        raise ValueError(f"Trạng thái không hợp lệ: {status}")
    path = slice_path(manifest_dir, slice_id)
    data = read_json(path)
    data["status"] = status
    data["error"] = error
    if status == "complete":
        data["completed_at"] = now_iso()
    write_json_atomic(path, data)
    return read_json(path)


def verify_slices(manifest_dir: Path) -> dict:
    slices = load_slices(manifest_dir)
    return {
        "slice_count": len(slices),
        "total_slices": slices[0].get("total_slices", len(slices)) if slices else 0,
        "pending": [s["slice_id"] for s in slices if s.get("status") == "pending"],
        "claimed": [s["slice_id"] for s in slices if s.get("status") == "claimed"],
        "complete": [s["slice_id"] for s in slices if s.get("status") == "complete"],
        "failed": [s["slice_id"] for s in slices if s.get("status") == "failed"],
        "remaining": [s["slice_id"] for s in slices if s.get("status") != "complete"],
        "ok": bool(slices) and all(s.get("status") == "complete" for s in slices),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Quản lý manifest slice cho Dual-Agent")
    parser.add_argument("--slug", required=True)
    parser.add_argument("--manifest-dir", type=Path, required=True)
    parser.add_argument("--names", nargs="+", default=[], help="Tên các slice (cho create)")
    parser.add_argument("--worker", default="agent")
    parser.add_argument("--slice-id", type=int)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("action", choices=["create", "status", "claim", "complete", "fail", "verify"])
    args = parser.parse_args()

    if args.action == "create":
        result = create_slices(args.slug, args.manifest_dir, args.names, args.force)
    elif args.action == "status":
        result = load_slices(args.manifest_dir)
    elif args.action == "claim":
        result = claim_slice(args.manifest_dir, args.worker)
    elif args.action in {"complete", "fail"}:
        if args.slice_id is None:
            parser.error("complete/fail cần --slice-id")
        result = update_slice(args.manifest_dir, args.slice_id,
                              "complete" if args.action == "complete" else "failed")
    else:
        result = verify_slices(args.manifest_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
