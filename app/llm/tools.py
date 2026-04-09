"""Tool definitions for the LLM compiler and query engine."""

from __future__ import annotations

# --- Compiler Tools (read + write) ---

COMPILER_TOOLS = [
    {
        "name": "read_wiki_file",
        "description": "Read the contents of an existing wiki file. Returns the full markdown content including frontmatter.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path relative to wiki/, e.g. 'index.md' or 'concepts/python.md'",
                }
            },
            "required": ["path"],
        },
    },
    {
        "name": "list_wiki_directory",
        "description": "List all markdown files in a wiki subdirectory. Returns filenames.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Subdirectory relative to wiki/, e.g. 'concepts' or 'entities'. Use '' for root.",
                }
            },
            "required": ["path"],
        },
    },
    {
        "name": "create_wiki_file",
        "description": "Create a new wiki file. Fails if file already exists — use update_wiki_file for existing files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path relative to wiki/, e.g. 'concepts/fastapi.md'",
                },
                "frontmatter": {
                    "type": "string",
                    "description": "YAML frontmatter content (without --- delimiters)",
                },
                "content": {
                    "type": "string",
                    "description": "Markdown body content",
                },
            },
            "required": ["path", "frontmatter", "content"],
        },
    },
    {
        "name": "update_wiki_file",
        "description": "Overwrite an existing wiki file with new content. Use this to update pages with new information.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path relative to wiki/, e.g. 'index.md'",
                },
                "frontmatter": {
                    "type": "string",
                    "description": "YAML frontmatter content (without --- delimiters)",
                },
                "content": {
                    "type": "string",
                    "description": "Full markdown body content (replaces everything)",
                },
            },
            "required": ["path", "frontmatter", "content"],
        },
    },
    {
        "name": "append_to_wiki_file",
        "description": "Append content to the end of an existing wiki file. Useful for adding entries to index or lists.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path relative to wiki/, e.g. 'index.md'",
                },
                "content": {
                    "type": "string",
                    "description": "Content to append at the end",
                },
            },
            "required": ["path", "content"],
        },
    },
]

# --- Query Tools (read-only) ---

QUERY_TOOLS = [
    {
        "name": "read_wiki_file",
        "description": "Read the contents of a wiki file. Returns the full markdown content.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path relative to wiki/, e.g. 'index.md' or 'concepts/python.md'",
                }
            },
            "required": ["path"],
        },
    },
    {
        "name": "list_wiki_directory",
        "description": "List all markdown files in a wiki subdirectory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Subdirectory relative to wiki/, e.g. 'concepts', 'entities', ''. Use '' for root.",
                }
            },
            "required": ["path"],
        },
    },
    {
        "name": "grep_wiki",
        "description": "Search wiki files for a keyword or pattern. Returns matching lines with file paths.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Search pattern (case-insensitive regex supported)",
                }
            },
            "required": ["pattern"],
        },
    },
]
