from Tools.read_tool import read_tool_def
from Tools.ls_tool import ls_tool_def
from Tools.bash_tool import bash_tool_def
from Tools.glob_tool import glob_tool_def
from Tools.grep_tool import grep_tool_def
from Tools.write_tool import write_tool_def
from Tools.edit_tool import edit_tool_def
from Tools.todo_write_tool import todo_write_tool_def

from pydantic_ai.toolsets import FunctionToolset

common_agent_tool_definitions = [
    read_tool_def,
    ls_tool_def,
    bash_tool_def,
    glob_tool_def,
    grep_tool_def,
    write_tool_def,
    edit_tool_def,
    todo_write_tool_def
]

common_agent_toolset = FunctionToolset(tools=[d.fn for d in common_agent_tool_definitions])
