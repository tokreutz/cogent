from Models.tool_definition import ToolDefinition

GREP_TOOL_SYSTEM_PROMPT = """A powerful search tool built on ripgrep

  Usage:
  - ALWAYS use Grep for search tasks. NEVER invoke `grep` or `rg` as a Bash command. The Grep tool has been optimized for correct permissions and access.
  - Supports full regex syntax (e.g., "log.*Error", "function\s+\w+")
  - Filter files with glob parameter (e.g., "*.js", "**/*.tsx") or type parameter (e.g., "js", "py", "rust")
  - Output modes: "content" shows matching lines, "files_with_matches" shows only file paths (default), "count" shows match counts
  - Use Task tool for open-ended searches requiring multiple rounds
  - Pattern syntax: Uses ripgrep (not grep) - literal braces need escaping (use `interface\{\}` to find `interface{}` in Go code)
  - Multiline matching: By default patterns match within single lines only. For cross-line patterns like `struct \{[\s\S]*?field`, use `multiline: true`
"""


import subprocess

def grep(
        pattern: str,
        path: str = ".",
        glob: str = "",
        output_mode: str = "files_with_matches",
        B: int = 0,
        A: int = 0,
        C: int = 0,
        n: bool = False,
        i: bool = False,
        type: str = "",
        head_limit: int = 0,
        multiline: bool = False,
        **kwargs,
    ) -> str:
    """
    Search files using ripgrep (rg).

    Args:
        pattern (str): Regex or string pattern to search for (required).
        path (str): Directory or file path to search (default: '.').
        glob (str): Comma-separated glob patterns to filter files.
        output_mode (str): One of 'content', 'files_with_matches', 'count'.
        B (int): Number of lines of context before matches.
        A (int): Number of lines of context after matches.
        C (int): Number of lines of context around matches (overrides A/B).
        n (bool): Include line numbers in content output.
        i (bool): Case-insensitive search.
        type (str): Ripgrep file type filter.
        head_limit (int): Limit output lines.
        multiline (bool): Enable multiline/dotall mode.
        **kwargs: Additional optional flags (accepts hyphenated names like '-B').

    Returns:
        str: Ripgrep output according to output_mode, or an error message.
    """

    # Accept hyphenated names if the caller sent them (e.g. "-B": 3)
    if "-B" in kwargs:
        try:
            B = int(kwargs["-B"])
        except Exception:
            pass
    if "-A" in kwargs:
        try:
            A = int(kwargs["-A"])
        except Exception:
            pass
    if "-C" in kwargs:
        try:
            C = int(kwargs["-C"])
        except Exception:
            pass
    if "-n" in kwargs:
        n = bool(kwargs["-n"])
    if "-i" in kwargs:
        i = bool(kwargs["-i"])
    if "type" in kwargs and not type:
        type = kwargs.get("type", type)

    if not pattern:
        return "Error: 'pattern' is required"

    output_mode = (output_mode or "files_with_matches").lower()
    if output_mode not in ("content", "files_with_matches", "count"):
        output_mode = "files_with_matches"

    cmd = ["rg", "--no-heading"]

    # Output mode selection
    if output_mode == "files_with_matches":
        cmd += ["-l"]
    elif output_mode == "count":
        cmd += ["-c"]
    elif output_mode == "content":
        # context flags; -C overrides -A/-B if provided
        if C and C > 0:
            cmd += ["-C", str(int(C))]
        else:
            if B and B > 0:
                cmd += ["-B", str(int(B))]
            if A and A > 0:
                cmd += ["-A", str(int(A))]
        if n:
            cmd += ["-n"]

    if i:
        cmd += ["-i"]

    if type:
        cmd += ["--type", type]

    if glob:
        # Allow multiple comma-separated globs by passing them as separate --glob flags
        # but many callers will pass one pattern like "*.js" or "**/*.ts"
        for g in (g.strip() for g in glob.split(",") if g.strip()):
            cmd += ["--glob", g]

    if multiline:
        # Enable multiline search and dot matches newline mode per description
        cmd += ["-U", "--multiline-dotall"]

    # Safety: put -- after options to ensure pattern beginning with '-' is treated as pattern
    cmd += ["--", pattern]
    if path:
        cmd += [path]

    try:
        # NEVER run via shell; invoke rg directly for correct permissions/access
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        out = (result.stdout or "") + (result.stderr or "")
        if not out:
            return "No matches found"

        # Apply head_limit (limit output lines / entries) without invoking a shell pipeline
        if head_limit and head_limit > 0:
            lines = out.splitlines()
            limited = lines[: int(head_limit)]
            out = "\n".join(limited)

        return out
    except FileNotFoundError:
        return "Error: ripgrep (`rg`) not found on PATH. Please install ripgrep."
    except Exception as e:
        return f"Error running grep: {e}"


# Export a ToolDefinition preserving the original detailed usage prompt
grep_tool_def = ToolDefinition(
    fn=grep,
    usage_system_prompt=GREP_TOOL_SYSTEM_PROMPT,
)