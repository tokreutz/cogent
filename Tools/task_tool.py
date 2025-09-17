from Models.agent_deps import AgentDeps
from pydantic_ai import RunContext, Tool
from Models.tool_definition import ToolDefinition

import textwrap
from pathlib import Path
import re

from sub_agents import create_sub_agent
from Toolsets.common_agent_toolset import common_agent_tool_definitions


async def task(ctx: RunContext[AgentDeps], description: str, prompt: str, subagent_type: str) -> str:
    """
    Run a sub-agent to perform a complex, multi-step task asynchronously.

    Args:
        ctx (RunContext[AgentDeps]): Execution context providing dependencies and runtime info.
        description (str): A short (3-5 word) description of the task being requested.
        prompt (str): A detailed prompt describing the task for the sub-agent to perform autonomously.
        subagent_type (str): The type of sub-agent to launch, selecting the agent specialization.

    Returns:
        str: The resulting output produced by the sub-agent, or an error message if execution failed.
    """
    # Removed direct print side-effect; rely on returned output only.

    # Load available sub-agent definitions from disk
    sub_agent_defs = load_sub_agent_definitions()

    # Find the selected sub-agent definition
    selected = None
    for sa in sub_agent_defs:
        if sa.type == subagent_type:
            selected = sa
            break

    # Fallback to a general-purpose agent if requested or if none specified
    if selected is None:
        if subagent_type == "general-purpose":
            # generic, empty system prompt
            selected = SubAgentDefinition(type="general-purpose", description="A general-purpose agent.", prompt="")
        else:
            return f"Unknown subagent_type '{subagent_type}'. Available types: {', '.join([s.type for s in sub_agent_defs]) + ', general-purpose' if sub_agent_defs else 'general-purpose'}"

    # Build the complete system prompt for the sub-agent by combining the agent's prompt
    # with tool usage instructions so the sub-agent is aware of available tools.
    tool_usage = _render_tool_usage()
    system_prompt = selected.prompt + "\n\n" + "Tool usage:\n" + tool_usage

    sub_agent = create_sub_agent(system_prompt=system_prompt)

    try:
        # Provide the user-supplied prompt as the actual task to perform
        result = await sub_agent.run(prompt, deps=ctx.deps)
        return result.output
    except Exception as e:
        return f"Error generating task plan: {e}"


from dataclasses import dataclass

@dataclass
class SubAgentDefinition:
    type: str
    description: str
    prompt: str


def _task_tool_description(sub_agents: list[SubAgentDefinition]) -> str:
    desc = textwrap.dedent("""
Launch a new agent to handle complex, multi-step tasks autonomously. 

Only available agent types and the tools they have access to:
    """).strip()
    for sa in sub_agents:
        desc += f"\n  - '{sa.type}': {sa.description}"

    desc += textwrap.dedent("""

When using the Task tool, you must specify a subagent_type parameter to select which agent type to use.

When NOT to use the Agent tool:
- If you want to read a specific file path, use the Read or Glob tool instead of the Agent tool, to find the match more quickly
- If you are searching for a specific class definition like "class Foo", use the Glob tool instead, to find the match more quickly
- If you are searching for code within a specific file or set of 2-3 files, use the Read tool instead of the Agent tool, to find the match more quickly
- Other tasks that are not related to the agent descriptions above

Usage notes:
1. Launch multiple agents concurrently whenever possible, to maximize performance; to do that, use a single message with multiple tool uses
2. When the agent is done, it will return a single message back to you. The result returned by the agent is not visible to the user. To show the user the result, you should send a text message back to the user with a concise summary of the result.
3. Each agent invocation is stateless. You will not be able to send additional messages to the agent, nor will the agent be able to communicate with you outside of its final report. Therefore, your prompt should contain a highly detailed task description for the agent to perform autonomously, and you should specify exactly what information the agent should return back to you in its final and only message to you.
4. The agent's outputs should generally be trusted
5. Clearly tell the agent whether you expect it to write code or just to do research (search, file reads, web fetches, etc.), since it is not aware of the user's intent
6. If the agent description mentions that it should be used proactively, then you should try your best to use it without the user having to ask for it first. Use your judgement.

Example usage:

<example_agent_descriptions_for_educational_purpose_only>
"code-reviewer": use this agent after you are done writing a signficant piece of code
"greeting-responder": use this agent when to respond to user greetings with a friendly joke
</example_agent_descriptions_for_educational_purpose_only>

<example>
user: "Please write a function that checks if a number is prime"
assistant: Sure let me write a function that checks if a number is prime
assistant: First let me use the Write tool to write a function that checks if a number is prime
assistant: I'm going to use the Write tool to write the following code:
<code>
function isPrime(n) {
  if (n <= 1) return false
  for (let i = 2; i * i <= n; i++) {
    if (n % i === 0) return false
  }
  return true
}
</code>
<commentary>
Since a signficant piece of code was written and the task was completed, now use the code-reviewer agent to review the code
</commentary>
assistant: Now let me use the code-reviewer agent to review the code
assistant: Uses the Task tool to launch the with the code-reviewer agent 
</example>

<example>
user: "Hello"
<commentary>
Since the user is greeting, use the greeting-responder agent to respond with a friendly joke
</commentary>
assistant: "I'm going to use the Task tool to launch the with the greeting-responder agent"
</example>
""")
    return desc


def create_task_tool(sub_agent_defs: list[SubAgentDefinition]) -> Tool:

    return Tool.from_schema(
        function=task,
        name='task',
        description="Runs a sub-agent to perform a complex, multi-step task autonomously.",
        json_schema={
            'additionalProperties': False,
            'properties': {
                'description': {
                    'description': 'A short (3-5 word) description of the task',
                    'type': 'string',
                },
                'prompt': {
                    'description': 'The task for the agent to perform. This should be a highly detailed description of the task for the agent to perform autonomously, including exactly what information the agent should return back to you in its final and only message to you.',
                    'type': 'string',
                },
                'subagent_type': {
                    'description': 'The type of specialized agent to use for this task. Must be one of: ' + ", ".join([sa.type for sa in sub_agent_defs]),
                    'type': 'string',
                },
            },
            'required': ['description', 'prompt', 'subagent_type'],
            'type': 'object',
        },
        takes_ctx=True,
    )


def create_task_tool_def(sub_agent_defs: list[SubAgentDefinition]) -> ToolDefinition:
    """
    Create and return a ToolDefinition for the task tool where the
    usage_system_prompt contains the full detailed guidance (including
    the available sub-agent descriptions).
    """
    return ToolDefinition(fn=task, usage_system_prompt=_task_tool_description(sub_agent_defs))


# --- Helpers for loading custom agent definitions from Agents/ ---

def load_sub_agent_definitions(agents_dir: str = "Agents") -> list[SubAgentDefinition]:
    """Load all .md files from the given directory and return a list of
    SubAgentDefinition where the filename (without .md) is used as the
    agent type and the file contents are used as the agent system prompt.

    The description is derived from the first non-empty line of the
    markdown file (stripped of leading '#' if present) or the first
    sentence as a fallback.
    """
    base = Path(agents_dir)
    defs: list[SubAgentDefinition] = []
    if not base.exists() or not base.is_dir():
        return defs

    for p in sorted(base.glob("*.md")):
        type_name = p.stem
        try:
            text = p.read_text(encoding='utf-8')
        except Exception:
            continue

        # derive description
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        description = "".join(lines[0:1]) if lines else ""
        if description.startswith("#"):
            description = description.lstrip('#').strip()

        # fallback to first sentence
        if not description:
            m = re.search(r"(.+?[\.\!\?])\s", text)
            description = m.group(1) if m else (text[:120].replace('\n', ' ').strip())

        defs.append(SubAgentDefinition(type=type_name, description=description, prompt=text))

    return defs


def _render_tool_usage() -> str:
    """Render usage text for common agent tools so sub-agents know what's available."""
    parts = [f"Tool name: {d.fn.__name__}\nTool description: {d.usage_system_prompt}" for d in common_agent_tool_definitions]
    return "\n---\n\n".join(parts) if parts else ""