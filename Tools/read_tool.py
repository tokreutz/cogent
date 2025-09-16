from Models.tool_definition import ToolDefinition

READ_TOOL_SYSTEM_PROMPT = """Reads a file from the local filesystem. You can access any file directly by using this tool.
Assume this tool is able to read all files on the machine. If the User provides a path to a file assume that path is valid. It is okay to read a file that does not exist; an error will be returned.

Usage:
- The file_path parameter must be an absolute path, not a relative path
- By default, it reads up to 2000 lines starting from the beginning of the file
- You can optionally specify a line offset and limit (especially handy for long files), but it's recommended to read the whole file by not providing these parameters
- Any lines longer than 2000 characters will be truncated
- Results are returned using cat -n format, with line numbers starting at 1
- This tool allows Claude Code to read images (eg PNG, JPG, etc). When reading an image file the contents are presented visually as Claude Code is a multimodal LLM.
- This tool can read PDF files (.pdf). PDFs are processed page by page, extracting both text and visual content for analysis.
- This tool can read Jupyter notebooks (.ipynb files) and returns all cells with their outputs, combining code, text, and visualizations.
- You have the capability to call multiple tools in a single response. It is always better to speculatively read multiple files as a batch that are potentially useful. 
- You will regularly be asked to read screenshots. If the user provides a path to a screenshot ALWAYS use this tool to view the file at the path. This tool will work with all temporary file paths like /var/folders/123/abc/T/TemporaryItems/NSIRD_screencaptureui_ZfB1tD/Screenshot.png
- If you read a file that exists but has empty contents you will receive a system reminder warning in place of file contents.
"""


import os

def read(file_path: str, offset: int = None, limit: int = None) -> str:
    """
    Read: Return lines from an absolute file path.

    Args:
    - file_path (str): absolute path to the file to read
    - offset (int, optional): 1-based starting line number (>=1)
    - limit (int, optional): max number of lines to return (>=1)
    """

    # Validate file_path
    if not file_path or not str(file_path).strip():
        return "Error: 'file_path' is required"
    if not os.path.isabs(file_path):
        return "Error: 'file_path' must be an absolute path"

    # Normalize offset/limit defaults and validate
    if offset is None:
        offset = 1
    else:
        try:
            offset = int(offset)
        except Exception:
            return "Error: 'offset' must be an integer"
        if offset < 1:
            return "Error: 'offset' must be >= 1"

    if limit is None:
        limit = 2000
    else:
        try:
            limit = int(limit)
        except Exception:
            return "Error: 'limit' must be an integer"
        if limit < 1:
            return "Error: 'limit' must be >= 1"

    # If file exists but is empty, return the system reminder instead of contents
    try:
        if os.path.exists(file_path) and os.path.getsize(file_path) == 0:
            return "Reminder: file exists but is empty"
    except Exception:
        # If stat fails for some reason, we'll let the attempt to open handle errors below.
        pass

    MAX_LINE_LEN = 2000
    collected = []
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            # Iterate lines without loading whole file into memory
            start = offset
            end = offset + limit - 1
            out_index = 1  # numbering in returned chunk starts at 1
            for lineno, raw_line in enumerate(f, start=1):
                if lineno < start:
                    continue
                if lineno > end:
                    break
                # Remove trailing newline to present clean numbered lines
                line = raw_line.rstrip("\n")
                if len(line) > MAX_LINE_LEN:
                    line = line[:MAX_LINE_LEN]
                # Emulate `cat -n` formatting: right-aligned width similar to cat -n
                collected.append(f"{out_index:6}\t{line}")
                out_index += 1

        if not collected:
            return "<system-reminder>no lines read (file may be empty or offset exceeds file length)</system-reminder>"

        return "\n".join(collected)
    except FileNotFoundError:
        return f"Error: file not found: {file_path}"
    except Exception as e:
        return f"Error reading file: {e}"


# Export a ToolDefinition preserving the original detailed usage prompt
read_tool_def = ToolDefinition(
    fn=read,
    usage_system_prompt=READ_TOOL_SYSTEM_PROMPT,
)