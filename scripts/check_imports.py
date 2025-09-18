#!/usr/bin/env python3
"""CI helper to forbid new imports of deprecated camel-case packages.

Fails if source (excluding shim dirs) contains 'from Models', 'from Tools', or 'from Toolsets'.
"""
from __future__ import annotations
import os
import sys
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
FORBIDDEN = [r'from\s+Models\b', r'from\s+Tools\b', r'from\s+Toolsets\b', r'import\s+Models\b', r'import\s+Tools\b', r'import\s+Toolsets\b']
PATTERNS = [re.compile(p) for p in FORBIDDEN]
SHIM_DIRS = {os.path.join(ROOT, 'Models'), os.path.join(ROOT, 'Tools'), os.path.join(ROOT, 'Toolsets')}

violations: list[tuple[str,int,str]] = []
for base, dirs, files in os.walk(ROOT):
    # Skip shim directories entirely
    if base in SHIM_DIRS:
        continue
    # Skip typical virtualenv / cache dirs
    parts = set(base.split(os.sep))
    if any(p in {'.git', '.pytest_cache', '__pycache__', 'venv', '.venv'} for p in parts):
        continue
    for fname in files:
        if not fname.endswith('.py'):
            continue
        path = os.path.join(base, fname)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for lineno, line in enumerate(f, start=1):
                    stripped = line.lstrip()
                    if not (stripped.startswith('from ') or stripped.startswith('import ')):
                        continue
                    for pat in PATTERNS:
                        if pat.search(stripped):
                            violations.append((path, lineno, stripped.rstrip()))
        except OSError:
            continue

if violations:
    print('Forbidden legacy imports detected:')
    for path, lineno, line in violations:
        rel = os.path.relpath(path, ROOT)
        print(f"  {rel}:{lineno}: {line}")
    print('\nPlease migrate to lowercase packages (models/, tools/, toolsets/).')
    sys.exit(1)
else:
    print('No forbidden legacy imports found.')
