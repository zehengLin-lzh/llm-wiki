"""End-to-end tests for the full wiki lifecycle."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.file_ops import FileOps
from app.core.ingest_service import IngestService
from app.core.lint import LintWorker
from app.core.snapshot import SnapshotManager


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    d = tmp_path / "data"
    d.mkdir()
    return d


@pytest.fixture
def file_ops(data_dir: Path) -> FileOps:
    return FileOps(data_dir)


@pytest.fixture
def ingest_service(file_ops: FileOps) -> IngestService:
    return IngestService(file_ops, machine_name="test-machine")


class TestIngestLifecycle:
    @pytest.mark.asyncio
    async def test_ingest_text(self, ingest_service: IngestService):
        result = await ingest_service.ingest_text(
            filename="test-note.txt",
            content="FastAPI is a web framework for Python.",
            subdir="personal",
            tags=["python", "web"],
        )
        assert result["source_type"] == "text"
        assert "raw_path" in result
        assert result["raw_path"].startswith("raw/personal/")

    @pytest.mark.asyncio
    async def test_ingest_markdown(self, ingest_service: IngestService):
        result = await ingest_service.ingest_markdown(
            filename="notes.md",
            content="# My Notes\n\nSome content here.",
            subdir="work",
        )
        assert result["source_type"] == "markdown"
        assert "work" in result["raw_path"]

    @pytest.mark.asyncio
    async def test_ingest_file_auto_detect_md(self, ingest_service: IngestService):
        result = await ingest_service.ingest_file(
            filename="readme.md",
            data=b"# README\n\nProject docs.",
            subdir="shared",
        )
        assert result["source_type"] == "markdown"

    @pytest.mark.asyncio
    async def test_ingest_file_auto_detect_txt(self, ingest_service: IngestService):
        result = await ingest_service.ingest_file(
            filename="notes.txt",
            data=b"Plain text content here.",
            subdir="personal",
        )
        assert result["source_type"] == "text"

    @pytest.mark.asyncio
    async def test_ingest_produces_frontmatter(self, ingest_service: IngestService, file_ops: FileOps):
        result = await ingest_service.ingest_text(
            filename="test.txt",
            content="Some content",
            subdir="personal",
            tags=["test"],
        )
        raw_content = file_ops.read_raw(result["raw_path"].replace("raw/", "", 1))
        assert "---" in raw_content
        assert "source_type: text" in raw_content
        assert "compiled: false" in raw_content
        assert "test-machine" in raw_content

    @pytest.mark.asyncio
    async def test_ingest_produces_git_commit(self, ingest_service: IngestService, file_ops: FileOps):
        from git import Repo
        await ingest_service.ingest_text(
            filename="committed.txt", content="test", subdir="personal"
        )
        repo = Repo(file_ops.data_path)
        commits = list(repo.iter_commits())
        assert any("[ingest]" in c.message for c in commits)


class TestLintLifecycle:
    def test_lint_empty_wiki(self, file_ops: FileOps):
        worker = LintWorker(file_ops)
        result = worker.run()
        assert result.total_wiki_files == 0
        assert len(result.orphan_pages) == 0

    def test_lint_detects_orphan(self, file_ops: FileOps):
        file_ops.write_wiki("index.md", "# Index")
        file_ops.write_wiki("concepts/orphan.md", "# Orphan Page")
        worker = LintWorker(file_ops)
        result = worker.run()
        assert "concepts/orphan.md" in result.orphan_pages

    def test_lint_detects_dead_link(self, file_ops: FileOps):
        file_ops.write_wiki("index.md", "# Index\n\n- [Missing](concepts/missing.md)")
        worker = LintWorker(file_ops)
        result = worker.run()
        assert len(result.dead_links) == 1
        assert result.dead_links[0][1] == "concepts/missing.md"

    @pytest.mark.asyncio
    async def test_lint_detects_missing_summary(self, file_ops: FileOps):
        ingest_svc = IngestService(file_ops, machine_name="test")
        await ingest_svc.ingest_text(
            filename="article.txt", content="Article content", subdir="personal"
        )
        worker = LintWorker(file_ops)
        result = worker.run()
        assert len(result.missing_summaries) == 1

    def test_lint_report_generation(self, file_ops: FileOps):
        file_ops.write_wiki("index.md", "# Index")
        worker = LintWorker(file_ops)
        filename = worker.run_and_save()
        assert filename.endswith("-lint.md")
        reports = file_ops.list_wiki("_reports")
        assert len(reports) == 1


class TestSnapshotLifecycle:
    def test_create_snapshot(self, data_dir: Path, file_ops: FileOps):
        # Write some data first
        file_ops.write_wiki("index.md", "# Index")
        mgr = SnapshotManager(data_dir)
        snap = mgr.create(reason="test")
        assert snap.id.endswith("-test")
        assert Path(snap.path).exists()

    def test_list_snapshots(self, data_dir: Path):
        mgr = SnapshotManager(data_dir)
        mgr.create(reason="first")
        mgr.create(reason="second")
        snapshots = mgr.list_snapshots()
        assert len(snapshots) == 2

    def test_prune_snapshots(self, data_dir: Path):
        mgr = SnapshotManager(data_dir)
        for i in range(5):
            mgr.create(reason=f"snap-{i}")
        removed = mgr.prune(keep_n=2)
        assert removed == 3
        assert len(mgr.list_snapshots()) == 2

    def test_should_create(self, data_dir: Path):
        mgr = SnapshotManager(data_dir)
        assert mgr.should_create() is True  # No snapshots yet
        mgr.create(reason="fresh")
        assert mgr.should_create(max_age_hours=24) is False  # Just created


class TestFullCycle:
    """Test the complete ingest → wiki → lint → snapshot cycle."""

    @pytest.mark.asyncio
    async def test_full_cycle(self, data_dir: Path, file_ops: FileOps):
        # 1. Ingest multiple sources
        svc = IngestService(file_ops, machine_name="test")
        r1 = await svc.ingest_text("python-tips.txt", "Python tips: use list comprehensions", "personal")
        r2 = await svc.ingest_text("rust-notes.txt", "Rust has ownership model", "personal")
        r3 = await svc.ingest_markdown("readme.md", "# Project\n\nProject overview here", "work")

        assert r1["source_type"] == "text"
        assert r2["source_type"] == "text"
        assert r3["source_type"] == "markdown"

        # 2. Verify raw files exist
        raw_files = file_ops.list_raw()
        assert len(raw_files) == 3

        # 3. Manually create some wiki content (simulating compiler output)
        file_ops.write_wiki("index.md", "# Index\n\n- [Python](concepts/python.md)\n- [Rust](concepts/rust.md)")
        file_ops.write_wiki("concepts/python.md", "# Python\n\nA programming language.")
        file_ops.write_wiki("concepts/rust.md", "# Rust\n\nSystems programming.")

        # 4. Run lint
        lint = LintWorker(file_ops)
        lint_result = lint.run()
        assert lint_result.total_wiki_files == 3
        assert lint_result.total_raw_files == 3
        # All raw files should be missing summaries (compiler didn't run)
        assert len(lint_result.missing_summaries) == 3

        # 5. Save lint report
        report_file = lint.run_and_save()
        assert report_file.endswith("-lint.md")

        # 6. Create snapshot
        snap_mgr = SnapshotManager(data_dir)
        snap = snap_mgr.create(reason="after-cycle")
        assert Path(snap.path).exists()

        # 7. Verify git history
        from git import Repo
        repo = Repo(data_dir)
        commits = list(repo.iter_commits())
        messages = [c.message for c in commits]
        assert any("[ingest]" in m for m in messages)
        assert any("[create]" in m for m in messages)
