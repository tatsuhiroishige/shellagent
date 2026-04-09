# Test 02: Multi-Pane Parallel Workflow

レイアウトプリセットを使い、複数ペインで並列作業する。

## Steps

1. `layout("dev")` でmain + terminalの2ペイン構成にする
2. `status()` で2ペイン確認
3. mainペインで `open_file("/tmp/test_multi.py")` → nvimでファイル作成
4. terminalペインで `pane_send("terminal", "python3 -c 'import http.server; ...'")` — 簡易HTTPサーバー起動
5. `pane_busy("terminal")` で実行中確認
6. mainに戻って `run("curl -s http://localhost:8888")` でサーバーにアクセス
7. `run_output()` で結果確認
8. `pane_kill("terminal")` でサーバー停止
9. `layout("reset")` で片付け
10. `log_tail()` で全操作確認

## 検証ポイント

- [ ] devレイアウトで2ペインが正しく作られる
- [ ] terminalペインでサーバーが起動してbusy=true
- [ ] mainペインからcurlでサーバーにアクセスできる
- [ ] resetで1ペインに戻る
