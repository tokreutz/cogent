from pydantic_ai import Agent, RunContext
from Models.provider_config import build_chat_model

from Toolsets.common_agent_toolset import common_agent_toolset
from Models.agent_deps import AgentDeps

def create_sub_agent(system_prompt: str, provider_name: str | None = None, model_name: str | None = None) -> Agent[AgentDeps]:
    model = build_chat_model(provider_name=provider_name, model_name=model_name)

    agent = Agent(
        model=model,
        system_prompt=system_prompt,
        deps_type=AgentDeps,
        toolsets=[
            common_agent_toolset,
        ])

    @agent.system_prompt
    def add_cwd(ctx: RunContext[AgentDeps]) -> str:
        return f"The current working directory is: {ctx.deps.cwd}"

    @agent.system_prompt
    def add_customization(ctx: RunContext[AgentDeps]) -> str:
        return system_prompt

    return agent