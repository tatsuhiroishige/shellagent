# Playwright Test 04: SPA / JavaScript-heavy Pages

w3mでは不可能なJavaScript依存ページの操作テスト。

## Steps

1. `pw_open("https://httpbin.org/")` を開く
2. `pw_text()` でトップページ確認（JS でレンダリングされる内容）
3. `pw_accessibility()` でページ構造確認
4. `pw_click("a[href='/get']")` で /get エンドポイントをクリック
5. `pw_text()` で JSON レスポンスが表示されることを確認
6. `pw_back()` で戻る
7. `pw_open("https://httpbin.org/headers")` で別ページを開く
8. `pw_text()` でブラウザヘッダー情報が表示されることを確認
9. `pw_close()`

## 検証ポイント

- [ ] JavaScript で動的にレンダリングされるページが正しく表示される
- [ ] pw_open() で別URLに遷移できる（ブラウザ再起動なし）
- [ ] JSON レスポンスのテキストが取得できる
- [ ] アクセシビリティツリーで動的コンテンツの構造が見える
