import json
import sys
from pathlib import Path

# Ensure project root is importable
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from Models.session_recorder import SessionRecorder

class DummyUsage:
    def __init__(self, input_tokens, output_tokens):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens

class PartBase:
    def __init__(self, content=None, tool_name=None, args=None, tool_call_id=None):
        self.content = content
        self.tool_name = tool_name
        self.args = args
        self.tool_call_id = tool_call_id
        self.timestamp = None

class SystemPromptPart(PartBase):
    pass
class UserPromptPart(PartBase):
    pass
class TextPart(PartBase):
    pass
class ToolCallPart(PartBase):
    pass
class ToolReturnPart(PartBase):
    pass

class DummyModelRequest:
    def __init__(self, parts):
        self.parts = parts
        from datetime import datetime, timezone
        self.timestamp = datetime.now(timezone.utc)

class DummyModelResponse:
    def __init__(self, parts, usage=None):
        self.parts = parts
        self.usage = usage
        from datetime import datetime, timezone
        self.timestamp = datetime.now(timezone.utc)


def test_flattened_structure(tmp_path):
    rec = SessionRecorder(tmp_path)
    req = DummyModelRequest([
        SystemPromptPart(content='sys'),
        UserPromptPart(content='user says'),
        ToolCallPart(tool_name='read', args='{ "file_path": "/x" }', tool_call_id='abc'),
    ])
    resp = DummyModelResponse([
        TextPart(content='assistant reply'),
        ToolReturnPart(tool_name='read', content='file content', tool_call_id='abc'),
    ], usage=DummyUsage(10, 5))

    rec.record([req, resp])
    data = json.loads(rec.path.read_text())
    assert data['schema_version'] == 1
    roles = [m['role'] for m in data['messages']]
    assert roles == ['system', 'user', 'tool_call', 'assistant', 'tool']
    assistant_entry = next(m for m in data['messages'] if m['role'] == 'assistant')
    assert assistant_entry['usage'] == {'input_tokens': 10, 'output_tokens': 5}
    assert assistant_entry['timestamp'] is not None
    assert all(m.get('timestamp') is not None for m in data['messages'])
    assert data['total_input_tokens'] == 10 and data['total_output_tokens'] == 5
