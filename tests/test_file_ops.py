from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from git import Repo

from app.core.file_ops import FileOps, RawImmutableError


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    """Provide a temporary data directory."""
    d = tmp_path / "data"
    d.mkdir()
    return d


@pytest.fixture
def file_ops(data_dir: Path) -> FileOps:
    return FileOps(data_dir)


class TestDirectorySetup:
    def test_creates_directory_structure(self, file_ops: FileOps) -> None:
        assert (file_ops.raw_path / "personal").is_dir()
        assert (file_ops.raw_path / "work").is_dir()
        assert (file_ops.raw_path / "shared").is_dir()
        assert (file_ops.wiki_path / "concepts").is_dir()
        assert (file_ops.wiki_path / "entities").is_dir()
        assert (file_ops.wiki_path / "summaries").is_dir()
        assert (file_ops.wiki_path / "_reports").is_dir()

    def test_initializes_git_repo(self, file_ops: FileOps) -> None:
        assert (file_ops.data_path / ".git").is_dir()
        repo = Repo(file_ops.data_path)
        assert len(list(repo.iter_commits())) >= 1


class TestRawOperations:
    def test_write_raw_creates_file(self, file_ops: FileOps) -> None:
        content = "---\nid: test_001\n---\n# Test\nContent here"
        path = file_ops.write_raw("personal", "test-article.md", content)
        assert path.exists()
        assert path.read_text() == content

    def test_write_raw_commits_to_git(self, file_ops: FileOps) -> None:
        file_ops.write_raw("personal", "test.md", "# Test")
        repo = Repo(file_ops.data_path)
        last_commit = list(repo.iter_commits())[0]
        assert "[ingest]" in last_commit.message

    def test_write_raw_refuses_overwrite(self, file_ops: FileOps) -> None:
        file_ops.write_raw("personal", "test.md", "# Original")
        with pytest.raises(RawImmutableError):
            file_ops.write_raw("personal", "test.md", "# Modified")

    def test_read_raw(self, file_ops: FileOps) -> None:
        file_ops.write_raw("work", "note.md", "# Work Note")
        content = file_ops.read_raw("work/note.md")
        assert content == "# Work Note"

    def test_list_raw(self, file_ops: FileOps) -> None:
        file_ops.write_raw("personal", "a.md", "# A")
        file_ops.write_raw("personal", "b.md", "# B")
        files = file_ops.list_raw("personal")
        assert len(files) == 2

    def test_safe_filename(self, file_ops: FileOps) -> None:
        path = file_ops.write_raw("personal", "My Article!!! (2024).md", "content")
        assert "my-article-2024.md" in path.name


class TestWikiOperations:
    def test_write_wiki_creates_file(self, file_ops: FileOps) -> None:
        path = file_ops.write_wiki("concepts/python.md", "# Python\nA language.")
        assert path.exists()
        assert "Python" in path.read_text()

    def test_write_wiki_allows_overwrite(self, file_ops: FileOps) -> None:
        file_ops.write_wiki("concepts/python.md", "# Python v1")
        file_ops.write_wiki("concepts/python.md", "# Python v2")
        content = file_ops.read_wiki("concepts/python.md")
        assert "v2" in content

    def test_write_wiki_commits(self, file_ops: FileOps) -> None:
        file_ops.write_wiki("index.md", "# Index")
        repo = Repo(file_ops.data_path)
        last = list(repo.iter_commits())[0]
        assert "[create]" in last.message

        file_ops.write_wiki("index.md", "# Updated Index")
        last = list(repo.iter_commits())[0]
        assert "[update]" in last.message

    def test_delete_wiki(self, file_ops: FileOps) -> None:
        file_ops.write_wiki("concepts/temp.md", "# Temp")
        assert file_ops.read_wiki("concepts/temp.md") != ""
        file_ops.delete_wiki("concepts/temp.md")
        assert file_ops.read_wiki("concepts/temp.md") == ""

    def test_read_wiki_nonexistent(self, file_ops: FileOps) -> None:
        assert file_ops.read_wiki("nonexistent.md") == ""

    def test_list_wiki(self, file_ops: FileOps) -> None:
        file_ops.write_wiki("concepts/a.md", "# A")
        file_ops.write_wiki("concepts/b.md", "# B")
        files = file_ops.list_wiki("concepts")
        assert len(files) == 2

    def test_grep_wiki(self, file_ops: FileOps) -> None:
        file_ops.write_wiki("concepts/fastapi.md", "# FastAPI\nA modern web framework")
        file_ops.write_wiki("concepts/flask.md", "# Flask\nA micro web framework")
        results = file_ops.grep_wiki("web framework")
        assert len(results) == 2

    def test_grep_wiki_no_match(self, file_ops: FileOps) -> None:
        file_ops.write_wiki("concepts/test.md", "# Test")
        results = file_ops.grep_wiki("nonexistent pattern xyz")
        assert len(results) == 0


class TestWikiTree:
    def test_wiki_tree_structure(self, file_ops: FileOps) -> None:
        file_ops.write_wiki("index.md", "# Index")
        file_ops.write_wiki("concepts/python.md", "# Python")
        tree = file_ops.wiki_tree()
        assert tree["name"] == "wiki"
        names = {c["name"] for c in tree["children"]}
        assert "index.md" in names
        assert "concepts" in names


class TestSchema:
    def test_read_schema_empty(self, file_ops: FileOps) -> None:
        assert file_ops.read_schema() == ""

    def test_write_and_read_schema(self, file_ops: FileOps) -> None:
        file_ops.write_schema("# My Schema\n\nRules here.")
        assert "My Schema" in file_ops.read_schema()


class TestGitHistory:
    def test_full_operation_history(self, file_ops: FileOps) -> None:
        """Verify a series of operations produces correct git history."""
        file_ops.write_raw("personal", "source.md", "# Source")
        file_ops.write_wiki("summaries/source-summary.md", "# Summary")
        file_ops.write_wiki("concepts/topic.md", "# Topic")
        file_ops.write_wiki("index.md", "# Index\n- topic")

        repo = Repo(file_ops.data_path)
        commits = list(repo.iter_commits())
        # init + 4 operations = 5 commits
        assert len(commits) >= 5
        messages = [c.message for c in commits]
        assert any("[ingest]" in m for m in messages)
        assert any("[create]" in m for m in messages)
