from models.tool_definition import ToolDefinition

EDIT_TOOL_SYSTEM_PROMPT = """Performs exact string replacements in files. 

Usage:
- You must use your `Read` tool at least once in the conversation before editing. This tool will error if you attempt an edit without reading the file. 
- When editing text from Read tool output, ensure you preserve the exact indentation (tabs/spaces) as it appears AFTER the line number prefix. The line number prefix format is: spaces + line number + tab. Everything after that tab is the actual file content to match. Never include any part of the line number prefix in the old_string or new_string.
- ALWAYS prefer editing existing files in the codebase. NEVER write new files unless explicitly required.
- Only use emojis if the user explicitly requests it. Avoid adding emojis to files unless asked.
- The edit will FAIL if `old_string` is not unique in the file. Either provide a larger string with more surrounding context to make it unique or use `replace_all` to change every instance of `old_string`. 
- Use `replace_all` for replacing and renaming strings across the file. This parameter is useful if you want to rename a variable for instance.
    """


def edit(
        file_path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
    ) -> str:
    """
    Perform exact string replacement in an existing file.

    Args:
        file_path (str): Absolute path to an existing file.
        old_string (str): The exact substring to replace.
        new_string (str): The replacement string.
        replace_all (bool): If True, replace all occurrences; otherwise replace a single occurrence.

    Returns:
        str: A success message indicating how many occurrences were replaced, or an error message on failure.
    """
    import os

    # Basic validation
    if not file_path or not str(file_path).strip():
        return "Error: 'file_path' is required"
    if not os.path.isabs(file_path):
        return "Error: 'file_path' must be an absolute path"
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        return f"Error: file does not exist: {file_path}"

    if old_string is None or new_string is None:
        return "Error: both 'old_string' and 'new_string' are required"
    if old_string == new_string:
        return "Error: 'new_string' must be different from 'old_string'"

    # Reject accidental inclusion of line-number prefix in supplied strings.
    # The prefix format to detect: optional spaces + digits + tab
    def _looks_like_prefix(s: str) -> bool:
        if not s:
            return False
        # If the string starts with something like "   12\t" or contains "\n   12\t",
        # it's likely the user pasted Read tool output including the numbering.
        if s.lstrip().startswith("\t"):
            # weird but treat as prefix-present
            return True
        # check beginning of string
        first_line = s.splitlines()[0]
        # if there is a leading tab and what precedes it are digits (maybe with spaces)
        if "\t" in first_line:
            left, _ = first_line.split("\t", 1)
            if left.strip().isdigit():
                return True
        # also detect occurrences of "\n<spaces><digits>\t" anywhere
        for part in ("\\n", "\n"):
            if part in s:
                for line in s.splitlines():
                    if line.lstrip().split("\t", 1)[0].strip().isdigit():
                        return True
        return False

    if _looks_like_prefix(old_string) or _looks_like_prefix(new_string):
        return (
            "Error: do not include the Read tool's line-number prefix in "
            "'old_string' or 'new_string'. Remove the leading '<spaces><line-number>\\t' "
            "from any pasted Read output and try again."
        )

    # Load raw file content for exact replacement (we called Read to comply with the requirement)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return f"Error: failed to open file for editing: {e}"

    # Count exact occurrences
    occurrences = content.count(old_string)
    if occurrences == 0:
        return "Error: 'old_string' not found in the file. Make it more specific or check the exact indentation/whitespace."

    if occurrences > 1 and not replace_all:
        return (
            f"Error: 'old_string' is not unique in the file (found {occurrences} occurrences). "
            "Provide more surrounding context in 'old_string' to make it unique, or set 'replace_all' to true to replace every instance."
        )

    # Perform the replacement
    try:
        if replace_all:
            new_content = content.replace(old_string, new_string)
            replaced = occurrences
        else:
            # replace a single occurrence
            new_content = content.replace(old_string, new_string, 1)
            replaced = 1
        # Write back to the same file (do not create new files)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
    except Exception as e:
        return f"Error: failed to write changes to file: {e}"

    return f"Replaced {replaced} occurrence(s) in {file_path}"


# Export a ToolDefinition preserving the original detailed usage prompt
edit_tool_def = ToolDefinition(
    fn=edit,
    usage_system_prompt=EDIT_TOOL_SYSTEM_PROMPT,
)