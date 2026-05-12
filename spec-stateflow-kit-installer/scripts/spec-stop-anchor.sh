#!/bin/bash
# spec-stop-anchor.sh — 在 Claude Code 会话结束时快照活跃 spec 任务
# 读取：~/.claude/spec-env.json  写入：~/.claude/spec-session.json（原子写）
# 始终 exit 0 — 失败静默，不影响 Claude Code。
# 注意：不使用 set -e，确保 python3 不可用时也能静默退出 0。

SPEC_ENV="$HOME/.claude/spec-env.json"
[ -f "$SPEC_ENV" ] || exit 0

python3 - "$SPEC_ENV" <<'PYEOF'
import json, os, sys, glob, subprocess, re
from datetime import datetime, timezone

spec_env_path = sys.argv[1]
try:
    with open(spec_env_path, 'r', encoding='utf-8') as f:
        env = json.load(f)
except Exception:
    sys.exit(0)

workspace = env.get('WORKSPACE', '')
doc_dir = env.get('DOC_DIR', 'doc')
spec_dir = os.path.join(workspace, doc_dir)

if not os.path.isdir(spec_dir):
    sys.exit(0)

task_files = glob.glob(os.path.join(spec_dir, '*/tasks.md'))
if not task_files:
    sys.exit(0)

MARKER_RE = re.compile(r'^- \[([ ~✓⏭])\] (\d+)\. (.+)$', re.MULTILINE)
SCOPE_TABLE_RE = re.compile(r'\|\s*\*\*Scope\*\*\s*\|\s*(.+?)\s*\|')
SPEC_TABLE_RE  = re.compile(r'\|\s*\*\*Specifics\*\*\s*\|\s*(.+?)\s*\|')
SCOPE_FLAT_RE  = re.compile(r'^\s*- Scope:\s*(.+)$', re.MULTILINE)
SPEC_FLAT_RE   = re.compile(r'^\s*- Specifics:\s*(.+)$', re.MULTILINE)

def extract_task_id(dirname):
    m = re.match(r'^([A-Z]+-\d+)', dirname)
    if m: return m.group(1)
    m = re.match(r'^(\d+)', dirname)
    if m: return m.group(1)
    return dirname

def get_git_head(spec_path):
    dirs_to_try = []
    prog_file = os.path.join(spec_path, 'progress.json')
    if os.path.isfile(prog_file):
        try:
            prog = json.load(open(prog_file, encoding='utf-8'))
            proj_name = prog.get('project_name', '')
            if proj_name:
                dirs_to_try.append(os.path.join(workspace, proj_name))
        except Exception:
            pass
    dirs_to_try.append(workspace)
    for d in dirs_to_try:
        try:
            head = subprocess.check_output(
                ['git', 'rev-parse', '--short', 'HEAD'],
                cwd=d, stderr=subprocess.DEVNULL, timeout=5
            ).decode().strip()
            if head:
                return head
        except Exception:
            continue
    return ''

def extract_task_details(content, task_num):
    scope, specifics = [], ''
    section_re = re.compile(
        rf'### Task {task_num}[:\s].*?\n(.*?)(?=\n### Task \d+[:\s]|\Z)',
        re.DOTALL
    )
    m = section_re.search(content)
    if m:
        section = m.group(1)
        sm = SCOPE_TABLE_RE.search(section)
        if sm:
            scope = [s.strip().strip('`') for s in sm.group(1).split(',') if s.strip()]
        spm = SPEC_TABLE_RE.search(section)
        if spm:
            specifics = spm.group(1).strip()
    else:
        flat_re = re.compile(
            rf'- \[~\] {task_num}\. .+?\n((?:[ \t]+-[^\n]+\n?)+)',
            re.MULTILINE
        )
        fm = flat_re.search(content)
        if fm:
            body = fm.group(1)
            sm = SCOPE_FLAT_RE.search(body)
            if sm:
                scope = [s.strip().strip('`') for s in sm.group(1).split(',') if s.strip()]
            spm = SPEC_FLAT_RE.search(body)
            if spm:
                specifics = spm.group(1).strip()
    return scope, specifics

active_specs = []    # (mtime, spec_path, task_num, task_name, content)
complete_specs = []  # (mtime, spec_path)

for tf in task_files:
    try:
        spec_path = os.path.dirname(tf)
        with open(tf, 'r', encoding='utf-8') as f:
            content = f.read()
        markers = MARKER_RE.findall(content)
        if not markers:
            continue
        mtime = os.path.getmtime(tf)
        has_tilde = any(m == '~' for m, n, nm in markers)
        all_done  = all(m in ('✓', '⏭') for m, n, nm in markers)
        if has_tilde:
            first_tilde = next((n, nm) for m, n, nm in markers if m == '~')
            active_specs.append((mtime, spec_path, int(first_tilde[0]), first_tilde[1].strip(), content))
        elif all_done:
            complete_specs.append((mtime, spec_path))
        # rollback（无 [~]，有 [ ]）：跳过——保留已有 session.json
    except Exception:
        continue

now_ts = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

if active_specs:
    active_specs.sort(key=lambda x: x[0], reverse=True)
    mtime, spec_path, task_num, task_name, content = active_specs[0]
    scope, specifics = extract_task_details(content, task_num)
    task_id = extract_task_id(os.path.basename(spec_path))
    git_head = get_git_head(spec_path)
    result = {
        'task_id': task_id,
        'spec_path': spec_path,
        'active_task_num': task_num,
        'active_task_name': task_name,
        'active_task_scope': scope,
        'active_task_specifics': specifics,
        'git_head': git_head,
        'updated_at': now_ts,
        'is_complete': False
    }
elif complete_specs:
    complete_specs.sort(key=lambda x: x[0], reverse=True)
    mtime, spec_path = complete_specs[0]
    task_id = extract_task_id(os.path.basename(spec_path))
    git_head = get_git_head(spec_path)
    result = {
        'task_id': task_id,
        'spec_path': spec_path,
        'is_complete': True,
        'git_head': git_head,
        'updated_at': now_ts
    }
else:
    # Rollback 或空——保留已有 session.json
    sys.exit(0)

out_path = os.path.expanduser('~/.claude/spec-session.json')
tmp_path = out_path + '.tmp'
try:
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, out_path)
except Exception:
    try:
        os.unlink(tmp_path)
    except Exception:
        pass

sys.exit(0)
PYEOF
exit 0
