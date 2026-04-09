---
trigger: always_on
---

# Editing Policy

## Workflow
1. `open_file(path)` — open in nvim
2. Make edits: `replace()`, `delete_lines()`, `insert_after()`, `bulk_insert()`
3. `commit_edit(path, summary)` — save and report
4. Verify with `read_file(path)` if needed

## Rules
- Use `replace()` for single-line changes only
- For multi-line changes: `delete_lines()` + `bulk_insert()`
- When deleting multiple ranges: delete bottom-to-top (line numbers shift)
- `bulk_insert(line=0)` is unreliable — use `line >= 1`
- After `commit_edit()`, the file is saved but nvim stays open
- To return to shell: either open another file or let `run()` auto-close nvim

## Tab Management
- Use `tab_open()` to view multiple files simultaneously
- `tab_list()` shows all open tabs
- Always close tabs you no longer need with `tab_close()`
