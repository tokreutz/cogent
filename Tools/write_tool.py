from Models.tool_definition import ToolDefinition

WRITE_TOOL_SYSTEM_PROMPT = """Writes a file to the local filesystem.

Usage:
- This tool will overwrite the existing file if there is one at the provided path.
- If this is an existing file, you MUST use the Read tool first to read the file's contents. This tool will fail if you did not read the file first.
- ALWAYS prefer editing existing files in the codebase. NEVER write new files unless explicitly required.
- NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.
- Only use emojis if the user explicitly requests it. Avoid writing emojis to files unless asked.
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

    # Check if file exists and require Read tool to have been used first
    if os.path.exists(file_path):
        # This is a simple check - in a more sophisticated implementation,
        # you might track which files have been read in the current session
        return "Error: file already exists. You MUST use the Read tool first to read the existing file's contents before overwriting it."

    try:
        dir_name = os.path.dirname(file_path)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Wrote to file: {file_path}"
    except Exception as e:
        return f"Error writing to file: {e}"


# Export a ToolDefinition preserving the original detailed usage prompt
write_tool_def = ToolDefinition(
    fn=write,
    usage_system_prompt=WRITE_TOOL_SYSTEM_PROMPT,
)