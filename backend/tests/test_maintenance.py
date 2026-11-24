"""
Regression tests for backend/app/services/maintenance.py and the
asyncio disk-cleanup scheduler wired in backend/app/main.py.

Coverage:
  1. clean_stale_files — skips recent files
  2. clean_stale_files — removes genuinely old files
  3. clean_stale_files — dry_run does not delete
  4. clean_stale_files — missing directory returns error summary (no crash)
  5. clean_stale_files — skips sub-directories (no recursion)
  6. clean_stale_files — partial error (unlink fails) is captured, not raised
  7. CleanupSummary.merge — arithmetic correctness
  8. clean_all_stale_files — sweeps both generated_dir and uploads_dir
  9. Scheduler integration — _run_daily_cleanup performs startup sweep and
     then sleeps; task can be cancelled cleanly without exception propagation.
"""

import asyncio
import os
import time
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from app.services.maintenance import (
    CleanupSummary,
    clean_all_stale_files,
    clean_stale_files,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_old_file(directory: Path, name: str, age_days: int = 10) -> Path:
    """Create a file and set its mtime to `age_days` days in the past."""
    p = directory / name
    p.write_bytes(b"x" * 128)
    old_mtime = time.time() - (age_days * 86_400)
    os.utime(p, (old_mtime, old_mtime))
    return p


def _make_new_file(directory: Path, name: str) -> Path:
    """Create a file with current mtime."""
    p = directory / name
    p.write_bytes(b"y" * 64)
    return p


# ---------------------------------------------------------------------------
# 1. Recent files are NOT removed
# ---------------------------------------------------------------------------
def test_clean_stale_files_keeps_recent_files(tmp_path):
    _make_new_file(tmp_path, "recent.pdf")
    summary = clean_stale_files(target_dir=tmp_path, max_age_days=7, dry_run=False)
    assert summary.files_removed == 0
    assert summary.bytes_reclaimed == 0
    assert (tmp_path / "recent.pdf").exists(), "Recent file should not be deleted"


# ---------------------------------------------------------------------------
# 2. Old files ARE removed
# ---------------------------------------------------------------------------
def test_clean_stale_files_removes_old_files(tmp_path):
    old = _make_old_file(tmp_path, "old_report.pdf", age_days=10)
    _make_new_file(tmp_path, "current.docx")

    summary = clean_stale_files(target_dir=tmp_path, max_age_days=7, dry_run=False)

    assert summary.files_removed == 1
    assert summary.bytes_reclaimed == 128
    assert not old.exists(), "Old file should have been deleted"
    assert (tmp_path / "current.docx").exists(), "New file must survive"


# ---------------------------------------------------------------------------
# 3. dry_run does NOT delete
# ---------------------------------------------------------------------------
def test_clean_stale_files_dry_run_no_deletion(tmp_path):
    old = _make_old_file(tmp_path, "stale.pptx", age_days=14)

    summary = clean_stale_files(target_dir=tmp_path, max_age_days=7, dry_run=True)

    assert summary.files_removed == 1          # counted
    assert summary.bytes_reclaimed == 128       # counted
    assert old.exists(), "dry_run must not delete the file"


# ---------------------------------------------------------------------------
# 4. Non-existent directory → error summary, no exception
# ---------------------------------------------------------------------------
def test_clean_stale_files_missing_directory(tmp_path):
    missing = tmp_path / "does_not_exist"
    summary = clean_stale_files(target_dir=missing, max_age_days=7)
    assert summary.files_removed == 0
    assert len(summary.errors) == 1
    assert "does not exist" in summary.errors[0]


# ---------------------------------------------------------------------------
# 5. Sub-directories are NOT entered or deleted
# ---------------------------------------------------------------------------
def test_clean_stale_files_ignores_subdirectories(tmp_path):
    sub = tmp_path / "subdir"
    sub.mkdir()
    # Put an "old" marker inside the sub-dir — it must NOT be touched
    (sub / "nested.txt").write_bytes(b"nested")
    old_mtime = time.time() - (10 * 86_400)
    os.utime(sub, (old_mtime, old_mtime))

    summary = clean_stale_files(target_dir=tmp_path, max_age_days=7, dry_run=False)

    assert summary.files_removed == 0
    assert sub.is_dir(), "Sub-directory must not be removed"


# ---------------------------------------------------------------------------
# 6. Partial errors are captured (unlink fails)
# ---------------------------------------------------------------------------
def test_clean_stale_files_captures_unlink_errors(tmp_path):
    old = _make_old_file(tmp_path, "locked.pdf", age_days=10)

    with patch.object(Path, "unlink", side_effect=PermissionError("locked")):
        summary = clean_stale_files(target_dir=tmp_path, max_age_days=7, dry_run=False)

    assert summary.files_removed == 0
    assert len(summary.errors) == 1
    assert "locked.pdf" in summary.errors[0]
    assert old.exists()  # still there because unlink was mocked to fail


# ---------------------------------------------------------------------------
# 7. CleanupSummary.merge arithmetic
# ---------------------------------------------------------------------------
def test_cleanup_summary_merge():
    a = CleanupSummary(files_removed=3, bytes_reclaimed=1024, errors=["err1"])
    b = CleanupSummary(files_removed=2, bytes_reclaimed=512, errors=["err2", "err3"])
    merged = a.merge(b)

    assert merged.files_removed == 5
    assert merged.bytes_reclaimed == 1536
    assert merged.errors == ["err1", "err2", "err3"]
    # originals unmodified
    assert a.files_removed == 3
    assert b.files_removed == 2


# ---------------------------------------------------------------------------
# 8. clean_all_stale_files sweeps both generated_dir and uploads_dir
# ---------------------------------------------------------------------------
def test_clean_all_stale_files_sweeps_both_dirs(tmp_path):
    gen_dir = tmp_path / "generated"
    up_dir = tmp_path / "uploads"
    gen_dir.mkdir()
    up_dir.mkdir()

    _make_old_file(gen_dir, "report.pdf", age_days=10)
    _make_old_file(up_dir, "upload.csv", age_days=10)
    _make_new_file(gen_dir, "fresh.pdf")

    with (
        patch("app.services.maintenance.settings") as mock_settings,
    ):
        mock_settings.generated_dir = gen_dir
        mock_settings.uploads_dir = up_dir

        summary = clean_all_stale_files(max_age_days=7, dry_run=False)

    assert summary.files_removed == 2
    assert summary.bytes_reclaimed == 256       # 128 + 128
    assert not (gen_dir / "report.pdf").exists()
    assert not (up_dir / "upload.csv").exists()
    assert (gen_dir / "fresh.pdf").exists()


# ---------------------------------------------------------------------------
# 9. Scheduler integration: startup sweep then cancels cleanly
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_run_daily_cleanup_startup_sweep_and_cancel():
    """
    _run_daily_cleanup should:
    - Call clean_stale_files on startup (startup sweep).
    - Then asyncio.sleep for 86400s (daily cadence).
    - Cancel cleanly when the lifespan task is cancelled.
    """
    from app.main import _run_daily_cleanup

    call_log: list[str] = []

    def fake_clean(target_dir, max_age_days, dry_run):
        call_log.append(str(target_dir))
        return CleanupSummary(files_removed=0, bytes_reclaimed=0, errors=[])

    # Patch sleep so it raises CancelledError immediately (simulating shutdown)
    async def fast_sleep(_duration):
        raise asyncio.CancelledError

    with (
        patch("app.main.clean_stale_files", side_effect=fake_clean),
        patch("asyncio.sleep", side_effect=fast_sleep),
    ):
        task = asyncio.create_task(_run_daily_cleanup())
        try:
            await task
        except asyncio.CancelledError:
            pass

    # Startup sweep must have called clean_stale_files for BOTH directories
    assert len(call_log) == 2, (
        f"Expected 2 cleanup calls on startup (generated + uploads), got {len(call_log)}: {call_log}"
    )
