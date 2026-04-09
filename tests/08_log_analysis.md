# Test 08: Server Log Analysis

ログファイルを生成して、ターミナルツールで分析する。SRE/DevOpsの日常タスク。

## Steps

1. `write_new_file("/tmp/access.log", ...)` でダミーアクセスログを生成:
   ```
   2026-04-09 10:00:01 GET /api/users 200 45ms
   2026-04-09 10:00:02 POST /api/login 401 12ms
   2026-04-09 10:00:03 GET /api/users 200 38ms
   2026-04-09 10:00:04 POST /api/login 401 15ms
   2026-04-09 10:00:05 GET /api/products 500 2300ms
   2026-04-09 10:00:06 POST /api/login 200 22ms
   2026-04-09 10:00:07 GET /api/products 500 2100ms
   2026-04-09 10:00:08 GET /api/users 200 41ms
   2026-04-09 10:00:09 GET /api/products 500 2500ms
   2026-04-09 10:00:10 POST /api/orders 201 89ms
   ```
2. `layout("dev")`
3. mainで `run("cat /tmp/access.log")` で全体確認
4. `run("grep 500 /tmp/access.log")` でエラー抽出
5. `run("grep 500 /tmp/access.log | wc -l")` でエラー件数カウント
6. `run("awk '{print $4}' /tmp/access.log | sort | uniq -c | sort -rn")` でエンドポイント別集計
7. `run("grep 500 /tmp/access.log | awk '{print $4}' | sort | uniq -c")` でエラーのエンドポイント特定
8. terminalペインで `pane_send("terminal", "grep 401 /tmp/access.log")` — 認証失敗も並行調査
9. `run_output()` + `pane_output("terminal")` で両方の結果を収集
10. `write_new_file("/tmp/report.md", ...)` で分析レポートをmarkdownで作成
11. `read_file("/tmp/report.md")` で確認
12. `layout("reset")`

## 検証ポイント

- [ ] grep/awk/sort/uniqのパイプラインがtmux経由で正しく動く
- [ ] 2ペインで並行調査ができる
- [ ] 分析結果からレポートファイルを生成できる
