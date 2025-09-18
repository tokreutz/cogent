import os
from fnmatch import fnmatch

from models.tool_definition import ToolDefinition

LS_TOOL_SYSTEM_PROMPT = """Lists files and directories in a given path. The path parameter must be an absolute path, not a relative path. You can optionally provide an array of glob patterns to ignore with the ignore parameter. You should generally prefer the Glob and Search tools, if you know which directories to search.
"""

def ls(path: str, ignore: list[str] = None) -> str:
    """
    Lists files and directories in a given path.

    Args:
        path (str): The absolute path to the directory to list (must be absolute, not relative).
        ignore (list[str], optional): An array of glob patterns to ignore.

    Returns:
        str: A newline-separated listing of files and directories (directories marked with '/'), or an error message.
    """

    # Validate path
    if not path or not str(path).strip():
        return "Error: 'path' is required"
    if not os.path.isabs(path):
        return "Error: 'path' must be an absolute path"
    if not os.path.isdir(path):
        return f"Error: path '{path}' is not a directory"

    # Validate ignore
    if ignore is None:
        ignore = []
    elif not isinstance(ignore, (list, tuple)):
        return "Error: 'ignore' must be an array of glob patterns"

    try:
        entries = sorted(os.listdir(path))
        filtered = []
        for name in entries:
            full = os.path.join(path, name)
            skip = False
            for pat in ignore:
                # skip non-string patterns silently
                if not isinstance(pat, str):
                    continue
                # Match both the basename and the absolute path against the pattern.
                if fnmatch(name, pat) or fnmatch(full, pat):
                    skip = True
                    break
            if skip:
                continue
            # Mark directories with a trailing slash for clarity
            filtered.append(name + ("/" if os.path.isdir(full) else ""))

        if not filtered:
            return "No files or directories found"

        return "\n".join(filtered)
    except Exception as e:
        return f"Error running LS: {e}"

ls_tool_def = ToolDefinition(
    fn=ls,
    usage_system_prompt=LS_TOOL_SYSTEM_PROMPT
)