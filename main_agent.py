import os
from pydantic_ai import Agent, RunContext
from Models.provider_config import build_chat_model
from Models.model_state import load_last_selection

from Toolsets.common_agent_toolset import common_agent_toolset, common_agent_tool_definitions
from Toolsets.root_agent_toolset import root_agent_toolset, root_agent_tool_definitions
from prompts import MAIN_SYSTEM_PROMPT
from Models.agent_deps import AgentDeps

def create_main_agent(provider_name: str | None = None, model_name: str | None = None) -> Agent[AgentDeps]:
    # If not explicitly provided and no environment override, attempt to load last persisted selection
    if not provider_name and not model_name and 'MODEL_PROVIDER' not in os.environ and 'MODEL_NAME' not in os.environ:
        try:
            sel = load_last_selection()
            if sel:
                provider_name = sel.provider
                model_name = sel.model
        except Exception:  # pragma: no cover
            pass
    model = build_chat_model(provider_name=provider_name, model_name=model_name)

    agent = Agent(
        model=model,
        system_prompt=MAIN_SYSTEM_PROMPT,
        deps_type=AgentDeps,
        toolsets=[
            common_agent_toolset,
            root_agent_toolset,
        ])
    
    @agent.system_prompt
    def add_cwd(ctx: RunContext[AgentDeps]) -> str:
        return f"The current working directory is: {ctx.deps.cwd}"

    @agent.system_prompt
    def add_tool_usage(ctx: RunContext[AgentDeps]) -> str:
        def render_tool_defs(defs) -> str:
            parts = [
            f"Tool name: {d.fn.__name__}\nTool description: {d.usage_system_prompt}"
            for d in defs
            ]
            return "---\n\n" + "\n---\n\n".join(parts) if parts else ""

        tool_usage = render_tool_defs(common_agent_tool_definitions)
        tool_usage += render_tool_defs(root_agent_tool_definitions)

        return tool_usage

    return agent
