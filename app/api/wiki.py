"""Wiki browsing API endpoints."""

from __future__ import annotations

import re

from fastapi import APIRouter, Query

from app.core.file_ops import FileOps

router = APIRouter(prefix="/api/wiki", tags=["wiki"])

_file_ops: FileOps | None = None


def init_wiki_router(file_ops: FileOps) -> None:
    global _file_ops
    _file_ops = file_ops


def _ops() -> FileOps:
    assert _file_ops is not None, "FileOps not initialized"
    return _file_ops


@router.get("/tree")
async def wiki_tree():
    """Return wiki directory tree as JSON."""
    return _ops().wiki_tree()


@router.get("/file")
async def wiki_file(path: str = Query(..., description="Path relative to wiki/")):
    """Return raw markdown content of a wiki file."""
    content = _ops().read_wiki(path)
    if not content:
        return {"ok": False, "error": f"File not found: {path}"}
    return {"ok": True, "path": path, "content": content}


@router.get("/rendered")
async def wiki_rendered(path: str = Query(..., description="Path relative to wiki/")):
    """Return wiki file rendered as simple HTML."""
    content = _ops().read_wiki(path)
    if not content:
        return {"ok": False, "error": f"File not found: {path}"}

    # Strip frontmatter
    body = content
    if body.startswith("---"):
        parts = body.split("---", 2)
        if len(parts) >= 3:
            body = parts[2].strip()

    html = _markdown_to_html(body)
    return {"ok": True, "path": path, "html": html, "raw": content}


def _markdown_to_html(md: str) -> str:
    """Simple markdown to HTML conversion."""
    lines = md.split("\n")
    html_lines = []
    in_code = False
    in_list = False

    for line in lines:
        # Code blocks
        if line.strip().startswith("```"):
            if in_code:
                html_lines.append("</code></pre>")
                in_code = False
            else:
                lang = line.strip()[3:]
                html_lines.append(f'<pre><code class="lang-{lang}">')
                in_code = True
            continue
        if in_code:
            html_lines.append(_esc(line))
            continue

        # Close list if needed
        if in_list and not line.strip().startswith("- "):
            html_lines.append("</ul>")
            in_list = False

        # Headings
        if line.startswith("### "):
            html_lines.append(f"<h4>{_inline(_esc(line[4:]))}</h4>")
        elif line.startswith("## "):
            html_lines.append(f"<h3>{_inline(_esc(line[3:]))}</h3>")
        elif line.startswith("# "):
            html_lines.append(f"<h2>{_inline(_esc(line[2:]))}</h2>")
        elif line.strip().startswith("- "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{_inline(_esc(line.strip()[2:]))}</li>")
        elif line.strip() == "":
            html_lines.append("<br>")
        else:
            html_lines.append(f"<p>{_inline(_esc(line))}</p>")

    if in_list:
        html_lines.append("</ul>")
    if in_code:
        html_lines.append("</code></pre>")

    return "\n".join(html_lines)


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _inline(text: str) -> str:
    """Process inline markdown: bold, italic, code, links."""
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="#" onclick="viewWikiLink(\'\2\')">\1</a>', text)
    return text
