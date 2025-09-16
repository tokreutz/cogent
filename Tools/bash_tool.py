from pydantic_ai import RunContext

from Models.agent_deps import AgentDeps
from Models.tool_definition import ToolDefinition

BASH_TOOL_SYSTEM_PROMPT = """Executes a given bash command in a persistent shell session with optional timeout, ensuring proper handling and security measures.

Before executing the command, please follow these steps:

1. Directory Verification:
   - If the command will create new directories or files, first use the LS tool to verify the parent directory exists and is the correct location
   - For example, before running "mkdir foo/bar", first use LS to check that "foo" exists and is the intended parent directory

2. Command Execution:
   - Always quote file paths that contain spaces with double quotes (e.g., cd "path with spaces/file.txt")
   - Examples of proper quoting:
     - cd "/Users/name/My Documents" (correct)
     - cd /Users/name/My Documents (incorrect - will fail)
     - python "/path/with spaces/script.py" (correct)
     - python /path/with spaces/script.py (incorrect - will fail)
   - After ensuring proper quoting, execute the command.
   - Capture the output of the command.

Usage notes:
  - The command argument is required.
  - You can specify an optional timeout in milliseconds (up to 600000ms / 10 minutes). If not specified, commands will timeout after 120000ms (2 minutes).
  - It is very helpful if you write a clear, concise description of what this command does in 5-10 words.
  - If the output exceeds 30000 characters, output will be truncated before being returned to you.
  - VERY IMPORTANT: You MUST avoid using search commands like `find` and `grep`. Instead use Grep, Glob, or Task to search. You MUST avoid read tools like `cat`, `head`, `tail`, and `ls`, and use Read and LS to read files.
 - If you _still_ need to run `grep`, STOP. ALWAYS USE ripgrep at `rg` first, which all Cogent users have pre-installed.
  - When issuing multiple commands, use the ';' or '&&' operator to separate them. DO NOT use newlines (newlines are ok in quoted strings).
  - Try to maintain your current working directory throughout the session by using absolute paths and avoiding usage of `cd`. You may use `cd` if the User explicitly requests it.
    <good-example>
    pytest /foo/bar/tests
    </good-example>
    <bad-example>
    cd /foo/bar && pytest tests
    </bad-example>




# Committing changes with git

When the user asks you to create a new git commit, follow these steps carefully:

1. You have the capability to call multiple tools in a single response. When multiple independent pieces of information are requested, batch your tool calls together for optimal performance. ALWAYS run the following bash commands in parallel, each using the Bash tool:
  - Run a git status command to see all untracked files.
  - Run a git diff command to see both staged and unstaged changes that will be committed.
  - Run a git log command to see recent commit messages, so that you can follow this repository's commit message style.
2. Analyze all staged changes (both previously staged and newly added) and draft a commit message:
  - Summarize the nature of the changes (eg. new feature, enhancement to an existing feature, bug fix, refactoring, test, docs, etc.). Ensure the message accurately reflects the changes and their purpose (i.e. "add" means a wholly new feature, "update" means an enhancement to an existing feature, "fix" means a bug fix, etc.).
  - Check for any sensitive information that shouldn't be committed
  - Draft a concise (1-2 sentences) commit message that focuses on the "why" rather than the "what"
  - Ensure it accurately reflects the changes and their purpose
3. You have the capability to call multiple tools in a single response. When multiple independent pieces of information are requested, batch your tool calls together for optimal performance. ALWAYS run the following commands in parallel:
   - Add relevant untracked files to the staging area.
   - Create the commit with a message ending with:
   🤖 Generated with Cogent

   Co-Authored-By: Cogent
   - Run git status to make sure the commit succeeded.
4. If the commit fails due to pre-commit hook changes, retry the commit ONCE to include these automated changes. If it fails again, it usually means a pre-commit hook is preventing the commit. If the commit succeeds but you notice that files were modified by the pre-commit hook, you MUST amend your commit to include them.

Important notes:
- NEVER update the git config
- NEVER run additional commands to read or explore code, besides git bash commands
- NEVER use the TodoWrite or Task tools
- DO NOT push to the remote repository unless the user explicitly asks you to do so
- IMPORTANT: Never use git commands with the -i flag (like git rebase -i or git add -i) since they require interactive input which is not supported.
- If there are no changes to commit (i.e., no untracked files and no modifications), do not create an empty commit
- In order to ensure good formatting, ALWAYS pass the commit message via a HEREDOC, a la this example:
<example>
git commit -m "$(cat <<'EOF'
   Commit message here.

   🤖 Generated with Cogent

   Co-Authored-By: Cogent
   EOF
   )"
</example>

# Creating pull requests
Use the gh command via the Bash tool for ALL GitHub-related tasks including working with issues, pull requests, checks, and releases. If given a Github URL use the gh command to get the information needed.

IMPORTANT: When the user asks you to create a pull request, follow these steps carefully:

1. You have the capability to call multiple tools in a single response. When multiple independent pieces of information are requested, batch your tool calls together for optimal performance. ALWAYS run the following bash commands in parallel using the Bash tool, in order to understand the current state of the branch since it diverged from the main branch:
   - Run a git status command to see all untracked files
   - Run a git diff command to see both staged and unstaged changes that will be committed
   - Check if the current branch tracks a remote branch and is up to date with the remote, so you know if you need to push to the remote
   - Run a git log command and `git diff [base-branch]...HEAD` to understand the full commit history for the current branch (from the time it diverged from the base branch)
2. Analyze all changes that will be included in the pull request, making sure to look at all relevant commits (NOT just the latest commit, but ALL commits that will be included in the pull request!!!), and draft a pull request summary
3. You have the capability to call multiple tools in a single response. When multiple independent pieces of information are requested, batch your tool calls together for optimal performance. ALWAYS run the following commands in parallel:
   - Create new branch if needed
   - Push to remote with -u flag if needed
   - Create PR using gh pr create with the format below. Use a HEREDOC to pass the body to ensure correct formatting.
<example>
gh pr create --title "the pr title" --body "$(cat <<'EOF'
## Summary
<1-3 bullet points>

## Test plan
[Checklist of TODOs for testing the pull request...]

🤖 Generated with Cogent
EOF
)"
</example>

Important:
- NEVER update the git config
- DO NOT use the TodoWrite or Task tools
- Return the PR URL when you're done, so the user can see it

# Other common operations
- View comments on a Github PR: gh api repos/foo/bar/pulls/123/comments
"""

def bash(ctx: RunContext[AgentDeps], command: str, timeout_ms: int = None) -> str:
    """
    Executes a given bash command in a (lightweight) persistent session.

    Args:
        ctx (RunContext[AgentDeps]): Execution context providing dependencies and runtime info.
        command (str): The bash command to execute. Required.
        timeout_ms (int, optional): Maximum time in milliseconds to allow the command to run. Defaults to 120000 (2 minutes).

    Returns:
        str: Description of the command and its output, or an error message on failure.
    """
    import os
    import re
    import shlex
    import subprocess

    # Validation: command required
    if not command or not str(command).strip():
        return "Error: 'command' is required"

    _bash_session = ctx.deps.bash_session

    # Normalize timeout
    DEFAULT_MS = 120_000
    MAX_MS = 600_000
    if timeout_ms is None:
        timeout_ms = DEFAULT_MS
    else:
        try:
            timeout_ms = int(timeout_ms)
        except Exception:
            return "Error: timeout_ms must be an integer number of milliseconds"
        if timeout_ms <= 0 or timeout_ms > MAX_MS:
            return f"Error: timeout_ms must be between 1 and {MAX_MS} milliseconds"

    timeout_sec = timeout_ms / 1000.0

    # Security: forbid direct use of common search/read utilities that we
    # want callers to use the specialized tools for.
    forbidden_cmds = ("grep", "find", "cat", "head", "tail", "ls")
    for fcmd in forbidden_cmds:
        # match standalone word (basic safety)
        if re.search(rf"(^|\s){re.escape(fcmd)}(\s|$|;|&&|\||\))", command):
            return (
                f"Error: use of `{fcmd}` is not allowed in this tool. "
                "Please use Grep, Glob, Task, Read, or LS tools instead."
            )

    # Detect unquoted absolute/relative paths that contain spaces.
    # Example matched string: /Users/name/My Documents
    # We require such paths be quoted with double quotes.
    # This heuristic looks for a slash followed by a sequence that contains whitespace
    # and is not already enclosed in single/double quotes.
    if re.search(r'(?<!["\'])/(?:[^"\n]*\s+[^"\n]*)', command):
        return (
            "Error: detected an unquoted path containing spaces. "
            "Always wrap file paths that contain spaces in double quotes. "
            "Example: cd \"/Users/name/My Documents\""
        )

    # Tokenize the command safely (this will respect existing quoting)
    try:
        tokens = shlex.split(command, posix=True)
    except Exception:
        return "Error: failed to parse command. Ensure proper quoting of arguments."

    if not tokens:
        return "Error: no command tokens found"

    # For commands that create files or directories, verify parent directories exist.
    # We handle common create operations like `mkdir` and `touch`.
    # (This is a best-effort check; more complex commands are not analyzed.)
    def _verify_parent_exists(path_candidate: str) -> tuple[bool, str]:
        # Expand user and vars, but do not resolve symlinks.
        expanded = os.path.expanduser(os.path.expandvars(path_candidate))
        parent = os.path.dirname(expanded) or "."
        # If parent is relative and we have a session cwd, resolve against it.
        if not os.path.isabs(parent) and _bash_session["cwd"]:
            parent = os.path.normpath(os.path.join(_bash_session["cwd"], parent))
        exists = os.path.isdir(parent)
        return exists, parent

    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t in ("mkdir", "touch"):
            # collect subsequent non-option tokens as potential paths
            j = i + 1
            while j < len(tokens) and tokens[j].startswith("-"):
                j += 1
            if j >= len(tokens):
                return f"Error: '{t}' requires a target path argument"
            # handle multiple targets: all remaining tokens that don't start with '-' or are not operators
            k = j
            while k < len(tokens) and not re.match(r'^[;&|]$|^\)\s*$', tokens[k]):
                candidate = tokens[k]
                # stop if candidate looks like a shell operator
                if candidate in (";", "&&", "||", "|"):
                    break
                exists, parent = _verify_parent_exists(candidate)
                if not exists:
                    return (
                        f"Error: parent directory '{parent}' for path '{candidate}' does not exist. "
                        "Please verify the intended parent directory with the LS tool before creating files/directories."
                    )
                k += 1
            # advance i past this command's args
            i = k
            continue
        i += 1

    # Handle explicit 'cd' requests: update session cwd without spawning a global chdir.
    if tokens[0] == "cd":
        if len(tokens) < 2:
            return "Error: 'cd' requires a target directory"
        target = tokens[1]
        # Expand and resolve the target relative to session cwd if necessary
        expanded = os.path.expanduser(os.path.expandvars(target))
        if not os.path.isabs(expanded) and _bash_session["cwd"]:
            expanded = os.path.normpath(os.path.join(_bash_session["cwd"], expanded))
        else:
            expanded = os.path.normpath(os.path.abspath(expanded))
        if not os.path.isdir(expanded):
            return f"Error: target directory '{expanded}' does not exist"
        _bash_session["cwd"] = expanded
        return f"Changed directory to {expanded}"

    # Build a short, clear description (5-10 words) of what this command does.
    # We keep it concise: "Executes command 'cmd' with provided arguments."
    cmd_name = tokens[0]
    description = f"Executes command '{cmd_name}' with provided arguments."

    # Execute the command in a subprocess, using session cwd if set.
    try:
        proc = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=_bash_session["cwd"] or None,
            timeout=timeout_sec,
            check=False,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
    except subprocess.TimeoutExpired as te:
        return f"{description}\n\nError: command timed out after {timeout_ms} ms"
    except Exception as e:
        return f"{description}\n\nError running command: {e}"

    # Truncate long outputs
    MAX_OUT = 30000
    if len(output) > MAX_OUT:
        output = output[:MAX_OUT] + "\n\n[Output truncated]"

    if not output.strip():
        return f"{description}\n\nNo output"

    return f"{description}\n\n{output}"

bash_tool_def = ToolDefinition(
    fn=bash,
    usage_system_prompt=BASH_TOOL_SYSTEM_PROMPT,
)