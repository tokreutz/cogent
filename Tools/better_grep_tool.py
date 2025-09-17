import os
import re
from typing import List, Dict, Tuple

from pathspec import PathSpec
from pathspec.patterns.gitwildmatch import GitWildMatchPattern

from Models.tool_definition import ToolDefinition

BETTER_GREP_SYSTEM_PROMPT = """Minimal code search (ordered from least to most contextual output).

FORMAT ORDER (always start as early in the list as possible):
    1. count   : Aggregate scope: TOTAL + per-file line-match counts (top 50). Fast breadth view.
    2. lines   : Precise occurrences: file:line:code (cap 200 lines). For enumerating usages or planning edits.
    3. context : Local neighborhoods: 5 lines before/after each match (cap 50 blocks). For semantic understanding pre-change.
    4. full    : Full file bodies (up to 10 files, size caps). Only for imminent multi-line refactors after narrowing scope.

RATIONALE: Each later format strictly adds more surrounding information. Escalate only if the previous format leaves unanswered questions.

FILTERING: Optional `glob` (comma separated, supports **). Use to narrow early: glob="src/**/*.py,tests/**/*.py" | glob="**/service/*.ts" | glob="*.md".
IGNORE CASE: Use ignore_case=true only when mixed case patterns are expected.

TRUNCATION: Explicit bracketed markers indicate partial output (e.g., [truncated file list at 50], [truncated at 200 matches]). If you see one, you may need a narrower glob or a refined pattern.

EXAMPLES:
1. count
     better_grep(pattern="deprecated_func", format="count") ->
         TOTAL:37
         8:src/legacy/adapter.py
         5:src/legacy/mapper.py
         4:tests/test_adapter.py
         ...
     Use to prioritize high-impact files.

2. lines
     better_grep(pattern="foo_bar\\(", format="lines") ->
         src/api/router.py:87:self.foo_bar(request)
         src/core/worker.py:142:result = foo_bar(job)
         tests/test_worker.py:55:foo_bar(mock_job)
     Provides line numbers for targeted edits/renames. Truncation ends with [truncated at 200 matches].

3. context
     better_grep(pattern="RETRY_POLICY", format="context") -> snippet blocks:
         FILE: src/config/retry.py
         ---
                 18: MAX_RETRY = 5
         =>  19: RETRY_POLICY = {"max": MAX_RETRY, "backoff": 2}
                 20: DEFAULT_TIMEOUT = 30

         FILE: src/job/runner.py
         ---
                 44: from config.retry import RETRY_POLICY
         =>  45: policy = RETRY_POLICY.copy()
                 46: policy["attempt"] = attempt
     Semantic inspection without full file noise.

4. full
     better_grep(pattern="class ConfigBuilder", format="full", glob="src/config/*.py") ->
         FILE: src/config/builder.py
         ---
         class ConfigBuilder:
                 ...
         [truncated file content at 20000 chars]  # only if large
     Only after count/lines/context clarified scope.

ANTI-PATTERNS:
    - Jumping straight to full.
    - Using context to count matches (use count or lines).
    - Broad pattern + truncation notice: refine pattern or add glob before escalating.

DECISION QUICK MAP:
    Sizing -> count
    Need exact lines -> lines
    Need surrounding logic -> context
    Need whole file(s) for refactor -> full

If earlier format answers the question, DO NOT escalate.
"""

DEFAULT_SKIP_DIRS = {
    ".git","__pycache__","node_modules",".venv","venv",".mypy_cache",
    ".pytest_cache","dist","build",".idea",".vscode","coverage","target"
}

# Format policy constants
LINES_MAX = 200
CONTEXT_LINES = 5
CONTEXT_BLOCKS_MAX = 50
COUNT_FILES_MAX = 50
FULL_FILES_MAX = 10
FULL_TOTAL_CHARS_MAX = 120_000
FULL_PER_FILE_CHARS_MAX = 20_000

def _compile_gitignore(root: str) -> PathSpec | None:
    gitignore_path = os.path.join(root, ".gitignore") if os.path.isdir(root) else os.path.join(os.path.dirname(root), ".gitignore")
    if not os.path.isfile(gitignore_path):
        return None
    try:
        with open(gitignore_path, "r", encoding="utf-8", errors="ignore") as fh:
            lines = fh.read().splitlines()
        return PathSpec.from_lines(GitWildMatchPattern, lines)
    except Exception:
        return None

def _expand_globs(glob: str) -> List[str]:
    if not glob:
        return []
    return [g.strip() for g in glob.split(',') if g.strip()]

def _should_include(rel_path: str, fname: str, full: str, glob_patterns: List[str]) -> bool:
    if not glob_patterns:
        return True
    for gp in glob_patterns:
        if re.fullmatch(gp.replace("**", ".*"), rel_path):  # simple fallback
            return True
        import fnmatch
        if fnmatch.fnmatch(rel_path, gp) or fnmatch.fnmatch(fname, gp) or fnmatch.fnmatch(full, gp):
            return True
    return False

def _gather_files(root: str, glob_patterns: List[str], git_spec: PathSpec | None) -> List[str]:
    if os.path.isfile(root):
        return [root]
    out: List[str] = []
    root_is_dir = os.path.isdir(root)
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in DEFAULT_SKIP_DIRS]
        for fname in files:
            full = os.path.join(dirpath, fname)
            rel = os.path.relpath(full, root) if root_is_dir else fname
            if git_spec and git_spec.match_file(rel):
                continue
            if not _should_include(rel, fname, full, glob_patterns):
                continue
            out.append(full)
    return out

def _scan_files(files: List[str], pattern: str, flags: int) -> Dict[str, List[Tuple[int, str]]]:
    compiled = re.compile(pattern, flags)
    matches: Dict[str, List[Tuple[int, str]]] = {}
    for f in files:
        try:
            with open(f, "r", encoding="utf-8", errors="ignore") as fh:
                for idx, line in enumerate(fh, start=1):
                    if compiled.search(line):
                        matches.setdefault(f, []).append((idx, line.rstrip("\n")))
        except Exception:
            continue
    return matches

def _format_lines(matches: Dict[str, List[Tuple[int, str]]]) -> str:
    lines: List[str] = []
    for f in sorted(matches.keys()):
        for ln, text in matches[f]:
            if len(lines) >= LINES_MAX:
                return "\n".join(lines) + f"\n[truncated at {LINES_MAX} matches]"
            lines.append(f"{f}:{ln}:{text.strip()}")
    return "\n".join(lines) if lines else "No matches found"

def _format_context(matches: Dict[str, List[Tuple[int, str]]]) -> str:
    blocks: List[str] = []
    added = 0
    for f in sorted(matches.keys()):
        try:
            with open(f, 'r', encoding='utf-8', errors='ignore') as fh:
                all_lines = fh.read().splitlines()
        except Exception:
            continue
        for ln, _ in matches[f]:
            if added >= CONTEXT_BLOCKS_MAX:
                return "\n\n".join(blocks) + f"\n\n[truncated at {CONTEXT_BLOCKS_MAX} blocks]"
            start = max(1, ln - CONTEXT_LINES)
            end = min(len(all_lines), ln + CONTEXT_LINES)
            snippet = []
            for i in range(start, end + 1):
                prefix = '=>' if i == ln else '  '
                snippet.append(f"{prefix}{i:>5}: {all_lines[i-1]}")
            blocks.append(f"FILE: {f}\n---\n" + "\n".join(snippet))
            added += 1
    return "\n\n".join(blocks) if blocks else "No matches found"


def _format_count(matches: Dict[str, List[Tuple[int, str]]]) -> str:
    counts = [(f, len(v)) for f, v in matches.items()]
    counts.sort(key=lambda x: (-x[1], x[0]))
    truncated = False
    if len(counts) > COUNT_FILES_MAX:
        counts = counts[:COUNT_FILES_MAX]
        truncated = True
    total = sum(c for _, c in counts)
    lines = [f"TOTAL:{total}"] + [f"{c}:{f}" for f, c in counts]
    if truncated:
        lines.append(f"[truncated file list at {COUNT_FILES_MAX}]")
    return "\n".join(lines) if counts else "0"


def _format_full(matches: Dict[str, List[Tuple[int, str]]]) -> str:
    files = sorted(matches.keys())[:FULL_FILES_MAX]
    chunks: List[str] = []
    total_chars = 0
    truncated_any = False
    for f in files:
        try:
            with open(f, 'r', encoding='utf-8', errors='ignore') as fh:
                content = fh.read()
        except Exception:
            continue
        if len(content) > FULL_PER_FILE_CHARS_MAX:
            content = content[:FULL_PER_FILE_CHARS_MAX] + f"\n[truncated file content at {FULL_PER_FILE_CHARS_MAX} chars]"
            truncated_any = True
        total_chars += len(content)
        if total_chars > FULL_TOTAL_CHARS_MAX:
            remaining = FULL_TOTAL_CHARS_MAX - (total_chars - len(content))
            if remaining < 0:
                remaining = 0
            content = content[:remaining] + f"\n[truncated aggregate content at {FULL_TOTAL_CHARS_MAX} chars]"
            truncated_any = True
            chunks.append(f"FILE: {f}\n---\n{content}".rstrip())
            break
        chunks.append(f"FILE: {f}\n---\n{content}".rstrip())
    out = "\n\n".join(chunks) if chunks else "No matches found"
    if truncated_any and '[truncated aggregate content' not in out and len(matches) > FULL_FILES_MAX:
        out += f"\n\n[truncated file list at {FULL_FILES_MAX}]"
    return out


def better_grep(
    pattern: str,
    path: str = '.',
    format: str = 'count',
    glob: str = '',
    ignore_case: bool = False,
) -> str:
    """Structured code search with fixed-format policies.

    Args:
        pattern: Required regex (Python). Keep it focused.
        path: Directory or file root (default '.')
        format: count|lines|context|full (default count)
        glob: Optional comma-separated globs to narrow search (supports **)
        ignore_case: Case-insensitive if True
    """
    if not pattern:
        return "Error: 'pattern' is required"
    if path and not os.path.exists(path):
        return f"Error: path '{path}' does not exist"

    chosen = (format or 'count').lower()
    if chosen not in {'lines','context','count','full'}:
        chosen = 'count'

    glob_patterns = _expand_globs(glob)
    gitignore_spec = _compile_gitignore(path)
    candidate_files = _gather_files(path, glob_patterns, gitignore_spec)
    if not candidate_files:
        return 'No matches found' if chosen != 'count' else '0'

    flags = re.MULTILINE | (re.IGNORECASE if ignore_case else 0)
    matches = _scan_files(candidate_files, pattern, flags)
    if not matches:
        return 'No matches found' if chosen != 'count' else '0'

    if chosen == 'lines':
        return _format_lines(matches)
    if chosen == 'context':
        return _format_context(matches)
    if chosen == 'count':
        return _format_count(matches)
    if chosen == 'full':
        return _format_full(matches)
    return 'No matches found'


better_grep_tool_def = ToolDefinition(
    fn=better_grep,
    usage_system_prompt=BETTER_GREP_SYSTEM_PROMPT,
)
