
# AI Coding agent
A Python based AI coding agent using Pydantic AI for agentic scaffolding.

- Supports tooling for file system access to perform code edits and files search. 
- Supports advanced features such as bash, prompt commands, and subagents. 
- Supports task management using a simple todo tool.

Current functionality:
- Single chat loop with history
  - Multi-line input with Shift+Enter (prompt_toolkit)
  - Per-project prompt history stored at `.cogent/history` (add to .gitignore if undesired)
- Tools for file system access
  - read (numbered output, supports offsets)
  - write (creates or overwrites files safely)
  - edit (exact string replacement with uniqueness safeguards)
  - ls (absolute path listing with ignore patterns)
  - grep (ripgrep wrapper with regex, glob, and type filtering)
  - search (minimal structured code search: count|lines|context|full in escalation order)
  - glob (mtime-sorted pattern matching)
- Tools for advanced use
  - bash (persistent cwd, restricted from using grep/find/cat/head/tail/ls)
  - task (launches specialized sub-agents; auto-loads definitions from Agents/)
- Tools for task management
  - todowrite (structured session TODO tracking)

next steps:
- advanced context management
- chat sessions
- your name it

## Multi-line Input
The CLI uses `prompt_toolkit` to support multi-line editing:
- Press `Alt+Enter` to insert a newline.
- Press `Enter` to submit.
- History is persisted per project in `.cogent/history`.

If you do not want the history committed, add this line to `.gitignore`:
```
.cogent/history
```

## Code Structure
The original monolithic `main.py` has been refactored for clarity:

- `main.py` – thin legacy entrypoint re-exporting the async `main()` and prompt helpers (kept for backward compatibility with tests and invocation patterns like `python main.py`).
- `cli/` – dedicated CLI package
  - `cli/prompt.py` – prompt session management, piped input handling, and slash command expansion.
  - `cli/runner.py` – orchestration loop (agent creation, history management, graceful exit) with `run_loop()` and sync `main()` wrapper.

All previously imported symbols used by tests (`init_prompt_session`, `get_user_input`, `_reset_prompt_for_tests`) remain accessible from `main`.