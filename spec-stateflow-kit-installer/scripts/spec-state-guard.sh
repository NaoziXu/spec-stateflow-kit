#!/bin/bash
# spec-state-guard.sh — Validates tasks.md state transitions (PostToolUse hook)
# Reads: stdin (tool JSON), tasks.md (disk)
# Writes: warnings to stderr only
# Always exits 0 — informational only, never blocks Claude Code.
# Note: set -e is not used so any error silently exits 0.

python3 - <<'PYEOF'
import json, os, re, sys

try:
    raw = sys.stdin.read()
    tool_input = json.loads(raw)
    file_path = tool_input.get('file_path', '')
except Exception:
    sys.exit(0)

if not file_path.endswith('tasks.md'):
    sys.exit(0)

if not os.path.isfile(file_path):
    sys.exit(0)

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
except Exception:
    sys.exit(0)

warnings = []

# --- Check A: out-of-order completion ---
OVERVIEW_RE = re.compile(r'^- \[([ ~✓⏭])\] (\d+)\. (.+)$', re.MULTILINE)
overview = OVERVIEW_RE.findall(content)
seen_incomplete = False
for marker, num, name in overview:
    if marker in (' ', '~'):
        seen_incomplete = True
    elif marker == '✓' and seen_incomplete:
        warnings.append(
            f"[spec-state-guard] Warning: Task {num} ({name.strip()}) marked [✓] after incomplete tasks"
            f" — did you skip the [~] transition? Confirm implementation is complete before marking done."
        )
        seen_incomplete = False

# --- Check B: [✓] task missing Commit ---
done_tasks = [(num, name) for marker, num, name in overview if marker == '✓']

def get_commit_value_new(content, task_num):
    section_re = re.compile(
        rf'### Task {task_num}[:\s].*?\n(.*?)(?=\n### Task \d+[:\s]|\Z)',
        re.DOTALL
    )
    m = section_re.search(content)
    if not m:
        return None
    commit_re = re.compile(r'\|\s*\*\*Commit\*\*\s*\|\s*(.+?)\s*\|')
    cm = commit_re.search(m.group(1))
    return cm.group(1).strip() if cm else None

def get_commit_value_old(content, task_num):
    flat_re = re.compile(
        rf'- \[✓\] {task_num}\. .+?\n((?:[ \t]+-[^\n]+\n?)+)',
        re.MULTILINE
    )
    m = flat_re.search(content)
    if not m:
        return None
    commit_re = re.compile(r'^\s*-\s*Commit:\s*(.+)$', re.MULTILINE)
    cm = commit_re.search(m.group(1))
    return cm.group(1).strip() if cm else None

EMPTY_VALUES = {'', '—', '-', '–'}

for num, name in done_tasks:
    commit_val = get_commit_value_new(content, num)
    if commit_val is None:
        commit_val = get_commit_value_old(content, num)
    if commit_val is None or commit_val in EMPTY_VALUES:
        warnings.append(
            f"[spec-state-guard] Warning: Task {num} ({name.strip()}) is marked [✓]"
            f" but Commit field is empty. Fill in: 'feat(module): [task-id] description (abc1234)'"
        )

for w in warnings:
    print(w, file=sys.stderr)

sys.exit(0)
PYEOF
exit 0
