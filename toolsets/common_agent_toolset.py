from tools.read_tool import read_tool_def
from tools.ls_tool import ls_tool_def
from tools.bash_tool import bash_tool_def
from tools.glob_tool import glob_tool_def
from tools.search_tool import search_tool_def
from tools.write_tool import write_tool_def
from tools.edit_tool import edit_tool_def
from tools.todo_write_tool import todo_write_tool_def

from pydantic_ai.toolsets import FunctionToolset

common_agent_tool_definitions = [
    read_tool_def,
    ls_tool_def,
    bash_tool_def,
    glob_tool_def,
    search_tool_def,
    write_tool_def,
    edit_tool_def,
    todo_write_tool_def
]

common_agent_toolset = FunctionToolset(tools=[d.fn for d in common_agent_tool_definitions])
