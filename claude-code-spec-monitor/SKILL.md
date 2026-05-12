---
name: claude-code-spec-monitor
description: "Monitor Claude Code for continuous spec task execution. Progress check every 15 min, auto-stop on completion. Triggers: monitor claude code, watch progress, guard claude code, watch dog, claude code guard, test monitor, verify monitor, monitor test, restart monitor. Used when user is away from computer and needs continuous monitoring of spec task execution, or wants to verify monitor scripts are working correctly."
alwaysApply: false
---

# Claude Code Monitor Guard

Monitor Claude Code executing spec tasks when user is away from computer. Progress check every 15 min, auto-stop on completion.

**No PID dependency.** Health is measured by actual changes: git commits, working tree changes, task progress, log file growth.

## Environment

Paths are read from `{SKILLS_DIR}/../spec-env.json`:

```json
{
  "WORKSPACE": "/path/to/workspace",
  "DOC_DIR": "doc",
  "CLAUDE_CLI": "/path/to/claude"
}
```

**⚠️ If `spec-env.json` doesn't exist**: Prompt user to install spec kit first, abort.

## File Protocol

| File | Path | Purpose |
|------|------|---------|
| Progress | `{SPEC_PATH}/progress.json` | Written by progress checker (LLM parse); includes `project_name` |
| Daemon state | `{SPEC_PATH}/monitor-state.json` | Daemon runtime state (git head, log size, last check time, checker PID) |
| Worker log | `{SPEC_PATH}/worker.log` | Claude Code stdout/stderr |
| Daemon log | `{SPEC_PATH}/daemon.log` | Daemon stdout/stderr (nohup redirect) |
| Daemon PID | `{SPEC_PATH}/daemon.pid` | Process control only (falls back to `/tmp` for unknown task IDs) |
| Lock | `{SPEC_PATH}/daemon.lock` | flock double-start prevention (falls back to `/tmp` for unknown task IDs) |

**Check interval: 15 min.** Worker processes identified by task_id pattern in command line — no PID files needed.

## Decision Routing

| User Input | Action |
|-----------|--------|
| "monitor" / "watch" / "guard" + task ID | → Operation A: Start Monitoring |
| "monitor" / "watch" without task ID | → Ask for task number first |
| "stop monitor" / "stop watching" + task ID | → Operation B: Stop Monitoring |
| "restart monitor" + task ID | → Operation C: Restart Monitoring |
| "monitor status" / "monitor state" | → Operation D: View Status |
| "test monitor" / "verify monitor" | → Operation E: Self-Test |

## Operations

### A. Start Monitoring

#### A1. Pre-check ⛔

```bash
# 1. Verify task exists + check progress (invoke spec-task-progress skill or read progress.json)
# If progress.json exists and is fresh: use it directly; otherwise: invoke skill to refresh

# 2. Check Claude Code availability
{CLAUDE_CLI} --version

# 3. Check for existing daemon
python3 {SKILLS_DIR}/claude-code-spec-monitor/scripts/monitor_daemon.py <task_id> status
```

| Check | Failure Action |
|-------|----------------|
| Task spec dir not found | Inform user, abort |
| progress.json is_complete=true | Inform "Task completed, no monitoring needed", abort |
| Claude Code not installed | Inform user, abort |
| Daemon already running | Inform "Monitoring already running for {task_id}", abort |

⛔ **Show progress and check interval (15 min) to user. Wait for confirmation before A2.**

#### A2. Confirm Project Directory ⛔

```bash
# 1. Locate spec directory
ls {WORKSPACE}/{DOC_DIR}/*<task_id>*
# SPEC_PATH = matched directory full path

# 2. Read or select project
python3 -c "import json; d=json.load(open('{SPEC_PATH}/progress.json')); print(d.get('project_name',''))" 2>/dev/null \
  || (ls {WORKSPACE}/ && echo "Please select project directory")
# If absent: write project_name into progress.json after user confirms (atomic update)

# 3. Check workspace
cd {WORKSPACE}/{project_name} && git status --short
```

⛔ **Show project directory and workspace status. Wait for confirmation before A3.**

#### A3. Launch Daemon

```bash
nohup python3 {SKILLS_DIR}/claude-code-spec-monitor/scripts/monitor_daemon.py \
  {task_id} start \
  >> {SPEC_PATH}/daemon.log 2>&1 &

sleep 2
python3 {SKILLS_DIR}/claude-code-spec-monitor/scripts/monitor_daemon.py {task_id} status
```

If daemon is NOT running after 2s, show log tail and abort:

```bash
tail -20 {SPEC_PATH}/daemon.log
# Inform user: "Daemon failed to start. See log above."
```

**Daemon internals (runs autonomously, no agent involvement):**
1. `snapshot.py init` → initializes `{SPEC_PATH}/monitor-state.json` state file
2. Loop every 15 min: `snapshot.py cycle` → handles everything:
   - Reads `progress.json` (written by LLM progress checker via spec-task-progress skill)
   - **Fresh + is_complete=true** → prints `ACTION: STOP` → daemon exits cleanly
   - **Fresh + in-progress** → kills old progress checker → spawns new one → updates `monitor-state.json`
   - **Degraded (missing or stale progress.json)** → kills old progress checker → spawns new one → logs git/log activity signals → no STOP triggered
   - Both paths: scans running processes for worker activity and saves state

**Progress checker lifecycle:**
- Spawned each cycle via: `claude -p "Check spec task progress\ntask_id:{task_id}" --dangerously-skip-permissions`
- Runs in project directory; parses tasks.md and writes progress.json
- Previous cycle's checker is killed before new one is spawned
- PID tracked in `{SPEC_PATH}/monitor-state.json` as `checker_pid` field (written by `snapshot.py cycle`)

**Worker identification:** `ps` scan for `claude` processes whose command line contains `task_id`. No PID file needed. Workers are identified and counted but not restarted by the daemon — the progress checker drives forward progress.

**Activity signals (logged in degraded mode, informational only):**

| Signal | Detection Method |
|--------|-----------------|
| Git commits | Compare `git rev-parse HEAD` |
| Git working tree | `git status --short` |
| Log file growth | Compare `{SPEC_PATH}/worker.log` file size |

#### A4. Report to User

```
✅ Monitoring started: {task_id} ({done}/{total}, {pct}%)
   Worker log: {SPEC_PATH}/worker.log
   Daemon log: {SPEC_PATH}/daemon.log
   Auto-check every 15 minutes
   💡 "monitor status" to check, "stop monitor {task_id}" to stop
```

---

### B. Stop Monitoring

```bash
python3 {SKILLS_DIR}/claude-code-spec-monitor/scripts/monitor_daemon.py {task_id} stop
```

Internally: `killpg(pgid, SIGTERM)` → waits up to 5s → `killpg(pgid, SIGKILL)` if alive → cleans pid/pgid/lock files. Also handles orphan cleanup if daemon already crashed.

Inform user: `Monitor {task_id} stopped.`

---

### C. Restart Monitoring

```bash
python3 {SKILLS_DIR}/claude-code-spec-monitor/scripts/monitor_daemon.py {task_id} restart
```

Stops existing daemon (if any) → starts new one → waits 2s → prints status with new PID.
Use when daemon is stalled or after manually fixing a workspace issue.

---

### D. View Status

```bash
# Single task
python3 {SKILLS_DIR}/claude-code-spec-monitor/scripts/monitor_daemon.py {task_id} status

# All active monitors (scan SPEC_DIR for daemon.pid files; fall back to /tmp for legacy/test-only)
SPEC_ENV="{SKILLS_DIR}/../spec-env.json"
WORKSPACE=$(python3 -c "import json,sys; e=json.load(open(sys.argv[1])); print(e.get('WORKSPACE',''))" "$SPEC_ENV" 2>/dev/null)
DOC_DIR=$(python3 -c "import json,sys; e=json.load(open(sys.argv[1])); print(e.get('DOC_DIR','doc'))" "$SPEC_ENV" 2>/dev/null)
for pid_file in "${WORKSPACE}/${DOC_DIR}"/*/daemon.pid /tmp/claude-monitor-*.pid; do
  [ -f "$pid_file" ] || continue
  id=$(basename "$(dirname "$pid_file")")
  python3 {SKILLS_DIR}/claude-code-spec-monitor/scripts/monitor_daemon.py "$id" status
  echo "---"
done
```

Actual output format per task:
```
Daemon:   running (PID=12345)
Progress: 13/35 (from progress.json)
Checked:  2026-01-15T10:30:00
Workers:  1 matching process(es)
Log:      {SPEC_PATH}/worker.log
DaemonLog:{SPEC_PATH}/daemon.log
```

If no PID files found: inform user "No monitoring tasks currently."

---

### E. Self-Test

```bash
python3 {SKILLS_DIR}/claude-code-spec-monitor/scripts/monitor_daemon.py _testonly_ test
```

Runs 8 test phases: environment checks → pre-test cleanup → status(no daemon) → stop(idempotency) → start → double-start prevention → status(running) → stop. Fully self-contained and self-cleaning. Uses `_testonly_` as the task ID, so no real Claude Code worker is launched.

| Result | Action |
|--------|--------|
| `ALL PASSED` | Scripts functioning correctly |
| `[FAIL] spec-env.json found` | Re-run installer |
| `[FAIL] /tmp is writable` | Check disk/permissions |
| `[FAIL] start: daemon alive after 2s` | Check Python 3 `fcntl`/`os.setsid` compatibility |
| `[FAIL] double-start: exits non-zero` | Lock mechanism broken; re-run installer |
| `[FAIL] double-start: "already running" in output` | Lock not reporting correctly; re-run installer |

---

## ⚠️ Do Not Run `snapshot.py stop` While Daemon Is Running

`snapshot.py stop` kills all matching processes and deletes two files:
- `{SPEC_PATH}/monitor-state.json` (daemon state — baseline values lost)
- `{SPEC_PATH}/worker.log` (worker log — debugging history lost)

Running it while the daemon is active causes:
1. Worker killed directly → progress checker also killed
2. State file deleted → daemon loses baseline values on next cycle
3. Worker log deleted → debugging history lost

Always use `python3 monitor_daemon.py <id> stop` to cleanly shut down the daemon first.

## Exception Handling

| Scenario | Handling |
|----------|----------|
| spec-env.json missing | "Install spec kit first", abort |
| Task spec dir not found | Inform user, abort |
| progress.json is_complete=true | "No monitoring needed", abort |
| Claude Code not installed | Inform user, abort |
| Daemon already running | "Monitoring already running", abort |
| Daemon fails to start | Show `tail -20 daemon.log`, inform user |
| State file corrupted | `python3 snapshot.py <id> init` to reinitialize |
| progress.json stale for many cycles | Degraded mode — progress checker keeps being spawned; check worker log |
| Claude Code exits on its own | Progress checker will report stale/missing next cycle; daemon logs degraded signals |
| Multiple claude processes matching task_id | All counted as workers; normal behavior |

## Quick Reference

| Operation | Command |
|-----------|---------|
| Start monitoring | `nohup python3 monitor_daemon.py <id> start >> {SPEC_PATH}/daemon.log 2>&1 &` |
| Stop monitoring | `python3 monitor_daemon.py <id> stop` |
| Restart monitoring | `python3 monitor_daemon.py <id> restart` |
| View status | `python3 monitor_daemon.py <id> status` |
| **Self-test** | `python3 monitor_daemon.py _testonly_ test` |
| Run one cycle manually | `python3 snapshot.py <id> cycle` |
| View snapshot state | `python3 snapshot.py <id> status` |
| View worker processes | `python3 snapshot.py <id> processes` |
| View worker log | `tail -f {SPEC_PATH}/worker.log` |
| View daemon log | `tail -f {SPEC_PATH}/daemon.log` |

## Complete Example

User says "monitor 586742":

```bash
# A1: Pre-check
# → Read progress.json (invoke spec-task-progress skill if stale/missing)
# → is_complete=false: 12/35, not finished
# Run: {CLAUDE_CLI} --version → OK
# Run: monitor_daemon.py 586742 status → not running
# ⛔ Confirm with user → OK

# A2: Confirm project directory
ls {WORKSPACE}/doc/*586742*/
# → {WORKSPACE}/doc/586742-remove-service-foundation-dependency/
python3 -c "import json; d=json.load(open('{SPEC_PATH}/progress.json')); print(d.get('project_name',''))"
# → {project_name}
cd {WORKSPACE}/{project_name} && git status --short
# → clean
# ⛔ Confirm with user → OK

# A3: Launch daemon
nohup python3 {SKILLS_DIR}/claude-code-spec-monitor/scripts/monitor_daemon.py \
  586742 start >> {SPEC_PATH}/daemon.log 2>&1 &

sleep 2
python3 {SKILLS_DIR}/claude-code-spec-monitor/scripts/monitor_daemon.py 586742 status
# → Daemon:   running (PID=12345)
# → Progress: 13/35 (from progress.json)
# → Workers:  1 matching process(es)

# A4: Report
# ✅ Monitoring started: 586742 (13/35, 37%)
#    Auto-check every 15 minutes

# --- Later: stop ---
python3 {SKILLS_DIR}/claude-code-spec-monitor/scripts/monitor_daemon.py 586742 stop
# → Monitor 586742 stopped.
```
