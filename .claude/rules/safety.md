---
trigger: always_on
---

# Safety Rules

## MCP First
- Always use shellagent MCP tools as the primary interface
- Do NOT use Bash tool to bypass MCP when MCP tools are available
- MCP hooks enforce safety guards that raw Bash cannot

## Forbidden Operations (hard-blocked by hooks)
- `rm -rf` — recursive delete
- `chmod -R` — recursive permission change
- `mkfs`, `dd if=` — disk operations
- `git push --force` — force push

## Verification Protocol
- After every edit (replace, insert, delete): call `commit_edit()` to save
- After `run()`: check `run_output()` to verify result
- Before destructive changes: capture current state first
- Never assume an operation succeeded — always verify

## nvim Safety
- One file at a time in the main pane (use tabs for multiple)
- Always exit nvim before running shell commands (`run()` does this automatically)
- If nvim gets stuck: use `run_kill()` then retry
