from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from Toolsets.common_agent_toolset import common_agent_toolset
from Models.agent_deps import AgentDeps

def create_sub_agent(system_prompt: str) -> Agent[AgentDeps]:
    model = OpenAIChatModel(
        "qwen3-coder-30b-a3b-instruct-mlx@6bit",
        provider=OpenAIProvider(api_key='api-key', base_url="http://localhost:1234/v1")
    )

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