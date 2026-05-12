#!/bin/bash
# launch_claude_spec.sh — 启动 Claude Code 执行 spec 任务
# 从 spec-env.json 读取路径配置，零硬编码
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 读取 spec-env.json（位于 SKILLS_DIR 上一级，即 SCRIPT_DIR 上三级）
ENV_FILE="$(cd "$SCRIPT_DIR/../../.." && pwd)/spec-env.json"
if [ ! -f "$ENV_FILE" ]; then
    echo "错误: spec-env.json 不存在: $ENV_FILE" >&2
    echo "请先安装 spec 套件" >&2
    exit 1
fi

# 读取并校验 JSON 字段
read_json_field() {
    local file="$1" key="$2"
    python3 -c "
import json, sys
try:
    with open('$file', 'r', encoding='utf-8') as f:
        d = json.load(f)
    v = d.get('$key')
    if v is None:
        print('错误: spec-env.json 缺少 $key 字段', file=sys.stderr)
        sys.exit(1)
    print(v)
except (OSError, json.JSONDecodeError) as e:
    print('错误: 无法读取 spec-env.json: ' + str(e), file=sys.stderr)
    sys.exit(1)
"
}

WORKSPACE=$(read_json_field "$ENV_FILE" "WORKSPACE")
DOC_DIR=$(read_json_field "$ENV_FILE" "DOC_DIR")
CLAUDE_CLI=$(read_json_field "$ENV_FILE" "CLAUDE_CLI")

# 读取可选 worktree 开关（默认 false）
WORKTREE_ENABLED=$(python3 -c "
import json, sys
try:
    d = json.load(open('$ENV_FILE'))
    print('true' if d.get('worktree', False) else 'false')
except: print('false')
")

# 参数解析
TASK_ID=""
PROJECT_DIR=""
PROMPT=""
EXTRA_ARGS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --task-id)    TASK_ID="$2";    shift 2 ;;
        --project-dir) PROJECT_DIR="$2"; shift 2 ;;
        --prompt)     PROMPT="$2";    shift 2 ;;
        --budget|--max-budget-usd) EXTRA_ARGS="$EXTRA_ARGS --max-budget-usd $2"; shift 2 ;;
        --model)      EXTRA_ARGS="$EXTRA_ARGS --model $2"; shift 2 ;;
        *) echo "未知参数: $1" >&2; exit 1 ;;
    esac
done

# 参数校验
if [ -z "$PROJECT_DIR" ]; then
    echo "错误: 必须指定 --project-dir" >&2
    exit 1
fi
if [ -z "$PROMPT" ]; then
    echo "错误: 必须指定 --prompt" >&2
    exit 1
fi
if [ ! -d "$PROJECT_DIR" ]; then
    echo "错误: 项目目录不存在: $PROJECT_DIR" >&2
    exit 1
fi
if ! command -v "$CLAUDE_CLI" &>/dev/null; then
    echo "错误: Claude Code 未找到: $CLAUDE_CLI" >&2
    exit 1
fi

# --- Worktree 设置（可选，由 spec-env.json worktree 字段控制）---
EFFECTIVE_DIR="$PROJECT_DIR"

if [ "$WORKTREE_ENABLED" = "true" ] && [ -n "$TASK_ID" ]; then
    WORKTREE_PATH="${PROJECT_DIR}/.worktrees/spec-${TASK_ID}"
    echo "Worktree 模式已启用"

    if [ -d "$WORKTREE_PATH" ]; then
        wt_status=$(cd "$WORKTREE_PATH" && git status --short 2>/dev/null || echo "ERROR")
        if [ "$wt_status" = "ERROR" ]; then
            echo "错误：无法检查已有 worktree 的 git 状态：$WORKTREE_PATH" >&2
            exit 1
        fi
        if [ -n "$wt_status" ]; then
            echo "错误：已有 worktree 存在未提交变更：" >&2
            echo "$wt_status" >&2
            echo "请手动处理未提交变更后重试。" >&2
            exit 1
        fi
        echo "复用已有 worktree：$WORKTREE_PATH"
    else
        git -C "$PROJECT_DIR" worktree add "$WORKTREE_PATH" -b "spec/${TASK_ID}" 2>&1 || {
            echo "错误：无法在 $WORKTREE_PATH 创建 worktree" >&2
            echo "常见原因：分支 'spec/${TASK_ID}' 已存在，或路径冲突。" >&2
            exit 1
        }
        echo "已创建 worktree：$WORKTREE_PATH"
    fi
    echo "Worktree: $WORKTREE_PATH"
    EFFECTIVE_DIR="$WORKTREE_PATH"
fi
# --- Worktree 设置结束 ---

# 日志文件：有 task-id 则解析 SPEC_PATH 放到 spec 目录内；否则用时间戳落 /tmp
if [ -n "$TASK_ID" ]; then
    SPEC_PATH=$(python3 -c "
import json, os, glob, sys
try:
    env = json.load(open('$ENV_FILE', encoding='utf-8'))
    spec_dir = os.path.join(env.get('WORKSPACE',''), env.get('DOC_DIR','doc'))
    if not os.path.isdir(spec_dir):
        sys.exit(1)
    candidates = sorted(
        [d for d in glob.glob(os.path.join(spec_dir, '*'))
         if os.path.isdir(d) and os.path.basename(d).startswith('$TASK_ID')],
        key=len
    )
    if candidates:
        print(candidates[0])
except Exception:
    pass
" 2>/dev/null)
    if [ -n "$SPEC_PATH" ]; then
        LOG_FILE="$SPEC_PATH/worker.log"
    else
        LOG_FILE="/tmp/claude-spec-${TASK_ID}.log"
    fi
else
    LOG_TS=$(date +%s)
    LOG_FILE="/tmp/claude-spec-output-${LOG_TS}.log"
fi

# 启动 Claude Code
cd "$EFFECTIVE_DIR"
if [ -n "$TASK_ID" ]; then
    nohup "$CLAUDE_CLI" -p "$PROMPT" \
        $EXTRA_ARGS \
        >> "$LOG_FILE" 2>&1 &
else
    nohup "$CLAUDE_CLI" -p "$PROMPT" \
        $EXTRA_ARGS \
        > "$LOG_FILE" 2>&1 &
fi

echo "PID: $!"
echo "项目目录: $PROJECT_DIR"
echo "日志: $LOG_FILE"
