---
name: spec-task-progress
description: "Query spec task execution progress and write progress.json. Triggers: check task progress, task status, task progress, progress, 查询进度, 任务状态, 任务进度, 进度查询, 查看进度, 帮我看一下spec任务的开发进度. Used when user or daemon wants to know how far a spec task has progressed."
alwaysApply: false
---

# Spec Task Progress Query

Query spec task progress by LLM-parsing `tasks.md`, then write structured `progress.json`.

> `query_task.py` and `query_overview.py` have been removed from this skill. All progress parsing is now done by LLM.

> **Design note**: No user-confirmation checkpoints — writing `progress.json` is idempotent and harmless. When daemon-invoked (Scene 3), no human is present. When user-invoked, the only side effect is overwriting the JSON file with fresh data.

## Trigger Formats

This skill handles two trigger formats:

**User / manual trigger:**
```
任务状态 586742
check task progress 586742
```

**Scene 3 (daemon trigger — no monitoring context):**
```
帮我看一下spec任务的开发进度
需求编号：{task_id}
```

When triggered via Scene 3, extract `task_id` from the `需求编号：` line and proceed directly to the progress query flow. Do not add monitoring context or restart suggestions to the output.

## Environment & Path Resolution

### Path Resolution

Both Claude Code and claw agent read `spec-env.json` for path resolution:

| Environment | File location | How to read |
|-------------|--------------|-------------|
| **Claude Code** | `~/.claude/spec-env.json` | Read at runtime: `SPEC_DIR = WORKSPACE + "/" + DOC_DIR` |
| **claw agent** | `{SKILLS_DIR}/../spec-env.json` | Read at runtime: `SPEC_DIR = WORKSPACE + "/" + DOC_DIR` |

```python
# Pseudocode for both environments (adjust path per environment)
import json, os
env = json.load(open(spec_env_path))
SPEC_DIR = os.path.join(env["WORKSPACE"], env["DOC_DIR"])
```

If `~/.claude/spec-env.json` does not exist (Claude Code side): output error "spec-env.json not found — please re-install the spec kit" and abort.

Both environments use identical logic once `SPEC_DIR` is resolved.

### Locating SPEC_PATH

Scan `SPEC_DIR` for a directory whose name **contains** `task_id`. Matching is deterministic:

1. **Prefix match first** — directory name starts with `task_id` (e.g. `586742-redesign-auth-module`)
2. **Substring match fallback** — `task_id` appears anywhere in the name (e.g. `T-EE-586742-redesign`)
3. **Tiebreak**: shortest name wins within each group

```
SPEC_PATH = deterministic match: prefix > substring, shortest wins
```

Example: `task_id = 586742` → matches `586742-redesign-auth-module/`

If no matching directory is found, output an error JSON (see Exception Handling).

## Progress Query Flow

```
1. Locate SPEC_PATH (see above)
2. Read {SPEC_PATH}/progress.json (if exists)
3. Check freshness: updated_at within 15 minutes (condition: age_seconds <= 900)
   ├─ Fresh → Return progress.json contents as-is, done.
   └─ Stale or missing → Continue to step 4
4. Read {SPEC_PATH}/tasks.md
5. LLM-parse tasks.md → compute progress fields
6. Write {SPEC_PATH}/progress.json (atomic: write to .tmp then rename)
7. Output a brief summary to stdout
```

**Freshness threshold**: `DAEMON_CYCLE_MINUTES = 15` minutes. Condition is `<=` (not `<`).

## tasks.md Parsing Rules

Count tasks by scanning **only top-level list items** (lines starting with `- [marker]`):

| Marker | Meaning | Counts as done? |
|--------|---------|----------------|
| `[✓]` | Completed | Yes |
| `[⏭]` | Skipped | Yes |
| `[~]` | In progress | No |
| `[ ]` | Not started | No |

- **Total**: count of all top-level task items
- **Done**: count of `[✓]` + `[⏭]` items
- **Next task**: the first `[ ]` or `[~]` item (by task number order)
- **is_complete**: `done == total` (and `total > 0`)

**Do not count markers that appear inside task content** (Scope, Specifics, Notes fields). Only the leading marker of a top-level list item counts.

**双层一致性：** tasks.md 采用双层结构时（Overview 列表 + `### Task N:` 表格），两层的状态标记可能不一致。解析规则：
- **计数层（Overview 列表）** 是 spec-task-progress 的计数依据——LLM 扫描 Overview 列表中的 `- [marker]` 行
- **权威层（表格 Status 字段）** 是任务状态的权威来源——不一致时以表格 Status 字段为准
- LLM 计数时以 Overview 列表的标记为准，但若发现两层不一致，应在输出中注明

## progress.json Schema

Write exactly these 8 fields. Preserve `project_name` from the existing file if present; otherwise set to null.

```json
{
  "task_id": "586742",
  "project_name": "mas-workflow",
  "done": 4,
  "total": 10,
  "next_task": 5,
  "next_task_name": "实现认证逻辑",
  "is_complete": false,
  "updated_at": "2024-01-15T10:30:00"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | string | The task ID as provided |
| `project_name` | string \| null | Project directory name (e.g. `mas-workflow`); set by driver/monitor, preserved on update |
| `done` | int | Count of [✓] + [⏭] tasks |
| `total` | int | Total task count |
| `next_task` | int \| null | Task number of next [ ] or [~] item; null if all done |
| `next_task_name` | string \| null | Name of next task; null if all done |
| `is_complete` | bool | true when done == total |
| `updated_at` | string | ISO 8601 timestamp (seconds precision) |

**`project_name` preservation rule**: When rewriting progress.json, read the existing file first. If it contains a non-null `project_name`, include that value in the new write. This field is owned by driver/monitor — the progress skill never sets it, only preserves it.

**Atomic write**: write to `{SPEC_PATH}/progress.json.tmp` first, then rename to `progress.json`. This prevents partial reads by the daemon.

## Output Format

After writing progress.json, output a brief summary:

```
进度已更新：{done}/{total}（{pct}%），下一个 Task {next_task}：{next_task_name}
```

If already fresh (cache hit):
```
进度（缓存）：{done}/{total}（{pct}%），下一个 Task {next_task}：{next_task_name}
```

If all complete:
```
进度已更新：{total}/{total}（100%），全部完成 ✓
```

## Exception Handling

| Scenario | Output |
|----------|--------|
| spec-env.json not found (claw env) | Prompt user to install spec kit, abort |
| No directory in SPEC_DIR matches task_id | Write error JSON, output error message |
| Multiple directories contain task_id | Deterministic auto-resolution: prefix > substring; shortest name wins — no user prompt needed |
| tasks.md not found | Write error JSON: `{"task_id":"…","done":0,"total":0,"next_task":null,"next_task_name":null,"is_complete":false,"updated_at":"<current ISO 8601 timestamp>"}` |
| tasks.md is empty | Same error JSON as above |
| SPEC_DIR not readable | Output error message, abort |

**Error JSON example** (tasks.md missing):
```json
{
  "task_id": "586742",
  "done": 0,
  "total": 0,
  "next_task": null,
  "next_task_name": null,
  "is_complete": false,
  "updated_at": "<current ISO 8601 timestamp>"
}
```

## Testing

When user inputs `测试 spec-task-progress` or `test spec-task-progress`:

1. Locate `test-cases/` directory relative to this SKILL.md
2. For each subdirectory (tc01, tc02, …) in order:
   - Read `tasks.md` from the test case directory
   - Parse it using the rules above (LLM parsing)
   - Read `expected.json`
   - Compare computed fields against expected (fields: done, total, next_task, next_task_name, is_complete)
   - Do **not** compare `task_id` (depends on directory name, not available in test fixture) or `updated_at` (runtime timestamp, changes every run)
   - Report PASS or FAIL with details
3. Output summary: `N/M cases passed`

**Example test run output:**
```
spec-task-progress 测试结果：

tc01-mixed-status        PASS
tc02-all-complete        PASS
tc03-marker-in-content   PASS
tc04-with-skipped        PASS
tc05-single-in-progress  PASS
tc06-all-pending         PASS

6/6 cases passed ✓
```

On FAIL, show the field diff:
```
tc03-marker-in-content   FAIL
  expected: done=1, total=2, next_task=2
  got:      done=3, total=2, next_task=null
```
