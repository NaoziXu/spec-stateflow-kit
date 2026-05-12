---
name: claude-code-spec-driver
description: "Generate Claude Code prompts based on spec task progress to drive continued development. Triggers: let claude code continue development, continue task execution, drive development, spec driver, keep going, continue working, test spec-driver, verify driver. Used when user wants Claude Code to continue development based on spec documents, or wants to verify driver logic is working correctly."
alwaysApply: false
---

# Claude Code Spec Driver

Generate prompts based on spec task progress from tasks.md to drive Claude Code to continue development.

## Environment Configuration

Paths are read from `{SKILLS_DIR}/../spec-env.json`, no hardcoding:

```json
{
  "WORKSPACE": "/path/to/workspace",
  "DOC_DIR": "doc",
  "CLAUDE_CLI": "/path/to/claude"
}
```

- **doc directory**: `{WORKSPACE}/{DOC_DIR}/` (assembled by scripts at runtime)
- **Project directory**: Read from `project_name` field in `{SPEC_PATH}/progress.json` (see Step 2)
- **Claude Code CLI**: Read from `CLAUDE_CLI` in spec-env.json

**⚠️ If `spec-env.json` doesn't exist**: Prompt user to install spec kit first.

## Pre-check

Must confirm before execution:

```bash
# 1. Claude Code is available (path read from spec-env.json)
{CLAUDE_CLI} --version

# 2. Workspace directory exists
ls {WORKSPACE}/
```

Abort on any failure, inform user.

## Decision Routing

| User Input | Execution Path | Default Mode |
|-----------|---------------|--------------|
| Contains task ID (e.g. "586742") | -> Single task drive | Standard |
| "continue development" / "keep going" | -> Query all tasks, select unfinished ones | Standard |
| Specifies task range (e.g. "do Task 16-20") | -> Limited range drive | Standard |
| No specific task | -> Query overview, let user choose | Standard |
| "how's the progress" / "where is it at" | -> Only query progress, don't start Claude Code | -- |
| "test spec-driver" | -> Self-Test | -- |

> **Mode override:** If the user explicitly says phrases like `"you may continue implementing"`, `"complete the rest without asking"`, `"continuous mode"`, or `"keep going without asking"`, switch to **Continuous Operation Mode** for this drive. Ambiguous confirmations (`OK` / `continue` / `okay`) do **not** activate Continuous Mode.

## Execution Flow

**Quick flow (task ID provided, Standard Mode):**
1. Read/refresh `progress.json` → `is_complete`? → YES: inform & abort / NO: continue
2. Locate spec dir + confirm project dir + check workspace
3. ⛔ Confirm mode → generate prompt → ⛔ show to user
4. Launch Claude Code in background (`nohup`)
5. Report log path + progress check commands

---

### Step 1: Query Progress

Read `{SPEC_PATH}/progress.json`. If the file is missing or `updated_at` is older than 15 minutes, trigger the `spec-task-progress` skill by sending the prompt `{task_id} progress query` — wait for it to write a fresh `progress.json` before continuing.

Check the returned data:

- **`is_complete: true`** → Inform user "Task {task_id} is already complete. No further execution needed." and **abort** (do not launch Claude Code).
- **`is_complete: false`** → Continue.

**When no task ID is provided** (routing: "No specific task" or "continue development"):
0. If `{SPEC_DIR}` has no subdirectories → inform user "No spec tasks found. Create one with spec-stateflow first." and **abort**
1. Scan `{SPEC_DIR}` for spec directories → list their task IDs and names to user
2. Ask: "Which task would you like to continue? (or reply with the task ID)"
3. Wait for user to select → proceed with the selected task ID

### Step 2: Locate Document Path + Confirm Project Directory + Check Workspace

```bash
# Match spec directory with glob
ls {WORKSPACE}/{DOC_DIR}/*<task_id>*/

# Confirm project directory
# 1. Check project_name field in progress.json
python3 -c "import json; d=json.load(open('{SPEC_PATH}/progress.json')); print(d.get('project_name',''))" 2>/dev/null
# 2. No project_name -> list WORKSPACE directories for user to choose
ls {WORKSPACE}/
# 3. Write after user confirmation — update project_name in progress.json (atomic)
python3 -c "
import json, os
p = '{SPEC_PATH}/progress.json'
d = json.load(open(p)) if os.path.exists(p) else {}
d['project_name'] = '{project_name}'
tmp = p + '.tmp'
json.dump(d, open(tmp,'w'), ensure_ascii=False, indent=2)
os.replace(tmp, p)
"

# Check workspace
cd {WORKSPACE}/{project_name} && git status --short
```

Confirm `{SPEC_PATH}` = matched directory full path.

⚠️ **When multiple directories match**: List all matches for user to choose, don't auto-pick the first one.

Workspace status check:
- Has uncommitted changes: Append workspace protection statement to prompt
- Workspace clean: Generate normally
- Has untracked files (new files): Normal, may be from previous Claude Code run

### Step 3: Select Mode + Generate Prompt + User Confirmation ⛔

**3.1 Determine execution mode**

| Mode | Trigger | Behavior |
|------|---------|----------|
| **Standard Mode (default)** | No explicit continuous authorization from user | Claude Code executes one task, updates `tasks.md`, then **stops and waits for user review/approval** before the next task |
| **Continuous Operation Mode** | User explicitly authorizes (e.g. `"you may continue implementing"`, `"complete the rest without asking"`, `"continuous mode"`) | Claude Code auto-advances to the next `[ ]` task after each completion without asking |

⛔ **Checkpoint: Confirm mode with user before generating prompt.** Ask: `"Generate prompt in [Standard / Continuous] mode -- confirm?"`

**3.2 Placeholder extraction rules**

| Placeholder | Source | Extraction Method |
|------------|--------|------------------|
| `{SPEC_DIR}` | spec-env.json | `{WORKSPACE}/{DOC_DIR}/` — root directory containing all spec folders |
| `{task_name}` | Spec directory name | Take everything after the first **numeric segment** (e.g. `586742-remove-service-foundation-dependency` → `remove-service-foundation-dependency`, `T-EE-586742-remove-service-foundation-dependency` → `remove-service-foundation-dependency`). If no numeric segment is found, fall back to everything after the first dash. |
| `{SPEC_PATH}` | Step 2 match result | Full directory path of the matched spec folder |

**3.3 Prompt templates**

> **Language note**: Prompt templates are intentionally in English — Claude Code performs best with English prompts regardless of the user's interface language.

**Standard Mode (default):**

```
I have previously generated documents through spec-stateflow. Please continue development based on the existing task documents. The task is {task_name}, and the document path is {SPEC_PATH}. Please execute tasks one by one. After completing each task:
1. Update tasks.md and mark the corresponding task status
2. Fill in the Verification and Commit fields
3. Stop and wait for my review and explicit approval before proceeding to the next task. Do not auto-advance.
```

**Continuous Operation Mode:**

```
I have previously generated documents through spec-stateflow. Please continue development based on the existing task documents. The task is {task_name}, and the document path is {SPEC_PATH}. You need to first check and update the spec documents to the latest progress, ensuring the task status in tasks matches the actual engineering state. After that, you should continue implementation autonomously using continuous mode without requiring my confirmation. After completing each small task, promptly update the progress in tasks.md, submit a git commit, and then proceed to the next task.
```

**Optional appendages (based on Step 2 check results):**

| Scenario | Appended Content |
|----------|-----------------|
| Workspace has uncommitted changes | `Note: There are uncommitted changes in the workspace. Do not git checkout to discard them. Check git status first to understand the current state, then continue from there.` |
| Limited task range | `Start from Task {start_number} and complete through Task {end_number}.` |
| Starting from specific task | `Current progress: Task 0-{last_completed_number} done, starting from Task {next_number}.` |

⛔ **Checkpoint: Display the generated prompt to user, confirm before launching Claude Code.**

### Step 4: Execute Claude Code

**Background run command (fixed log file, append mode):**

```bash
cd {PROJECT_DIR} && nohup {CLAUDE_CLI} \
  -p "{Step 3 generated prompt}" \
  >> {SPEC_PATH}/worker.log 2>&1 &
echo "Launched. Log: {SPEC_PATH}/worker.log"
```

Where `{PROJECT_DIR}` and `{CLAUDE_CLI}` are dynamically obtained from spec-env.json, `{task_id}` is the numeric task ID.

**Parameter defaults:**

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--max-turns` | Maximum turns | Optional, unlimited if not set |

**Can also use launch_claude_spec.sh script:**

```bash
{SKILLS_DIR}/claude-code-spec-driver/scripts/launch_claude_spec.sh \
  --project-dir {PROJECT_DIR} \
  --task-id {task_id} \
  --prompt "{prompt}"
```

> **Note:** When used together with `claude-code-spec-monitor`, both use the same log file `{SPEC_PATH}/worker.log` in append mode. The monitor detects log growth to determine if the process is active.

### Step 5: Monitor Progress

After launch, proactively report to user:
1. Log file path
2. How to check progress

```bash
# View output
tail -50 {SPEC_PATH}/worker.log

# Check if matching claude processes exist
ps -ewwo pid,etime,command | grep -v grep | grep claude | grep {task_id}

# Check new commits (most reliable progress indicator)
cd {PROJECT_DIR} && git log --oneline -5
```

To query the latest progress, invoke the `spec-task-progress` skill with the task ID.

## Exception Handling

| Scenario | Handling |
|----------|----------|
| spec-env.json doesn't exist | Prompt "Please install spec kit first", abort |
| SPEC_DIR has no spec directories | Inform user "No spec tasks found. Create one with spec-stateflow first." and abort |
| Spec directory doesn't exist for task ID | List all directories under doc for user to choose |
| Multiple directories match same ID | List all matches for user to choose |
| Invalid/non-existent task ID | Inform user, run full overview for selection |
| progress.json is_complete=true | Inform user "Task is already complete. No further execution needed.", abort |
| Claude Code not installed / CLAUDE_CLI path invalid | Run `{CLAUDE_CLI} --version`, inform user to install first or fix spec-env.json |
| Claude Code process exits immediately | Check logs, common causes: auth expired, model unavailable |
| Compilation failure | Claude Code will handle itself, inform user if it keeps failing |

## Complete Example

User says "Let Claude Code continue 586742", full execution:

```bash
# Step 1: Read progress.json (invoke spec-task-progress skill if stale/missing)
# Check: is_complete=false → continue; is_complete=true → abort

# Step 2: Locate docs + confirm project + check workspace
# Read from spec-env.json: WORKSPACE={WORKSPACE}, DOC_DIR=doc
ls {WORKSPACE}/doc/*586742*/
# -> {WORKSPACE}/doc/586742-remove-service-foundation-dependency/
python3 -c "import json; d=json.load(open('{SPEC_PATH}/progress.json')); print(d.get('project_name',''))" 2>/dev/null
# -> {project_name}
cd {WORKSPACE}/{project_name} && git status --short

# Step 3: Generate prompt -> show to user for confirmation
# Step 4: Launch
cd {WORKSPACE}/{project_name} && nohup {CLAUDE_CLI} \
  -p "I have previously generated documents through spec-stateflow..." \
  >> {SPEC_PATH}/worker.log 2>&1 &

# Step 5: Report log path + progress
tail -50 {SPEC_PATH}/worker.log
cd {WORKSPACE}/{project_name} && git log --oneline -5
# To query progress: invoke spec-task-progress skill with task ID 586742
```

## Testing

When user inputs `test spec-driver`:

> **Scope**: Tests the driver's decision logic using fixture data. No files are written, no Claude Code is launched — purely logic verification.

1. Locate `test-cases/` directory relative to this SKILL.md
2. For each subdirectory (tc01, tc02, …) in order:
   - Read `input.json`
   - Apply the relevant driver logic from this SKILL.md to the input
   - Read `expected.json`
   - Compare computed result against expected fields
   - Report PASS or FAIL with details
3. Output summary: `N/M cases passed`

| Category | Cases | What is tested |
|----------|-------|----------------|
| Routing | tc01–tc03 | User phrase → correct execution path (single_task / query_all / progress_only) |
| Mode detection | tc04–tc07 | Explicit vs ambiguous authorization → Standard / Continuous mode |
| Task name extraction | tc08–tc10 | Spec directory name → `{task_name}` placeholder value |
| Abort conditions | tc11 | is_complete=true → abort without launching Claude Code |
| Prompt assembly | tc12 | Workspace status → correct template and appendages |

For prompt assembly tests (tc12), `prompt_contains` and `prompt_not_contains` are lists of substrings. The generated prompt must contain **all** `prompt_contains` strings and **none** of the `prompt_not_contains` strings. Matching is case-sensitive; expected values in `expected.json` must match the exact case produced by the prompt templates.

**Example test run output:**
```
spec-driver test results:

tc01-route-single-task            PASS
tc02-route-no-task                PASS
tc03-route-progress-only          PASS
tc04-mode-continuous-explicit-en  PASS
tc05-mode-continuous-explicit-zh  PASS
tc06-mode-ambiguous-ok            PASS
tc07-mode-ambiguous-continue-zh   PASS
tc08-task-name-numeric-prefix     PASS
tc09-task-name-alpha-then-numeric PASS
tc10-task-name-no-numeric-fallback PASS
tc11-abort-on-complete            PASS
tc12-prompt-workspace-protection  PASS

12/12 cases passed ✓
```

On FAIL, show the field diff:
```
tc06-mode-ambiguous-ok   FAIL
  expected: mode=standard
  got:      mode=continuous
```
