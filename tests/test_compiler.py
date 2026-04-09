"""Tests for the compiler's tool execution and helper functions."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.compiler import Compiler, CompileResult
from app.core.file_ops import FileOps


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    d = tmp_path / "data"
    d.mkdir()
    return d


@pytest.fixture
def file_ops(data_dir: Path) -> FileOps:
    return FileOps(data_dir)


@pytest.fixture
def compiler(file_ops: FileOps) -> Compiler:
    return Compiler(file_ops)


class TestToolExecution:
    def test_read_wiki_file(self, compiler: Compiler, file_ops: FileOps):
        file_ops.write_wiki("index.md", "# Index\nTest content")
        result = CompileResult()
        output = compiler._execute_tool("read_wiki_file", {"path": "index.md"}, result)
        assert "Index" in output
        assert len(result.operations) == 1

    def test_read_wiki_file_missing(self, compiler: Compiler):
        result = CompileResult()
        output = compiler._execute_tool("read_wiki_file", {"path": "nonexistent.md"}, result)
        assert "does not exist" in output

    def test_list_wiki_directory(self, compiler: Compiler, file_ops: FileOps):
        file_ops.write_wiki("concepts/a.md", "# A")
        file_ops.write_wiki("concepts/b.md", "# B")
        result = CompileResult()
        output = compiler._execute_tool("list_wiki_directory", {"path": "concepts"}, result)
        assert "a.md" in output
        assert "b.md" in output

    def test_create_wiki_file(self, compiler: Compiler, file_ops: FileOps):
        result = CompileResult()
        output = compiler._execute_tool("create_wiki_file", {
            "path": "concepts/new.md",
            "frontmatter": "id: test\ntype: concept",
            "content": "# New Concept",
        }, result)
        assert "Created" in output
        assert file_ops.read_wiki("concepts/new.md") != ""

    def test_create_wiki_file_already_exists(self, compiler: Compiler, file_ops: FileOps):
        file_ops.write_wiki("concepts/existing.md", "# Existing")
        result = CompileResult()
        output = compiler._execute_tool("create_wiki_file", {
            "path": "concepts/existing.md",
            "frontmatter": "id: test",
            "content": "# Overwrite",
        }, result)
        assert "already exists" in output

    def test_update_wiki_file(self, compiler: Compiler, file_ops: FileOps):
        file_ops.write_wiki("index.md", "# Old")
        result = CompileResult()
        output = compiler._execute_tool("update_wiki_file", {
            "path": "index.md",
            "frontmatter": "id: index",
            "content": "# Updated Index",
        }, result)
        assert "Updated" in output
        assert "Updated Index" in file_ops.read_wiki("index.md")

    def test_append_to_wiki_file(self, compiler: Compiler, file_ops: FileOps):
        file_ops.write_wiki("index.md", "# Index\n\nExisting content")
        result = CompileResult()
        output = compiler._execute_tool("append_to_wiki_file", {
            "path": "index.md",
            "content": "- New entry",
        }, result)
        assert "Appended" in output
        content = file_ops.read_wiki("index.md")
        assert "Existing content" in content
        assert "New entry" in content

    def test_append_to_nonexistent(self, compiler: Compiler):
        result = CompileResult()
        output = compiler._execute_tool("append_to_wiki_file", {
            "path": "nonexistent.md",
            "content": "test",
        }, result)
        assert "does not exist" in output

    def test_unknown_tool(self, compiler: Compiler):
        result = CompileResult()
        output = compiler._execute_tool("delete_everything", {}, result)
        assert "Unknown tool" in output


class TestFrontmatterParsing:
    def test_parse_valid(self, compiler: Compiler):
        content = "---\nid: test_123\ncompiled: false\n---\n\n# Content"
        fm = compiler._parse_frontmatter(content)
        assert fm["id"] == "test_123"
        assert fm["compiled"] is False

    def test_parse_no_frontmatter(self, compiler: Compiler):
        content = "# Just Content"
        fm = compiler._parse_frontmatter(content)
        assert fm == {}

    def test_parse_invalid_yaml(self, compiler: Compiler):
        content = "---\n: invalid: yaml:\n---\n\n# Content"
        fm = compiler._parse_frontmatter(content)
        # Should not crash, returns empty or partial
        assert isinstance(fm, dict)


class TestWikiStructure:
    def test_get_wiki_structure_empty(self, compiler: Compiler):
        result = compiler._get_wiki_structure()
        assert "empty" in result.lower()

    def test_get_wiki_structure_with_files(self, compiler: Compiler, file_ops: FileOps):
        file_ops.write_wiki("index.md", "# Index")
        file_ops.write_wiki("concepts/python.md", "# Python")
        result = compiler._get_wiki_structure()
        assert "index.md" in result
        assert "python.md" in result
