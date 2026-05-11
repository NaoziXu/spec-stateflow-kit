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

# 日志文件：有 task-id 则用固定名（追加模式，与 monitor 约定一致）；否则用时间戳
if [ -n "$TASK_ID" ]; then
    LOG_FILE="/tmp/claude-spec-${TASK_ID}.log"
else
    LOG_TS=$(date +%s)
    LOG_FILE="/tmp/claude-spec-output-${LOG_TS}.log"
fi

# 启动 Claude Code
cd "$PROJECT_DIR"
if [ -n "$TASK_ID" ]; then
    nohup "$CLAUDE_CLI" -p "$PROMPT" --dangerously-skip-permissions \
        $EXTRA_ARGS \
        >> "$LOG_FILE" 2>&1 &
else
    nohup "$CLAUDE_CLI" -p "$PROMPT" --dangerously-skip-permissions \
        $EXTRA_ARGS \
        > "$LOG_FILE" 2>&1 &
fi

echo "PID: $!"
echo "项目目录: $PROJECT_DIR"
echo "日志: $LOG_FILE"
