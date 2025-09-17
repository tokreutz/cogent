
# AI Coding agent
A Python based AI coding agent using Pydantic AI for agentic scaffolding.

- Supports tooling for file system access to perform code edits and files search. 
- Supports advanced features such as bash, prompt commands, and subagents. 
- Supports task management using a simple todo tool.

Current functionality:
- Single chat loop with history
- Tools for file system access
  - read (numbered output, supports offsets)
  - write (creates or overwrites files safely)
  - edit (exact string replacement with uniqueness safeguards)
  - ls (absolute path listing with ignore patterns)
  - grep (ripgrep wrapper with regex, glob, and type filtering)
  - better_grep (structured code search: count|lines|context|full in escalating context order)
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