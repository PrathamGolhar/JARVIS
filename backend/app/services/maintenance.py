from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import logging
from pathlib import Path
import time

from app.settings import settings

logger = logging.getLogger("jarvis.maintenance")


@dataclass
class CleanupSummary:
    files_removed: int
    bytes_reclaimed: int
    errors: list[str] = field(default_factory=list)

    def merge(self, other: "CleanupSummary") -> "CleanupSummary":
        """Return a new summary combining self and other."""
        return CleanupSummary(
            files_removed=self.files_removed + other.files_removed,
            bytes_reclaimed=self.bytes_reclaimed + other.bytes_reclaimed,
            errors=self.errors + other.errors,
        )


def clean_stale_files(
    target_dir: Path | str | None = None,
    max_age_days: int = 7,
    dry_run: bool = False,
) -> CleanupSummary:
    """
    Safely clean files older than ``max_age_days`` from a single directory.

    Defaults to ``settings.generated_dir`` when *target_dir* is not given.
    Returns a :class:`CleanupSummary` describing what was (or would be) removed.
    Does **not** recurse into sub-directories — only top-level files are
    considered so that project folders are never accidentally deleted.
    """
    directory = Path(target_dir) if target_dir else settings.generated_dir
    if not directory.exists() or not directory.is_dir():
        return CleanupSummary(
            files_removed=0,
            bytes_reclaimed=0,
            errors=[f"Directory does not exist: {directory}"],
        )

    cutoff_time = time.time() - (max_age_days * 86400)
    files_removed = 0
    bytes_reclaimed = 0
    errors: list[str] = []

    for file_path in directory.iterdir():
        if not file_path.is_file():
            continue  # skip sub-directories
        try:
            stat = file_path.stat()
            if stat.st_mtime < cutoff_time:
                size = stat.st_size
                if not dry_run:
                    file_path.unlink()
                    logger.info(
                        "Cleaned stale file: %s (size: %d bytes, age: %.1f days)",
                        file_path.name,
                        size,
                        (time.time() - stat.st_mtime) / 86400,
                    )
                files_removed += 1
                bytes_reclaimed += size
        except Exception as exc:
            err_msg = f"Failed to clean {file_path.name}: {exc}"
            logger.warning(err_msg)
            errors.append(err_msg)

    return CleanupSummary(
        files_removed=files_removed,
        bytes_reclaimed=bytes_reclaimed,
        errors=errors,
    )


def clean_all_stale_files(max_age_days: int = 7, dry_run: bool = False) -> CleanupSummary:
    """
    Convenience wrapper: sweep **both** ``generated_dir`` and ``uploads_dir``.

    Returns a merged :class:`CleanupSummary` with totals across both directories.
    Safe to call even if either directory does not yet exist.
    """
    gen_summary = clean_stale_files(
        target_dir=settings.generated_dir,
        max_age_days=max_age_days,
        dry_run=dry_run,
    )
    up_summary = clean_stale_files(
        target_dir=settings.uploads_dir,
        max_age_days=max_age_days,
        dry_run=dry_run,
    )
    combined = gen_summary.merge(up_summary)
    logger.info(
        "Cleanup sweep complete: removed=%d files, reclaimed=%d bytes, errors=%d%s",
        combined.files_removed,
        combined.bytes_reclaimed,
        len(combined.errors),
        " (dry_run)" if dry_run else "",
    )
    return combined
