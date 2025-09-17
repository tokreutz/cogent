
# AI Coding agent
A Python based AI coding agent using Pydantic AI for agentic scaffolding.

- Supports tooling for file system access to perform code edits and files search. 
- Supports advanced features such as bash, prompt commands, and subagents. 
- Supports task management using a simple todo tool.

Current functionality:
- Single chat loop with history
  - Multi-line input (Enter inserts newline, Esc+Enter submits)
  - Line-edit prompt history (for arrow key recall) stored at `.cogent/history` (add to .gitignore if undesired)
  - Full conversation transcripts now archived per session in `.cogent/sessions/<session_id>.json`
    - Schema v1: flattened entries list with roles: system, user, assistant, tool_call, tool; includes per-response token usage and aggregate totals.
- Tools for file system access
  - read (numbered output, supports offsets)
  - write (creates or overwrites files safely)
  - edit (exact string replacement with uniqueness safeguards)
  - ls (absolute path listing with ignore patterns)
  - search (ripgrep-backed regex/glob/type filtering + minimal structured code search: count|lines|context|full in escalation order)
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
The CLI uses `prompt_toolkit` to support multi-line editing with the following bindings:
- Press `Enter` to insert a newline.
- Press `Esc+Enter` to submit.
- Line-edit history is persisted per project in `.cogent/history`.
- Each interactive run creates / updates a session transcript JSON under `.cogent/sessions/`.
  - Session JSON schema v1 fields: `schema_version`, `session_id`, `started_at`, `updated_at`, `message_count` (original request/response objects), `entry_count` (flattened parts), `total_input_tokens`, `total_output_tokens`, `messages` (flattened ordered entries with roles and optional usage/tool metadata).

If you do not want the history committed, add this line to `.gitignore`:
Add these lines to `.gitignore` to exclude both artifacts if desired:
```
.cogent/history
.cogent/sessions/
```

## Code Structure
The original monolithic `main.py` has been refactored for clarity:

- `main.py` – thin legacy entrypoint re-exporting the async `main()` and prompt helpers (kept for backward compatibility with tests and invocation patterns like `python main.py`).
- `cli/` – dedicated CLI package
  - `cli/prompt.py` – prompt session management, piped input handling, and slash command expansion.
  - `cli/runner.py` – orchestration loop (agent creation, history management, graceful exit) with `run_loop()` and sync `main()` wrapper.

All previously imported symbols used by tests (`init_prompt_session`, `get_user_input`, `_reset_prompt_for_tests`) remain accessible from `main`.

## Model Providers & Switching

The agent supports configurable model providers via an OpenAI-compatible interface (local LM Studio or OpenAI API). Configuration lives in `providers.json` at the project root:

```json
{
  "providers": [
    {
      "name": "lmstudio",
      "type": "openai-compatible",
      "base_url": "http://localhost:1234/v1",
      "api_key_env": "LMSTUDIO_API_KEY",
      "api_key_optional": true,
      "models": ["qwen3-coder-30b-a3b-instruct-mlx@6bit"],
      "default_model": "qwen3-coder-30b-a3b-instruct-mlx@6bit"
    },
    {
      "name": "openai",
      "type": "openai",
      "base_url": "https://api.openai.com/v1",
      "api_key_env": "OPENAI_API_KEY",
      "api_key_optional": false,
      "models": ["gpt-4o-mini", "gpt-4o"],
      "default_model": "gpt-4o-mini"
    }
  ]
}
```

Environment variable overrides:

- `MODEL_PROVIDER`: Choose provider (e.g. `openai` or `lmstudio`).
- `MODEL_NAME`: Override model within selected provider.
- `OPENAI_API_KEY`: Required for provider `openai`.
- `LMSTUDIO_API_KEY`: Optional for provider `lmstudio` (placeholder used if unset).

If `providers.json` is missing, built‑in defaults are used (one-line warning printed).

### Interactive Switching

Use the `/model` slash command in the CLI to switch providers/models at runtime:

```
/model
Available models:
  1. lmstudio:qwen3-coder-30b-a3b-instruct-mlx@6bit (current)
  2. openai:gpt-4o-mini
  3. openai:gpt-4o
Select number (or blank to cancel): 2
[model] Switched to openai:gpt-4o-mini. Conversation context will reset.
```

Notes:
- Conversation history is reset after a switch to avoid cross-model context mixing.
- Current selection is indicated with `(current)`.
- Press Enter on an empty line to cancel.

### Programmatic Creation

Factory functions accept optional overrides:

```python
from main_agent import create_main_agent
agent = create_main_agent(provider_name="openai", model_name="gpt-4o-mini")
```

### Adding New Providers

Add another object to `providers.json` with the same shape. For OpenAI-compatible endpoints (e.g. a self-hosted server), set `type` to `openai-compatible`, specify `base_url`, and add a placeholder `api_key_env` (mark optional if not required).

### Troubleshooting

- Unknown provider: Ensure the `name` matches exactly an entry in `providers.json`.
- Missing API key: Export the required environment variable before launching.
- Empty model list: Provide either a `models` array or a `default_model`.

### .env Loading

If a `.env` file exists in the project root, its `KEY=VALUE` lines are loaded once at startup (only for variables not already present in the process environment). This allows you to place secrets like `OPENAI_API_KEY` in `.env` without exporting them manually each shell session. Lines beginning with `#` or without `=` are ignored. Existing environment variables always take precedence over `.env` values.

### Persistence of Last Selection

After you switch with `/model`, the chosen provider/model pair is persisted to `.cogent/state.json`:

```json
{ "provider": "openai", "model": "gpt-4o-mini" }
```

On the next run, if you do not set `MODEL_PROVIDER` or `MODEL_NAME` and do not pass overrides to `create_main_agent`, the saved selection is used automatically. Precedence order:
1. Explicit arguments to `create_main_agent()`
2. Environment variables (`MODEL_PROVIDER`, `MODEL_NAME`)
3. Persisted state file (`.cogent/state.json`)
4. First entry in `providers.json`

Delete the state file or use a different selection to change this default.

### Prompt Model Indicator

The interactive prompt displays the active model: `(model-name) >`. Long names (>40 chars) are truncated with an ellipsis. After switching models with `/model`, the prompt updates on the next input cycle.