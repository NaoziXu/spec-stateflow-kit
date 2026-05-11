# Claude Code Usage Guidelines

This document defines the standard for Claude Code collaboration. **The Spec workflow is fully implemented by the `spec-stateflow` skill (including planning and execution); this document does not re-define Spec implementation details.**

## Quick Decision

When receiving a user instruction, judge in the following order:

```
User Input
│
├─ Complex / multi-module / requires design / API change? ──→ YES → Needs Spec → Complex/Fix, follow Spec flow
│
├─ "continue" / "keep going" / "resume" with recovery semantics? ──→ Read tasks.md → locate breakpoint → continue
│
├─ "updatecode" ──→ Read current spec's tasks.md, resume coding from breakpoint. Flow: update progress → code → verify → commit
│
├─ Clear, simple, small-scope change? ──→ YES → Simple type, execute directly, no Spec needed
│
├─ Routine repetitive operation? ──→ Routine type, no Spec needed
│
└─ Uncertain ──→ Investigate → Reclassify
```

**Classification is the key decision point**: Don't create a Spec when unnecessary; must create one when needed.

---

## Task Classification

Choose different handling based on task complexity:

| Type | Applicable Scenarios | Handling |
|------|---------------------|----------|
| **Complex** | Multi-module / needs design / API change | Must follow 3 steps: use `spec-stateflow` to plan + generate tasks.md |
| **Fix** | Bug fix / systematic refactoring of tech debt | Must follow 2+ steps: use `spec-stateflow`, Phase 1-2 required, Phase 3 as needed |
| **Simple** | Single file/function change / config tweak / small code change | No Spec, execute directly, result in commit |
| **Routine** | Daily repetitive operations | No Spec |

**Default bias**: When uncertain, prioritize Complex/Fix over Simple.

**Special note**: When you judge Simple but the user explicitly requests a Spec, **you must follow the user's request** and treat as Complex.

**Simple boundaries**: A pure config change like "change timeout from 5s to 10s" can be done directly without Spec. But if it involves multiple related changes, it's not Simple.

---

## Spec Workflow 4-Phase Summary

**Before each task, determine whether a Spec needs to be created.** If yes, execute via `spec-stateflow` skill:

1. **Requirement analysis / confirmation** — Invoke `spec-stateflow`, complete Phase 1
2. **Technical design** — Design architecture based on requirements, output Spec design document
3. **Task breakdown** — Break down specific tasks into Spec
4. **Execute tasks and update progress** — Execute one by one
5. **After Spec completion** — Update `{SPEC_PATH}/tasks.md` final status

### Spec Execution Rules

- When receiving a task, **first ask "Should a Spec be created?"** rather than "Is this a complex task?"
- **Must confirm before creating Spec**: Confirm Spec scope and "clear definition", only start after confirmation
- Progress updates to `{SPEC_PATH}/tasks.md` for real-time tracking

> **Source of truth priority**: `{SPEC_PATH}/tasks.md` is the single source of truth, consistent with `spec-stateflow` skill's State Assurance.

**About Plan mode**: In Plan mode, just execute Plan-related tasks. The Spec workflow is a complete development process that doesn't need extra execution in Plan mode. Use Grep etc. for code search in Plan mode.

---

## Common Commands

| User Command | Claude Code Behavior |
|-------------|---------------------|
| `updatecode` | Read current spec's tasks.md, resume coding from breakpoint |
| "continue" / "resume" | Read `{SPEC_PATH}/tasks.md` and continue from breakpoint |
| "check progress" / "task status" | Read tasks.md and display current progress |

> For common development response templates and dependency analysis commands, see `CLAUDE-reference.md`.

---

## Code Change Management Rules

All code changes must follow these rules:

1. **Must confirm change scope and impact before change** — especially cross-module changes
2. **Must verify after change** — Use `git diff` to confirm change content and impact scope
3. **Must update related docs after change** — including design documents
4. **Must ensure compilation passes after change** — compilation passing is the minimum requirement
5. **Must commit after change** — Changes must be committed to version control

> For pre-change assessment commands and dependency impact analysis tables, see `CLAUDE-reference.md`.

---

## Session Recovery Flow

When encountering "This session is being continued from a previous conversation" or similar compression prompts, follow this flow:

### 1. First Confirm Current Spec Progress

Must confirm the following information during recovery:

| Information Item | How to Obtain | Required |
|-----------------|--------------|---------|
| Current task progress | Read tasks.md in latest spec directory | Yes |
| Git commit history | `git log --oneline -5` to confirm latest commits/changes | Yes |
| Git staging status | Check for uncommitted changes (e.g. `586742`) | Yes |
| Workspace status | Check for "in-progress" files | Yes |

**Recovery Decision**
- At least 1 completed task → **Continue executing current Spec task** (verify last `[✓]` task per spec-stateflow Compression Recovery Step 2)
- 0 completed tasks → **Continue from first `[ ]` or `[~]` task** (skip verification, jump to Step 4 per spec-stateflow Compression Recovery)

### 2. Resume Execution

After recovery, continue executing Spec tasks

1. **Confirm latest changes**: Check git commit/staging for uncommitted changes, confirm these are reflected in task progress
2. **Locate Spec directory**: Find directory containing current task ID in `{SPEC_DIR}`, confirm `tasks.md`
3. **Confirm current task status**: Check `[~]` marked tasks in `tasks.md`, confirm whether to continue → if confirmed done change to `[✓]` → if not done change to `[ ]`
4. **Continue next task**: Based on git changes and actual code state, update Scope/Specifics fields, continue execution and update `tasks.md` progress

### 3. Recovery Exceptions

**Session interrupted with unfinished tasks**
- Execute immediately: `Follow the spec-stateflow Compression Recovery flow to restore current Spec progress`
- Follow `spec-stateflow` skill's Compression Recovery flow
- **Note after recovery**: If tasks are marked `[~]`, must confirm the real status in `tasks.md`

**Session interrupted but no clear changes**
- Execute immediately: `Read latest Spec progress and continue execution`
- Check recent git changes to confirm if Claude Code is executing
- If interrupted task exists but Spec still exists, continue that Spec task

**Common Recovery Errors**
- **Forgot to check `{SPEC_DIR}` for tasks** — Don't just say "Can't find Spec directory"
- **`tasks.md` status inaccurate** — Don't trust in-memory progress, must re-read and confirm
- **Incorrectly assuming "already completed"** — Even if Spec looks complete, must check `[~]`, may just be paused
- **Progress not updated after recovery** — Must immediately check progress and update `tasks.md` Notes field after recovery

### 4. Post-Recovery Behavior

After recovery, continue executing tasks per Spec flow:
1. `git status` to confirm workspace state
2. `git log --oneline -3` to confirm recent commit history
3. Decide whether to continue or wait for user confirmation based on status

---

## Commit Message Format

| Type | Format |
|------|--------|
| New feature | `feat(module): [taskID] brief description of change` |
| Bug fix | `fix(module): [taskID] bug fix description` |
| Refactor | `refactor(module): [taskID] refactoring description` |
| New dependency | `feat(module): add dependency` or `chore: add dependency` |
| Maintenance | `chore: maintenance change description` |
