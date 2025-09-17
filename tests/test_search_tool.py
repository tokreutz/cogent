import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from Tools.search_tool import search

TEST_DIR = os.path.dirname(__file__)

SAMPLE_CODE = """\nclass Alpha:\n    pass\n\nclass Beta:\n    def run(self):\n        print('running Beta')\n\n# TODO: Beta improvement\n"""

SAMPLE_CODE_2 = """\nfunction utilBeta() {\n  // beta helper\n  return 42;\n}\n"""

def setup_module(module):
    with open(os.path.join(TEST_DIR, 'sample1.py'), 'w', encoding='utf-8') as f:
        f.write(SAMPLE_CODE)
    with open(os.path.join(TEST_DIR, 'sample2.js'), 'w', encoding='utf-8') as f:
        f.write(SAMPLE_CODE_2)

def teardown_module(module):
    for name in ('sample1.py', 'sample2.js'):
        path = os.path.join(TEST_DIR, name)
        if os.path.exists(path):
            os.remove(path)

def test_lines_format():
    out = search(pattern='Beta', path=TEST_DIR, format='lines')
    assert 'sample1.py' in out
    assert ':' in out

def test_context_format():
    out = search(pattern='Beta', path=TEST_DIR, format='context')
    assert 'FILE:' in out and 'Beta' in out

def test_count_format():
    out = search(pattern='Beta', path=TEST_DIR, format='count')
    assert out.splitlines()[0].startswith('TOTAL:')
    lines = out.splitlines()[1:]
    assert any('sample1.py' in l for l in lines)

def test_full_format():
    out = search(pattern='Alpha', path=TEST_DIR, format='full')
    assert 'class Alpha' in out
