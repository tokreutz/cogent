from Models.tool_definition import ToolDefinition

WRITE_TOOL_SYSTEM_PROMPT = """Writes content to an absolute file path (creates directories as needed).

Usage:
- Overwrites the existing file if one already exists at the path.
- Prefer using the Edit tool for surgical modifications to existing files; use Write mainly for creating new files or full rewrites.
- NEVER proactively create documentation files (*.md) or README files unless explicitly requested by the user.
- Only use emojis if the user explicitly requests it.
"""


import os

def write(file_path: str, content: str) -> str:
    """
    Write content to an absolute file path (creates dirs if needed).

    Args:
        file_path (str): Absolute path to write to.
        content (str): Content to write to the file.

    Returns:
        str: Success message if written, or an error message on failure.
    """

    if not file_path or not str(file_path).strip():
        return "Error: 'file_path' is required"
    if not os.path.isabs(file_path):
        return "Error: 'file_path' must be an absolute path"
    if content is None:
        return "Error: 'content' is required"

    overwrite = os.path.exists(file_path)

    try:
        dir_name = os.path.dirname(file_path)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return ("Overwrote file: " if overwrite else "Wrote new file: ") + file_path
    except Exception as e:
        return f"Error writing to file: {e}"


# Export a ToolDefinition preserving the original detailed usage prompt
write_tool_def = ToolDefinition(
    fn=write,
    usage_system_prompt=WRITE_TOOL_SYSTEM_PROMPT,
)