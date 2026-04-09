# Test 13: API Exploration → Client Library

未知のAPIを叩いて構造を理解し、クライアントラッパーを書く。

## Scenario

"JSONPlaceholder APIを調査して、使いやすいCLIクライアントを作れ"

## Steps

### Phase 1: API調査
1. `browse_open("https://jsonplaceholder.typicode.com/")` でドキュメント確認
2. `browse_text(30)` で利用可能なエンドポイント確認
3. `browse_close()`
4. `run("curl -s https://jsonplaceholder.typicode.com/posts/1 | python3 -m json.tool")` で実際のレスポンス構造確認
5. `run_output()`
6. `run("curl -s https://jsonplaceholder.typicode.com/users/1 | python3 -m json.tool")` で別エンドポイントも確認
7. `run_output()`

### Phase 2: 実装
8. `write_new_file("/tmp/jph.py", ...)` — CLIクライアント:
   - `jph posts [n]` — 直近n件のポスト一覧
   - `jph user <id>` — ユーザー詳細
   - `jph post <id>` — ポスト詳細 + コメント数
9. `read_file("/tmp/jph.py")` で確認

### Phase 3: テスト
10. `layout("dev")`
11. mainで `run("python3 /tmp/jph.py posts 5")`
12. terminalで `pane_send("terminal", "python3 /tmp/jph.py user 1")`
13. `run_output()` + `pane_output("terminal")` で両方確認
14. `run("python3 /tmp/jph.py post 1")` でコメント付き表示
15. `run_output()`
16. `layout("reset")`

## 検証ポイント

- [ ] ブラウザ→curl→コード作成の調査フローが自然
- [ ] 作成したCLIツールが実際にAPIを叩いて動く
- [ ] devレイアウトで並列テストができる
