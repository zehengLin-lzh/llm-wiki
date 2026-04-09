"""Query engine: answers questions by reading the wiki via LLM tool calls."""

from __future__ import annotations

import json
from typing import Any, AsyncIterator

import structlog

from app.core.file_ops import FileOps
from app.llm.base import BaseLLMProvider
from app.llm.tools import QUERY_TOOLS

log = structlog.get_logger()

QUERY_SYSTEM_PROMPT = """\
You are a research assistant for the user's personal wiki. Your job is to answer questions by reading the wiki files.

Tools available: read_wiki_file, list_wiki_directory, grep_wiki.

## IMPORTANT: Always read files before answering
You MUST use read_wiki_file to read relevant wiki pages BEFORE answering.
The wiki state provided in the user message shows what files exist — use the tools to read their full content.
Do NOT answer based only on file names or the index — always read the actual pages.

## Workflow
1. Look at the wiki state to identify relevant files
2. Use read_wiki_file to read those files (e.g. read_wiki_file with path "entities/fastapi.md")
3. Use grep_wiki if you need to search for keywords
4. Answer based on the content you read, citing sources as [wiki/path/file.md]
5. If the wiki genuinely doesn't have info on the topic, say so

## Rules
- ALWAYS read at least one wiki file before answering
- Cite the wiki files you used
- Keep answers concise and direct
- Never fabricate content not found in wiki files
"""

MAX_QUERY_ROUNDS = 10


class QueryEvent:
    """Events yielded during query processing."""

    def __init__(self, type: str, data: Any = None):
        self.type = type  # tool_call_started, tool_call_finished, token, done, error
        self.data = data

    def to_dict(self) -> dict:
        return {"type": self.type, "data": self.data}


class QueryEngine:
    """Answers questions by reading the wiki via LLM tool calls."""

    def __init__(self, file_ops: FileOps):
        self.file_ops = file_ops

    def _build_context(self) -> str:
        """Pre-load wiki index and structure so the LLM has context from the start."""
        parts = []

        # Index content
        index = self.file_ops.read_wiki("index.md")
        if index:
            parts.append(f"## Current wiki/index.md\n\n{index}")

        # Wiki file listing
        for subdir in ["concepts", "entities", "summaries"]:
            files = self.file_ops.list_wiki(subdir)
            if files:
                names = [f.name for f in files]
                parts.append(f"wiki/{subdir}/: {', '.join(names)}")

        return "\n\n".join(parts) if parts else "(Wiki is empty)"

    async def query(
        self,
        user_message: str,
        history: list[dict],
        provider: BaseLLMProvider,
    ) -> AsyncIterator[QueryEvent]:
        """Process a query, yielding events as they happen."""

        # Pre-load wiki context so LLM has something to work with immediately
        context = self._build_context()
        augmented_message = (
            f"{user_message}\n\n"
            f"---\n"
            f"Here is the current wiki state for reference:\n\n{context}\n\n"
            f"Use the tools to read specific wiki files for detailed information before answering."
        )

        # Build messages: history + new message
        messages = list(history) + [{"role": "user", "content": augmented_message}]

        try:
            for round_num in range(MAX_QUERY_ROUNDS):
                result = await provider.tool_call(
                    messages=messages,
                    tools=QUERY_TOOLS,
                    system=QUERY_SYSTEM_PROMPT,
                )

                # If there are tool calls, execute them
                if result.tool_calls:
                    # Build assistant message
                    assistant_content = []
                    if result.text:
                        assistant_content.append({"type": "text", "text": result.text})
                    for tc in result.tool_calls:
                        assistant_content.append({
                            "type": "tool_use",
                            "id": tc.id,
                            "name": tc.name,
                            "input": tc.input,
                        })
                    messages.append({"role": "assistant", "content": assistant_content})

                    # Execute tools and yield events
                    tool_results = []
                    for tc in result.tool_calls:
                        yield QueryEvent("tool_call_started", {
                            "name": tc.name,
                            "args": tc.input,
                        })
                        output = self._execute_tool(tc.name, tc.input)
                        preview = output[:150] + "..." if len(output) > 150 else output
                        yield QueryEvent("tool_call_finished", {
                            "name": tc.name,
                            "preview": preview,
                        })
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tc.id,
                            "content": output,
                        })
                    messages.append({"role": "user", "content": tool_results})
                    continue

                # No tool calls — this is the final answer
                if result.text:
                    yield QueryEvent("token", result.text)
                yield QueryEvent("done", {"rounds": round_num + 1})
                return

            # Exceeded max rounds
            yield QueryEvent("error", "Query exceeded maximum tool call rounds")

        except Exception as e:
            log.error("query.error", error=str(e))
            yield QueryEvent("error", str(e))

    def _execute_tool(self, name: str, args: dict) -> str:
        """Execute a read-only query tool."""
        try:
            if name == "read_wiki_file":
                path = args.get("path", "")
                content = self.file_ops.read_wiki(path)
                if not content:
                    return f"File wiki/{path} does not exist or is empty."
                return content

            elif name == "list_wiki_directory":
                path = args.get("path", "")
                files = self.file_ops.list_wiki(path)
                if not files:
                    return f"Directory wiki/{path} is empty or does not exist."
                return "\n".join(f.name for f in files)

            elif name == "grep_wiki":
                pattern = args.get("pattern", "")
                results = self.file_ops.grep_wiki(pattern)
                if not results:
                    return f"No matches found for '{pattern}'."
                lines = []
                for fpath, line in results[:20]:
                    rel = fpath.relative_to(self.file_ops.wiki_path)
                    lines.append(f"wiki/{rel}: {line}")
                return "\n".join(lines)

            else:
                return f"Unknown tool: {name}"

        except Exception as e:
            return f"Error: {e}"
