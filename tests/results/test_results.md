# ShellAgent MCP Server Test Results

Timestamp: 2026-04-09T23:55:00+09:00
Runner: Claude Opus 4.6 via MCP tools (direct invocation)

## Summary

| Test | Name | Result |
|------|------|--------|
| 05 | Full Agent Scenario | PASS |
| 06 | Git Branch/Edit/Commit Workflow | PASS |
| 07 | Bug Investigation/Fix/Verify | PASS |
| 08 | Server Log Analysis | PASS |
| 09 | Configuration File Management | PASS |
| 10 | Web Research to Documentation | PASS |
| 11 | Build and Test (TDD cycle) | PASS |
| 12 | Live Monitoring Dashboard | PASS |
| 13 | API Exploration / Client Library | PASS |

**Overall: 9/9 PASS**

## Test Details

### Test 05: Full Agent Scenario
- [x] browse -> code -> run flow with window focus switching works naturally
- [x] nvim edit and run() switching (nvim auto-close) is stable
- [x] Operation log records all steps in chronological order
- [x] layout("dev") -> layout("reset") lifecycle correct
- [x] Error correction and re-execution loop possible
- Note: Open-Meteo docs page is JS-heavy so w3m shows limited content, but browse_text still returned useful navigation info. The API endpoint was already known and the script worked correctly on first run, fetching live Tokyo weather data (13.8C, light drizzle).

### Test 06: Git Branch/Edit/Commit Workflow
- [x] Review layout creates 3 panes (main + diff + log) correctly
- [x] Different git commands sent to different panes simultaneously
- [x] nvim edit -> git diff flow is natural
- Note: Git repo at /tmp/git-test already had some state from a prior run. The test adapted and completed the full workflow: create file, commit, branch, edit in nvim, diff in separate pane, git log in third pane, final commit on feature branch.

### Test 07: Bug Investigation/Fix/Verify
- [x] Bug reproduction confirmed: "Tax: 80, Total: 1080"
- [x] replace() accurately changes only targeted strings (0.08 -> 0.10 and comment)
- [x] run() auto-closes nvim and executes commands smoothly
- [x] Fix verified: "Tax: 100, Total: 1100"
- Full bug-reproduce -> fix -> verify cycle completed without interruption.

### Test 08: Server Log Analysis
- [x] grep/awk/sort/uniq pipelines work correctly via tmux
- [x] 2-pane parallel investigation (500 errors in main, 401 errors in terminal)
- [x] Analysis report generated as markdown file, read back successfully
- grep found 3x500 errors all on /api/products, 2x401 on /api/login. Endpoint distribution correctly counted via awk pipeline.

### Test 09: Configuration File Management
- [x] JSON partial editing works (replaced cache_ttl, debug, workers individually)
- [x] replace() changed only intended values (used key:value patterns to avoid ambiguity with bare "2" -> "8")
- [x] diff -> edit -> diff confirmation cycle works
- [x] JSON remains valid after editing (python3 json.load succeeds)
- After edits, diff correctly shows only db_host difference between prod and staging.

### Test 10: Web Research to Documentation
- [x] Interactive browser (browse_open + browse_search + browse_text) and dump mode (browse_dump) used together
- [x] Multiple sources (Python 3.10 whatsnew + PEP 636) combined into a cheatsheet
- [x] browse_close() returns to main for file creation
- browse_search("Structural Pattern Matching") navigated to the correct section. PEP 636 dump returned the full tutorial text (~500 lines).

### Test 11: Build and Test (TDD cycle)
- [x] Test execution -> failure -> fix -> retest loop works naturally
- [x] Main and terminal panes used for parallel verification
- [x] run() auto-close of nvim during fix/test switching is stable
- Intentionally introduced a bug (replaced ** with ^), saw AssertionError, fixed it, all tests passed on retry.

### Test 12: Live Monitoring Dashboard
- [x] 3 panes (multi layout) run separate processes simultaneously
- [x] Each pane's output captured independently (agent-1: all logs, agent-2: ERROR only)
- [x] pane_kill() stops individual processes via Ctrl+C
- [x] Real-time log streaming visible in tmux (verified via pane_output after ~15 seconds)
- Note: The head -20 aggregation command was slow (needed 20s for 20 lines at 1/sec), so was killed and replaced with a faster pipeline test which confirmed awk/sort/uniq works.

### Test 13: API Exploration / Client Library
- [x] Browser -> curl -> code creation investigation flow is natural
- [x] Created CLI tool (jph.py) works with live JSONPlaceholder API
- [x] Dev layout allows parallel testing (posts in main, user in terminal)
- All three CLI commands verified: "posts 5" listed 5 posts, "user 1" showed Leanne Graham's details, "post 1" showed title + 5 comments.

## Notes

- The tmux session "shellagent" persisted throughout all tests with no crashes or hangs
- layout("reset") reliably returned to single-pane state between tests
- The nvim auto-close feature (when run() is called while nvim is open) worked consistently across all tests
- run_output() returns the full tmux scroll buffer, which can include output from previous commands. This is by design but means the caller needs to parse for the relevant section.
- pane_busy() returned false for the log generator scripts in Test 12, likely because bash spawns child processes (sleep) which are not the foreground process of the pane itself. The scripts were still running correctly.
- All network-dependent tests (Open-Meteo API, JSONPlaceholder API, Python docs, PEP website) succeeded, confirming external connectivity through the tmux environment.
