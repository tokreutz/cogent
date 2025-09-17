import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Dict


class SessionRecorder:
    """Persist a single chat session transcript to a JSON file.

    A new UUID-based session id is generated at construction. After each
    model turn, call `record(history_messages)` with the full list returned
    by the agent. The recorder will write an idempotent JSON structure to
    `.cogent/sessions/<session_id>.json`.

    This introduces per-session archival without altering the existing
    prompt_toolkit line-edit history file at `.cogent/history`.
    """

    def __init__(self, base_cwd: str | os.PathLike[str]):
        self.session_id = str(uuid.uuid4())
        self.started_at = datetime.now(timezone.utc).isoformat()
        self._base = Path(base_cwd) / '.cogent' / 'sessions'
        self._base.mkdir(parents=True, exist_ok=True)
        self._path = self._base / f'{self.session_id}.json'

    @property
    def path(self) -> Path:  # exposed for tests
        return self._path

    def _flatten_model_request(self, obj: Any) -> List[Dict[str, Any]]:
        parts_out: List[Dict[str, Any]] = []
        parts = getattr(obj, 'parts', None)
        if not parts:
            return []
        parent_ts = getattr(obj, 'timestamp', None)
        parent_ts_iso = parent_ts.isoformat() if hasattr(parent_ts, 'isoformat') else None
        for p in parts:
            # SystemPromptPart / UserPromptPart
            p_type = type(p).__name__.lower()
            ts = getattr(p, 'timestamp', None)
            base = {
                'timestamp': ts.isoformat() if hasattr(ts, 'isoformat') else parent_ts_iso,
            }
            if p_type.endswith('systempromptpart'):
                base['role'] = 'system'
                base['content'] = getattr(p, 'content', None)
            elif p_type.endswith('userpromptpart'):
                base['role'] = 'user'
                base['content'] = getattr(p, 'content', None)
            elif p_type.endswith('textpart'):
                base['role'] = 'assistant'
                base['content'] = getattr(p, 'content', None)
            elif p_type.endswith('toolcallpart'):
                base['role'] = 'tool_call'
                base['tool_name'] = getattr(p, 'tool_name', None)
                base['args'] = getattr(p, 'args', None)
                base['tool_call_id'] = getattr(p, 'tool_call_id', None)
            elif p_type.endswith('toolreturnpart'):
                base['role'] = 'tool'
                base['tool_name'] = getattr(p, 'tool_name', None)
                base['content'] = getattr(p, 'content', None)
                base['tool_call_id'] = getattr(p, 'tool_call_id', None)
            else:
                base['role'] = 'meta'
                base['raw_repr'] = repr(p)
            parts_out.append(base)
        return parts_out

    def _serialize_message(self, m: Any) -> List[Dict[str, Any]]:
        # ModelRequest / ModelResponse flatten into individual parts
        if hasattr(m, 'parts'):
            flattened = self._flatten_model_request(m)
            if flattened:
                # Attach usage to first assistant part for responses
                usage = getattr(m, 'usage', None)
                if usage and flattened:
                    # Assume usage has input_tokens/output_tokens attributes
                    u = {}
                    for attr in ('input_tokens', 'output_tokens'):
                        if hasattr(usage, attr):
                            u[attr] = getattr(usage, attr)
                    if u:
                        flattened[0]['usage'] = u
                return flattened
        # Fallback to simple content representation
        role = getattr(m, 'role', None) or getattr(m, 'type', None) or 'unknown'
        content = getattr(m, 'content', None) or repr(m)
        return [{
            'role': role,
            'content': content,
        }]

    def record(self, messages: List[Any]) -> None:
        flat_messages: List[Dict[str, Any]] = []
        for m in messages:
            flat_messages.extend(self._serialize_message(m))
        # Derive aggregate token counts
        total_input = 0
        total_output = 0
        for fm in flat_messages:
            usage = fm.get('usage') if isinstance(fm, dict) else None
            if usage:
                total_input += usage.get('input_tokens', 0)
                total_output += usage.get('output_tokens', 0)
        data = {
            'schema_version': 1,
            'session_id': self.session_id,
            'started_at': self.started_at,
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'message_count': len(messages),  # original message objects
            'entry_count': len(flat_messages),  # flattened entries
            'total_input_tokens': total_input,
            'total_output_tokens': total_output,
            'messages': flat_messages,
        }
        tmp_path = self._path.with_suffix('.json.tmp')
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self._path)
