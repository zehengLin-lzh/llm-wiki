"""Lint worker: checks wiki health — orphan pages, dead links, missing summaries."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import structlog
import yaml

from app.core.file_ops import FileOps

log = structlog.get_logger()


class LintResult:
    def __init__(self):
        self.orphan_pages: list[str] = []
        self.dead_links: list[tuple[str, str]] = []  # (source_file, broken_link)
        self.missing_summaries: list[str] = []  # raw files without summaries
        self.total_wiki_files: int = 0
        self.total_raw_files: int = 0


class LintWorker:
    """Runs health checks on the wiki."""

    def __init__(self, file_ops: FileOps):
        self.file_ops = file_ops

    def run(self) -> LintResult:
        """Run all lint checks and return results."""
        result = LintResult()

        wiki_files = list(self.file_ops.wiki_path.rglob("*.md"))
        wiki_files = [f for f in wiki_files if not f.name.startswith(".") and "_reports" not in str(f)]
        result.total_wiki_files = len(wiki_files)

        raw_files = list(self.file_ops.raw_path.rglob("*.md"))
        result.total_raw_files = len(raw_files)

        # Build link graph
        all_wiki_rel = set()
        links_from: dict[str, list[str]] = {}
        links_to: dict[str, set[str]] = {}

        for f in wiki_files:
            rel = str(f.relative_to(self.file_ops.wiki_path))
            all_wiki_rel.add(rel)
            links_from[rel] = []
            content = f.read_text(encoding="utf-8")

            # Find markdown links
            for match in re.finditer(r'\[([^\]]*)\]\(([^)]+)\)', content):
                target = match.group(2)
                # Normalize relative paths
                target = self._resolve_link(rel, target)
                if target:
                    links_from[rel].append(target)
                    links_to.setdefault(target, set()).add(rel)

        # 1. Orphan pages: no incoming links (except index.md)
        for rel in all_wiki_rel:
            if rel == "index.md":
                continue
            if rel not in links_to or len(links_to[rel]) == 0:
                result.orphan_pages.append(rel)

        # 2. Dead links: point to non-existent files
        for source, targets in links_from.items():
            for target in targets:
                if target not in all_wiki_rel:
                    result.dead_links.append((source, target))

        # 3. Missing summaries: raw files without corresponding summary
        for raw_file in raw_files:
            fm = self._parse_frontmatter(raw_file)
            raw_id = fm.get("id", "")
            if not raw_id:
                continue
            # Check if summary exists
            expected_summary = f"summaries/{raw_id}-summary.md"
            if expected_summary not in all_wiki_rel:
                rel_raw = str(raw_file.relative_to(self.file_ops.raw_path))
                result.missing_summaries.append(rel_raw)

        log.info(
            "lint.complete",
            orphans=len(result.orphan_pages),
            dead_links=len(result.dead_links),
            missing_summaries=len(result.missing_summaries),
        )
        return result

    def generate_report(self, result: LintResult) -> str:
        """Generate a markdown lint report."""
        now = datetime.now(timezone.utc)
        lines = [
            f"# Lint Report — {now.strftime('%Y-%m-%d %H:%M UTC')}",
            "",
            f"**Wiki files**: {result.total_wiki_files}",
            f"**Raw files**: {result.total_raw_files}",
            "",
        ]

        # Orphans
        lines.append(f"## Orphan Pages ({len(result.orphan_pages)})")
        if result.orphan_pages:
            lines.append("Pages with no incoming links:")
            for p in result.orphan_pages:
                lines.append(f"- `{p}`")
        else:
            lines.append("None found.")
        lines.append("")

        # Dead links
        lines.append(f"## Dead Links ({len(result.dead_links)})")
        if result.dead_links:
            lines.append("Links pointing to non-existent files:")
            for src, target in result.dead_links:
                lines.append(f"- `{src}` → `{target}`")
        else:
            lines.append("None found.")
        lines.append("")

        # Missing summaries
        lines.append(f"## Missing Summaries ({len(result.missing_summaries)})")
        if result.missing_summaries:
            lines.append("Raw files without wiki summaries:")
            for r in result.missing_summaries:
                lines.append(f"- `{r}`")
        else:
            lines.append("All raw files have summaries.")

        return "\n".join(lines)

    def run_and_save(self) -> str:
        """Run lint and save report to wiki/_reports/."""
        result = self.run()
        report = self.generate_report(result)
        now = datetime.now(timezone.utc)
        filename = f"{now.strftime('%Y%m%d')}-lint.md"
        self.file_ops.write_wiki(f"_reports/{filename}", report, reason="lint report")
        return filename

    def _resolve_link(self, source: str, target: str) -> str | None:
        """Resolve a relative link to a wiki-relative path."""
        if target.startswith("http") or target.startswith("#"):
            return None
        # Strip anchors
        target = target.split("#")[0]
        if not target:
            return None
        # Resolve relative paths
        source_dir = str(Path(source).parent)
        if source_dir == ".":
            resolved = target
        else:
            resolved = str((Path(source_dir) / target).as_posix())
        # Normalize
        parts = []
        for p in resolved.split("/"):
            if p == "..":
                if parts:
                    parts.pop()
            elif p != ".":
                parts.append(p)
        return "/".join(parts)

    def _parse_frontmatter(self, path: Path) -> dict:
        content = path.read_text(encoding="utf-8")
        if not content.startswith("---"):
            return {}
        parts = content.split("---", 2)
        if len(parts) < 3:
            return {}
        try:
            return yaml.safe_load(parts[1]) or {}
        except yaml.YAMLError:
            return {}
