#!/bin/bash
# launch_claude_spec.sh — Launch Claude Code to execute a spec task
# Reads path config from spec-env.json, no hardcoding
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Read spec-env.json (located one level above SKILLS_DIR, i.e. three levels above SCRIPT_DIR)
ENV_FILE="$(cd "$SCRIPT_DIR/../../.." && pwd)/spec-env.json"
if [ ! -f "$ENV_FILE" ]; then
    echo "Error: spec-env.json not found: $ENV_FILE" >&2
    echo "Please install the spec kit first." >&2
    exit 1
fi

# Read and validate JSON fields
read_json_field() {
    local file="$1" key="$2"
    python3 -c "
import json, sys
try:
    with open('$file', 'r', encoding='utf-8') as f:
        d = json.load(f)
    v = d.get('$key')
    if v is None:
        print('Error: spec-env.json missing field: $key', file=sys.stderr)
        sys.exit(1)
    print(v)
except (OSError, json.JSONDecodeError) as e:
    print('Error: cannot read spec-env.json: ' + str(e), file=sys.stderr)
    sys.exit(1)
"
}

WORKSPACE=$(read_json_field "$ENV_FILE" "WORKSPACE")
DOC_DIR=$(read_json_field "$ENV_FILE" "DOC_DIR")
CLAUDE_CLI=$(read_json_field "$ENV_FILE" "CLAUDE_CLI")

# Argument parsing
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
        *) echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
done

# Argument validation
if [ -z "$PROJECT_DIR" ]; then
    echo "Error: --project-dir is required" >&2
    exit 1
fi
if [ -z "$PROMPT" ]; then
    echo "Error: --prompt is required" >&2
    exit 1
fi
if [ ! -d "$PROJECT_DIR" ]; then
    echo "Error: project directory does not exist: $PROJECT_DIR" >&2
    exit 1
fi
if ! command -v "$CLAUDE_CLI" &>/dev/null; then
    echo "Error: Claude Code not found: $CLAUDE_CLI" >&2
    exit 1
fi

EFFECTIVE_DIR="$PROJECT_DIR"

# Log file: if task-id given, resolve SPEC_PATH and write inside spec dir; otherwise use /tmp with timestamp
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

# Launch Claude Code
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
echo "Project dir: $PROJECT_DIR"
echo "Log: $LOG_FILE"
