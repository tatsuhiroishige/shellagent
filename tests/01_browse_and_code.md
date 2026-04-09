# Test 01: Browse → Research → Code

ブラウザで調査して、その結果を元にスクリプトを書いて動かす。

## Steps

1. `init()` でセッション確認
2. `browse_open("https://wttr.in/:help")` で wttr.in のAPI仕様を調べる
3. `browse_text()` で内容を読む
4. `browse_close()` でブラウザを閉じる（mainに戻る）
5. `write_new_file("/tmp/weather.sh", ...)` で天気取得スクリプトを書く
6. `run("bash /tmp/weather.sh")` で実行
7. `run_output()` で結果確認
8. `log_tail()` で操作ログを確認 — 全ステップが記録されていること

## 検証ポイント

- [ ] ブラウザ→mainのフォーカス切替が自然に見える
- [ ] browse_textでwttr.inのヘルプ内容が読める
- [ ] 作成したスクリプトが正しく動作する
- [ ] 操作ログに全8ステップが記録される
