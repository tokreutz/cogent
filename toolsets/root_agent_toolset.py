from pydantic_ai.toolsets import FunctionToolset

from tools.task_tool import SubAgentDefinition, create_task_tool_def, load_sub_agent_definitions

# Load custom agents from the Agents/ directory and ensure a general-purpose fallback
_sub_agents = load_sub_agent_definitions()

if not any(sa.type == 'general-purpose' for sa in _sub_agents):
    _sub_agents.append(SubAgentDefinition(
        type="general-purpose",
        description="A general-purpose agent capable of handling a wide range of tasks.",
        prompt="",
    ))

root_agent_tool_definitions = [
    create_task_tool_def(_sub_agents)
]

root_agent_toolset = FunctionToolset(
    tools=[d.fn for d in root_agent_tool_definitions]
)