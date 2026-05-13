[![中文](https://img.shields.io/badge/README-中文-red)](README.zh-CN.md)

# Spec Stateflow Kit

> State-driven structured development workflow for AI coding agents. Eliminates "where was I?" by making `tasks.md` the single source of truth — compression-immune, stall-resistant, scope-controlled.

## Quick Install

Tell your Claw Agent:

> "Please install the spec kit, the kit directory is at `/path/to/spec-stateflow-kit`"

No manual steps required. → [Full installation guide](Installation.md)

---

## How Spec Works

Spec is a **state-driven structured development workflow**. Instead of diving into code directly, it forces every complex task through a disciplined pipeline:

```
Requirements → Design → Tasks → Execute → Track
```

The core insight: **the task tracker (`tasks.md`) is the single source of truth**. Every code change is bound to a tracked task. Progress is defined by tracker state, not by conversation memory.

### Why It Works

| Problem | Spec's Answer |
|---------|--------------|
| "Where was I?" | Read `tasks.md` — status markers tell you exactly |
| Session got compressed | Recovery flow reads tracker, verifies last completed task, resumes |
| Scope creep | Each task has Scope/Specifics fields; changes go to Notes + User corrections counter |
| "Did I finish?" | Tracker says `[✓]` or it didn't happen. Period. |
| Multiple tasks in flight | One `tasks.md` per requirement. Separate `{SPEC_PATH}` directories. Never mix. |

---

## Kit Architecture

```
spec-stateflow-kit/
├── spec-stateflow-kit-installer/    ← Installer (deploys everything)
│   ├── SKILL.md                     ← Install / Uninstall logic
│   ├── spec-env.json.example        ← Environment config template
│   ├── test-cases/                  ← Logic test fixtures (language/marker detection)
│   ├── test-prompts.json
│   └── scripts/
│       ├── spec-stop-anchor.sh      ← Stop Hook script
│       └── spec-state-guard.sh      ← PostToolUse Hook script
│
├── spec-stateflow/                  ← Core workflow engine (runs inside Claude Code)
│   ├── SKILL.md                     ← 4-phase workflow + state machine
│   └── test-prompts.json
│
├── spec-router/                     ← Always-active routing (runs inside Claude Code)
│   └── SKILL.md                     ← Task classification + command routing + session recovery
│
├── spec-task-progress/              ← Progress query (runs inside Claw Agent + Claude Code)
│   ├── SKILL.md
│   ├── test-cases/                  ← LLM parse test fixtures
│   └── test-prompts.json
│
├── claude-code-spec-driver/         ← Drive Claude Code to continue dev
│   ├── SKILL.md
│   ├── test-cases/                  ← Decision logic test fixtures
│   ├── scripts/launch_claude_spec.sh
│   └── test-prompts.json
│
├── claude-code-spec-monitor/        ← Monitor guard (stall restart / completion stop)
│   ├── SKILL.md
│   ├── scripts/snapshot.py          ← Stall detection state machine
│   └── test-prompts.json
│
├── Installation.md                  ← Install guide
└── README.md                        ← This file
```

### Deployment Topology

```
┌─────────────────────────────────┐     ┌──────────────────────────────────┐
│        Claw Agent Side          │     │        Claude Code Side          │
│                                 │     │                                  │
│  {SKILLS_DIR}/                  │     │  ~/.claude/                      │
│    spec-stateflow-kit-installer │     │    spec-env.json                 │
│    spec-task-progress           │     │    settings.json  (hooks)        │
│    claude-code-spec-driver      │     │    skills/spec-stateflow/        │
│    claude-code-spec-monitor     │     │    skills/spec-task-progress/    │
│                                 │     │    skills/spec-router/           │
│  {SKILLS_DIR}/../spec-env.json  │     │    scripts/spec-stop-anchor.sh   │
└─────────────────────────────────┘     │    scripts/spec-state-guard.sh   │
                                        └──────────────────────────────────┘
```

The installer (`spec-stateflow-kit-installer`) manages the full lifecycle — copying skills, writing config, installing hook scripts — so the user never touches paths manually.

---

## spec-stateflow: State Design Pattern

The core skill `spec-stateflow` implements a **finite state machine** with 4 macro-states, each with internal transitions:

### Macro States

```
[Classified] ──(complex/fix)──→ [Planning] ──(confirmed)──→ [Executing] ──(all done)──→ [Complete]
      │                              │                           │
  (simple/routine)             (rejected)                   (error)
      │                              │                           │
      ↓                              ↓                           ↓
  [Direct Execution]          [Revise Plan]              [Diagnose → Fix]
                                                                 ↑
                                                                 │
                                                            [Recovery] ←──(session compressed/interrupted)
```

| Macro State | Internal Phases | Entry Condition | Exit Condition |
|-------------|----------------|-----------------|----------------|
| **Planning** | Phase 1 (Requirements) → Phase 2 (Design) → Phase 3 (Tasks) | Task classified as Complex/Fix | User confirms `tasks.md` |
| **Executing** | Phase 4 — sequential task execution | `tasks.md` confirmed | All tasks `[✓]` or `[⏭]` |
| **Complete** | Final summary generation | All tasks done | User confirms summary |
| **Recovery** | Compression Recovery (6-step) | Session compressed/interrupted | Tracker reconciled with code state |

### Task-Level State Machine

Each task within `tasks.md` follows a strict lifecycle:

```
[ ] Not Started ──(start)──→ [~] In Progress ──(done + verified)──→ [✓] Done
                                 │                       │
                          (session compressed)   (verification failed)
                                 │                       │
                                 ↓                       ↓
                              [ ] Re-verify          [~] Rework
```

| Status | Meaning | Transition Rule |
|--------|---------|----------------|
| `[ ]` | Not started | → `[~]` before editing code |
| `[~]` | In progress / paused | → `[✓]` after verification passes; → `[ ]` if session compressed and state uncertain |
| `[✓]` | Done | Only set after Verification field is filled; never retroactive |
| `[⏭]` | Skipped | User decision only; agent cannot self-skip |

### State Assurance Rules

1. **Tracker is truth** — If memory and tracker disagree, trust tracker; pause and reconcile
2. **Timeliness** — Status must be updated **before** committing code, not after
3. **Specifics field is critical** — Must be precise down to method/field level; recovery depends on it
4. **No retroactive writes** — Progress not recorded before compression is unreliable; re-verify instead
5. **User corrections counter** — ≥2 triggers escalation

---

## Skill Descriptions

### spec-stateflow
**Role:** Core workflow engine (runs inside Claude Code)
**What it does:** Implements the full 4-phase structured development workflow:
- Phase 1: Requirements analysis with EARS syntax → `requirements.md`
- Phase 2: Technical solution design (architecture, API, DB) → `design.md`
- Phase 3: Task breakdown with field-level specifics → `tasks.md`
- Phase 4: Sequential execution with state tracking, compression recovery, and context switching

**Key design:** State-driven execution — every action maps to a state transition in `tasks.md`. The tracker is the single source of truth.

### spec-stateflow-kit-installer
**Role:** Lifecycle manager
**What it does:** Installs or uninstalls the entire kit in 2 modes:
- **Install** (7 steps): Check Claude Code → Configure environment → Copy 4 Claw Agent skills → Validate paths → Install Claude Code skills (spec-stateflow + spec-task-progress + spec-router) → Install hook scripts → Configure settings.json
- **Uninstall** (10 steps): Confirm → Stop monitor processes → Remove all components → Remove hook scripts → Remove settings.json entries → Cleanup

**Key design:** Path alignment validation prevents misrouted env files, self-test verifies monitor scripts during install, full cleanup on uninstall (installer itself is also removed).

### spec-router
**Role:** Always-active routing layer (runs inside Claude Code)
**What it does:** Loaded in every Claude Code session (`alwaysApply: true`). Provides three services:
1. **Task classification** — maps user input to Complex / Fix / Simple / Routine and routes accordingly
2. **Command routing** — handles `continue` / `resume` / `check progress` without requiring the user to mention spec-stateflow
3. **Step 0 session recovery** — reads `~/.claude/spec-session.json` on session start; if recent and incomplete, pre-loads context and routes directly to Compression Recovery Step 2

**Key design:** Thin routing layer only — no workflow logic. Delegates immediately to `spec-stateflow` for all execution. Reads `~/.claude/spec-env.json` for path resolution.

### spec-task-progress
**Role:** Progress query (LLM-based)
**What it does:** LLM-parses `tasks.md` and writes structured `progress.json`:
- Checks freshness of existing `progress.json` (≤15 min threshold) — returns cached result if fresh
- Otherwise: reads `tasks.md`, counts `[✓]`/`[⏭]`/`[~]`/`[ ]` markers, writes 7-field `progress.json`
- Deployed to both Claw Agent side (`{SKILLS_DIR}`) and Claude Code side (`~/.claude/skills/`) — daemon spawns it via `claude -p` for progress checks

**Key design:** Pure LLM parsing — no regex scripts. Atomic writes (tempfile+rename) prevent race conditions. Dual-environment path resolution (CLAUDE.md for Claude Code, spec-env.json for agent). Consumed by spec-driver and spec-monitor.

### claude-code-spec-driver
**Role:** Claude Code launcher
**What it does:** Generates prompts based on task progress and launches Claude Code in non-interactive background mode:
1. Query progress → 2. Locate spec docs + confirm project → 3. Generate prompt (user confirms ⛔) → 4. Launch Claude Code → 5. Report PID + log path

**Key design:** `project_name` field in `progress.json` for project directory persistence, workspace protection (uncommitted changes → append warning to prompt).

### claude-code-spec-monitor
**Role:** Autonomous monitoring guard
**What it does:** Monitors Claude Code execution when user is away. Checks progress every 15 min, stops on completion:
1. Pre-check → 2. Initialize state → 3. Start monitor daemon (15-min cycle) → 4. Report status

**Cycle logic (snapshot.py cycle command):**
- Reads `progress.json` (fresh = ≤15 min); spawns a new LLM progress checker each cycle via `claude -p`
- Fresh + is_complete=true → `ACTION: STOP` → daemon exits cleanly
- Degraded (stale/missing progress.json) → spawn checker, log git/log activity signals, no STOP
- Worker processes identified by task_id pattern in `ps` output — no PID files needed

**Key design:** Decoupled from spec-driver. Progress checker is a separate `claude -p` process (spec-task-progress skill). All runtime files co-located in `{SPEC_PATH}/` (`monitor-state.json`, `worker.log`, `daemon.pid`, `daemon.lock`); `/tmp` used only as fallback for test-only task IDs.

---

## Best Practices: Long-Cycle Development with Spec

### Driving Claude Code for Robust Task Execution

Spec enables reliable long-cycle development by enforcing **state-driven execution**. Here's how to use it effectively:

#### Execution Modes

| Mode | Trigger | Behavior | Best For |
|------|---------|----------|----------|
| **Standard** (default) | User says "continue" / "next" after each task | Claude Code executes one task → updates `tasks.md` → **stops and waits** for user review before next task | Complex tasks requiring review at each step |
| **Continuous** | User explicitly authorizes: "you may continue implementing without asking" | Claude Code auto-advances through `[ ]` tasks after each commit. Auto-pauses on: compile failure, user corrections ≥2, scope expansion, risky ops | Trusted tasks where user will be away |

> ⚠️ **Critical**: Ambiguous confirmations like "OK" / "continue" / "okay" do **NOT** activate Continuous Mode. Must use explicit authorization. Authorization does not survive session compression.

#### The Long-Cycle Workflow

```
User: "Implement payment gateway T-12345"
    ↓
Claude Code: Classifies as Complex → Phase 1 (requirements.md)
    ↓
User: confirms → Phase 2 (design.md)
    ↓
User: confirms → Phase 3 (tasks.md, e.g. 8 tasks)
    ↓
User: "continue" → Task 1 [~] → code → verify → [✓] → commit → STOP
    ↓
User: "next" → Task 2 [~] → code → verify → [✓] → commit → STOP
    ↓
... (repeat until all done)
    ↓
Claude Code: All [✓] → generate final summary → STOP for user confirmation
```

**Why this works for long cycles:**
- **Compression immunity**: If session interrupts, Compression Recovery (6-step flow) reconstructs state from `tasks.md` + git verification
- **No lost progress**: `tasks.md` is the single source of truth; memory is secondary
- **Granular control**: User reviews every commit in Standard Mode; Continuous Mode auto-pauses on any anomaly

---

### Remote Supervision via your Claw Agent

When you need to step away but want Claude Code to keep working, use the **monitor** component:

#### Simple Voice Commands

| What you want | Tell your Claw Agent |
|---------------|----------------|
| Check task progress | "task progress" / "586742 progress" |
| Let Claude Code continue dev | "continue 586742" / "keep going" |
| **Start remote supervision** | "monitor 586742" / "watch dog" |
| Check monitor status | "monitor status" |
| Stop supervision | "stop monitor 586742" |

#### How Supervision Works

```
User: "monitor 586742" (progress: 3/8, 37%)
    ↓
Claw Agent: 1) Verify task + progress  2) Check Claude Code availability
    ↓
Claw Agent: Start monitor daemon (15-min cycle)
    ↓
Monitor daemon (every 15 min):
    ├─ progress.json fresh + is_complete=true? → STOP (daemon exits)
    ├─ progress.json fresh + in-progress?      → kill old checker → spawn new checker
    └─ progress.json stale or missing?         → spawn new checker, log activity signals
    ↓
All tasks complete → STOP: daemon exits cleanly
```

**What happens during supervision:**
- Claude Code runs autonomously in **Continuous Mode** (auto-advances through tasks)
- Every 15 minutes, the daemon spawns a fresh LLM progress checker and reads `progress.json`
- Progress checker parses `tasks.md` and writes structured `progress.json` atomically
- When all tasks complete, daemon detects `is_complete=true` in fresh progress.json → exits

**Key design points:**
- No RESTART logic — the daemon monitors, the Claude Code worker drives itself
- Worker processes identified by task_id in command line (no PID files)
- Workspace protection: uncommitted changes trigger warning in launch prompt

---

### End-to-End Example: 35-Task Refactoring Project

```
Day 1  Morning:  User creates spec T-586742 (service-foundation dependency removal)
         ↓
         Phase 1-3: requirements.md → design.md → tasks.md (35 tasks)
         ↓
Day 1  Afternoon: User says "continue 586742" → Standard Mode
         ↓
         Tasks 1-5: execute → [✓] → commit → wait for "next"
         ↓
Day 2  Morning:  User says "monitor 586742" → leaves for meeting
         ↓
         Claude Code (Continuous Mode): Tasks 6-20 auto-execute
         Monitor: checks every 15 min, progress checker spawned each cycle
         ↓
Day 2  Evening:  User checks "monitor status" → progress 20/35 (57%)
         User says "stop monitor" → review changes → "continue 586742"
         ↓
Day 3-4:        Standard Mode: Tasks 21-35 with user review at each step
         ↓
Day 4  Evening:  All [✓] → final summary → spec complete
```

> **Rule of thumb**: Start with Standard Mode for the first few tasks to build trust. Switch to monitor/supervision for the middle bulk. Return to Standard Mode for the final critical tasks.

---

## Design Principles

These principles guide the Spec Stateflow Kit architecture and should be understood before customizing or extending the system:

1. **Tracker is Truth** — `tasks.md` is the single source of truth. Memory and conversation are secondary. When they conflict, pause and reconcile.
2. **Confirmation Gates** — Every phase transition (1→2→3→4) requires explicit user confirmation. No autonomous phase skipping.
3. **Compression Immunity** — Session interruption does not lose progress. The 6-step Compression Recovery flow reconstructs state from `tasks.md` + git verification.
4. **Continuous Mode is Opt-in** — Auto-advance only activates with explicit user authorization ("you may continue without asking"). Ambiguous confirmations like "OK" are ignored.
5. **One Tracker Per Requirement** — Never mix tasks from different requirements in one `tasks.md`. Use separate `{SPEC_PATH}` directories.
6. **Verification Before [✓]** — A task is only marked done after programmatic verification passes (compile, test, grep). Never retroactive.
7. **Decoupled Monitoring** — The monitor depends on the driver for prompt generation but not for monitoring logic. Either can be replaced independently.

---

## Quick Start Walkthrough

Here's how a typical task flows through the Spec system, from classification to completion:

### Scenario: "Add a new payment gateway integration"

**Step 1 — Classification** → Agent judges: multi-module / API changes / needs design → **Complex type → Enter Spec workflow**

**Step 2 — Phase 1 (Requirements)** → Agent writes `requirements.md` with EARS syntax → User confirms → ✅ Proceed

**Step 3 — Phase 2 (Design)** → Agent writes `design.md` with architecture, API signatures, DB schema → User confirms → ✅ Proceed

**Step 4 — Phase 3 (Tasks)** → Agent breaks down into 8 tasks in `tasks.md`:
```
- [ ] 1. Create PaymentGateway interface
- [ ] 2. Implement Stripe adapter
- [ ] 3. Add webhook endpoint
- [ ] 4. Write unit tests
- [ ] 5. Update API documentation
- [ ] 6. Add database migration
- [ ] 7. Integration test with sandbox
- [ ] 8. Update deployment config
```
User confirms → ✅ Proceed

**Step 5 — Phase 4 (Execution)** → Agent executes tasks sequentially:
```
Task 1: mark [~] → code → verify → mark [✓] → commit → stop for review
User: "next"
Task 2: mark [~] → code → verify → mark [✓] → commit → stop for review
...
```

**Step 6 — Completion** → All tasks `[✓]`. Agent generates summary. User confirms. Spec workflow complete.

---

## See Also

| Document | What You'll Find There |
|----------|------------------------|
| `Installation.md` | Step-by-step installation, verification, and uninstall |
| `spec-stateflow/SKILL.md` | Full 4-phase workflow spec, state machine, compression recovery |
| `spec-task-progress/SKILL.md` | Query commands for tracking task progress |
| `claude-code-spec-driver/SKILL.md` | How to launch Claude Code for continuous development |
| `claude-code-spec-monitor/SKILL.md` | Auto-stop on completion, activity signals in degraded mode |
| `spec-stateflow-kit-installer/SKILL.md` | Lifecycle management: install / uninstall |

---

## Glossary

| Term | Definition |
|------|------------|
| **Spec** | Short for "specification". A structured development workflow that forces complex tasks through requirements → design → tasks → execution. |
| **tasks.md** | The single source of truth for task progress. Contains task list with status markers (`[ ]`, `[~]`, `[✓]`, `[⏭]`), scope, specifics, and verification. |
| **Compression Recovery** | The 6-step process to recover context after a session interruption or memory compression. Reads `tasks.md`, verifies last completed task, and resumes. |
| **Continuous Operation Mode** | An opt-in execution mode where Claude Code auto-advances to the next task without waiting for user approval after each commit. |
| **EARS** | Easy Approach to Requirements Syntax. A structured requirements format: "When [trigger], the [system] shall [response]." |
| **{SPEC_PATH}** | The full directory path for a single spec: `{WORKSPACE}/{DOC_DIR}/{TaskID}-{Description}/`. |
| **Stall Detection** | The monitor's degraded-mode activity check: when progress.json is missing or stale, the daemon logs git commit changes, working-tree changes, and log file growth as activity signals — informational only, no restart triggered. |
| **User Corrections** | A counter tracking how many times the user has corrected the agent's assumptions. ≥2 triggers escalation. |

---

## FAQ & Common Pitfalls

### Frequently Asked Questions

| Question | Answer |
|----------|--------|
| Can I use Spec for a simple config change? | No. Simple changes (single file / single method / no design needed) should be executed directly without Spec. See **Task Classification** in `spec-stateflow` skill. |
| What happens if `tasks.md` gets corrupted? | Follow **Compression Recovery** in `spec-stateflow` Phase 4. The agent will manually rebuild `tasks.md` from `design.md` (there is no automated script for this). Always back up `tasks.md` before major changes. |
| Can I run multiple specs in parallel? | No. One `tasks.md` per requirement. Create separate `{SPEC_PATH}` directories. Never mix tasks from different specs in one tracker. |
| How do I switch between two active specs? | Pause current (mark `[~]`), create new tracker for new work. When returning, re-verify the last `[✓]` row per Compression Recovery Step 2. |
| Does the monitor work without git? | Yes. Stall detection falls back to progress-only tracking if git is unavailable. However, git status change detection will be disabled. |

### Common Pitfalls

1. **Retroactive tracker updates** — Writing `[✓]` after session compression without re-verifying code state first. Always re-verify per Compression Recovery Step 2.
2. **Skipping Phase 1-2** — Jumping directly to `tasks.md` without confirmed requirements/design. This leads to scope creep and rework.
3. **Mixing spec directories** — Putting multiple requirements in one `tasks.md`. Always separate concerns into different `{SPEC_PATH}` directories.
4. **Ambiguous continuous mode activation** — Saying "OK" or "continue" does NOT activate Continuous Operation Mode. Must explicitly say "you may continue implementing without asking".
5. **Ignoring uncommitted changes warning** — The driver appends workspace protection to prompts, but Claude Code may still accidentally discard changes if not careful. Always check `git status` first.
