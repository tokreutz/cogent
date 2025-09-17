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


def test_glob_narrowing(tmp_path):
    root = tmp_path
    (root / 'a.py').write_text('print("Alpha")\n')
    (root / 'b.js').write_text('console.log("Alpha")\n')
    out = search(pattern='Alpha', path=str(root), format='count', glob='*.py')
    # Should only count occurrences in a.py
    assert 'TOTAL:' in out
    assert 'a.py' in out and 'b.js' not in out


def test_gitignore_exclusion(tmp_path):
    root = tmp_path
    (root / '.gitignore').write_text('ignored.py\n')
    (root / 'kept.py').write_text('print("Keep")\n')
    (root / 'ignored.py').write_text('print("Keep")\n')
    out = search(pattern='Keep', path=str(root), format='lines')
    assert 'kept.py' in out and 'ignored.py' not in out


def test_binary_skip(tmp_path):
    root = tmp_path
    (root / 'text.txt').write_text('PatternHere\n')
    # Create binary file containing the pattern and a null byte
    (root / 'bin.dat').write_bytes(b'\x00PatternHere\x00')
    out = search(pattern='PatternHere', path=str(root), format='count')
    # Should count only text file (1) and note skipped binary
    assert 'TOTAL:1' in out
    assert 'binary files' in out


def test_invalid_regex(tmp_path):
    (tmp_path / 'f.txt').write_text('hi')
    out = search(pattern='[unclosed', path=str(tmp_path), format='count')
    assert out.startswith('Error: invalid regex:')


def test_no_matches_metadata(tmp_path):
    # Create > MAX_FILES_SCANNED small files without pattern to trigger truncation then search absent pattern
    from Tools.search_tool import MAX_FILES_SCANNED
    for i in range(MAX_FILES_SCANNED + 10):
        (tmp_path / f'f{i}.txt').write_text('nothing to see')
    out = search(pattern='XYZ_NO_MATCH', path=str(tmp_path), format='lines')
    assert 'No matches found' in out
    # Since truncation occurs, metadata marker should appear
    assert 'truncated file scan' in out
