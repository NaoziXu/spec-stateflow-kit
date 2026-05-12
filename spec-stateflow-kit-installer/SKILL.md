---
name: spec-stateflow-kit-installer
description: "Install or uninstall the Spec Stateflow Kit. Triggers: install spec kit, uninstall spec, spec-stateflow-kit-installer, initialize spec, remove spec, 安装spec, 卸载spec, 初始化spec, test installer, 测试 installer, test spec-installer, verify installer. Manages skills, spec-env.json, hook scripts (spec-stop-anchor.sh, spec-state-guard.sh), spec-router, and settings.json allowedTools."
alwaysApply: false
---

# Spec Stateflow Kit Installer

Manage the full Spec Stateflow Kit lifecycle: install or uninstall.

> **Convention**: `{KIT_DIR}` is the source package directory (where this installer was downloaded to). `{SKILLS_DIR}` is the target runtime directory where this agent loads skills from — these are two different paths. `{KIT_DIR}` is the installation source; `{SKILLS_DIR}` is the installation destination.

## SKILLS_DIR Detection (Required Before Any Operation)

**What is SKILLS_DIR?** The directory where this agent loads and runs skills from. After installation, all spec kit scripts will run from `{SKILLS_DIR}/spec-*/scripts/`. The `spec-env.json` config file will live at `{SKILLS_DIR}/../spec-env.json`.

**Detection strategy — run in order, stop at first success:**

**Step 1 — Self-identify from your own context (primary):**
You know which directory you load skills from — it is part of your configuration or runtime context. Use that path directly as `{SKILLS_DIR}`.

**Step 2 — Infer from this file's location (when installer is already in SKILLS_DIR):**
The path of this SKILL.md is `{something}/spec-stateflow-kit-installer/SKILL.md`. If this file is being read from your skills directory (i.e., the installer is already installed), then `SKILLS_DIR` is the **parent** of `spec-stateflow-kit-installer/`.
> ⚠️ During a **first install**, this file is read from the kit source directory (`{KIT_DIR}`), not from your skills directory — do not use Step 2 for first installs.

**Step 3 — Infer from your own agent design:**
You are a specific agent product with a known architecture. Based on your own design, you should know where skills are stored — use that knowledge directly. Do not ask the user.

If your product's skills directory is not immediately obvious from self-knowledge, silently check common locations (no user interaction). Use the first one that exists and is writable:
- `~/.codebuddy/skills/` (Codebuddy)
- `~/.cursor/skills/` (Cursor agent)
- `~/skills/` (generic fallback)

> ⚠️ Do NOT use `~/.claude/skills/` as SKILLS_DIR. That directory belongs to Claude Code and is where this installer deploys the Claude Code–side skills in Step 5. Using it as SKILLS_DIR would collapse the claw-side and Claude Code-side skill namespaces into one directory, breaking path resolution for both.

**Step 4 — Last resort (non-technical user prompt):**
If all above steps fail, ask the user in plain language — no jargon, no path syntax:
> "I need to find the folder where your agent stores skill files. Could you tell me which agent software you're using, or open your agent's settings and describe what you see?"

Use the user's answer to infer the path. Expand `~` and verify the directory exists and is writable before proceeding.

> ⚠️ Never hardcode this path. Never ask the user for a raw directory path using technical terms like "SKILLS_DIR" — that is developer jargon. All subsequent steps must use the resolved `{SKILLS_DIR}`.

## Managed Components

| Component | Install Location | Description |
|-----------|-----------------|-------------|
| spec-stateflow-kit-installer | `{SKILLS_DIR}/` | This installer skill (self-installs from kit) |
| spec-task-progress | `{SKILLS_DIR}/` | Progress query skill |
| claude-code-spec-driver | `{SKILLS_DIR}/` | Drive Claude Code to continue development |
| claude-code-spec-monitor | `{SKILLS_DIR}/` | Monitor guard (stall restart / completion stop) |
| spec-env.json (claw side) | `{SKILLS_DIR}/../` | Centralized path configuration (claw side) |
| spec-env.json (Claude Code side) | `~/.claude/` | Centralized path configuration (Claude Code side) |
| spec-stateflow | `~/.claude/skills/` | Claude Code side spec workflow skill |
| spec-task-progress (Claude Code side) | `~/.claude/skills/` | Claude Code progress query skill (daemon spawn) |
| spec-router | `~/.claude/skills/` | Always-active routing skill (alwaysApply: true) |
| spec-stop-anchor.sh | `~/.claude/scripts/` | Stop Hook — snapshots active spec task context |
| spec-state-guard.sh | `~/.claude/scripts/` | PostToolUse Hook — validates tasks.md transitions |
| settings.json entries | `~/.claude/settings.json` | hooks (Stop + PostToolUse) + allowedTools whitelist |

## Decision Routing

| User Input | Mode |
|-----------|------|
| "install spec" / "install spec kit" / "initialize spec" / "安装spec" / "初始化spec" | → **Install** |
| "uninstall spec" / "remove spec" / "卸载spec" | → **Uninstall** |
| "test installer" / "测试 installer" / "test spec-installer" | → **Self-Test** |
| No specific mode | → Ask user: "Install or uninstall?" |

---

## Mode 1: Install

### Step 0: Locate Kit Directory

First, check if the user already provided a kit path in their message (e.g. "install spec kit at ~/Desktop/spec-stateflow-kit"). If yes, use that path directly. If not, ask:

> "Please enter the path to the spec-stateflow-kit directory (e.g. `/Users/yourname/Desktop/spec-stateflow-kit`):"

Expand `~` if present. Then validate:

```bash
ls "{KIT_DIR}/spec-task-progress" \
   "{KIT_DIR}/claude-code-spec-driver" \
   "{KIT_DIR}/claude-code-spec-monitor" \
   "{KIT_DIR}/spec-stateflow" \
   "{KIT_DIR}/spec-router/SKILL.md" \
   "{KIT_DIR}/spec-stateflow-kit-installer/scripts/spec-stop-anchor.sh" \
   "{KIT_DIR}/spec-stateflow-kit-installer/scripts/spec-state-guard.sh"
```

| Result | Action |
|--------|--------|
| All present | Set `{KIT_DIR}` and continue |
| Directory doesn't exist | `⛔ Directory not found: {input}. Please check the path and try again.` → re-prompt |
| Missing subdirectories | `⛔ This does not look like a valid spec-stateflow-kit. Missing: {list}. Please verify the path.` → re-prompt |

> ⚠️ `{KIT_DIR}` must be confirmed before proceeding. All `cp` commands in the steps below depend on it.

### Step 1: Pre-check — Claude Code

```
[1/7] Checking Claude Code...
```

```bash
which claude && claude --version
```

**Abort on failure**, inform user:

> ⛔ Claude Code is not installed or unavailable. Please install and verify Claude Code first, then re-run the spec kit installer.

### Step 2: Configure Environment (Interactive)

```
[2/7] Configuring environment...
```

**Q1: Workspace root directory**

- ⚠️ **Must be specified by user, no default value**
- Interactive prompt: `Please enter the workspace root directory (parent of all projects and doc):`
- Validation: Directory must exist
- Confirm: `Workspace root directory set to {input}, confirm? (y/n)`
- User declines → re-enter

**Q2: Spec document path**

- Default `{DOC_DIR_name}`: `doc`
- Auto-assemble proposal: `{WORKSPACE}/{DOC_DIR_name}`
- Confirm: `Spec document path is {WORKSPACE}/{DOC_DIR_name}, confirm? (y/n)`
- User declines → ask for custom **directory name** (e.g. `specs`, `documents`). **Name only, not full path.** Update `{DOC_DIR_name}` and re-show: `Spec document path is {WORKSPACE}/{new_name}, confirm? (y/n)`
- Auto-create if not exists: `mkdir -p {WORKSPACE}/{DOC_DIR_name}`

**Q3: Claude Code CLI path**

- Auto-detect: `which claude`
- Validate: `claude --version` must succeed
- Confirm: `Claude Code path is {detected_value}, confirm? (y/n)`
- User declines → ask for custom path

**After all pass**, write `{SKILLS_DIR}/../spec-env.json`:

```json
{
  "WORKSPACE": "{user specified}",
  "DOC_DIR": "{DOC_DIR_name confirmed in Q2, e.g. 'doc'}",
  "CLAUDE_CLI": "{auto-detected or user specified}",
  "allowed_bash_patterns": [],
  "worktree": false
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `WORKSPACE` | string | required | Workspace root directory |
| `DOC_DIR` | string | `"doc"` | Spec document directory name (relative to WORKSPACE) |
| `CLAUDE_CLI` | string | auto-detected | Claude Code CLI path |
| `allowed_bash_patterns` | string[] | `[]` | Extra Bash allowedTools patterns (e.g. `"gradle build *"`) |
| `worktree` | bool | `false` | Enable git worktree isolation for spec execution |

> ⚠️ `DOC_DIR` is a **directory name** (e.g. `"doc"`), not a full path. All skills compute the full path as `{WORKSPACE}/{DOC_DIR}` at runtime.

**Sync spec-env.json to Claude Code side:**

```bash
mkdir -p ~/.claude
cp "{SKILLS_DIR}/../spec-env.json" ~/.claude/spec-env.json
echo "✅ spec-env.json synced to ~/.claude/spec-env.json"
```

Note: Two independent copies (not a symlink). If the user manually edits `{SKILLS_DIR}/../spec-env.json`, re-run the installer's "update path config" step to sync.

### Step 3: Install Skills

```
[3/7] Installing Skills...
```

For each skill (`spec-task-progress`, `claude-code-spec-driver`, `claude-code-spec-monitor`, `spec-stateflow-kit-installer`):

1. Check if `{SKILLS_DIR}/{skill}/` exists
2. If exists → ask "⚠️ {skill} already exists, overwrite? (y/n)" → skip if declined
3. Copy: `cp -r {KIT_DIR}/{skill}/ {SKILLS_DIR}/{skill}/`
4. Report: `✅ {skill} installed`

After all skills copied, set execute permissions:

```bash
chmod +x {SKILLS_DIR}/claude-code-spec-driver/scripts/launch_claude_spec.sh
find {SKILLS_DIR}/claude-code-spec-driver {SKILLS_DIR}/claude-code-spec-monitor \
  -type f -name "*.py" -exec chmod +x {} \;
```

**Validate claude-code-spec-monitor (self-test):**

```bash
python3 {SKILLS_DIR}/claude-code-spec-monitor/scripts/monitor_daemon.py _testonly_ test
```

Check the exit code:

| Exit code | Meaning | Action |
|-----------|---------|--------|
| **0** (all checks passed) | Monitor working correctly | Report: `✅ claude-code-spec-monitor self-test passed` |
| **Non-zero** (any check failed) | Monitor broken | See below |

**If the test fails:**

1. Remove the broken skill:
   ```bash
   rm -rf {SKILLS_DIR}/claude-code-spec-monitor/
   ```
2. Report to the user:
   > ⚠️ **claude-code-spec-monitor self-test FAILED** — the skill has been removed to prevent a broken installation.
   >
   > See test output above for which checks failed. Common causes:
   > - `spec-env.json` missing or misconfigured (Step 2 must succeed first)
   > - `/tmp` not writable
   > - Python 3 not available at `python3`
   >
   > Fix the issue, then uninstall and re-run the installer to retry.
3. **Continue with Steps 4–7** — other components install normally.

### Step 4: Post-Installation Path Validation

```
[4/7] Validating installation paths...
```

This phase verifies the path arithmetic is correct before continuing.

**Check 1 — Path alignment (CRITICAL):**

Compute the expected `SPEC_ENV_PATH` as each installed script would compute it (SCRIPT_DIR 3 levels up), and verify it matches the actual spec-env.json written in Step 2:

```bash
python3 -c "import os; script_dir='{SKILLS_DIR}/claude-code-spec-monitor/scripts'; expected=os.path.normpath(os.path.join(script_dir,'..','..','..','spec-env.json')); actual=os.path.normpath('{SKILLS_DIR}/../spec-env.json'); print('MATCH' if expected==actual else f'MISMATCH: expected={expected}, actual={actual}')"
```

If MISMATCH → abort with:
> ⛔ Path alignment failed. The scripts would look for spec-env.json at `{expected}` but it was written to `{actual}`. Check your SKILLS_DIR detection and try installing again.

**Check 2 — Smoke test (CRITICAL):**

Verify that spec-task-progress skill can load its environment and locate the doc directory:

```bash
python3 -c "import json,os; env_path=os.path.normpath(os.path.join('{SKILLS_DIR}','..','spec-env.json')); env=json.load(open(env_path,encoding='utf-8')); ws=env.get('WORKSPACE',''); dd=env.get('DOC_DIR','doc'); sd=os.path.join(ws,dd); print(f'WORKSPACE={ws}'); print(f'DOC_DIR={dd}'); print(f'SPEC_DIR={sd}'); print(f'exists={os.path.isdir(sd)}')"
```

Expected: exits 0, prints `exists=True` (directory auto-created in Step 2). If spec-env.json load fails or `exists=False` → abort with path details.

**Check 3 — CLAUDE_CLI reachable (WARNING):**

```bash
{CLAUDE_CLI} --version
```

Failure → warn with: `⚠️ CLAUDE_CLI not reachable at {CLAUDE_CLI} — update CLAUDE_CLI in spec-env.json if needed.` and continue.

**Check 4 — WORKSPACE exists (WARNING):**

```bash
ls {WORKSPACE}
```

Failure → warn, continue.

**Report:**
```
安装校验结果：
✅ 路径对齐：spec-env.json 路径推导正确
✅ 环境加载：spec-env.json 可被技能加载，SPEC_DIR 存在
✅ CLAUDE_CLI：{version}
✅ WORKSPACE：存在
```

### Step 5: Install Claude Code Skills

```
[5/7] Installing Claude Code skills...
```

This step installs **three** skills to `~/.claude/skills/`. All parts must be executed.

**Part A — spec-stateflow:**

1. Ensure target directory: `mkdir -p ~/.claude/skills`
2. Check if `~/.claude/skills/spec-stateflow/` exists
3. If exists → ask "⚠️ spec-stateflow already exists, overwrite? (y/n)" → skip if declined
4. Copy: `cp -r {KIT_DIR}/spec-stateflow/ ~/.claude/skills/spec-stateflow/`
5. Report: `✅ spec-stateflow → ~/.claude/skills/spec-stateflow/`

**Part B — spec-task-progress (Claude Code side, REQUIRED):**

> This is the Claude Code–side copy of the progress skill. When the daemon spawns Claude Code via `claude -p`, Claude Code must be able to load this skill from `~/.claude/skills/`. The claw-side copy in `{SKILLS_DIR}/spec-task-progress/` is separate and serves a different purpose. Both must exist.

6. Check if `~/.claude/skills/spec-task-progress/` exists
7. If exists → ask "⚠️ spec-task-progress already exists in Claude Code skills, overwrite? (y/n)" → skip if declined
8. Copy: `cp -r {KIT_DIR}/spec-task-progress/ ~/.claude/skills/spec-task-progress/`
9. Report: `✅ spec-task-progress → ~/.claude/skills/spec-task-progress/`

**Part C — spec-router (REQUIRED, alwaysApply):**

10. Check if `~/.claude/skills/spec-router/` exists
11. If exists → ask "⚠️ spec-router already exists, overwrite? (y/n)" → skip if declined
12. Copy: `cp -r {KIT_DIR}/spec-router/ ~/.claude/skills/spec-router/`
13. Report: `✅ spec-router → ~/.claude/skills/spec-router/  [alwaysApply]`

### Step 6: Install Hook Scripts

```
[6/7] Installing hook scripts...
```

```bash
mkdir -p ~/.claude/scripts
```

For each script in `{KIT_DIR}/spec-stateflow-kit-installer/scripts/`:

1. If `~/.claude/scripts/{script}` exists → ask "⚠️ {script} already exists, overwrite? (y/n)" → skip if declined
2. Copy: `cp {KIT_DIR}/spec-stateflow-kit-installer/scripts/{script} ~/.claude/scripts/`
3. Set executable: `chmod +x ~/.claude/scripts/{script}`
4. Report: `✅ {script} → ~/.claude/scripts/`

### Step 7: Configure settings.json

```
[7/7] Configuring ~/.claude/settings.json...
```

Load or create `~/.claude/settings.json` (create as `{}` if not exists). Then merge the following entries using Python:

**Hook entries to add:**

```json
{
  "hooks": {
    "Stop": [
      {"command": "~/.claude/scripts/spec-stop-anchor.sh"}
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "command": "~/.claude/scripts/spec-state-guard.sh"
      }
    ]
  }
}
```

**allowedTools entries to add:**

Base kit tools:
```
Read, Write, Edit, Glob, Grep,
Bash(git *), Bash(find *), Bash(ls *), Bash(cat *), Bash(python3 *), Bash(npm run *)
```

Also merge any patterns from `spec-env.json` `allowed_bash_patterns` array.

**Merge rules:**
- Existing hook with same `command` string → prompt user "⚠️ hook already exists, overwrite? (y/n)", default: keep existing
- Duplicate `allowedTools` entry (exact string match) → silently skip
- Report: `✅ settings.json: N hook entries added, M allowedTools entries added`

### Install Completion Report

```
✅ Spec kit installation complete!

  📁 Workspace: {WORKSPACE}
  📁 Spec docs: {WORKSPACE}/{DOC_DIR}
  🔧 Claude Code: {CLAUDE_CLI}
  📂 Skills dir: {SKILLS_DIR}

  Installed Skills (claw side):
    ✅ spec-stateflow-kit-installer
    ✅ spec-task-progress
    ✅ claude-code-spec-driver
    ✅ claude-code-spec-monitor  (self-test passed)
    [or]
    ⚠️ claude-code-spec-monitor  REMOVED — self-test failed (see above)

  Installed Skills (Claude Code side):
    ✅ spec-stateflow → ~/.claude/skills/spec-stateflow/
    ✅ spec-task-progress → ~/.claude/skills/spec-task-progress/
    ✅ spec-router → ~/.claude/skills/spec-router/  [alwaysApply]

  Configured:
    ✅ spec-env.json → ~/.claude/spec-env.json (path resolution unified)
    ✅ spec-stop-anchor.sh → ~/.claude/scripts/
    ✅ spec-state-guard.sh → ~/.claude/scripts/
    ✅ settings.json: Stop hook + PostToolUse hook added
    ✅ settings.json: allowedTools {N} entries added

  Validated:
    ✅ spec-env.json path alignment correct
    ✅ Scripts load spec-env.json successfully
    ✅ CLAUDE_CLI: {version}
    ✅ WORKSPACE: exists

  💡 Say "check task progress" to start using
```

---

## Mode 2: Uninstall

Remove all spec-related components from the system. Your spec documents in `{WORKSPACE}/{DOC_DIR}` are **never touched**.

### Step 1: Pre-check — Confirm Uninstall

⛔ **Checkpoint**: Scan all spec components and confirm with the user before removing anything.

```
Checking for spec kit components...

  [claw side]
  spec-env.json (claw):              {found at {SKILLS_DIR}/../spec-env.json / not found}
  spec-task-progress:                {found at {SKILLS_DIR}/spec-task-progress/ / not found}
  claude-code-spec-driver:           {found at {SKILLS_DIR}/claude-code-spec-driver/ / not found}
  claude-code-spec-monitor:          {found at {SKILLS_DIR}/claude-code-spec-monitor/ / not found}
  spec-stateflow-kit-installer:      {found at {SKILLS_DIR}/spec-stateflow-kit-installer/ / not found}

  [Claude Code side]
  spec-stateflow:                    {found at ~/.claude/skills/spec-stateflow/ / not found}
  spec-task-progress (Claude Code):  {found at ~/.claude/skills/spec-task-progress/ / not found}
  spec-router:                       {found at ~/.claude/skills/spec-router/ / not found}
  spec-env.json (Claude Code):       {found at ~/.claude/spec-env.json / not found}
  spec-stop-anchor.sh:               {found at ~/.claude/scripts/spec-stop-anchor.sh / not found}
  spec-state-guard.sh:               {found at ~/.claude/scripts/spec-state-guard.sh / not found}
  settings.json hook entries:        {found N entries / not found}
  settings.json allowedTools:        {found N entries / not found}
  spec-session.json:                 {found at ~/.claude/spec-session.json / not found}

  [Running processes]
  monitor daemon:                    {running (PID {pid}) / not running}

  ✅ Your spec documents at {WORKSPACE}/{DOC_DIR} will NOT be removed.
  ✅ ~/.claude/CLAUDE.md will NOT be modified.

⚠️ This will remove ALL listed components including the installer itself.
   After removal, re-install by telling the agent the original kit path again.
   Continue? (y/n)
```

User declines → abort.

### Step 2: Stop Running Monitor Processes

Stop all running monitor daemon instances **before** deleting any skill files.

```bash
for pid_file in /tmp/claude-monitor-*.pid; do
    [ -f "$pid_file" ] || continue
    PID=$(cat "$pid_file" 2>/dev/null)
    if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
        kill "$PID" 2>/dev/null
        sleep 1
        kill -0 "$PID" 2>/dev/null && kill -9 "$PID" 2>/dev/null
        echo "✅ Stopped monitor process $PID"
    else
        echo "⏭️  No active process for $pid_file, skipped"
    fi
done
```

### Step 3: Remove spec-env.json (claw side)

```bash
rm -f "{SKILLS_DIR}/../spec-env.json"
echo "✅ spec-env.json (claw side) removed"
```

### Step 4: Remove Skills (claw side)

```bash
for skill in spec-task-progress claude-code-spec-driver claude-code-spec-monitor spec-stateflow-kit-installer; do
    if [ -d "{SKILLS_DIR}/$skill" ]; then
        rm -rf "{SKILLS_DIR}/$skill"
        echo "✅ $skill removed"
    else
        echo "⏭️  $skill not found, skipped"
    fi
done
```

### Step 5: Remove Claude Code Skills

This step removes **three** skills from `~/.claude/skills/`.

**Part A — spec-stateflow:**

```bash
if [ -d "$HOME/.claude/skills/spec-stateflow" ]; then
    rm -rf "$HOME/.claude/skills/spec-stateflow"
    echo "✅ spec-stateflow removed"
else
    echo "⏭️  spec-stateflow not found, skipped"
fi
```

**Part B — spec-task-progress (Claude Code side):**

```bash
if [ -d "$HOME/.claude/skills/spec-task-progress" ]; then
    rm -rf "$HOME/.claude/skills/spec-task-progress"
    echo "✅ spec-task-progress (Claude Code) removed"
else
    echo "⏭️  spec-task-progress (Claude Code) not found, skipped"
fi
```

**Part C — spec-router:**

```bash
if [ -d "$HOME/.claude/skills/spec-router" ]; then
    rm -rf "$HOME/.claude/skills/spec-router"
    echo "✅ spec-router removed"
else
    echo "⏭️  spec-router not found, skipped"
fi
```

### Step 6: Remove spec-env.json (Claude Code side)

```bash
if [ -f "$HOME/.claude/spec-env.json" ]; then
    rm -f "$HOME/.claude/spec-env.json"
    echo "✅ ~/.claude/spec-env.json removed"
else
    echo "⏭️  ~/.claude/spec-env.json not found, skipped"
fi
```

### Step 7: Remove settings.json Hook + allowedTools Entries

Load `~/.claude/settings.json` and remove spec kit entries:

```python
# Identify entries to remove:
# Stop hooks: command contains "spec-stop-anchor.sh"
# PostToolUse hooks: command contains "spec-state-guard.sh"
# allowedTools: exact string match against kit tools list

KIT_TOOLS = [
    "Read", "Write", "Edit", "Glob", "Grep",
    "Bash(git *)", "Bash(find *)", "Bash(ls *)",
    "Bash(cat *)", "Bash(python3 *)", "Bash(npm run *)"
]

# Load settings, prune matching entries
# After pruning: if hooks['Stop'] becomes [] → keep [] (don't remove key)
# After pruning: if allowedTools becomes [] → keep [] (don't remove key)
# Report: "Removed N hook entries, M allowedTools entries"
```

### Step 8: Remove Hook Scripts

```bash
for script in spec-stop-anchor.sh spec-state-guard.sh; do
    if [ -f "$HOME/.claude/scripts/$script" ]; then
        rm -f "$HOME/.claude/scripts/$script"
        echo "✅ ~/.claude/scripts/$script removed"
    else
        echo "⏭️  ~/.claude/scripts/$script not found, skipped"
    fi
done
# Note: ~/.claude/scripts/ directory itself is not removed (may contain other user scripts)
```

### Step 9: Remove spec-session.json

```bash
if [ -f "$HOME/.claude/spec-session.json" ]; then
    rm -f "$HOME/.claude/spec-session.json"
    echo "✅ ~/.claude/spec-session.json removed"
else
    echo "⏭️  ~/.claude/spec-session.json not found, skipped"
fi
```

### Step 10: Cleanup /tmp state files

```bash
rm -f /tmp/claude-monitor-*.json /tmp/claude-monitor-*.pid /tmp/claude-monitor-*.lock /tmp/claude-monitor-*-daemon.log /tmp/claude-spec-*.log
echo "✅ /tmp state files cleaned up"
```

If any file cannot be removed, warn and continue:
> ⚠️ Could not remove some /tmp state files. They are harmless and will be cleaned up on next reboot.

### Uninstall Completion Report

```
✅ Spec kit uninstall complete!

  Removed:
    ✅ spec-env.json                  (claw side)
    ✅ spec-task-progress             (claw side)
    ✅ claude-code-spec-driver
    ✅ claude-code-spec-monitor
    ✅ spec-stateflow-kit-installer
    ✅ spec-stateflow                 (Claude Code side)
    ✅ spec-task-progress             (Claude Code side)
    ✅ spec-router                    (Claude Code side)
    ✅ ~/.claude/spec-env.json
    ✅ settings.json hook entries
    ✅ settings.json allowedTools entries
    ✅ spec-stop-anchor.sh
    ✅ spec-state-guard.sh
    ✅ spec-session.json
    ✅ /tmp state files

  ✅ Preserved:
    📁 Spec documents at {WORKSPACE}/{DOC_DIR} — untouched
    📄 ~/.claude/CLAUDE.md — untouched

  ℹ️ To re-install: tell the agent "install spec kit at {original_kit_path}"
     The agent reads SKILL.md directly from the kit directory — no copying required.
```

---

## Exception Handling

| Scenario | Mode | Handling |
|----------|------|----------|
| Claude Code not installed | Install | Abort at Step 1, prompt user to install first |
| SKILLS_DIR cannot be detected | Any | Run fallback detection; if still unknown, ask user |
| SKILLS_DIR not writable | Install | Warn user: "Cannot write to {SKILLS_DIR} (permission denied). Fix permissions." Abort |
| spec-env.json already exists | Install | Overwrite silently (no prompt) |
| spec-env.json is corrupted (invalid JSON) | Install | Warn user, offer to overwrite with fresh config |
| Path alignment check fails | Install | Abort at Step 4 with clear diagnosis |
| Smoke test fails (spec-env.json not loadable) | Install | Abort at Step 4, diagnose path arithmetic |
| ~/.claude/scripts/ not writable | Install | Warn user, skip Step 6 |
| settings.json is corrupted | Install | Warn user, offer to reset to `{}` before merging |
| WORKSPACE directory doesn't exist | Install | Require user to re-enter valid path |
| No spec components found | Uninstall | Inform "Nothing to uninstall", abort |
| Monitor process cannot be killed (Step 2) | Uninstall | Warn user with PID; continue removing files; advise `kill -9 {PID}` or reboot |
| /tmp state file removal fails (Step 10) | Uninstall | Warn "could not remove some /tmp files"; continue; advise reboot for cleanup |

## Bundled Resources

| Resource | Purpose |
|----------|---------|
| `scripts/spec-stop-anchor.sh` | Stop Hook script — deployed to `~/.claude/scripts/` in Step 6 |
| `scripts/spec-state-guard.sh` | PostToolUse Hook script — deployed to `~/.claude/scripts/` in Step 6 |
| `spec-env.json.example` | Reference example showing the spec-env.json format — not read by the installer |

## Testing

When user inputs `test installer`, `测试 installer`, or `test spec-installer`:

> **Scope**: Tests the installer's decision logic using fixture data. Does **not** write any files, copy any skills, or touch any config — purely logic verification. Safe to run at any time.

1. Locate `test-cases/` directory relative to this SKILL.md
2. For each subdirectory (tc01, tc02, …) in order:
   - Read `input.json`
   - Apply the relevant installer logic from this SKILL.md to the input
   - Read `expected.json`
   - Compare computed result against expected fields
   - Report PASS or FAIL with details
3. Output summary: `N/M cases passed`

| Category | Cases | What is tested |
|----------|-------|----------------|
| Language detection | tc01–tc04 | CLAUDE.md content + request phrase → `cjk` or `english` |
| Marker detection | tc05–tc07 | CLAUDE.md content → marker status and required action |
| Legacy keyword detection | tc08 | CLAUDE.md without markers → legacy keyword scan result |

**Example test run output:**
```
spec-installer 测试结果：

tc01-lang-detect-cjk-above-threshold     PASS
tc02-lang-detect-english-below-threshold PASS
tc03-lang-detect-empty-cjk-request       PASS
tc04-lang-detect-empty-english-request   PASS
tc05-marker-balanced                     PASS
tc06-marker-none-no-legacy               PASS
tc07-marker-unbalanced                   PASS
tc08-legacy-keywords-no-markers          PASS

8/8 cases passed ✓
```

---

## Notes

- **Installer removed on uninstall**: The installer skill (`{SKILLS_DIR}/spec-stateflow-kit-installer/`) is removed during uninstall. To re-install, tell the agent the kit directory path (e.g. "install spec kit at ~/Desktop/spec-stateflow-kit"). The agent reads `spec-stateflow-kit-installer/SKILL.md` directly from the kit source directory — no manual copying required.
- **How install is triggered**: The agent reads `{KIT_DIR}/spec-stateflow-kit-installer/SKILL.md` directly from the kit directory provided by the user. The skill self-copies to `{SKILLS_DIR}` during Step 3. No pre-installation of the skill into SKILLS_DIR is needed.
- **Post-install**: The source package `{KIT_DIR}` can be kept or moved; runtime only uses `{SKILLS_DIR}`
- **Runtime config**: Paths in both `spec-env.json` copies can be manually edited; all skills read dynamically at runtime. Sync both copies if edited manually.
- **spec-env.json copies**: Claw side at `{SKILLS_DIR}/../spec-env.json`; Claude Code side at `~/.claude/spec-env.json`. Both contain the same content and are kept in sync by the installer.
