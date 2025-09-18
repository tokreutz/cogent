import os
import sys
import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from models.todo_item import TodoItem, TodoState
from pydantic import ValidationError


def test_valid_states():
    for state in [TodoState.pending, TodoState.in_progress, TodoState.completed]:
        item = TodoItem(id=1, description="x", state=state)
        assert item.state == state


def test_invalid_state():
    with pytest.raises(ValidationError):
        TodoItem(id=1, description="x", state="done")


def test_schema_enum():
    schema = TodoItem.model_json_schema()
    state_schema = schema['properties']['state']
    # If enum inline
    if 'enum' in state_schema:
        values = state_schema['enum']
    else:
        # Follow $ref into $defs
        ref = state_schema.get('$ref')
        assert ref and ref.startswith('#/$defs/')
        def_name = ref.split('/')[-1]
        enum_def = schema['$defs'][def_name]
        values = enum_def['enum']
    assert set(values) == {"pending", "in_progress", "completed"}


def test_extra_forbidden():
    with pytest.raises(ValidationError):
        TodoItem(id=1, description="x", state=TodoState.pending, extra_field=123)


def test_serialization_roundtrip():
    item = TodoItem(id=42, description="Do stuff", state=TodoState.in_progress)
    data = item.model_dump()
    assert data == {"id": 42, "description": "Do stuff", "state": "in_progress"}
    new_item = TodoItem(**data)
    assert new_item == item
