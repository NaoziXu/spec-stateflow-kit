---
name: spec-router
description: "Always-active spec workflow router — loaded every session. Routes all user requests: classifies tasks (Complex/Fix/Simple/Routine), handles continue/resume via Step 0 fast-path recovery, and resolves SPEC_DIR/SPEC_PATH from ~/.claude/spec-env.json. Activated on any dev task, 'continue', 'resume', 'check progress', or 'task status'."
alwaysApply: true
---

# Spec Workflow Router

> Always-active. Provides task classification, command routing, and path resolution.
> Full 4-phase workflow details: invoke the `spec-stateflow` skill.

## Path Resolution

Read `~/.claude/spec-env.json` at runtime:

```json
{
  "WORKSPACE": "/actual/workspace/path",
  "DOC_DIR": "doc",
  "CLAUDE_CLI": "/actual/path/to/claude"
}
```

- `SPEC_DIR` = `{WORKSPACE}/{DOC_DIR}/`
- `SPEC_PATH` = `{SPEC_DIR}/{TaskID}-{Description}/`

If `~/.claude/spec-env.json` does not exist: output "spec-env.json not found — please re-install the spec kit" and stop.

## Quick Decision

```
User Input
│
├─ Complex / multi-module / needs design / API change? ──→ Complex → Use spec-stateflow (full workflow)
│
├─ Bug fix / systematic refactoring? ──────────────────→ Fix → Use spec-stateflow (Phase 1-2 required)
│
├─ "continue" / "resume"? ──────────────────────────────→ Run Step 0 (below) → then invoke spec-stateflow Compression Recovery
│
├─ Single file / obvious fix / no design? ─────────────→ Simple → Execute directly, no Spec
│
└─ Routine / repetitive operation? ────────────────────→ Routine → Execute directly, no Spec
```

## Task Classification

| Type | Triggers | Action |
|------|----------|--------|
| **Complex** | Multi-module / needs design / API change | Use spec-stateflow (full Phase 1→4) |
| **Fix** | Bug fix / systematic tech debt / cross-module refactor | Use spec-stateflow (Phase 1-2 required) |
| **Simple** | Single file / single method / obvious fix / no design needed | Execute directly, no Spec |
| **Routine** | Repetitive operations (format, rename, config tweak) | Execute directly, no Spec |

> **Fix vs Simple boundary**: Fix = cross-module impact, or requires design before coding. Simple = localized, obvious fix in ≤1 file, no architectural implications.
>
> **Default bias**: When task type is uncertain, prefer Complex or Fix over Simple. A false positive (treating Simple as Complex) wastes one planning step. A false negative (treating Complex as Simple) loses all the work done without a Spec.

## Common Commands

| Command | Action |
|---------|--------|
| `continue` / `resume` | Step 0 (fast-path recovery) → invoke spec-stateflow Compression Recovery |
| `updatecode` | Read `{SPEC_PATH}/tasks.md` (resolve via spec-session.json); resume coding from first `[ ]` or `[~]` task |
| `check progress` / `task status` | Read `{SPEC_PATH}/tasks.md` (resolve via spec-session.json or ask user); display task list with statuses |

## Step 0: Session Context Recovery

`~/.claude/spec-session.json` fields:

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | string | Active spec ID, e.g. `SPEC-00042` |
| `is_complete` | bool | True if spec finished |
| `updated_at` | ISO-8601 string | Timestamp of last session stop |
| `spec_path` | string | Absolute path to spec directory |
| `active_task_num` | int | Current task number |
| `active_task_name` | string | Current task name |
| `active_task_scope` | string | Task scope summary |
| `active_task_specifics` | string | Task specifics detail |
| `git_head` | string | Short SHA recorded at session stop |

When user says "continue" / "resume", execute Step 0 before invoking spec-stateflow Compression Recovery:

```
1. Read ~/.claude/spec-session.json
   - Not found → skip to full 6-step Compression Recovery
   - Malformed / JSON parse error → treat as not found; skip to full 6-step Compression Recovery

2. Check updated_at
   - updated_at > 4 hours ago → stale; skip to full 6-step Compression Recovery

3. If is_complete == true:
   - Output: "Spec {task_id} is already complete. No recovery needed."
   - Ask user: "Do you want to review the completed spec or start a new task?"
   - Stop Step 0; do NOT enter Compression Recovery

4. If is_complete == false and updated_at within 4h:
   - Locate {spec_path} directory
   - If directory not found → skip to full 6-step Compression Recovery
   - Pre-load context: task_id, active_task_num, active_task_name, active_task_scope, active_task_specifics
   - Output: "Resuming {task_id} — Task {active_task_num}: {active_task_name}"
   - Check git_head: run `git rev-parse --short HEAD` in workspace
     - If command fails (non-git workspace or no commits): skip git_head check; proceed without warning
     - If git_head differs: output "⚠️ git HEAD changed since last session — Step 2 code verification required"
     - Force Step 2 (do not skip code verification)
   - → Invoke spec-stateflow: enter Compression Recovery at Step 2 (skip Step 1 directory scan)

5. Step 0 does NOT bypass Step 2 git verification — even with a valid session.json,
   if git_head changed or any [✓] rows exist, Step 2 is mandatory.
```
