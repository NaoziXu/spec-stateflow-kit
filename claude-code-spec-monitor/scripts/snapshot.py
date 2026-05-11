#!/usr/bin/env python3
"""
Claude Code Monitor - State Snapshot Management (v3)

progress.json  ← written by spec-task-progress skill (LLM parse)
checker.json   ← written by daemon (PID tracking)
/tmp/claude-monitor-{task_id}.json ← daemon runtime state

Usage:
  python3 snapshot.py <task_id> cycle    -- Run one monitoring cycle (replaces old check+ACTION)
  python3 snapshot.py <task_id> init     -- Initialize state file (legacy, kept for compatibility)
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

# Daemon cycle interval in minutes — shared constant for both freshness threshold and sleep interval
DAEMON_CYCLE_MINUTES = 15


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

class SpecEnvError(Exception):
    """Raised when spec-env.json is missing or malformed."""
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
    """Read progress.json; return None on any failure."""
    path = os.path.join(spec_path, "progress.json")
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def is_progress_fresh(data: Optional[dict]) -> bool:
    """Return True if progress.json was updated within one daemon cycle."""
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
# checker.json helpers (written by daemon, read by daemon)
# ---------------------------------------------------------------------------

def read_checker_json(spec_path: str) -> Optional[dict]:
    """Read checker.json (daemon metadata); return None on any failure."""
    path = os.path.join(spec_path, "checker.json")
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def write_checker_json(spec_path: str, pid: int) -> None:
    """Atomically write checker.json after spawning a new progress checker."""
    path = os.path.join(spec_path, "checker.json")
    data = {
        "progress_checker_pid": pid,
        "triggered_by": "daemon",
        "spawned_at": datetime.now().isoformat(timespec="seconds"),
    }
    tmp_path = path + ".tmp"
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    os.replace(tmp_path, path)


# ---------------------------------------------------------------------------
# Spec path helpers
# ---------------------------------------------------------------------------

def find_spec_path(task_id: str, env: dict) -> Optional[str]:
    """Scan SPEC_DIR for a directory whose name contains task_id.

    Matching strategy (deterministic):
    1. Prefer names that start with task_id (prefix match)
    2. Fall back to substring match
    3. If multiple matches at same priority, prefer shortest name (most specific)
    """
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
    """Return project directory from .project file inside spec dir, or None."""
    spec_path = find_spec_path(task_id, env)
    if not spec_path:
        return None
    project_file = os.path.join(spec_path, '.project')
    if not os.path.exists(project_file):
        return None
    with open(project_file, encoding='utf-8') as f:
        return os.path.join(env['WORKSPACE'], f.read().strip())


# ---------------------------------------------------------------------------
# Process helpers
# ---------------------------------------------------------------------------

def parse_etime(etime_str: str) -> float:
    """Parse ps etime (D-HH:MM:SS / HH:MM:SS / MM:SS / SS) to minutes."""
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
        # Seconds only (very new process)
        hours, minutes, seconds = 0, 0, int(segments[0])
    elif len(segments) == 2:
        hours, minutes, seconds = 0, int(segments[0]), int(segments[1])
    elif len(segments) == 3:
        hours, minutes, seconds = int(segments[0]), int(segments[1]), int(segments[2])
    else:
        return 0.0
    return float(days * 24 * 60 + hours * 60 + minutes + seconds / 60.0)


def get_all_matching_processes(task_id: str) -> List[dict]:
    """Return all claude processes whose command line contains task_id.

    Each element: {"pid": int, "etime_minutes": float, "cmd": str}
    """
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
    """Worker processes = all matching processes minus the progress checker."""
    all_matching = get_all_matching_processes(task_id)
    if progress_checker_pid is None:
        return all_matching
    return [p for p in all_matching if p['pid'] != progress_checker_pid]


def kill_progress_checker(progress_checker_pid: int) -> None:
    """Terminate the previous progress checker; silently skip if already gone."""
    try:
        os.kill(progress_checker_pid, signal.SIGTERM)
    except ProcessLookupError:
        pass


def spawn_progress_checker(task_id: str, claude_cli: str, project_dir: str) -> int:
    """Launch a new progress checker (Scene 3 prompt) and return its PID."""
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
    """Check for uncommitted changes in project directory (not doc/spec dir)."""
    result = subprocess.run(
        ['git', 'status', '--short'],
        cwd=project_dir,
        capture_output=True, text=True
    )
    return bool(result.stdout.strip())


def has_git_head_changed(project_dir: str, last_head: Optional[str]) -> bool:
    """Return True if HEAD has moved since last_head was recorded."""
    if not last_head:
        return False
    result = subprocess.run(
        ['git', 'rev-parse', 'HEAD'],
        cwd=project_dir,
        capture_output=True, text=True
    )
    return result.stdout.strip() != last_head


def get_current_git_head(project_dir: str) -> Optional[str]:
    """Return current git HEAD hash, or None on failure."""
    result = subprocess.run(
        ['git', 'rev-parse', 'HEAD'],
        cwd=project_dir,
        capture_output=True, text=True
    )
    head = result.stdout.strip()
    return head if head else None


def has_log_growth(task_id: str, last_log_size: Optional[int]) -> bool:
    """Return True if the Claude Code log file has grown since last check."""
    if last_log_size is None:
        return False
    log_path = get_log_path(task_id)
    if not os.path.exists(log_path):
        return False
    return os.path.getsize(log_path) > last_log_size


def get_current_log_size(task_id: str) -> Optional[int]:
    """Return current size of the log file in bytes, or None if not found."""
    log_path = get_log_path(task_id)
    if not os.path.exists(log_path):
        return None
    return os.path.getsize(log_path)


# ---------------------------------------------------------------------------
# State file (/tmp/claude-monitor-{task_id}.json)
# ---------------------------------------------------------------------------

def get_state_path(task_id: str) -> str:
    return f"/tmp/claude-monitor-{task_id}.json"


def get_log_path(task_id: str) -> str:
    return f"/tmp/claude-spec-{task_id}.log"


def load_state(task_id: str) -> dict:
    """Load daemon runtime state, returning empty dict if not found."""
    path = get_state_path(task_id)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(task_id: str, last_git_head: Optional[str], last_log_size: Optional[int]) -> None:
    """Persist baseline values for next cycle comparison."""
    path = get_state_path(task_id)
    state = load_state(task_id)
    if last_git_head is not None:
        state['last_git_head'] = last_git_head
    if last_log_size is not None:
        state['last_log_size'] = last_log_size
    state['last_check_time'] = datetime.now().isoformat()
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def init_state_if_missing(task_id: str) -> None:
    """Create initial state file if it doesn't exist."""
    path = get_state_path(task_id)
    if not os.path.exists(path):
        state = {
            'task_id': task_id,
            'last_git_head': None,
            'last_log_size': None,
        }
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# STOP trigger
# ---------------------------------------------------------------------------

def trigger_stop(task_id: str) -> None:
    """Mark task as complete and signal daemon to stop."""
    print(f"[cycle] STOP: task {task_id} is_complete=true and progress.json is fresh.")
    state_path = get_state_path(task_id)
    state = load_state(task_id)
    state['daemon_status'] = 'COMPLETED'
    state['last_check_time'] = datetime.now().isoformat()
    try:
        with open(state_path, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    # Signal the daemon process group to stop (daemon reads state and exits)
    # The daemon loop checks for daemon_status == 'COMPLETED'
    print("ACTION: STOP")


# ---------------------------------------------------------------------------
# Main cycle logic
# ---------------------------------------------------------------------------

def run_cycle(task_id: str, env: dict) -> None:
    """Execute one monitoring cycle: read progress, manage checker, detect workers."""
    spec_path = find_spec_path(task_id, env)
    project_dir = find_project_dir(task_id, env)

    data = read_progress_json(spec_path) if spec_path else None
    checker = read_checker_json(spec_path) if spec_path else None
    progress_checker_pid: Optional[int] = checker.get("progress_checker_pid") if checker else None

    claude_cli = env.get('CLAUDE_CLI', 'claude')
    cwd = project_dir or env.get('WORKSPACE', '.')

    if data and is_progress_fresh(data):
        # --- Fresh path ---
        if data.get("is_complete"):
            # Kill lingering progress checker before stopping
            if progress_checker_pid:
                kill_progress_checker(progress_checker_pid)
            # Remove stale checker.json so next run starts clean
            if spec_path:
                try:
                    os.remove(os.path.join(spec_path, "checker.json"))
                except FileNotFoundError:
                    pass
            trigger_stop(task_id)
            return

        # Replace progress checker every cycle
        if progress_checker_pid:
            kill_progress_checker(progress_checker_pid)
        new_pid = spawn_progress_checker(task_id, claude_cli, cwd)
        if spec_path:
            write_checker_json(spec_path, new_pid)
        progress_checker_pid = new_pid
        print(f"[cycle] Fresh progress ({data.get('done')}/{data.get('total')}), spawned new checker PID={new_pid}")

    else:
        # --- Degraded path: missing or stale progress.json (includes cold start) ---
        if progress_checker_pid:
            kill_progress_checker(progress_checker_pid)
        new_pid = spawn_progress_checker(task_id, claude_cli, cwd)
        if spec_path:
            write_checker_json(spec_path, new_pid)
        progress_checker_pid = new_pid
        print(f"[cycle] Degraded: progress.json {'missing' if data is None else 'stale'}, spawned new checker PID={new_pid}")

        # Record git/log signals for logging only — no STOP in degraded mode
        state = load_state(task_id)
        last_head = state.get('last_git_head')
        last_log_size = state.get('last_log_size')

        if project_dir:
            git_changed = has_git_head_changed(project_dir, last_head)
            tree_changed = has_git_working_tree_changes(project_dir)
        else:
            git_changed = False
            tree_changed = False
        log_changed = has_log_growth(task_id, last_log_size)

        if git_changed or tree_changed or log_changed:
            print(f"[cycle] Degraded: activity detected (git_head={git_changed}, tree={tree_changed}, log={log_changed}), waiting for next cycle")
        else:
            print(f"[cycle] Degraded: no activity signals, waiting for next cycle")

    # Worker detection (both paths) — uses updated progress_checker_pid
    workers = get_worker_processes(task_id, progress_checker_pid)
    print(f"[cycle] Active workers: {len(workers)}")
    for w in workers:
        print(f"  PID={w['pid']} etime={w['etime_minutes']:.1f}min")

    # Persist baseline values for next cycle
    current_head = get_current_git_head(project_dir) if project_dir else None
    current_log_size = get_current_log_size(task_id)
    save_state(task_id, current_head, current_log_size)


# ---------------------------------------------------------------------------
# Legacy commands (kept for compatibility)
# ---------------------------------------------------------------------------

def cmd_init(task_id: str) -> None:
    """Initialize state file."""
    init_state_if_missing(task_id)
    print(f"State initialized: {get_state_path(task_id)}")


def cmd_status(task_id: str) -> None:
    state = load_state(task_id)
    if not state:
        print(f"State file missing: {get_state_path(task_id)}")
        return
    matches = get_all_matching_processes(task_id)
    print(f"Task {task_id} monitor state:")
    head = state.get('last_git_head', 'unknown')
    print(f"  Git HEAD: {head[:8] + '...' if head and head not in ('unknown', None) else head}")
    print(f"  Last check: {state.get('last_check_time', 'unknown')}")
    print(f"  Log file: {get_log_path(task_id)}")
    print(f"  Matching processes: {len(matches)}")
    for m in matches:
        print(f"    PID {m['pid']}, {m['etime_minutes']:.1f} min")
    print(f"  State file: {get_state_path(task_id)}")


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

    state_path = get_state_path(task_id)
    if os.path.exists(state_path):
        os.remove(state_path)
        print(f"Removed: {state_path}")

    log_path = get_log_path(task_id)
    if os.path.exists(log_path):
        os.remove(log_path)
        print(f"Removed: {log_path}")

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
        init_state_if_missing(task_id)
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
