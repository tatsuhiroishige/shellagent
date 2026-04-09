# Test 06: Git Branch → Edit → Commit Workflow

ブランチ切って、コード修正して、diffを確認して、コミットする。日常の開発フロー。

## Steps

1. `layout("review")` で main + diff + log の3ペイン構成
2. mainで `run("cd /tmp && mkdir -p git-test && cd git-test && git init")`
3. `write_new_file("/tmp/git-test/app.py", ...)` で初期コード作成
4. `run("cd /tmp/git-test && git add . && git commit -m 'initial'")`
5. `run("cd /tmp/git-test && git checkout -b feature/add-logging")`
6. `open_file("/tmp/git-test/app.py")` で編集
7. `replace("print(result)", "import logging; logging.info(result); print(result)")`
8. `commit_edit("/tmp/git-test/app.py", "Add logging")`
9. diffペインで `pane_send("diff", "cd /tmp/git-test && git diff")` — 差分確認
10. `pane_output("diff")` で差分を読む
11. logペインで `pane_send("log", "cd /tmp/git-test && git log --oneline --all")` — ブランチ確認
12. `run("cd /tmp/git-test && git add -A && git commit -m 'feat: add logging'")`
13. `layout("reset")`

## 検証ポイント

- [ ] reviewレイアウトで3ペインが正しく並ぶ
- [ ] 各ペインに異なるgitコマンドを同時に送れる
- [ ] nvimでの編集→git diffの流れが自然
