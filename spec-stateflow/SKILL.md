---
name: spec-stateflow
description: "Structured software engineering workflow with state-driven execution: requirement analysis → technical design → task planning → execution with state navigation and session recovery. Triggers: new feature, complex architecture, multi-module integration, database/UI design, or any task requiring structured planning and execution. Trigger words: new feature, architecture design, requirement implementation, spec workflow, state recovery, task tracking"
alwaysApply: false
---

# Spec Stateflow

**Important: You must follow these rules. Each phase must be confirmed by the user before proceeding to the next phase.**

## How to Use This Skill

1. **Follow the four phases in order** — each phase requires user confirmation before proceeding:
   - **Phase 1:** Write requirements using EARS syntax → `requirements.md`
   - **Phase 2:** Design technical solution (architecture, API, DB, etc.) → `design.md`
   - **Phase 3:** Break down tasks with field-level specifics → `tasks.md`
   - **Phase 4:** Execute tasks with state tracking, compression recovery, and context switching
2. **[HIGHEST PRIORITY]Real-time `tasks.md` updates** — After completing each small task, you MUST immediately update `{SPEC_PATH}/tasks.md`, before compilation, testing, or starting the next task. Not updated = not done. See Phase 4 State Assurance for details

**Testing:** This skill includes `test-prompts.json` with 10 test scenarios covering all phases and edge cases. Use them to validate skill behavior.

## Path Convention

All Spec files use the following placeholders. Actual paths are resolved from `~/.claude/spec-env.json` (WORKSPACE + DOC_DIR fields):

| Placeholder | Meaning |
|------------|---------|
| `{SPEC_DIR}` | Spec file root directory |
| `{SPEC_NAME}` | Current spec name |
| `{SPEC_PATH}` | Full path = `{SPEC_DIR}/{SPEC_NAME}` |

**Spec file list:**

| File | Description |
|------|-------------|
| `{SPEC_PATH}/requirements.md` | Requirements document (Phase 1 output) |
| `{SPEC_PATH}/design.md` | Technical design document (Phase 2 output) |
| `{SPEC_PATH}/tasks.md` | Task breakdown & progress tracker (Phase 3 output, **single source of truth**) |

## Entry Points

| Your situation | Start here |
|----------------|-----------|
| Ready to execute (user confirmed plan) | **Phase 4 → Quick Start** |
| User authorized continuous batch / driver-monitor automation | **Phase 4 → [Continuous Operation Mode](#continuous-operation-mode)** |

> For all runtime states (error, context switch, task completion, etc.), see **Phase 4 → State Navigation**.

## Workflow Rules

1. When you determine that the user's input implies a new requirement (not explicitly stated), you may work independently following standard software engineering practices. Confirm with the user when necessary.

2. When the user explicitly states a new requirement, you must follow the full workflow: understand the problem and requirements clearly, and confirm with the user before proceeding to the next phase.

---

## Phase 1: Requirements Document and Acceptance Criteria Design

Before drafting requirements.md, detect the primary language of the user's initial prompt:
- Base detection on natural language words only; ignore code blocks, commands, and technical terms
- If the user has already specified a document language (e.g., "write in English", "用中文写"), use that and skip detection
- Record the detected language as DOC_LANG for use in Phase 1, 2, and 3

Write all natural-language content of requirements.md in DOC_LANG. Technical terms, code snippets, and command examples remain in their original form. If the user issues a language override at any point, update DOC_LANG immediately and apply to all remaining documents.

First complete the requirements design using EARS (Easy Approach to Requirements Syntax) method. You must confirm requirement details with the user. After final confirmation, the requirements are finalized, then proceed to the next phase.

Save to `{SPEC_PATH}/requirements.md`.

Before presenting to the user, run a Critic subagent to review quality:

```
Critic subagent prompt:
You are reviewing a requirements document for quality. Report findings only — do not rewrite the document.

## Document
{requirements.md full text}

## Check dimensions
For each finding, classify as HIGH or MEDIUM.

HIGH (must fix):
- EARS syntax violation: AC not in "When/While <condition>, the <system name> shall <response>" form
- Missing AC: a user story has no verifiable acceptance criterion
- Logical contradiction: user story and AC describe conflicting behavior
- Unverifiable AC: criterion cannot be objectively tested

MEDIUM (fix if minor):
- Missing edge case or error path
- AC could be more specific
- Missing negative case (what the system shall NOT do)

## Output format
### HIGH findings
- [R{n} AC{m}] {description}

### MEDIUM findings
- [R{n} AC{m}] {description}

### Summary
HIGH: {count} | MEDIUM: {count}
```

After receiving Critic findings:
- **HIGH issues**: fix all of them and update `{SPEC_PATH}/requirements.md`
- **MEDIUM issues**: fix only those that do not require rewriting an entire section; list the rest in the Critic summary for user decision
- **No issues found**: skip revision, proceed directly to user confirmation
- **Critic subagent fails**: continue with the unreviewed draft; note "自动审查已跳过 / Auto-review skipped" in the summary

When presenting requirements.md to the user, append the following Critic summary:

```
---
**Requirements Auto-Review Summary**
- Dimensions checked: EARS syntax, edge case coverage, internal consistency, missing ACs
- HIGH issues: {n} found, all fixed
- MEDIUM issues: {n} found, {m} fixed; remaining items for your decision:
  - [R{n} AC{m}] {description}
```

After confirming with the user, proceed to the next phase.

**If user rejects or requests changes:** Update requirements.md and re-confirm. Do NOT proceed to Phase 2 until user explicitly approves.

**Reference format:**

```markdown
# Requirements Document

## Introduction

Requirement description

## Requirements

### Requirement 1 - Requirement Name

**User Story:** User story content

#### Acceptance Criteria

1. Use EARS syntax: While <optional precondition>, when <optional trigger>, the <system name> shall <system response>. For example: When "Mute" is selected, the laptop shall suppress all audio output.
2. ...
...
```

---

## Phase 2: Technical Solution Design

Use the DOC_LANG detected in Phase 1 for all natural-language content in this document. If the user issues a language override at any point, update DOC_LANG immediately.

At the start of Phase 2, launch parallel codebase exploration and skeleton drafting simultaneously:

**Parallel step A — Launch Explore subagent** with the following prompt:
```
You are exploring an existing codebase to support a technical design task.

## Requirements context
{summary of requirement names and key scope from requirements.md, ≤200 words}

## Search tasks
1. Find files and classes matching these names/patterns: {module names, class names, interface names extracted from requirements}
2. For each found class/interface: list key method signatures
3. Find existing test files for the affected modules
4. Identify any patterns (naming conventions, error handling, data formats) that the new design should follow

## Output format
### Files found
- {path}: {brief description}

### Key classes / interfaces
- {ClassName} ({path}): {key methods}

### Existing patterns
- {pattern name}: {description}

### Potential conflicts
- {description of existing code that may need changes}

Be factual and concise. Do not make design recommendations.
```

**Parallel step B — Draft design skeleton** (do not wait for subagent): draft section headings and key bullet points for Background, Design Goals, Business Model, and System Design.

**After Explore subagent completes:**
- Success → merge findings into the design draft; if any finding contradicts the draft, revise the affected section to reflect the actual code state
- Failure / timeout → continue Phase 2 with main agent exploration only; append the following note at the end of design.md: "代码库探索 subagent 不可用，已降级为串行探索 / Explore subagent unavailable, fell back to serial exploration" (this note is a passive record, not an error alert)

After completing the design document body, append a `<details>` exploration log at the end of design.md:

```markdown
<details>
<summary>Codebase exploration log (auto-generated, collapsible)</summary>

**Exploration time**: {timestamp}
**Search scope**: {file patterns and class names searched}

**Key files found**:
- {path}: {brief description}

**Key patterns found**:
- {pattern name}: {description}

**Potential conflicts**:
- {description}

</details>
```

After completing the requirements design, based on the current technical architecture and the confirmed requirements above, design the technical solution. It should be concise but accurately describe the technical architecture (e.g., architecture, tech stack, technology selection, database/interface design, test strategy, security). Use mermaid diagrams when necessary.

**Must include chapters:** Background, Design Goals, Business Model, System Design (precise to package path, class name, method signature), Refactoring Design (if applicable), Deployment Plan (for large tasks), Risk Assessment (for large tasks).

Save to `{SPEC_PATH}/design.md`. You must confirm with the user clearly, then proceed to the next phase.

**If user rejects or requests changes:** Update design.md and re-confirm. Do NOT proceed to Phase 3 until user explicitly approves.

**Reference format:**

```markdown
# Technical Solution Design

## Background
Why this design is needed — business context and problem statement

## Design Goals
- Goal 1: ...
- Goal 2: ...

## Business Model
Core domain models, entity relationships, key data flows

## System Design
### Architecture Overview
(mermaid diagram or component description)

### Module: {module-name}
- **Package:** `com.example.module`
- **New classes:**
  - `ClassName` — responsibility description
  - `InterfaceName` — method signatures: `ReturnType methodName(ParamType param)`
- **Modified classes:**
  - `ExistingClass` — add method `newMethod()`, change field `field` scope

### API Design
| Endpoint | Method | Request | Response |
|----------|--------|---------|----------|
| `/api/xxx` | POST | `{field: type}` | `{field: type}` |

### Database Design
Table name, columns, indexes, migration steps

### Test Strategy
Unit test scope, integration test plan, verification methods

## Refactoring Design (if applicable)
What to refactor, why, and how to do it incrementally

## Deployment Plan (for large tasks)
Environments, rollout steps, rollback plan

## Risk Assessment (for large tasks)
| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| ... | High/Med/Low | High/Med/Low | ... |
```

---

## Phase 3: Task Breakdown

Use the DOC_LANG detected in Phase 1 for all natural-language content in this document (Task Name, Specifics, Notes, etc.). Technical terms, code snippets, and command strings remain in their original form.

After completing the technical solution design, based on the requirements document and technical solution, break down specific tasks. You must confirm with the user clearly, then save to `{SPEC_PATH}/tasks.md`. After confirming with the user, proceed to the next phase.

**If user rejects or requests changes:** Adjust task breakdown and re-confirm. Do NOT proceed to Phase 4 until user explicitly approves.

### 编译独立性原则（Compilation Independence Principle）

拆分任务时，**编译独立性是任务边界的第一约束**，优先于逻辑独立性：

- 每个任务的 Scope + Affected 所涵盖的变更，必须构成一个可独立编译的完整单元
- 当多个变更存在编译依赖关系（如：新增接口方法、同步实现类、更新全部调用方），必须合并为**同一个任务**，在 Specifics 字段中逐一列出所有涉及的类、方法和调用点
- 禁止将"接口变更"与"实现/调用方变更"拆入不同任务

### Task Field Specification

Every task in `{SPEC_PATH}/tasks.md` must contain the following fields:

| Field | Specification | Example |
|-------|--------------|---------|
| **Task name** | Verb-object structure, ≤10 words | `Remove unused methods from IMultiAppInfo` |
| **Scope** | Files directly modified by this task | `IMultiAppInfoProxyInterface.java`, `MultiAppInfoProxy.java` |
| **Affected** | Files that need sync changes due to this task (imports, calls, etc.) | `NoticeService.java`, `BpmService.java` |
| **Specifics** | **Most critical field.** Precise down to method/field level | `Interface remove methodA(), methodB(); add methodC(String)` |
| **Status** | `[✓]` Done / `[ ]` Not started / `[~]` In progress or paused / `[⏭]` Skipped (user decision only; dependencies not auto-blocked, flag in final summary) | `[✓]` |
| **Verification** | **必填。** 须包含：① 项目编译命令；② 如项目有自动化测试，须包含与本任务 Scope 相关的测试命令。示例：`./gradlew compileJava && ./gradlew test --tests 'com.example.ServiceTest'` | `./gradlew compileJava && ./gradlew test --tests 'com.example.ServiceTest'` |
| **Commit** | Backfill **after** git commit: actual commit message + short hash | `feat(proxy): remove unused methods (a1b2c3d)` |
| **User corrections** | Count of user corrections; ≥2 triggers escalation | `0` |
| **Notes** | Dependencies, blockers, scope changes | `Depends on task 1` |

**Critical field — Specifics:** Must be precise down to method/field level. After session compression, recovery depends entirely on this field to reconstruct what was done and what remains.

### Affected Field: Dependency Impact Reference

When filling in the Affected field, focus on identifying these 5 categories of downstream impact:

| Impact Type | Description | Example |
|-------------|-------------|---------|
| **API / Interface Change** | Adding, modifying, or removing interface methods | Callers must update method signatures and return types |
| **Module Dependency** | Cross-module data flow or call-chain changes | Service A calls a new method on Service B |
| **Data Model** | Database schema or DTO field changes | New fields require syncing ORM mappings and DTOs |
| **Config Entry** | Environment variable, config file, or constant changes | New config entries must be declared in spec-env.json and docs |
| **Interface Contract** | Changes to externally exposed API format or behavior | Callers (clients / frontend / external systems) must update accordingly |

**Status values:**
- `[ ]` — Not started
- `[~]` — In progress
- `[✓]` — Done
- `[⏭]` — Skipped (only when user explicitly decides to skip; agent cannot self-skip; skipped tasks are excluded from execution — dependencies are not auto-blocked, but flag them in the final task summary)

### Task Format Reference

Tasks use a **dual-layer format**: an Overview list for machine parsing + `### Task N:` sections with Markdown tables for human-readable details.

```markdown
# Implementation Plan

## Task Overview

- [✓] 1. Remove unused methods from IMultiAppInfo
- [ ] 2. Add getAppName method

---

### Task 1: Remove unused methods from IMultiAppInfo

| Field | Content |
|-------|---------|
| **Status** | `[✓]` |
| **Scope** | `IMultiAppInfoProxyInterface.java`, `MultiAppInfoProxy.java` |
| **Affected** | `NoticeService.java` |
| **Specifics** | Interface remove getCachedV2AppInfo(), listV1OfflineApps(); impl class sync |
| **Verification** | grep signatures + compile verification |
| **Commit** | feat(proxy): remove unused methods (a1b2c3d) |
| **User corrections** | 0 |
| **Notes** | User requested keeping getV1AppInfo 3-param overload |
| **Requirement** | R1 |

---

### Task 2: Add getAppName method

| Field | Content |
|-------|---------|
| **Status** | `[ ]` |
| **Scope** | `IMultiAppInfoProxyInterface.java`, `MultiAppInfoProxy.java` |
| **Affected** | — |
| **Specifics** | Interface add getAppName(String); impl class add getAppName(String) |
| **Verification** | `./gradlew compileJava` |
| **Commit** | — |
| **User corrections** | — |
| **Notes** | Depends on task 1 completion |
| **Requirement** | R2 |
```

### Machine Parsing Contract

When generating or updating `tasks.md`, task status markers must use only the four forms `[ ]` `[~]` `[✓]` `[⏭]`. No emoji or other characters may be substituted.

**Dual-layer sync rule:** The status marker in the Overview list and the Status field in the corresponding `### Task N:` table must remain consistent. When updating task status, both locations must be changed together — update the Overview marker first, then the table Status field (or both simultaneously). When inconsistent, the `### Task N:` table Status field is the authoritative value.

> Note: Format constraints apply only to what can be reliably enforced — the status marker characters. Other format details (line structure, sub-field format, etc.) are handled by spec-task-progress's LLM parsing capability and are not enforced in this contract.

---

## Phase 4: Task Execution

Execute tasks in order from `{SPEC_PATH}/tasks.md`. This phase covers execution mechanics, state navigation, and session recovery.

**Validation:** Before executing, confirm `{SPEC_PATH}/tasks.md` exists, contains valid task entries (Scope + Specifics + Verification fields), and **all tasks have valid status markers** (`[ ]` / `[~]` / `[✓]` / `[⏭]`). If the file is missing, malformed, or has tasks with missing/invalid status markers, stop and fix the format before proceeding.

### Quick Start

First time with a confirmed `tasks.md`:

```
0. Validate tasks.md format — ensure every task has a valid status marker [ ]/[~]/[✓]/[⏭]. Fix any missing/invalid markers before proceeding.
1. Read {SPEC_PATH}/tasks.md → if any [~] task exists, continue it; otherwise find first [ ] task
2. Mark it [~] → execute per Specifics description
3. When done: mark [✓], fill Verification, stage changes
4. Show diff → wait for user review and explicit commit approval (**skipped in [Continuous Operation Mode](#continuous-operation-mode)**)
5. If user approves: commit → backfill Commit field with actual message + short hash → next task. If user rejects: revert status to [~], address feedback, repeat from step 2
6. User says "next" → repeat from step 1
```

**Session compressed?** Jump to [Compression Recovery](#compression-recovery).
**Continuous batch authorized by the user (e.g. "you may continue implementing" / "complete the rest without asking"), or running under driver/monitor automation?** Jump to [Continuous Operation Mode](#continuous-operation-mode).

### State Navigation

#### Where Am I?

> Task type classification is handled by spec-router before spec-stateflow is invoked. All states below assume a Complex or Fix task is already in progress.

| Current State | What To Do Next | Key Output |
|---------------|-----------------|------------|
| Just entered spec-stateflow | Determine entry point — see Entry Points table above | Phase 1 or Phase 4 |
| Planning in progress (Phase 1-3) | Continue current phase → wait for user confirmation before next phase | Confirmed spec doc |
| Ready to implement | Read `{SPEC_PATH}/tasks.md`, mark first pending task as `[~]` | Task in progress |
| Just finished a task | Update `tasks.md` to `[✓]` → verify → commit → next task | Updated tracker |
| Hit an error | Stop → diagnose → fix → re-verify → **wait for user confirmation** → judge next step based on user's direction | Documented fix |
| Session interrupted / compressed | Jump to [Compression Recovery](#compression-recovery) | Recovered context |
| User asks unrelated question | Handle query → return to previous state, do NOT modify tracker | Continuity preserved |
| User starts a new feature mid-task | Pause current (mark `[~]`) → create new tracker → see Context Switching | New `{SPEC_PATH}` |
| User changes direction mid-task | Stop → document in Notes → wait for confirmation | Updated tracker |
| User corrects design assumption | Update `tasks.md` Notes **and** `design.md` → wait for confirmation | Synced docs |
| All tasks done | Generate final summary → wait for user confirmation → complete | See Task Completion |

#### Task Completion

When all tasks in `tasks.md` are `[✓]` or `[⏭]`:

1. **Generate final summary** including:
   - Total tasks: done / skipped
   - Skipped tasks list (if any) — flag each with its original scope and reason for skip
   - User corrections total across all tasks
2. **Present summary to user** and wait for confirmation
3. After user confirms: the spec workflow is complete. Spec files (`requirements.md`, `design.md`, `tasks.md`) are retained as project documentation

#### State Transition Rules

The State Navigation table is the primary reference. The flow diagram below illustrates the core state machine; all scenarios in the table are authoritative.

```
[Planning] --(confirmed)--> [Executing] --(task done)--> [Update tracker] --(more tasks)--> [Executing]
    │                                                                     └─(all done)--> [Complete]
    └─(rejected)--> [Revise plan]

[Executing] --(error)--> [Diagnosing] --(fixed)--> [Update tracker] --> [Executing]
                                    └─(stuck)--> [Ask user] --(user responds)--> [Judge next step based on user's direction]

[Complete] --(user confirms)--> [Done]

[Any state] --(unrelated user query)--> [Handle query] --> [Return to prior state]
[Any state] --(user changes direction)--> [Stop + document] --> [Wait for confirmation]
[Any state] --(user corrects design assumption)--> [Update tasks.md + design.md] --> [Wait for confirmation]
[Any state] --(session compressed/interrupted)--> [Recovery] --(tracker reconciled)--> [Resume prior state]
```

**Critical rule:** You cannot transition from `[Executing]` to the next task without updating the tracker. Updating `tasks.md` is the **definition** of task completion.

### Continuous Operation Mode

Skips per-task `show diff → wait approval`. Auto-advances to next `[ ]` task. All other tracker disciplines remain mandatory.

#### Activation

- User explicitly authorizes continuous batch (e.g. `you may continue implementing` / `complete the rest without asking`)
- Invoked by driver/monitor automation

Ambiguous confirmations (`OK` / `continue` / `okay`) **do NOT** activate. Authorization does **not** survive session compression.

#### Behavior Diff

| Discipline | Status |
|------------|--------|
| Mark `[~]` / `[✓]`, fill Verification + Commit | ✅ Kept |
| Run verification (compile / test / grep) | ✅ Kept |
| Per-task independent commit | ✅ Kept |
| Increment User corrections on rejection | ✅ Kept |
| Show diff → wait approval | ❌ Skipped |
| Wait for `next` between tasks | ❌ Auto-advance |

#### Auto-Pause Triggers

Reverts to Default Mode immediately on:

| Trigger | Action |
|---------|--------|
| Compilation / verification fails | Rollback to `[~]`, record in Notes |
| User corrections ≥ 2 | Escalate per project config |
| Scope expansion | Record drift, wait for confirmation |
| Risky ops (force push, reset --hard, schema migration, etc.) | Stop and ask |
| User interrupts | Stop after current task's commit |
| All tasks complete | Switch to Task Completion |
| Session compression recovery | Revert to Default, re-confirm |

### State Assurance

#### The Tracker (`tasks.md`)

`{SPEC_PATH}/tasks.md` is the primary state reference. If memory, conversation, and tracker disagree, **pause and reconcile with the user** — never silently override user intent.

#### Timeliness Guarantee

`{SPEC_PATH}/tasks.md` must be updated in real time — never retroactively:

| Event | Action | Why |
|-------|--------|-----|
| Start a task | `[ ]` → `[~]` **before** editing code | Prevents duplicate work |
| Finish a task (before commit) | `[~]` → `[✓]`, fill Verification **immediately** | Defines completion |
| Finish a task (after commit) | Backfill Commit field with actual message + short hash | Traceability |
| User changes scope | Record in Notes **immediately**, increment User corrections | Prevents drift |
| Session compresses | `[~]` → `[ ]` if uncertain about state | Prevents false progress |

**Precedence:** This takes precedence over compilation, testing, and starting the next task. A task whose tracker entry is not updated is considered NOT done.

**Prohibited:**
- Never reconstruct progress after compression without re-verifying code state first
- Never write progress retroactively after compression — progress not written before compression is unreliable

### Compression Recovery

`{SPEC_PATH}/tasks.md` is the operational basis for recovery.

**Trigger:** System message "This session is being continued from a previous conversation" or when memory is fuzzy.

| Quick Step | Full Step Mapping |
|-----------|------------------|
| Fast session re-location via spec-session.json | Step 0 |
| Read and confirm progress | Step 1 |
| Verify code state | Step 2-3 |
| Determine next step | Step 4-6 |

#### Full Compression Recovery Flow (6 Steps)

**Step 0: Fast Session Re-location (delegate to spec-router)**
- spec-router handles Step 0 when user says "continue" / "resume"
- Step 0 reads `~/.claude/spec-session.json`, pre-loads task context, and either fast-forwards to Step 2 (fresh session) or falls through to Step 1 (stale/missing)
- If spec-router Step 0 fast-forwarded here: proceed directly to Step 2 (skip Step 1 directory scan)

**Step 1: Read Spec files, confirm `{SPEC_PATH}/tasks.md` progress**
- Read `{SPEC_PATH}/requirements.md`, `{SPEC_PATH}/design.md`, `{SPEC_PATH}/tasks.md`
- `tasks.md` is the **only trustworthy state source** — summary progress descriptions are NOT reliable
- **Special cases:**
  - **If Spec files don't exist:**
    - Spec planning hasn't started. Ask user to confirm task scope, then begin Phase 1.
  - **If files exist but `tasks.md` is missing:** Rebuild `tasks.md` from `design.md`, note in remarks "table rebuilt after compression recovery"
  - **If all files exist:** Proceed to Step 2

**Step 2: Verify actual code state**
- Run `git status` and `git diff` to confirm working tree state
- **If no `[✓]` rows in `tasks.md`** (no tasks completed yet): first `[ ]` or `[~]` row is the next task, skip the rest of this step and all of Step 3 → go to Step 4
- **If `[✓]` rows exist:** **Only verify the last `[✓]` row** (state boundary), re-execute verification per "Scope + Specifics + Verification" fields
- If verification passes → trust all prior `[✓]`; if fails → change that task status to `[ ]`, consider backtracking
- If `tasks.md` doesn't match actual state, **fix `tasks.md` first, then continue**

**Step 3: Do not trust summary "completed" conclusions**
- Summary claims of "completed", "aligned", "fixed" — only verify the **last completed task**
- Especially for precision-critical conclusions (interface/impl alignment, method signature matching, compile status)
- If verification fails, revert that task to `[ ]`, consider backtracking

**Step 4: Re-confirm next task**
- Explicitly state the next task name and scope
- Do not continue based on vague summary descriptions (e.g., "continue fixing remaining interfaces")

**Step 5: Use programmatic verification, not manual reading**
- For "does it exist", "is it aligned", "does it match" — prefer Bash tools (grep, javap, diff) for programmatic verification
- Never judge interface/impl alignment, method existence, or parameter matching by reading alone

**Step 6: Update `tasks.md` before executing**
- Before making any code changes, update `{SPEC_PATH}/tasks.md` first
- Ensure `tasks.md` is consistent with actual state

### Context Switching

| Scenario | Rule |
|----------|------|
| User starts a new feature | Pause current task (mark `[~]`), create new tracker for new work |
| User raises multiple parallel requests | Confirm priority and order with user; create separate Spec directories (different `{SPEC_NAME}`) for each; execute sequentially, never mix tasks.md |

**Key principle:** One `tasks.md` per requirement. Different requirements must have different `{SPEC_PATH}`.

**Do not abandon unfinished tasks.** Unless user explicitly says "cancel" or "skip", mark unfinished tasks as `[~]` and record progress.

**When returning to a previous task, re-verify state.** Verify the last `[✓]` row per Step 2 of Compression Recovery.

