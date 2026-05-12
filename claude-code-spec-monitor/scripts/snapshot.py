#!/usr/bin/env python3
"""
Claude Code Monitor - State Snapshot Management

File protocol:
  {SPEC_PATH}/progress.json      <- written by spec-task-progress skill (LLM parse); includes project_name
  {SPEC_PATH}/monitor-state.json <- daemon runtime state + checker PID (managed by this script)
  {SPEC_PATH}/worker.log         <- Claude Code worker output (written by launch_claude_spec.sh)
  {SPEC_PATH}/daemon.log         <- monitor daemon output (nohup redirect)
  {SPEC_PATH}/daemon.pid         <- daemon PID file (falls back to /tmp for unknown task IDs)
  {SPEC_PATH}/daemon.lock        <- flock double-start prevention (falls back to /tmp)

Usage:
  python3 snapshot.py <task_id> cycle    -- Run one monitoring cycle
  python3 snapshot.py <task_id> init     -- Initialize state file
  python3 snapshot.py <task_id> status   -- View current state
  python3 snapshot.py <task_id> processes -- List matching claude processes
  python3 snapshot.py <task_id> stop     -- Kill processes, delete state + log files
"""
import glob, json, os, re, signal, subprocess, sys, time
from datetime import datetime
from typing import List, Optional

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
SPEC_ENV_PATH = os.path.normpath(os.path.join(SCRIPT_DIR, '..', '..', '..', 'spec-env.json'))

DAEMON_CYCLE_MINUTES = 15


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

class SpecEnvError(Exception):
    pass


def load_spec_env():
    if not os.path.exists(SPEC_ENV_PATH):
        raise SpecEnvError(f"spec-env.json not found at {SPEC_ENV_PATH}. Install spec kit first.")
    try:
        with open(SPEC_ENV_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise SpecEnvError(f"spec-env.json is corrupted: {e}")


# ---------------------------------------------------------------------------
# progress.json helpers (written by skill, read by daemon)
# ---------------------------------------------------------------------------

def read_progress_json(spec_path: str) -> Optional[dict]:
    path = os.path.join(spec_path, "progress.json")
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def is_progress_fresh(data: Optional[dict]) -> bool:
    if not data or not isinstance(data, dict):
        return False
    updated_str = data.get("updated_at")
    if not updated_str:
        return False
    try:
        updated = datetime.fromisoformat(updated_str)
        return (datetime.now() - updated).total_seconds() <= DAEMON_CYCLE_MINUTES * 60
    except (ValueError, TypeError):
        return False


# ---------------------------------------------------------------------------
# Spec path helpers
# ---------------------------------------------------------------------------

def find_spec_path(task_id: str, env: dict) -> Optional[str]:
    workspace = env.get('WORKSPACE', '')
    doc_dir_name = env.get('DOC_DIR', 'doc')
    spec_dir = os.path.join(workspace, doc_dir_name)
    if not spec_dir or not os.path.isdir(spec_dir):
        return None

    prefix_matches = []
    substring_matches = []
    for name in os.listdir(spec_dir):
        if not os.path.isdir(os.path.join(spec_dir, name)):
            continue
        if name.startswith(task_id):
            prefix_matches.append(name)
        elif task_id in name:
            substring_matches.append(name)

    if prefix_matches:
        return os.path.join(spec_dir, sorted(prefix_matches, key=len)[0])
    if substring_matches:
        return os.path.join(spec_dir, sorted(substring_matches, key=len)[0])
    return None


def find_project_dir(task_id: str, env: dict) -> Optional[str]:
    """Return project directory from project_name field in progress.json."""
    spec_path = find_spec_path(task_id, env)
    if not spec_path:
        return None
    progress = read_progress_json(spec_path)
    if not progress:
        return None
    project_name = progress.get('project_name')
    if not project_name:
        return None
    return os.path.join(env['WORKSPACE'], project_name)


# ---------------------------------------------------------------------------
# Path helpers — SPEC_PATH-based with /tmp fallback for unknown task IDs
# ---------------------------------------------------------------------------

def get_state_path(spec_path: Optional[str], task_id: str = '') -> str:
    if spec_path:
        return os.path.join(spec_path, 'monitor-state.json')
    return f'/tmp/claude-monitor-{task_id}.json'


def get_log_path(spec_path: Optional[str], task_id: str = '') -> str:
    if spec_path:
        return os.path.join(spec_path, 'worker.log')
    return f'/tmp/claude-spec-{task_id}.log'


def get_daemon_log_path(spec_path: Optional[str], task_id: str = '') -> str:
    if spec_path:
        return os.path.join(spec_path, 'daemon.log')
    return f'/tmp/claude-monitor-{task_id}-daemon.log'


# ---------------------------------------------------------------------------
# State file (monitor-state.json inside SPEC_PATH)
# ---------------------------------------------------------------------------

def load_state(spec_path: Optional[str], task_id: str = '') -> dict:
    path = get_state_path(spec_path, task_id)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(
    spec_path: Optional[str],
    task_id: str,
    last_git_head: Optional[str],
    last_log_size: Optional[int],
    checker_pid: Optional[int] = None,
    daemon_status: Optional[str] = None,
) -> None:
    path = get_state_path(spec_path, task_id)
    state = load_state(spec_path, task_id)
    if last_git_head is not None:
        state['last_git_head'] = last_git_head
    if last_log_size is not None:
        state['last_log_size'] = last_log_size
    if checker_pid is not None:
        state['checker_pid'] = checker_pid
    elif 'checker_pid' not in state:
        state['checker_pid'] = None
    if daemon_status is not None:
        state['daemon_status'] = daemon_status
    state['last_check_time'] = datetime.now().isoformat()
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def init_state_if_missing(spec_path: Optional[str], task_id: str = '') -> None:
    path = get_state_path(spec_path, task_id)
    if not os.path.exists(path):
        state = {
            'task_id': task_id,
            'last_git_head': None,
            'last_log_size': None,
            'checker_pid': None,
        }
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Process helpers
# ---------------------------------------------------------------------------

def parse_etime(etime_str: str) -> float:
    etime_str = etime_str.strip()
    if not etime_str or etime_str == '-':
        return 0.0
    parts = etime_str.split('-')
    if len(parts) == 2:
        days = int(parts[0])
        time_part = parts[1]
    else:
        days = 0
        time_part = parts[0]
    segments = time_part.split(':')
    if len(segments) == 1:
        hours, minutes, seconds = 0, 0, int(segments[0])
    elif len(segments) == 2:
        hours, minutes, seconds = 0, int(segments[0]), int(segments[1])
    elif len(segments) == 3:
        hours, minutes, seconds = int(segments[0]), int(segments[1]), int(segments[2])
    else:
        return 0.0
    return float(days * 24 * 60 + hours * 60 + minutes + seconds / 60.0)


def get_all_matching_processes(task_id: str) -> List[dict]:
    result = subprocess.run(
        ['ps', '-ewwo', 'pid,etime,command'],
        capture_output=True, text=True
    )
    lines = result.stdout.strip().split('\n')[1:]
    matches = []
    for line in lines:
        parts = line.strip().split(None, 2)
        if len(parts) < 3:
            continue
        pid_str, etime, cmd = parts[0], parts[1], parts[2]
        cmd_parts = cmd.split()
        is_claude_cmd = False
        if cmd_parts:
            first = cmd_parts[0].lower()
            if first.endswith('/claude') or first == 'claude':
                is_claude_cmd = True
            elif first == 'npx' and len(cmd_parts) > 1 and cmd_parts[1].lower() == 'claude':
                is_claude_cmd = True
        if is_claude_cmd and re.search(r'(?<![0-9])' + re.escape(str(task_id)) + r'(?![0-9])', cmd):
            matches.append({
                'pid': int(pid_str),
                'etime_minutes': parse_etime(etime),
                'cmd': cmd,
            })
    return matches


def get_worker_processes(task_id: str, progress_checker_pid: Optional[int]) -> List[dict]:
    all_matching = get_all_matching_processes(task_id)
    if progress_checker_pid is None:
        return all_matching
    return [p for p in all_matching if p['pid'] != progress_checker_pid]


def kill_progress_checker(progress_checker_pid: int) -> None:
    try:
        os.kill(progress_checker_pid, signal.SIGTERM)
    except ProcessLookupError:
        pass


def spawn_progress_checker(task_id: str, claude_cli: str, project_dir: str) -> int:
    prompt = f"帮我看一下spec任务的开发进度\n需求编号：{task_id}"
    proc = subprocess.Popen(
        [claude_cli, "-p", prompt, "--dangerously-skip-permissions"],
        cwd=project_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc.pid


# ---------------------------------------------------------------------------
# Degradation signals
# ---------------------------------------------------------------------------

def has_git_working_tree_changes(project_dir: str) -> bool:
    result = subprocess.run(
        ['git', 'status', '--short'],
        cwd=project_dir,
        capture_output=True, text=True
    )
    return bool(result.stdout.strip())


def has_git_head_changed(project_dir: str, last_head: Optional[str]) -> bool:
    if not last_head:
        return False
    result = subprocess.run(
        ['git', 'rev-parse', 'HEAD'],
        cwd=project_dir,
        capture_output=True, text=True
    )
    return result.stdout.strip() != last_head


def get_current_git_head(project_dir: str) -> Optional[str]:
    result = subprocess.run(
        ['git', 'rev-parse', 'HEAD'],
        cwd=project_dir,
        capture_output=True, text=True
    )
    head = result.stdout.strip()
    return head if head else None


def has_log_growth(spec_path: Optional[str], task_id: str, last_log_size: Optional[int]) -> bool:
    if last_log_size is None:
        return False
    log_path = get_log_path(spec_path, task_id)
    if not os.path.exists(log_path):
        return False
    return os.path.getsize(log_path) > last_log_size


def get_current_log_size(spec_path: Optional[str], task_id: str) -> Optional[int]:
    log_path = get_log_path(spec_path, task_id)
    if not os.path.exists(log_path):
        return None
    return os.path.getsize(log_path)


# ---------------------------------------------------------------------------
# STOP trigger
# ---------------------------------------------------------------------------

def trigger_stop(task_id: str, spec_path: Optional[str]) -> None:
    print(f"[cycle] STOP: task {task_id} is_complete=true and progress.json is fresh.")
    state = load_state(spec_path, task_id)
    state['daemon_status'] = 'COMPLETED'
    state['last_check_time'] = datetime.now().isoformat()
    path = get_state_path(spec_path, task_id)
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    print("ACTION: STOP")


# ---------------------------------------------------------------------------
# Main cycle logic
# ---------------------------------------------------------------------------

def run_cycle(task_id: str, env: dict) -> None:
    spec_path = find_spec_path(task_id, env)
    project_dir = find_project_dir(task_id, env)

    data = read_progress_json(spec_path) if spec_path else None

    state = load_state(spec_path, task_id)
    progress_checker_pid: Optional[int] = state.get('checker_pid')

    claude_cli = env.get('CLAUDE_CLI', 'claude')
    cwd = project_dir or env.get('WORKSPACE', '.')

    if data and is_progress_fresh(data):
        if data.get("is_complete"):
            if progress_checker_pid:
                kill_progress_checker(progress_checker_pid)
            trigger_stop(task_id, spec_path)
            return

        if progress_checker_pid:
            kill_progress_checker(progress_checker_pid)
        new_pid = spawn_progress_checker(task_id, claude_cli, cwd)
        save_state(spec_path, task_id, None, None, checker_pid=new_pid)
        progress_checker_pid = new_pid
        print(f"[cycle] Fresh progress ({data.get('done')}/{data.get('total')}), spawned new checker PID={new_pid}")

    else:
        if progress_checker_pid:
            kill_progress_checker(progress_checker_pid)
        new_pid = spawn_progress_checker(task_id, claude_cli, cwd)
        save_state(spec_path, task_id, None, None, checker_pid=new_pid)
        progress_checker_pid = new_pid
        print(f"[cycle] Degraded: progress.json {'missing' if data is None else 'stale'}, spawned new checker PID={new_pid}")

        state = load_state(spec_path, task_id)
        last_head = state.get('last_git_head')
        last_log_size = state.get('last_log_size')

        if project_dir:
            git_changed = has_git_head_changed(project_dir, last_head)
            tree_changed = has_git_working_tree_changes(project_dir)
        else:
            git_changed = False
            tree_changed = False
        log_changed = has_log_growth(spec_path, task_id, last_log_size)

        if git_changed or tree_changed or log_changed:
            print(f"[cycle] Degraded: activity detected (git_head={git_changed}, tree={tree_changed}, log={log_changed}), waiting for next cycle")
        else:
            print(f"[cycle] Degraded: no activity signals, waiting for next cycle")

    workers = get_worker_processes(task_id, progress_checker_pid)
    print(f"[cycle] Active workers: {len(workers)}")
    for w in workers:
        print(f"  PID={w['pid']} etime={w['etime_minutes']:.1f}min")

    current_head = get_current_git_head(project_dir) if project_dir else None
    current_log_size = get_current_log_size(spec_path, task_id)
    save_state(spec_path, task_id, current_head, current_log_size)


# ---------------------------------------------------------------------------
# Legacy commands (kept for compatibility)
# ---------------------------------------------------------------------------

def cmd_init(task_id: str) -> None:
    try:
        env = load_spec_env()
        spec_path = find_spec_path(task_id, env)
    except SpecEnvError:
        spec_path = None
    init_state_if_missing(spec_path, task_id)
    print(f"State initialized: {get_state_path(spec_path, task_id)}")


def cmd_status(task_id: str) -> None:
    try:
        env = load_spec_env()
        spec_path = find_spec_path(task_id, env)
    except SpecEnvError:
        spec_path = None

    state_path = get_state_path(spec_path, task_id)
    if not os.path.exists(state_path):
        print(f"State file missing: {state_path}")
        return
    state = load_state(spec_path, task_id)
    matches = get_all_matching_processes(task_id)
    print(f"Task {task_id} monitor state:")
    head = state.get('last_git_head', 'unknown')
    print(f"  Git HEAD: {head[:8] + '...' if head and head not in ('unknown', None) else head}")
    print(f"  Last check: {state.get('last_check_time', 'unknown')}")
    print(f"  Log file: {get_log_path(spec_path, task_id)}")
    print(f"  Matching processes: {len(matches)}")
    for m in matches:
        print(f"    PID {m['pid']}, {m['etime_minutes']:.1f} min")
    print(f"  State file: {state_path}")


def cmd_processes(task_id: str) -> None:
    matches = get_all_matching_processes(task_id)
    print(f"Matching claude processes for task {task_id}:")
    if not matches:
        print("  None found")
    for m in matches:
        print(f"  PID {m['pid']}, {m['etime_minutes']:.1f} min")
        print(f"    CMD: {m['cmd'][:100]}...")


def cmd_stop(task_id: str) -> None:
    """Kill all matching processes and remove state/log files."""
    matches = get_all_matching_processes(task_id)
    if matches:
        print(f"Killing {len(matches)} matching process(es)...")
        for m in matches:
            try:
                os.kill(m['pid'], signal.SIGKILL)
            except ProcessLookupError:
                pass
    else:
        print("No matching processes found, nothing to kill.")

    try:
        env = load_spec_env()
        spec_path = find_spec_path(task_id, env)
    except SpecEnvError:
        spec_path = None

    for path in (get_state_path(spec_path, task_id), get_log_path(spec_path, task_id)):
        if os.path.exists(path):
            os.remove(path)
            print(f"Removed: {path}")

    print("STOPPED: Cleanup complete")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python3 snapshot.py <task_id> <cycle|init|status|processes|stop>")
        sys.exit(1)

    task_id = sys.argv[1]
    command = sys.argv[2]

    if command == 'cycle':
        env = load_spec_env()
        spec_path = find_spec_path(task_id, env)
        init_state_if_missing(spec_path, task_id)
        run_cycle(task_id, env)
    elif command == 'init':
        cmd_init(task_id)
    elif command == 'status':
        cmd_status(task_id)
    elif command == 'processes':
        cmd_processes(task_id)
    elif command == 'stop':
        cmd_stop(task_id)
    else:
        print(f"Unknown command: {command}")
        print("Available: cycle, init, status, processes, stop")
        sys.exit(1)
