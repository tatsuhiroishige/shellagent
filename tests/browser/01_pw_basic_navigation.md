# Playwright Test 01: Basic Navigation

Playwrightブラウザの基本操作テスト。

## Steps

1. `init()` でセッション確認
2. `pw_open("https://example.com")` でページを開く
3. tmux の `pwbrowse` ウィンドウに2ペイン（スクリーンショット + ログ）が表示されることを確認
4. `pw_text()` でページテキスト取得 — "Example Domain" が含まれること
5. `pw_url()` で現在のURL確認 — `https://example.com/` であること
6. `pw_accessibility()` でアクセシビリティツリー取得 — heading, link 等の構造が見えること
7. `pw_screenshot()` で手動スクリーンショット更新
8. `pw_click("a")` で "More information..." リンクをクリック
9. `pw_url()` でURLが変わったことを確認（iana.org に遷移）
10. `pw_back()` で example.com に戻る
11. `pw_url()` で戻ったことを確認
12. `pw_close()` でブラウザ終了

## 検証ポイント

- [ ] pwbrowse ウィンドウが自動作成される
- [ ] 左ペインにスクリーンショットが表示される（chafa）
- [ ] 右ペインに操作ログが流れる
- [ ] pw_text() で JS 実行後のテキストが取れる
- [ ] pw_accessibility() で構造化されたツリーが返る
- [ ] リンククリック→戻るの往復ができる
- [ ] pw_close() 後に main ウィンドウにフォーカスが戻る
