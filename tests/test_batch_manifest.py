import json
import sys

sys.path.insert(0, "scripts")

from translate.batch_manifest import create_batches, claim_batch, update_batch, verify_manifest


def _write_chunk(path, cid, chapter):
    path.write_text(json.dumps({
        "chunk_id": cid,
        "total_chunks": 4,
        "chapter": chapter,
        "text": f"Nội dung {cid}",
    }, ensure_ascii=False), encoding="utf-8")


def test_manifest_groups_by_chapter_and_resumes(tmp_path):
    chunks = tmp_path / "chunks"
    progress = tmp_path / "progress"
    chunks.mkdir()
    for cid in range(4):
        _write_chunk(chunks / f"chunk-{cid:03d}.json", cid, "Chương 1" if cid < 2 else "Chương 2")
    (progress / "chunk_000.json").parent.mkdir()
    (progress / "chunk_000.json").write_text(json.dumps({"translated_text": "Đã dịch"}), encoding="utf-8")

    batches = create_batches("book", chunks, progress, batch_size=3)
    assert [b["chunk_ids"] for b in batches] == [[1], [2, 3]]
    claimed = claim_batch(progress / "batches", "agent-a")
    assert claimed["status"] == "claimed"
    update_batch(progress / "batches", claimed["batch_id"], "complete")
    result = verify_manifest(progress / "batches", progress)
    assert result["duplicate_chunk_ids"] == []
    assert result["missing_progress_ids"] == [2, 3]


def test_failed_batch_can_be_reclaimed(tmp_path):
    chunks = tmp_path / "chunks"
    progress = tmp_path / "progress"
    chunks.mkdir()
    _write_chunk(chunks / "chunk-000.json", 0, "Chương 1")
    create_batches("book", chunks, progress)
    claimed = claim_batch(progress / "batches", "agent-a")
    update_batch(progress / "batches", claimed["batch_id"], "failed", "lỗi QA")
    reclaimed = claim_batch(progress / "batches", "agent-b")
    assert reclaimed["claimed_by"] == "agent-b"
