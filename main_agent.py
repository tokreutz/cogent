from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from Toolsets.common_agent_toolset import common_agent_toolset, common_agent_tool_definitions
from Toolsets.root_agent_toolset import root_agent_toolset, root_agent_tool_definitions
from prompts import MAIN_SYSTEM_PROMPT
from Models.agent_deps import AgentDeps

def create_main_agent() -> Agent[AgentDeps]:
    model = OpenAIChatModel(
        "qwen3-coder-30b-a3b-instruct-mlx@6bit",
        provider=OpenAIProvider(api_key='api-key', base_url="http://localhost:1234/v1")
    )

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
