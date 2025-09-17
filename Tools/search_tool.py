import os
import re
from typing import List, Dict, Tuple

from pathspec import PathSpec
from pathspec.patterns.gitwildmatch import GitWildMatchPattern

from Models.tool_definition import ToolDefinition

SEARCH_SYSTEM_PROMPT = """Minimal code search (least -> most context outputs).

Call: search(pattern, path='.', format='count', glob='', ignore_case=false)

Formats:
  1. count   : TOTAL + per-file line counts (top 50). Use first for breadth & prioritization.
  2. lines   : file:line:code (cap 200). Enumerate occurrences / plan edits.
  3. context : 5 lines before/after (cap 50 blocks). Understand semantics without full files.
  4. full    : Up to 10 whole files (size caps). Only for imminent multi-line refactor after narrowing.

Escalate only if prior format insufficient. Refine with glob before escalating if truncated.

Truncation markers explicitly indicate partial results.

Decision quick map:
  Scope sizing -> count
  Need exact line numbers -> lines
  Need local logic -> context
  Need full file bodies -> full

Anti-patterns: jumping straight to full; using context to count occurrences; broad pattern with truncation (refine or add glob first).
"""

DEFAULT_SKIP_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv", ".mypy_cache",
    ".pytest_cache", "dist", "build", ".idea", ".vscode", "coverage", "target"
}

MAX_FILES_SCANNED = 5000
_BINARY_SNIFF_BYTES = 1024

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
    return [g.strip() for g in glob.split(',') if g.strip()] if glob else []

def _matches_globs(rel_path: str, fname: str, full: str, glob_patterns: List[str]) -> bool:
    if not glob_patterns:
        return True
    import fnmatch
    for gp in glob_patterns:
        # Support ** via fnmatch (already handles)
        if fnmatch.fnmatch(rel_path, gp) or fnmatch.fnmatch(fname, gp) or fnmatch.fnmatch(full, gp):
            return True
    return False

def _is_binary(path: str) -> bool:
    try:
        with open(path, 'rb') as fh:
            chunk = fh.read(_BINARY_SNIFF_BYTES)
        if b'\x00' in chunk:
            return True
    except Exception:
        return False
    return False

def _gather_files(root: str, glob_patterns: List[str], git_spec: PathSpec | None) -> Tuple[List[str], bool, int]:
    """Collect candidate text files.

    Returns (files, truncated, binary_skipped)
    """
    if os.path.isfile(root):
        return ([root], False, 0)
    out: List[str] = []
    truncated = False
    binary_skipped = 0
    root_is_dir = os.path.isdir(root)
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in DEFAULT_SKIP_DIRS]
        for fname in files:
            full = os.path.join(dirpath, fname)
            rel = os.path.relpath(full, root) if root_is_dir else fname
            if git_spec and git_spec.match_file(rel):
                continue
            if not _matches_globs(rel, fname, full, glob_patterns):
                continue
            if _is_binary(full):
                binary_skipped += 1
                continue
            out.append(full)
            if len(out) >= MAX_FILES_SCANNED:
                truncated = True
                return out, truncated, binary_skipped
    return out, truncated, binary_skipped

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

def search(
    pattern: str,
    path: str = '.',
    format: str = 'count',
    glob: str = '',
    ignore_case: bool = False,
) -> str:
    """Structured code search with fixed-format policies.

    Args:
        pattern: Required regex (Python).
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
    candidate_files, files_truncated, binary_skipped = _gather_files(path, glob_patterns, gitignore_spec)
    if not candidate_files:
        return 'No matches found' if chosen != 'count' else '0'
    try:
        flags = re.MULTILINE | (re.IGNORECASE if ignore_case else 0)
        matches = _scan_files(candidate_files, pattern, flags)
    except re.error as e:
        return f"Error: invalid regex: {e}"
    if not matches:
        base = 'No matches found' if chosen != 'count' else '0'
        # Append scan metadata if relevant
        meta_bits = []
        if files_truncated:
            meta_bits.append(f"[truncated file scan at {MAX_FILES_SCANNED}]")
        if binary_skipped:
            meta_bits.append(f"[skipped {binary_skipped} binary files]")
        if meta_bits:
            return base + ' ' + ' '.join(meta_bits)
        return base

    if chosen == 'lines':
        out = _format_lines(matches)
    elif chosen == 'context':
        out = _format_context(matches)
    elif chosen == 'count':
        out = _format_count(matches)
    elif chosen == 'full':
        out = _format_full(matches)
    else:
        out = 'No matches found'

    meta_bits = []
    if files_truncated:
        meta_bits.append(f"[truncated file scan at {MAX_FILES_SCANNED}]")
    if binary_skipped:
        meta_bits.append(f"[skipped {binary_skipped} binary files]")
    if meta_bits:
        out = out + ("\n" if '\n' not in out[-1:] else '') + " ".join(meta_bits)
    return out

search_tool_def = ToolDefinition(
    fn=search,
    usage_system_prompt=SEARCH_SYSTEM_PROMPT,
)
