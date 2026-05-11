---
name: spec-stateflow-kit-installer
description: "Install or uninstall the Spec Stateflow Kit. Triggers: install spec kit, uninstall spec, spec-stateflow-kit-installer, initialize spec, remove spec, 安装spec, 卸载spec, 初始化spec, test installer, 测试 installer, test spec-installer, verify installer. Manages skills, spec-env.json, CLAUDE.md injection (auto language detection), and spec-stateflow."
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

> ⚠️ Do NOT use `~/.claude/skills/` as SKILLS_DIR. That directory belongs to Claude Code and is where this installer deploys the Claude Code–side skills in Step 7. Using it as SKILLS_DIR would collapse the claw-side and Claude Code-side skill namespaces into one directory, breaking path resolution for both.

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
| spec-env.json | `{SKILLS_DIR}/../` | Centralized path configuration |
| claude.md spec content | `~/.claude/CLAUDE.md` | Spec-related rules — decision & workflow (auto-translated to match CLAUDE.md language) |
| claude-reference.md | `~/.claude/CLAUDE-reference.md` | Spec-related reference — dependency analysis, code standards, quality standards (auto-translated, same language as CLAUDE.md) |
| spec-stateflow | `~/.claude/skills/` | Claude Code side spec workflow skill |
| spec-task-progress（Claude Code 侧） | `~/.claude/skills/` | Claude Code 进度查询 skill（daemon spawn 时使用） |

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
   "{KIT_DIR}/spec-stateflow-kit-installer/claude-sample.md" \
   "{KIT_DIR}/spec-stateflow-kit-installer/claude-reference-sample.md"
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
  "CLAUDE_CLI": "{auto-detected or user specified}"
}
```

> ⚠️ `DOC_DIR` is a **directory name** (e.g. `"doc"`), not a full path. All skills compute the full path as `{WORKSPACE}/{DOC_DIR}` at runtime.

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
3. **Continue with Steps 4–7** — other components (claude.md, spec-stateflow, etc.) install normally.

### Step 4: Post-Installation Path Validation

```
[4/7] Validating installation paths...
```

This phase verifies the path arithmetic is correct before writing CLAUDE.md.

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

### Step 5: Configure Claude Code — claude.md (with language auto-detection + path-resolution prefix)

```
[5/7] Configuring Claude Code (claude.md)...
```

1. Read `~/.claude/CLAUDE.md` (create empty file if not exists).
2. **Detect existing kit injection** by searching for the marker `<!-- SPEC_STATEFLOW_KIT_BEGIN -->`.
3. If marker present → prompt `Spec config already exists (BEGIN/END marker found), overwrite? (y/n)`:
   - User confirms → remove the existing block (everything from `<!-- SPEC_STATEFLOW_KIT_BEGIN -->` through `<!-- SPEC_STATEFLOW_KIT_END -->`, inclusive) before continuing.
   - User declines → skip Step 5 entirely.
4. **Auto-detect language** by analysing the (post-removal) text content of `~/.claude/CLAUDE.md`:
   - Calculate CJK ratio using this logic:
     ```python
     import re
     content = open(os.path.expanduser("~/.claude/CLAUDE.md")).read()
     cjk_pattern = re.compile(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]')
     non_ws = re.sub(r'\s', '', content)
     cjk_count = len(cjk_pattern.findall(non_ws))
     ratio = cjk_count / len(non_ws) if non_ws else 0
     is_cjk = ratio > 0.3
     ```
   - `is_cjk == True` → target language is CJK (translate to Chinese).
   - `is_cjk == False` → target language is English.
   - CLAUDE.md is empty/new (no non-whitespace content after removal): look at the language of the user's current installation request instead — if the user wrote in Chinese (CJK characters present in the request), use CJK; otherwise default to English.
5. **Read `claude-sample.md`** from `{KIT_DIR}/spec-stateflow-kit-installer/`.
   - CJK target → translate the ENTIRE body to Chinese while preserving markdown structure, code blocks, and **placeholders verbatim**.
   - English target → use as-is.
   - **Critical: do NOT substitute placeholders in the body.** `{SPEC_DIR}`, `{SPEC_NAME}`, `{SPEC_PATH}`, `{CLAUDE_CLI}`, `{WORKSPACE}`, `{DOC_DIR}` must remain as literal text. The body teaches their meaning; the path-resolution prefix (built next) supplies the actual values.
6. **Build the path-resolution prefix block** using values from `{SKILLS_DIR}/../spec-env.json`. This is the only place where actual paths are filled in.

   English form:
   ```markdown
   ## Spec Path Resolution

   | Placeholder | Meaning | Actual Value |
   |-------------|---------|--------------|
   | `{SPEC_DIR}` | Spec file root directory | `<WORKSPACE>/<DOC_DIR>/` |
   | `{SPEC_NAME}` | Current Spec name (varies per task) | `<TaskID>-<TaskDescription>` |
   | `{SPEC_PATH}` | Full path | `{SPEC_DIR}/{SPEC_NAME}` |
   | `{CLAUDE_CLI}` | Claude Code CLI binary | `<CLAUDE_CLI>` |
   ```

   CJK form:
   ```markdown
   ## Spec 路径解析

   | 占位符 | 含义 | 实际值 |
   |-------|------|-------|
   | `{SPEC_DIR}` | Spec 文件根目录 | `<WORKSPACE>/<DOC_DIR>/` |
   | `{SPEC_NAME}` | 当前 Spec 名称（按任务变化） | `<TaskID>-<TaskDescription>` |
   | `{SPEC_PATH}` | 完整路径 | `{SPEC_DIR}/{SPEC_NAME}` |
   | `{CLAUDE_CLI}` | Claude Code CLI 程序 | `<CLAUDE_CLI>` |
   ```

   Substitute `<WORKSPACE>`, `<DOC_DIR>`, `<CLAUDE_CLI>` with the literal values from `spec-env.json`. Left-column entries stay as `{...}` text — they are the symbolic names the body refers to. `{SPEC_NAME}` and `{SPEC_PATH}` actual-value cells stay symbolic because they vary per task.
7. **Append the marker-wrapped block** to `~/.claude/CLAUDE.md`:

   ```
   <!-- SPEC_STATEFLOW_KIT_BEGIN -->
   {path-resolution prefix block from step 6}

   {translated claude-sample.md body from step 5, placeholders kept verbatim}
   <!-- SPEC_STATEFLOW_KIT_END -->
   ```

   The BEGIN/END markers are mandatory; uninstall depends on them — never omit.

   **Encoding safety — CRITICAL for CJK content:**
   When writing CJK (Chinese/Japanese/Korean) text to `~/.claude/CLAUDE.md`, some agent write tools may corrupt UTF-8 characters. To prevent garbled output, use **one of these safe write methods** (in order of preference):

   **Method A — `cat` heredoc (safest for bash):**
   ```bash
   cat <<'EOF' >> ~/.claude/CLAUDE.md
   <!-- SPEC_STATEFLOW_KIT_BEGIN -->
   {content here}
   <!-- SPEC_STATEFLOW_KIT_END -->
   EOF
   ```

   **Method B — Python with explicit UTF-8:**
   ```bash
   python3 -c "
   import codecs
   content = '''{escaped_content}'''
   with codecs.open('$HOME/.claude/CLAUDE.md', 'a', 'utf-8') as f:
       f.write(content)
   "
   ```

   **Method C — `printf` with escape sequences (fallback):**
   ```bash
   printf '%s\n' '{line1}' '{line2}' ... >> ~/.claude/CLAUDE.md
   ```

   > ⚠️ **Avoid direct agent `Write` tool for CJK content** unless you have verified it handles UTF-8 correctly. If the written file shows方块/乱码 when read back with `cat`, the encoding was corrupted — re-write using Method A or B above.

### Step 6: Configure Claude Code — claude-reference.md (same language as CLAUDE.md + path-resolution prefix)

```
[6/7] Configuring Claude Code (claude-reference.md)...
```

1. Read `claude-reference-sample.md` from `{KIT_DIR}/spec-stateflow-kit-installer/` (English base template).
2. Use the same target language detected in Step 5:
   - CJK → translate the ENTIRE body to Chinese while preserving markdown structure, code blocks, and **placeholders verbatim**.
   - English → use as-is.
3. **Critical: do NOT substitute placeholders in the body.** `{SPEC_DIR}`, `{SPEC_NAME}`, `{SPEC_PATH}`, `{CLAUDE_CLI}` etc. must remain as literal text — same rule as Step 5. The path-resolution prefix block (built next) supplies the actual values.
4. **Build the path-resolution prefix block** using the same template and values from `spec-env.json` — same English/CJK forms shown in Step 5 sub-step 6 above, chosen based on detected language.
5. Check if `~/.claude/CLAUDE-reference.md` exists.
   - Yes → prompt `⚠️ CLAUDE-reference.md already exists, overwrite? (y/n)` → skip Step 6 if declined.
6. **Write the file** with this layout (the entire file IS the kit injection — no inline markers needed because uninstall removes the whole file):

   ```
   {path-resolution prefix block built in step 6 item 4 above}

   {translated claude-reference-sample.md body from step 2, placeholders kept verbatim}
   ```

   **Encoding safety — same rule as Step 5:**
   For CJK content, do **not** rely on direct agent file-write tools. Use one of the safe methods from Step 5 (heredoc `cat`, Python with `codecs.open(..., 'utf-8')`, or `printf`). Since this is a full file overwrite (not append), use `'w'` mode instead of `'a'`:

   ```bash
   cat <<'EOF' > ~/.claude/CLAUDE-reference.md
   {content here}
   EOF
   ```

   Or with Python:
   ```bash
   python3 -c "
   import codecs
   content = '''{escaped_content}'''
   with codecs.open('$HOME/.claude/CLAUDE-reference.md', 'w', 'utf-8') as f:
       f.write(content)
   "
   ```

7. Report: `✅ claude-reference.md installed (language: {detected_language})`

### Step 7: Install spec-stateflow + spec-task-progress to Claude Code

```
[7/7] Installing spec-stateflow + spec-task-progress (Claude Code side)...
```

This step installs **two** skills to `~/.claude/skills/`. Both are required — do not stop after the first.

**Part A — spec-stateflow:**

1. Ensure target directory: `mkdir -p ~/.claude/skills`
2. Check if `~/.claude/skills/spec-stateflow/` exists
3. If exists → ask "⚠️ spec-stateflow already exists, overwrite? (y/n)" → skip if declined
4. Copy: `cp -r {KIT_DIR}/spec-stateflow/ ~/.claude/skills/spec-stateflow/`
5. Report: `✅ spec-stateflow → ~/.claude/skills/spec-stateflow/`

**Part B — spec-task-progress (Claude Code side, REQUIRED):**

> This is the Claude Code–side copy of the progress skill. When the daemon spawns Claude Code via `claude -p`, Claude Code must be able to load this skill from `~/.claude/skills/`. The claw-side copy in `{SKILLS_DIR}/spec-task-progress/` is separate and serves a different purpose. Both must exist.
>
> In Claude Code context, this skill resolves `SPEC_DIR` by reading the `Spec 路径解析` table in `~/.claude/CLAUDE.md` (injected in Step 5). No hardcoded paths are used — path resolution is always dynamic at runtime.

6. Check if `~/.claude/skills/spec-task-progress/` exists
7. If exists → ask "⚠️ spec-task-progress already exists in Claude Code skills, overwrite? (y/n)" → skip if declined
8. Copy: `cp -r {KIT_DIR}/spec-task-progress/ ~/.claude/skills/spec-task-progress/`
9. Report: `✅ spec-task-progress → ~/.claude/skills/spec-task-progress/`

### Install Completion Report

```
✅ Spec kit installation complete!

  📁 Workspace: {WORKSPACE}
  📁 Spec docs: {WORKSPACE}/{DOC_DIR}
  🔧 Claude Code: {CLAUDE_CLI}
  📂 Skills dir: {SKILLS_DIR}

  Installed Skills:
    ✅ spec-stateflow-kit-installer
    ✅ spec-task-progress
    ✅ claude-code-spec-driver
    ✅ claude-code-spec-monitor  (self-test passed)
    [or]
    ⚠️ claude-code-spec-monitor  REMOVED — self-test failed (see above)

  Validated:
    ✅ spec-env.json → {SKILLS_DIR}/../spec-env.json
    ✅ Path alignment correct
    ✅ Scripts load spec-env.json successfully

  Configured:
    ✅ claude.md spec content injected (language: {detected_language})
    ✅ claude-reference.md installed (language: {detected_language})
    ✅ spec-stateflow → ~/.claude/skills/spec-stateflow/
    ✅ spec-task-progress → ~/.claude/skills/spec-task-progress/

  💡 Say "check task progress" to start using
```

---

## Mode 2: Uninstall

Remove all spec-related components from the system. Your spec documents in `{WORKSPACE}/{DOC_DIR}` are **never touched**.

### Step 1: Pre-check — Confirm Uninstall

⛔ **Checkpoint**: Scan all spec components and confirm with the user before removing anything.

```
Checking for spec kit components...

  [claw-side]
  spec-env.json:                     {found at {SKILLS_DIR}/../spec-env.json / not found}
  spec-task-progress:                {found at {SKILLS_DIR}/spec-task-progress/ / not found}
  claude-code-spec-driver:           {found at {SKILLS_DIR}/claude-code-spec-driver/ / not found}
  claude-code-spec-monitor:          {found at {SKILLS_DIR}/claude-code-spec-monitor/ / not found}
  spec-stateflow-kit-installer:      {found at {SKILLS_DIR}/spec-stateflow-kit-installer/ / not found}

  [Claude Code side]
  spec-stateflow:                    {found at ~/.claude/skills/spec-stateflow/ / not found}
  spec-task-progress (Claude Code):  {found at ~/.claude/skills/spec-task-progress/ / not found}
  claude.md spec content:            {found (markers present) / not found}
  CLAUDE-reference.md:               {found at ~/.claude/CLAUDE-reference.md / not found}

  [Running processes]
  monitor daemon:                    {running (PID {pid}) / not running}

  ✅ Your spec documents at {WORKSPACE}/{DOC_DIR} will NOT be removed.

⚠️ This will remove ALL listed components including the installer itself.
   After removal, re-install by telling the agent the original kit path again.
   Continue? (y/n)
```

User declines → abort.

### Step 2: Stop Running Monitor Processes

Stop all running monitor daemon instances **before** deleting any skill files. Deleting scripts while a daemon is running leaves orphan processes with no kill handle.

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

If a process cannot be killed:
> ⚠️ Could not stop monitor process {PID}. It may be a zombie or owned by another user. Proceeding with file removal. You may need to manually kill it (`kill -9 {PID}`) or reboot.

### Step 3: Remove spec-env.json

```bash
rm -f "{SKILLS_DIR}/../spec-env.json"
echo "✅ spec-env.json removed"
```

### Step 4: Remove Skills (claw-side)

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

### Step 5: Remove spec-stateflow + spec-task-progress (Claude Code side)

This step removes **two** skills from `~/.claude/skills/`. Both parts must be executed — do not stop after the first.

**Part A — spec-stateflow:**

```bash
if [ -d "$HOME/.claude/skills/spec-stateflow" ]; then
    rm -rf "$HOME/.claude/skills/spec-stateflow"
    echo "✅ spec-stateflow removed"
else
    echo "⏭️  spec-stateflow not found, skipped"
fi
```

**Part B — spec-task-progress (Claude Code side, REQUIRED):**

```bash
if [ -d "$HOME/.claude/skills/spec-task-progress" ]; then
    rm -rf "$HOME/.claude/skills/spec-task-progress"
    echo "✅ spec-task-progress (Claude Code) removed"
else
    echo "⏭️  spec-task-progress (Claude Code) not found, skipped"
fi
```

### Step 6: Remove spec content from CLAUDE.md

1. Check if `~/.claude/CLAUDE.md` exists → skip if not found.
2. **Marker-based removal (primary path)** — search for `<!-- SPEC_STATEFLOW_KIT_BEGIN -->` and `<!-- SPEC_STATEFLOW_KIT_END -->`:
   - Both markers found, balanced → log the line range being removed, then **auto-remove** (no additional confirmation needed — user already confirmed in Step 1): delete from `<!-- SPEC_STATEFLOW_KIT_BEGIN -->` through `<!-- SPEC_STATEFLOW_KIT_END -->` (inclusive); compress consecutive blank lines to max 1.
   - Only one marker present (unbalanced) → warn `⚠️ Unbalanced markers in CLAUDE.md — refusing automatic removal. Please inspect ~/.claude/CLAUDE.md manually.` and skip.
   - Neither marker found → fall through to legacy fallback (step 3).
3. **Legacy fallback (only when markers are absent)** — search for legacy spec keywords (`spec-stateflow`, `SPEC_DIR`, `Spec Workflow`, `Spec 路径约定`, `Spec 工作流`):
   - No keywords found → no spec content; skip.
   - Keywords found → preview and warn: `⚠️ No BEGIN/END markers — this install predates marker support. Auto-removal may affect content beyond the spec section. Continue with legacy 3-strategy removal? (y/n)`. On confirmation, execute **legacy 3-strategy removal** below. On decline, skip and suggest manual review.
4. Report: `✅ spec content removed from CLAUDE.md` or `⏭️ CLAUDE.md not modified`.

**Legacy 3-strategy removal (only when markers are absent — execute in order, stop at first success):**

| Strategy | Condition | Action |
|----------|-----------|--------|
| **A — Section header** (preferred) | Found header `# Claude Code Usage Guidelines` or `# Claude Code 使用规范` | Remove from that header line to end of file |
| **B — Keyword lines** (fallback) | No header but spec keywords exist | Remove lines containing keywords; compress consecutive blank lines to max 1 |
| **C — Manual** (last resort) | Neither header nor keywords found | Inform user, skip auto-removal, suggest manual review |

**Post-removal**: If file becomes empty/whitespace-only, keep file with no content.

### Step 7: Remove CLAUDE-reference.md

`CLAUDE-reference.md` is entirely generated by the installer and contains no user content — remove automatically.

```bash
if [ -f "$HOME/.claude/CLAUDE-reference.md" ]; then
    rm -f "$HOME/.claude/CLAUDE-reference.md"
    echo "✅ CLAUDE-reference.md removed"
else
    echo "⏭️  CLAUDE-reference.md not found, skipped"
fi
```

### Step 8: Cleanup /tmp state files

```bash
rm -f /tmp/claude-monitor-*.json /tmp/claude-monitor-*.pid /tmp/claude-monitor-*.lock /tmp/claude-monitor-*-daemon.log /tmp/claude-spec-*.log
echo "✅ /tmp state files cleaned up"
```

If any file cannot be removed (e.g. permission denied), warn and continue:
> ⚠️ Could not remove some /tmp state files. They are harmless and will be cleaned up on next reboot.

### Uninstall Completion Report

```
✅ Spec kit uninstall complete!

  Removed:
    ✅ spec-env.json
    ✅ spec-task-progress             (claw-side)
    ✅ claude-code-spec-driver
    ✅ claude-code-spec-monitor
    ✅ spec-stateflow-kit-installer
    ✅ spec-stateflow                 (Claude Code side)
    ✅ spec-task-progress             (Claude Code side)
    ✅ claude.md spec content
    ✅ CLAUDE-reference.md
    ✅ /tmp state files

  ✅ Preserved:
    📁 Spec documents at {WORKSPACE}/{DOC_DIR} — untouched

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
| claude.md already has spec content | Install | Ask whether to overwrite/append |
| claude.md is read-only / permission denied | Install/Uninstall | Warn user, skip this step |
| claude-reference.md already exists | Install | Ask whether to overwrite |
| WORKSPACE directory doesn't exist | Install | Require user to re-enter valid path |
| No spec components found | Uninstall | Inform "Nothing to uninstall", abort |
| Monitor process cannot be killed (Step 2) | Uninstall | Warn user with PID; continue removing files; advise `kill -9 {PID}` or reboot |
| /tmp state file removal fails (Step 8) | Uninstall | Warn "could not remove some /tmp files"; continue; advise reboot for cleanup |
| Language detection on empty CLAUDE.md | Install | Check request language first: CJK if user wrote in Chinese, otherwise default to English |
| CJK content written as garbled /方块乱码 | Install | Re-write using safe method from Step 5/6 (heredoc `cat` or Python `codecs.open(..., 'utf-8')`). Verify with `cat ~/.claude/CLAUDE.md` before proceeding to Step 7. |

## Bundled Resources

| Resource | Purpose |
|----------|---------|
| `claude-sample.md` | English base template for CLAUDE.md injection — decision & workflow rules (translated to CJK if auto-detected). **Placeholders (`{SPEC_DIR}`, `{SPEC_NAME}`, `{SPEC_PATH}`, `{CLAUDE_CLI}`, `{WORKSPACE}`, `{DOC_DIR}`) are kept verbatim in the body** so the body teaches their meaning; actual values are supplied by the path-resolution prefix block built by the installer (Install Step 5 step 6). |
| `claude-reference-sample.md` | English base template for CLAUDE-reference.md — dependency analysis, code standards, quality standards (translated to CJK, same language as CLAUDE.md). **Same placeholder rule as above.** |
| `spec-env.json.example` | Reference example showing the spec-env.json format — not read by the installer |

## Testing

When user inputs `test installer`, `测试 installer`, or `test spec-installer`:

> **Scope**: Tests the installer's decision logic using fixture data. Does **not** write any files, copy any skills, or touch CLAUDE.md — purely logic verification. Safe to run at any time.

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

**Language detection logic (applied to tc01–tc04):**
```python
import re
non_ws = re.sub(r'\s', '', claude_md_content)
cjk_count = len(re.findall(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]', non_ws))
ratio = cjk_count / len(non_ws) if non_ws else 0
is_cjk = ratio > 0.3
# If non_ws is empty: check request_phrase for CJK characters instead
```

**Marker detection logic (applied to tc05–tc08):**
- Both `<!-- SPEC_STATEFLOW_KIT_BEGIN -->` and `<!-- SPEC_STATEFLOW_KIT_END -->` present → `balanced`
- Only one present → `unbalanced`
- Neither present → `none` → then scan for legacy keywords: `spec-stateflow`, `SPEC_DIR`, `Spec Workflow`, `Spec 路径约定`, `Spec 工作流`

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

On FAIL, show the field diff:
```
tc01-lang-detect-cjk-above-threshold   FAIL
  expected: language=cjk
  got:      language=english
```

---

## Notes

- **Installer removed on uninstall**: The installer skill (`{SKILLS_DIR}/spec-stateflow-kit-installer/`) is removed during uninstall. To re-install, tell the agent the kit directory path (e.g. "install spec kit at ~/Desktop/spec-stateflow-kit"). The agent reads `spec-stateflow-kit-installer/SKILL.md` directly from the kit source directory — no manual copying required.
- **How install is triggered**: The agent reads `{KIT_DIR}/spec-stateflow-kit-installer/SKILL.md` directly from the kit directory provided by the user. The skill self-copies to `{SKILLS_DIR}` during Step 3. No pre-installation of the skill into SKILLS_DIR is needed.
- **Post-install**: The source package `{KIT_DIR}` can be kept or moved; runtime only uses `{SKILLS_DIR}`
- **Runtime config**: Paths in `spec-env.json` can be manually edited; all skills read dynamically at runtime
- **spec-env.json location**: Always at `{SKILLS_DIR}/../spec-env.json`. Python daemon scripts (`monitor_daemon.py` etc.) derive this path from `__file__` at runtime (3 levels up). The Claude Code–side `spec-task-progress` is an LLM skill with no Python scripts — it reads `SPEC_DIR` from the `Spec 路径解析` table in `~/.claude/CLAUDE.md`, not from `spec-env.json`.
