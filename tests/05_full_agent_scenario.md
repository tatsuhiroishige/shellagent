# Test 05: Full Agent Scenario

エージェントが「Webで調べて→コードを書いて→テストして→結果を報告する」一連の流れ。
shellagentの全レイヤーを横断する統合テスト。

## Scenario

"Open-Meteo APIを使って、東京の今日の天気を取得するPythonスクリプトを作れ"

## Steps

### Phase 1: 調査
1. `init()`
2. `layout("dev")` でdev構成
3. `browse_open("https://open-meteo.com/en/docs")` でAPI docs確認
4. `browse_text(50)` でドキュメント読み取り
5. `browse_scroll("down", 2)` でスクロール
6. `browse_text(50)` でエンドポイント情報取得
7. `browse_close()` → mainに戻る

### Phase 2: 実装
8. `write_new_file("/tmp/tokyo_weather.py", ...)` — APIから天気取得するスクリプト
9. `open_file("/tmp/tokyo_weather.py")` でnvimで確認
10. 必要に応じて `replace()` で修正
11. `commit_edit()` で保存

### Phase 3: テスト
12. `run("python3 /tmp/tokyo_weather.py")` で実行
13. `run_busy()` で実行中確認
14. `run_output()` で結果確認
15. エラーがあれば Phase 2 に戻って修正

### Phase 4: 報告
16. `log_tail(20)` で全操作ログを確認
17. `layout("reset")` で片付け
18. `status()` で最終状態確認

## 検証ポイント

- [ ] browse→code→run の流れがウィンドウフォーカス切替を含めて自然
- [ ] nvimでの編集とrun()の切替（nvim自動終了）が安定
- [ ] 操作ログに全ステップが時系列で記録される
- [ ] layout("dev")→layout("reset")のライフサイクルが正しい
- [ ] エラー時の修正→再実行ループが可能

## 期待する操作ログ（概要）

```
init → layout(dev) → browse_open → browse_text → browse_scroll → browse_text
→ browse_close → write_new_file → open_file → commit_edit → run → run_output
→ log_tail → layout(reset) → status
```
