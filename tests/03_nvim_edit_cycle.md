# Test 03: Full nvim Edit Cycle

ファイルの作成→編集→検証の完全サイクル。

## Steps

1. `write_new_file("/tmp/hello.py", "def greet(name):\n    return f'Hello {name}'\n\nprint(greet('World'))\n")`
2. `read_file("/tmp/hello.py")` で内容確認
3. `open_file("/tmp/hello.py")` でnvimで開く
4. `replace("World", "shellagent")` で文字列置換
5. `commit_edit("/tmp/hello.py", "Changed greeting target")` で保存
6. `read_file("/tmp/hello.py")` で変更を確認 — "shellagent"が入っていること
7. `run("python3 /tmp/hello.py")` で実行
8. `run_output()` で "Hello shellagent" が出力されること
9. `open_file("/tmp/hello.py")` で再度開く
10. `delete_lines(1, 2)` で関数定義を削除
11. `bulk_insert(1, "def greet(name, emoji='👋'):\n    return f'{emoji} Hello {name}!'")` で新しい実装を挿入
12. `commit_edit("/tmp/hello.py", "Added emoji parameter")`
13. `run("python3 /tmp/hello.py")` → 出力に絵文字が含まれること

## 検証ポイント

- [ ] write→read→open→replace→commit の流れが途切れない
- [ ] replaceで正確に1箇所だけ置換される
- [ ] delete_lines + bulk_insertで複数行編集ができる
- [ ] run()でnvimが自動的に閉じてからコマンドが実行される
