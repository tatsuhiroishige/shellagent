#!/usr/bin/env bash
# PostToolUse hook: remind to save after edits

INPUT=$(cat)
TOOL=$(echo "$INPUT" | jq -r '.tool_name // empty')

case "$TOOL" in
    mcp__shellagent__replace|\
    mcp__shellagent__insert_after|\
    mcp__shellagent__bulk_insert|\
    mcp__shellagent__delete_lines)
        echo '{"message": "Remember to call commit_edit() to save the file and report the diff."}'
        ;;
esac

exit 0
