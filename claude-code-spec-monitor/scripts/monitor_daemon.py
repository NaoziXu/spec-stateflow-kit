#!/usr/bin/env python3
"""
Claude Code Monitor Daemon

File protocol:
  /tmp/claude-monitor-{id}.pid      <- daemon PID (alive check / stop target)
  /tmp/claude-monitor-{id}.lock     <- flock (prevents double-start; auto-released on crash)
  /tmp/claude-monitor-{id}.json     <- daemon runtime state (managed by snapshot.py)
  /tmp/claude-spec-{id}.log         <- Claude Code worker output
  {SPEC_PATH}/progress.json         <- written by progress checker (LLM parse)
  {SPEC_PATH}/checker.json          <- written by snapshot.py cycle (tracks progress checker PID)

Usage (run via nohup in background):
  nohup python3 monitor_daemon.py <task_id> start >> /tmp/claude-monitor-<task_id>-daemon.log 2>&1 &
  python3 monitor_daemon.py <task_id> stop
  python3 monitor_daemon.py <task_id> status
  python3 monitor_daemon.py <task_id> restart
  python3 monitor_daemon.py _testonly_ test   (or any placeholder task_id)
"""
import fcntl, json, os, signal, subprocess, sys, time
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

CHECK_INTERVAL = 900   # seconds between monitoring cycles (15 minutes)

SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
SNAPSHOT_PY   = os.path.join(SCRIPT_DIR, 'snapshot.py')
SPEC_ENV_PATH = os.path.normpath(os.path.join(SCRIPT_DIR, '..', '..', '..', 'spec-env.json'))

# Global: keep lock_fd open for the lifetime of the daemon
_lock_fd = None
_task_id = None


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def paths(task_id):
    return {
        'pid':        f'/tmp/claude-monitor-{task_id}.pid',
        'lock':       f'/tmp/claude-monitor-{task_id}.lock',
        'state':      f'/tmp/claude-monitor-{task_id}.json',
        'log':        f'/tmp/claude-spec-{task_id}.log',
        'daemon_log': f'/tmp/claude-monitor-{task_id}-daemon.log',
    }


# ---------------------------------------------------------------------------
# Daemon alive check (used by stop / status)
# ---------------------------------------------------------------------------

def daemon_alive(p):
    """Return (alive: bool, pid: int|None)."""
    if not os.path.exists(p['pid']):
        return False, None
    with open(p['pid']) as f:
        pid = int(f.read().strip())
    try:
        os.kill(pid, 0)
        return True, pid
    except ProcessLookupError:
        return False, pid
    except PermissionError:
        return True, pid


# ---------------------------------------------------------------------------
# Snapshot helper
# ---------------------------------------------------------------------------

def run_snapshot(task_id, *args):
    result = subprocess.run(
        ['python3', SNAPSHOT_PY, task_id] + list(args),
        capture_output=True, text=True
    )
    if result.stderr.strip():
        print(f'[snapshot stderr] {result.stderr.strip()}')
    return result.stdout.strip()


def _now():
    return datetime.now().strftime('%H:%M:%S')


# ---------------------------------------------------------------------------
# SIGTERM handler
# ---------------------------------------------------------------------------

def _sigterm_handler(signum, frame):
    global _task_id
    print(f'[{_now()}] Daemon received SIGTERM, cleaning up...')
    if _task_id:
        p = paths(_task_id)
        for key in ('pid', 'lock'):
            try:
                os.remove(p[key])
            except FileNotFoundError:
                pass
    sys.exit(0)


# ---------------------------------------------------------------------------
# start
# ---------------------------------------------------------------------------

def cmd_start(task_id):
    global _lock_fd, _task_id
    _task_id = task_id
    p = paths(task_id)

    # 1. Prevent double-start via flock
    _lock_fd = open(p['lock'], 'w')
    try:
        fcntl.flock(_lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print(f'ERROR: Monitor already running for task {task_id} (lock held)')
        sys.exit(1)

    # 2. Write PID file
    with open(p['pid'], 'w') as f:
        f.write(str(os.getpid()))

    print(f'[{_now()}] Daemon started: PID={os.getpid()}')

    # 3. Register SIGTERM handler
    signal.signal(signal.SIGTERM, _sigterm_handler)

    # 4. Initialize state file
    run_snapshot(task_id, 'init')

    # 5. Monitoring loop — run one cycle immediately, then every 15 min
    next_check = 0  # trigger first cycle on the very first iteration

    while True:
        if time.time() >= next_check:
            next_check = time.time() + CHECK_INTERVAL

            print(f'[{_now()}] Running monitoring cycle...')
            output = run_snapshot(task_id, 'cycle')
            if output:
                print(output)

            # Check for STOP signal from snapshot.py
            if 'ACTION: STOP' in output:
                print(f'[{_now()}] All tasks completed. Shutting down.')
                break

            # Also check state file for daemon_status (belt-and-suspenders)
            if os.path.exists(p['state']):
                try:
                    with open(p['state'], encoding='utf-8') as f:
                        state = json.load(f)
                    if state.get('daemon_status') == 'COMPLETED':
                        print(f'[{_now()}] daemon_status=COMPLETED detected. Shutting down.')
                        break
                except Exception:
                    pass

        time.sleep(30)

    # 6. Cleanup on loop exit
    for key in ('pid', 'lock'):
        try:
            os.remove(p[key])
        except FileNotFoundError:
            pass
    print(f'[{_now()}] Daemon exited cleanly.')


# ---------------------------------------------------------------------------
# stop
# ---------------------------------------------------------------------------

def cmd_stop(task_id):
    p = paths(task_id)
    alive, pid = daemon_alive(p)

    if not alive:
        print(f'Daemon not running for task {task_id}')
        # Clean up stale files
        for key in ('pid', 'lock'):
            try:
                os.remove(p[key])
            except FileNotFoundError:
                pass
        return

    print(f'Stopping daemon PID={pid}...')
    try:
        # Send SIGTERM to the entire process group to clean up children (e.g. snapshot.py)
        pgid = os.getpgid(pid)
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        # pgid or process group gone; fall back to direct kill in case pid still exists
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    except OSError:
        # Other OS error (e.g. permission denied for killpg); try direct kill
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

    # Wait up to 5s for graceful exit
    for _ in range(5):
        time.sleep(1)
        alive, _ = daemon_alive(p)
        if not alive:
            break

    # Force kill if still alive
    alive, _ = daemon_alive(p)
    if alive:
        print('Force killing (SIGKILL)...')
        try:
            pgid = os.getpgid(pid)
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        except OSError:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

    # Clean up remaining files
    for key in ('pid', 'lock'):
        try:
            os.remove(p[key])
        except FileNotFoundError:
            pass

    print(f'Monitor {task_id} stopped.')


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

def cmd_status(task_id):
    p = paths(task_id)
    alive, pid = daemon_alive(p)

    if alive:
        print(f'Daemon:   running (PID={pid})')
    elif pid:
        print(f'Daemon:   NOT running (stale PID file, PID={pid})')
        print('          Run "stop" to clean up stale files.')
    else:
        print(f'Daemon:   not running')

    if os.path.exists(p['state']):
        try:
            with open(p['state'], encoding='utf-8') as f:
                state = json.load(f)
            print(f'Checked:  {state.get("last_check_time", "unknown")}')
            ds = state.get('daemon_status', 'running')
            if ds != 'running':
                print(f'Status:   {ds}')
        except Exception:
            print('State:    (parse error)')
    else:
        print('State:    file not found')

    # Show progress from progress.json if available
    try:
        import importlib.util
        snapshot_spec = importlib.util.spec_from_file_location('snapshot', SNAPSHOT_PY)
        snapshot_mod = importlib.util.module_from_spec(snapshot_spec)
        snapshot_spec.loader.exec_module(snapshot_mod)
        find_spec_path = snapshot_mod.find_spec_path
        load_spec_env = snapshot_mod.load_spec_env
        SpecEnvError = snapshot_mod.SpecEnvError
        env = load_spec_env()
        spec_path = find_spec_path(task_id, env)
        if spec_path:
            prog_path = os.path.join(spec_path, 'progress.json')
            if os.path.exists(prog_path):
                with open(prog_path, encoding='utf-8') as f:
                    prog = json.load(f)
                done, total = prog.get('done', '?'), prog.get('total', '?')
                print(f'Progress: {done}/{total} (from progress.json)')
    except Exception as e:
        if 'SpecEnvError' in str(type(e)):
            print(f'Progress: (spec-env.json unavailable: {e})')
        pass

    # Count matching worker processes
    result = run_snapshot(task_id, 'processes')
    worker_count = result.count('PID ')
    print(f'Workers:  {worker_count} matching process(es)')

    print(f'Log:      {p["log"]}')
    print(f'DaemonLog:{p["daemon_log"]}')


# ---------------------------------------------------------------------------
# restart
# ---------------------------------------------------------------------------

def cmd_restart(task_id):
    p = paths(task_id)
    alive, _ = daemon_alive(p)
    if alive:
        print('Stopping existing daemon...')
    else:
        print('No daemon running, cleaning up stale files...')
    cmd_stop(task_id)

    print('Starting new daemon...')
    with open(p['daemon_log'], 'a') as log_fh:
        subprocess.Popen(
            [sys.executable, os.path.abspath(__file__), task_id, 'start'],
            stdout=log_fh,
            stderr=log_fh,
            start_new_session=True,
        )

    time.sleep(2)
    print('Verifying daemon started...')
    cmd_status(task_id)


# ---------------------------------------------------------------------------
# test
# ---------------------------------------------------------------------------

_TEST_TASK_ID = '_testonly_'


def _t_check(label, condition, results, detail=''):
    status = 'PASS' if condition else 'FAIL'
    line = f'  [{status}] {label}' + (f'  ({detail})' if detail else '')
    results.append((status, line))
    print(line)
    return condition


def _t_section(title):
    print(f'\n{title}')


def _t_cleanup(p):
    """Stop test daemon if still alive, then remove all test artefacts."""
    alive, _ = daemon_alive(p)
    if alive:
        try:
            cmd_stop(_TEST_TASK_ID)
        except Exception:
            pass
    for key in ('pid', 'lock', 'state', 'daemon_log'):
        try:
            os.remove(p[key])
        except FileNotFoundError:
            pass


def _t_summary(results):
    passed = sum(1 for s, _ in results if s == 'PASS')
    failed = sum(1 for s, _ in results if s == 'FAIL')
    print('\n' + '=' * 52)
    if failed == 0:
        print(f'  Result: ALL PASSED  ({passed} checks)')
    else:
        print(f'  Result: FAILED  ({failed} failed, {passed} passed)')
    print('=' * 52)
    return failed == 0


def cmd_test():
    """
    Self-test: exercise each command in sequence and report PASS/FAIL per step.
    Exit 0 = all passed.  Exit 1 = at least one check failed.
    """
    p = paths(_TEST_TASK_ID)
    results = []
    ok = True

    print('=' * 52)
    print('  monitor_daemon self-test')
    print('=' * 52)
    try:
        return _cmd_test_body(p, results, ok)
    finally:
        _t_cleanup(p)


def _cmd_test_body(p, results, ok):

    # ── 1. Environment ───────────────────────────────
    _t_section('[1/8] Environment checks')
    if not _t_check('spec-env.json exists', os.path.exists(SPEC_ENV_PATH), results):
        ok = False
        print('  ABORT: spec-env.json required.')
        _t_summary(results)
        return False
    ok &= _t_check('snapshot.py exists', os.path.exists(SNAPSHOT_PY), results)
    ok &= _t_check('/tmp is writable', os.access('/tmp', os.W_OK), results)

    # ── 2. Pre-test cleanup ──────────────────────────
    _t_section('[2/8] Pre-test cleanup')
    _t_cleanup(p)
    ok &= _t_check('test artefacts cleared', not os.path.exists(p['pid']), results)

    # ── 3. status — no daemon ────────────────────────
    _t_section('[3/8] status (no daemon running)')
    try:
        cmd_status(_TEST_TASK_ID)
        ok &= _t_check('status: no crash when absent', True, results)
    except Exception as e:
        ok &= _t_check('status: no crash when absent', False, results, str(e))
    alive, _ = daemon_alive(p)
    ok &= _t_check('daemon_alive: False when not running', not alive, results)

    # ── 4. stop — no daemon (idempotent) ────────────
    _t_section('[4/8] stop (no daemon, idempotency check)')
    try:
        cmd_stop(_TEST_TASK_ID)
        ok &= _t_check('stop: no crash when absent', True, results)
    except Exception as e:
        ok &= _t_check('stop: no crash when absent', False, results, str(e))

    # ── 5. start ─────────────────────────────────────
    _t_section('[5/8] start')
    with open(p['daemon_log'], 'a') as log_fh:
        subprocess.Popen(
            [sys.executable, os.path.abspath(__file__), _TEST_TASK_ID, 'start'],
            stdout=log_fh, stderr=log_fh,
            start_new_session=True,
        )
    time.sleep(2)
    alive, pid1 = daemon_alive(p)
    if not _t_check('start: daemon alive after 2s', alive, results, f'PID={pid1}'):
        ok = False
        print(f'  ABORT: daemon did not start. See: {p["daemon_log"]}')
        _t_summary(results)
        return False
    ok &= _t_check('start: pid file exists', os.path.exists(p['pid']), results)

    # ── 6. double-start prevention ───────────────────
    _t_section('[6/8] double-start (lock prevention)')
    r = subprocess.run(
        [sys.executable, os.path.abspath(__file__), _TEST_TASK_ID, 'start'],
        capture_output=True, text=True,
    )
    ok &= _t_check('double-start: exits non-zero', r.returncode != 0, results,
                   f'rc={r.returncode}')
    keyword_hit = 'already running' in r.stdout.lower() or 'lock' in r.stdout.lower()
    ok &= _t_check('double-start: "already running" in output', keyword_hit, results)

    # ── 7. status — daemon running ───────────────────
    _t_section('[7/8] status (daemon running)')
    try:
        cmd_status(_TEST_TASK_ID)
        ok &= _t_check('status: no crash while running', True, results)
    except Exception as e:
        ok &= _t_check('status: no crash while running', False, results, str(e))
    alive, _ = daemon_alive(p)
    ok &= _t_check('daemon_alive: True while running', alive, results)

    # ── 8. stop ──────────────────────────────────────
    _t_section('[8/8] stop')
    cmd_stop(_TEST_TASK_ID)
    time.sleep(1)
    alive, _ = daemon_alive(p)
    ok &= _t_check('stop: daemon no longer alive', not alive, results)
    ok &= _t_check('stop: pid file removed', not os.path.exists(p['pid']), results)
    ok &= _t_check('stop: lock file removed', not os.path.exists(p['lock']), results)
    try:
        cmd_stop(_TEST_TASK_ID)
        ok &= _t_check('stop: idempotent (second call)', True, results)
    except Exception as e:
        ok &= _t_check('stop: idempotent (second call)', False, results, str(e))

    return _t_summary(results)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: python3 monitor_daemon.py <task_id> <start|stop|status|restart|test>')
        sys.exit(1)

    task_id = sys.argv[1]
    command = sys.argv[2]

    if command == 'start':
        cmd_start(task_id)
    elif command == 'stop':
        cmd_stop(task_id)
    elif command == 'status':
        cmd_status(task_id)
    elif command == 'restart':
        cmd_restart(task_id)
    elif command == 'test':
        success = cmd_test()
        sys.exit(0 if success else 1)
    else:
        print(f'Unknown command: {command}')
        print('Available: start, stop, status, restart, test')
        sys.exit(1)
