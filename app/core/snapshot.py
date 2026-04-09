"""Snapshot system: create/list/restore/prune data snapshots."""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

import structlog
from pydantic import BaseModel

log = structlog.get_logger()


class SnapshotInfo(BaseModel):
    id: str
    reason: str
    created_at: str
    size_mb: float
    path: str


class SnapshotManager:
    """Manages snapshots of the data directory."""

    def __init__(self, data_path: Path):
        self.data_path = data_path
        self.snapshots_dir = data_path / ".snapshots"
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

    def create(self, reason: str = "manual") -> SnapshotInfo:
        """Create a snapshot of the entire data directory."""
        now = datetime.now(timezone.utc)
        ts = now.strftime("%Y%m%d_%H%M%S")
        slug = reason.replace(" ", "-").lower()[:30]
        snap_name = f"{ts}-{slug}"
        snap_path = self.snapshots_dir / snap_name

        log.info("snapshot.creating", name=snap_name)

        # Copy data/ excluding .snapshots/ and .git/
        shutil.copytree(
            self.data_path,
            snap_path,
            ignore=shutil.ignore_patterns(".snapshots", ".git"),
        )

        size = sum(f.stat().st_size for f in snap_path.rglob("*") if f.is_file())
        size_mb = round(size / (1024 * 1024), 2)

        log.info("snapshot.created", name=snap_name, size_mb=size_mb)

        return SnapshotInfo(
            id=snap_name,
            reason=reason,
            created_at=now.isoformat(),
            size_mb=size_mb,
            path=str(snap_path),
        )

    def list_snapshots(self) -> list[SnapshotInfo]:
        """List all snapshots, newest first."""
        snapshots = []
        for d in sorted(self.snapshots_dir.iterdir(), reverse=True):
            if not d.is_dir():
                continue
            parts = d.name.split("-", 2)
            reason = parts[2] if len(parts) > 2 else "unknown"
            size = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
            mtime = datetime.fromtimestamp(d.stat().st_mtime, tz=timezone.utc)
            snapshots.append(SnapshotInfo(
                id=d.name,
                reason=reason,
                created_at=mtime.isoformat(),
                size_mb=round(size / (1024 * 1024), 2),
                path=str(d),
            ))
        return snapshots

    def prune(self, keep_n: int = 3) -> int:
        """Remove old snapshots, keeping the most recent N."""
        snapshots = self.list_snapshots()
        removed = 0
        for snap in snapshots[keep_n:]:
            snap_path = Path(snap.path)
            if snap_path.exists():
                shutil.rmtree(snap_path)
                removed += 1
                log.info("snapshot.pruned", id=snap.id)
        return removed

    def should_create(self, max_age_hours: int = 24) -> bool:
        """Check if a new snapshot should be created (based on age of latest)."""
        snapshots = self.list_snapshots()
        if not snapshots:
            return True
        latest = Path(snapshots[0].path)
        age_hours = (datetime.now().timestamp() - latest.stat().st_mtime) / 3600
        return age_hours > max_age_hours
