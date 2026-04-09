# Test 11: Write Code → Run Tests → Fix → Pass

テスト駆動の修正サイクル。CI的な日常フロー。

## Steps

1. テストファイルを先に作成:
   ```python
   write_new_file("/tmp/test_calc.py", """
   import subprocess, sys
   
   def run(expr):
       r = subprocess.run([sys.executable, "/tmp/calc.py", expr], capture_output=True, text=True)
       return r.stdout.strip()
   
   # Tests
   assert run("2+3") == "5", f"Expected 5, got {run('2+3')}"
   assert run("10*5") == "50", f"Expected 50, got {run('10*5')}"
   assert run("100/4") == "25.0", f"Expected 25.0, got {run('100/4')}"
   assert run("2**8") == "256", f"Expected 256, got {run('2**8')}"
   print("All tests passed!")
   """)
   ```

2. 意図的にバグ入りの実装を作成:
   ```python
   write_new_file("/tmp/calc.py", """
   import sys
   expr = sys.argv[1]
   # Bug: eval without handling power operator
   result = eval(expr.replace("^", "**"))
   print(result)
   """)
   ```

3. `layout("dev")`
4. mainで `run("python3 /tmp/test_calc.py")` — テスト実行
5. `run_output()` で結果確認（passするはず、でも意図的にバグを仕込む場面を想定）
6. terminalペインで `pane_send("terminal", "python3 /tmp/calc.py '2+3'")` — 個別テスト
7. `pane_output("terminal")` で確認
8. テスト失敗なら `open_file("/tmp/calc.py")` で修正
9. `replace(...)` で修正
10. `commit_edit(...)` で保存
11. `run("python3 /tmp/test_calc.py")` で再テスト
12. "All tests passed!" が出るまで繰り返す
13. `layout("reset")`

## 検証ポイント

- [ ] テスト実行→失敗→修正→再テストのループが自然に回る
- [ ] mainとterminalで並行して検証できる
- [ ] run()のnvim自動終了が修正→テストの切替で安定する
