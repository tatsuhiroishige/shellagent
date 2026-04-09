#!/usr/bin/env bash
# PreToolUse hook: block destructive commands
# Exit 2 = block the tool call

INPUT=$(cat)
TOOL=$(echo "$INPUT" | jq -r '.tool_name // empty')
CMD=""

if [ "$TOOL" = "mcp__shellagent__run" ] || [ "$TOOL" = "mcp__shellagent__term_send" ]; then
    CMD=$(echo "$INPUT" | jq -r '.tool_input.cmd // empty')
fi

[ -z "$CMD" ] && exit 0

# Block destructive patterns
if echo "$CMD" | grep -qE 'rm\s+(-rf|-fr)\s'; then
    echo "BLOCKED: rm -rf is forbidden" >&2
    exit 2
fi

if echo "$CMD" | grep -qE 'chmod\s+-R\s'; then
    echo "BLOCKED: recursive chmod is forbidden" >&2
    exit 2
fi

if echo "$CMD" | grep -qE '(mkfs|dd\s+if=)'; then
    echo "BLOCKED: disk operations are forbidden" >&2
    exit 2
fi

if echo "$CMD" | grep -qE 'git\s+push\s+.*--force'; then
    echo "BLOCKED: force push is forbidden" >&2
    exit 2
fi

exit 0
