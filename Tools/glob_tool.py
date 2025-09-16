from Models.tool_definition import ToolDefinition

GLOB_TOOL_SYSTEM_PROMPT = """- Fast file pattern matching tool that works with any codebase size
- Supports glob patterns like "**/*.js" or "src/**/*.ts"
- Returns matching file paths sorted by modification time
- Use this tool when you need to find files by name patterns
- When you are doing an open ended search that may require multiple rounds of globbing and grepping, use the Agent tool instead
- You have the capability to call multiple tools in a single response. It is always better to speculatively perform multiple searches as a batch that are potentially useful.
"""


import glob as glob_
import os

def glob(pattern: str, path: str = None) -> str:
    """
    Find files matching a glob pattern.

    Args:
        pattern (str): Glob pattern to search for (required).
        path (str, optional): Directory to search in (omit to search current directory).

    Returns:
        str: A newline-separated list of matching file paths, or an error message.
    """

    # Validate pattern
    if not pattern or not str(pattern).strip():
        return "Error: 'pattern' is required"

    # Validate path if provided
    if path is not None:
        if str(path).strip().lower() in ("undefined", "null", ""):
            return "Error: omit the 'path' field to use the default directory; do not pass 'undefined' or 'null'"
        if not os.path.isdir(path):
            return f"Error: path '{path}' is not a valid directory"
        base_dir = path
    else:
        base_dir = "."

    try:
        # If pattern is absolute, use it directly; otherwise join with base_dir
        if os.path.isabs(pattern):
            search_pattern = pattern
        else:
            search_pattern = os.path.join(base_dir, pattern)

        matches = glob_.glob(search_pattern, recursive=True)
        if not matches:
            return "No matches found"

        # Filter out non-files (optional) and sort by modification time (newest first)
        # Keep directories too in case the pattern is meant to match them.
        matches = [m for m in matches if os.path.exists(m)]
        matches.sort(key=lambda p: os.path.getmtime(p), reverse=True)

        return "\n".join(matches)
    except Exception as e:
        return f"Error running Glob: {e}"


# Export a ToolDefinition preserving the original detailed usage prompt
glob_tool_def = ToolDefinition(
    fn=glob,
    usage_system_prompt=GLOB_TOOL_SYSTEM_PROMPT,
)