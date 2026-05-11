# Claude Code Reference Guide

Detailed reference for dependency analysis, code standards, and quality management. For operational decision rules, see CLAUDE.md.

---

## Dependency Analysis

When a task involves cross-module impact, analyze within 30 seconds:

| Impact Type | Analysis Method | Quick Location Command |
|------------|----------------|----------------------|
| **API impact**: add/modify/delete method or function signature | Find call sites and implementations | Search codebase for the function/method name |
| **Module dependencies**: delete or rename a module/class/interface | Find all import/require/use sites | Search codebase for the module or type name |
| **Data model impact**: add/modify/delete a field or type | Find all usages of that field or type | Search codebase for the field/type name |
| **Config impact**: add/delete/modify config keys | Find all features depending on the config | Search codebase for the config key or variable name |
| **Interface/contract impact**: change a public API or shared interface | Find all implementors and callers | Search codebase for the interface/trait/protocol name |

**Analysis result recording**: Write impact analysis results to `tasks.md` Notes field, ensuring other tasks or recovery can quickly understand dependencies.

---

## Pre-Change Assessment

Must assess the following before making changes:

```bash
# 1. Check current workspace status
git status

# 2. View recent commits for context
git log --oneline -5

# 3. View current content of files to be modified
git show HEAD:<file-path>
```

---

## Code Standards

### General Rules

- **Commit messages**: Each commit message ≤300 characters, clearly describe what was done
- **Change size limits**
  - Single task modifications: keep changes focused and reviewable
  - Prefer small, incremental commits over large batch changes
  - Each commit should represent one logical change
- **Complex splitting rules**: When a task is too large, split into smaller subtasks
  - Split criteria: each subtask should be independently verifiable
- Task tracking bound to **progress**, tracked via `{SPEC_PATH}/tasks.md`, progress must not be skipped or omitted

### Interaction Rules

During development, don't require user confirmation for simple operations:
- "Can I execute this?"
- "Shall I continue to the next step?"
- "Can I commit?"

**Exception**: Key decision points requiring user input, **must wait for confirmation**: "This technical approach needs your confirmation, shall I proceed?"

Interaction focus:
- Scope/impact/approach confirmation before changes
- Design decision choices
- `{SPEC_PATH}/tasks.md` progress update & next priority
- Blocker or exception requests

### Quality Check

**Before commit**: Check all code standard requirements are met

**After commit**: Run build/compile/lint verification to ensure changes don't break existing functionality

| Check Item | Requirement |
|-----------|------------|
| Dead code | Remove unused imports, variables, and unreachable code |
| Interface consistency | Modifying a public interface must sync all implementors |
| Build verification | Post-change build/compile must pass |

**Must update current task progress to `tasks.md` before executing the next task.**

---

## Common Development Responses

| Scenario | Suggested User Response |
|----------|----------------------|
| Task needs more details | "Please provide more details about XXX" |
| Design choice encountered | "Option A and B each have trade-offs, please choose" |
| Dependency issue | "Please resolve XXX dependency first" |
| Build/compile error | Search codebase for the failing symbol or module to locate root cause |
| Need to confirm intent | "Please confirm whether to XXX" |
| Need to rollback | "Please rollback to the last stable state" |
| Technical approach uncertain | "Please suggest a technical approach before continuing" |

---

## Work Quality Standards

### General Requirements

- Each task should have focused, reviewable changes
- Must verify build/tests before and after changes
- All code changes must have corresponding commit messages

### Quality Checklist

Self-check after each task completion:

- [ ] **Build verification** — Must verify build/compile passes after modifying/adding/deleting interfaces or modules
- [ ] **Progress update** — Must update tasks.md progress status after task completion
- [ ] **tasks.md sync** — Current task status must match actual code state
- [ ] **Commit message format** — Commit message must include task ID, ≤300 characters
- [ ] **Change scope consistent** — Actual change scope matches tasks.md record
- [ ] **No extraneous changes** — diff check shows no unexpected changes

**All items above must pass before executing the next task**

### Quality Improvement Suggestions

Quality improvement is a continuous iterative process:

1. **Standards** — Establish clear code standards and change rules
2. **Verification + Inspection** — Use build tools and linters for verification; regularly check change scope and consistency
3. **Analysis + Recording** — Analyze change impact and record in `tasks.md` Notes field, ensuring quick context recovery next time; reference `design.md` when necessary
4. **Auto-commit** — Use automated tools for code commits and progress updates

### Common Quality Issues

- **Frequent Agent calls causing progress stalls** — Optimize with batch shell operations to reduce round trips
- **Unnecessary tool calls** — Use search/diff/build tools only when needed, avoid aimless frequent calls
- **MCP tool calls** — Record MCP tool usage in tasks.md Notes for future optimization
- **Over-quality** — Quality improvement is a means not an end, ensure changes are correct

### Quality Risk Assessment

| Risk Type | Mitigation |
|----------|-----------|
| **Shell tool abuse** | Tool usage must be "purposeful", distinguish "verification" vs "exploratory" calls; verification calls can execute directly |
| **Agent abuse** | Don't spawn new Agents unless necessary; prefer direct shell execution over Agent proxy |
| **MCP tool abuse** | Record MCP tool usage in tasks.md Notes for future optimization |
| **Over-quality** | Quality improvement is a means not an end, ensure changes are correct |
