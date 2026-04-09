from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import structlog
from git import Repo

log = structlog.get_logger()


class RawImmutableError(Exception):
    """Raised when attempting to modify an existing raw file."""


class FileOps:
    """Controlled file operations for the data directory with automatic git commits."""

    def __init__(self, data_path: Path):
        self.data_path = data_path.resolve()
        self.raw_path = self.data_path / "raw"
        self.wiki_path = self.data_path / "wiki"
        self._ensure_dirs()
        self._repo = self._ensure_git()

    def _ensure_dirs(self) -> None:
        dirs = [
            self.raw_path / "personal",
            self.raw_path / "work",
            self.raw_path / "shared",
            self.wiki_path / "concepts",
            self.wiki_path / "entities",
            self.wiki_path / "summaries",
            self.wiki_path / "_reports",
            self.data_path / ".snapshots",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    def _ensure_git(self) -> Repo:
        git_dir = self.data_path / ".git"
        if git_dir.exists():
            return Repo(self.data_path)

        repo = Repo.init(self.data_path)
        # Create .gitignore for data repo
        gitignore = self.data_path / ".gitignore"
        gitignore.write_text(".snapshots/\n")
        repo.index.add([".gitignore"])
        repo.index.commit("[init] Initialize wiki data repository")
        log.info("file_ops.git_init", path=str(self.data_path))
        return repo

    def _commit(self, paths: list[Path], message: str) -> None:
        """Stage and commit files."""
        rel_paths = []
        for p in paths:
            try:
                rel = p.relative_to(self.data_path)
                rel_paths.append(str(rel))
            except ValueError:
                rel_paths.append(str(p))

        self._repo.index.add(rel_paths)
        self._repo.index.commit(message)
        log.info("file_ops.commit", message=message, files=rel_paths)

    def _commit_delete(self, paths: list[Path], message: str) -> None:
        """Stage deletions and commit."""
        rel_paths = []
        for p in paths:
            try:
                rel = p.relative_to(self.data_path)
                rel_paths.append(str(rel))
            except ValueError:
                rel_paths.append(str(p))

        self._repo.index.remove(rel_paths, working_tree=True)
        self._repo.index.commit(message)
        log.info("file_ops.commit_delete", message=message, files=rel_paths)

    # --- Raw operations (append-only) ---

    def read_raw(self, rel_path: str) -> str:
        """Read a raw file. rel_path is relative to data/raw/."""
        path = (self.raw_path / rel_path).resolve()
        self._validate_inside(path, self.raw_path)
        return path.read_text(encoding="utf-8")

    def list_raw(self, subdir: str = "") -> list[Path]:
        """List raw files, optionally under a subdirectory."""
        base = self.raw_path / subdir if subdir else self.raw_path
        if not base.exists():
            return []
        return sorted(
            [f for f in base.rglob("*.md") if f.is_file()],
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )

    def write_raw(
        self,
        subdir: str,
        filename: str,
        content: str,
        reason: str = "new ingest",
    ) -> Path:
        """Write a new raw file. Raises RawImmutableError if file exists."""
        filename = self._safe_filename(filename)
        path = (self.raw_path / subdir / filename).resolve()
        self._validate_inside(path, self.raw_path)

        if path.exists():
            raise RawImmutableError(
                f"Raw file already exists and cannot be overwritten: {path}"
            )

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        self._commit([path], f"[ingest] raw/{subdir}/{filename}: {reason}")
        return path

    # --- Wiki operations (full CRUD) ---

    def read_wiki(self, rel_path: str) -> str:
        """Read a wiki file. rel_path is relative to data/wiki/."""
        path = (self.wiki_path / rel_path).resolve()
        self._validate_inside(path, self.wiki_path)
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def list_wiki(self, subdir: str = "") -> list[Path]:
        """List wiki files, optionally under a subdirectory."""
        base = self.wiki_path / subdir if subdir else self.wiki_path
        if not base.exists():
            return []
        return sorted(
            [f for f in base.rglob("*.md") if f.is_file()],
            key=lambda f: f.name,
        )

    def write_wiki(
        self,
        rel_path: str,
        content: str,
        reason: str = "update",
    ) -> Path:
        """Write (create or overwrite) a wiki file."""
        path = (self.wiki_path / rel_path).resolve()
        self._validate_inside(path, self.wiki_path)

        path.parent.mkdir(parents=True, exist_ok=True)
        op = "update" if path.exists() else "create"
        path.write_text(content, encoding="utf-8")
        self._commit([path], f"[{op}] wiki/{rel_path}: {reason}")
        return path

    def delete_wiki(self, rel_path: str, reason: str = "removed") -> None:
        """Delete a wiki file."""
        path = (self.wiki_path / rel_path).resolve()
        self._validate_inside(path, self.wiki_path)

        if not path.exists():
            return

        self._commit_delete([path], f"[delete] wiki/{rel_path}: {reason}")

    def grep_wiki(self, pattern: str) -> list[tuple[Path, str]]:
        """Search wiki files for a pattern. Returns list of (path, matching_line)."""
        results = []
        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error:
            # Fall back to literal search
            regex = re.compile(re.escape(pattern), re.IGNORECASE)

        for f in self.wiki_path.rglob("*.md"):
            if not f.is_file():
                continue
            try:
                for line in f.read_text(encoding="utf-8").splitlines():
                    if regex.search(line):
                        results.append((f, line.strip()))
            except (OSError, UnicodeDecodeError):
                continue
        return results

    def wiki_tree(self) -> dict:
        """Return wiki directory structure as nested dict."""
        return self._build_tree(self.wiki_path)

    # --- Schema ---

    def read_schema(self) -> str:
        """Read data/schema.md."""
        path = self.data_path / "schema.md"
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def write_schema(self, content: str) -> Path:
        """Write data/schema.md."""
        path = self.data_path / "schema.md"
        path.write_text(content, encoding="utf-8")
        self._commit([path], "[update] schema.md: schema updated")
        return path

    # --- Helpers ---

    def _validate_inside(self, path: Path, base: Path) -> None:
        """Ensure resolved path is inside base directory (path traversal guard)."""
        if not str(path.resolve()).startswith(str(base.resolve())):
            raise ValueError(f"Path traversal detected: {path} is outside {base}")

    def _safe_filename(self, name: str) -> str:
        """Sanitize filename."""
        name = re.sub(r"[^\w\s\-.]", "", name)
        name = re.sub(r"\s+", "-", name).strip("-")
        if not name:
            name = "untitled"
        if not name.endswith(".md"):
            name += ".md"
        return name.lower()

    def _build_tree(self, path: Path, prefix: str = "") -> dict:
        """Build a dict tree of directory structure."""
        result: dict[str, Any] = {"name": path.name, "type": "directory", "children": []}
        try:
            entries = sorted(path.iterdir(), key=lambda e: (not e.is_dir(), e.name))
        except PermissionError:
            return result

        for entry in entries:
            if entry.name.startswith("."):
                continue
            if entry.is_dir():
                result["children"].append(self._build_tree(entry))
            elif entry.suffix == ".md":
                result["children"].append({"name": entry.name, "type": "file"})
        return result
