import os
from Tools.better_grep_tool import better_grep

TEST_DIR = os.path.dirname(__file__)

SAMPLE_CODE = """\nclass Alpha:\n    pass\n\nclass Beta:\n    def run(self):\n        print('running Beta')\n\n# TODO: Beta improvement\n"""

SAMPLE_CODE_2 = """\nfunction utilBeta() {\n  // beta helper\n  return 42;\n}\n"""

def setup_module(module):
    # create temp files inside tests dir
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
    out = better_grep(pattern='Beta', path=TEST_DIR, format='lines')
    assert 'sample1.py' in out
    assert ':' in out  # line number separator

def test_context_format():
    out = better_grep(pattern='Beta', path=TEST_DIR, format='context')
    assert 'FILE:' in out
    assert 'Beta' in out

def test_count_format():
    out = better_grep(pattern='Beta', path=TEST_DIR, format='count')
    assert out.splitlines()[0].startswith('TOTAL:')
    # Ensure per-file entries exist
    lines = out.splitlines()[1:]
    assert any('sample1.py' in l for l in lines)


def test_full_format():
    out = better_grep(pattern='Alpha', path=TEST_DIR, format='full')
    assert 'class Alpha' in out
