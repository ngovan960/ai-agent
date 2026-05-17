"""Tool Schema Definitions — structured JSON Schema for LLM tool calling (Fix #3)

Defines the exact input/output schemas for every tool available to agents,
preventing hallucination and format drift.
"""

from typing import Any

TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "read_file": {
        "description": "Read the contents of a file. Returns None if file doesn't exist.",
        "input": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative or absolute path to the file",
                },
            },
            "required": ["path"],
        },
        "output": {
            "type": "string",
            "nullable": True,
            "description": "File contents as string, or None if not found",
        },
    },
    "write_file": {
        "description": "Write content to a file. Creates parent directories if needed.",
        "input": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative or absolute path to the file",
                },
                "content": {
                    "type": "string",
                    "description": "Full content to write to the file",
                },
            },
            "required": ["path", "content"],
        },
        "output": {
            "type": "boolean",
            "description": "True if write was successful",
        },
    },
    "edit_file": {
        "description": "Replace old_string with new_string in a file. Returns False if old_string not found.",
        "input": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative or absolute path to the file",
                },
                "old_string": {
                    "type": "string",
                    "description": "Exact existing text to replace (case-sensitive, include exact whitespace)",
                },
                "new_string": {
                    "type": "string",
                    "description": "New text to insert in place of old_string",
                },
            },
            "required": ["path", "old_string", "new_string"],
        },
        "output": {
            "type": "boolean",
            "description": "True if edit was successful",
        },
    },
    "run_bash": {
        "description": "Run a bash command. Returns stdout, stderr, and exit code.",
        "input": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Bash command to execute",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Command timeout in seconds",
                    "default": 60,
                },
            },
            "required": ["command"],
        },
        "output": {
            "type": "object",
            "properties": {
                "stdout": {"type": "string"},
                "stderr": {"type": "string"},
                "exit_code": {"type": "integer"},
                "success": {"type": "boolean"},
            },
        },
    },
    "grep": {
        "description": "Search for a regex pattern in file contents.",
        "input": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Regex pattern to search for",
                },
                "include": {
                    "type": "string",
                    "description": "File glob pattern to filter (e.g. '*.py')",
                },
                "path": {
                    "type": "string",
                    "description": "Directory to search in",
                },
            },
            "required": ["pattern"],
        },
        "output": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "file": {"type": "string"},
                    "line": {"type": "integer"},
                    "content": {"type": "string"},
                },
            },
        },
    },
    "glob": {
        "description": "List files matching a glob pattern.",
        "input": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern (e.g. '**/*.py')",
                },
            },
            "required": ["pattern"],
        },
        "output": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of matching file paths",
        },
    },
}

TOOL_NAMES = list(TOOL_SCHEMAS.keys())


def get_tool_schema(tool_name: str) -> dict[str, Any] | None:
    """Get schema for a specific tool."""
    return TOOL_SCHEMAS.get(tool_name)


def get_all_tool_schemas() -> dict[str, dict[str, Any]]:
    """Get all tool schemas for LLM function calling definitions."""
    return dict(TOOL_SCHEMAS)


def format_tools_for_llm() -> list[dict[str, Any]]:
    """Format tool schemas in OpenAI/Anthropic-compatible format."""
    tools = []
    for name, schema in TOOL_SCHEMAS.items():
        tools.append({
            "type": "function",
            "function": {
                "name": name,
                "description": schema["description"],
                "parameters": schema["input"],
            },
        })
    return tools
