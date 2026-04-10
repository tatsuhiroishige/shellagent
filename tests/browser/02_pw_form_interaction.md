# Playwright Test 02: Form Interaction

フォーム入力・ボタンクリック・JavaScript対応のテスト。

## Steps

1. `pw_open("https://httpbin.org/forms/post")` でフォームページを開く
2. `pw_accessibility()` でフォーム構造を確認 — input, button 等が見えること
3. `pw_type("input[name='custname']", "Test User")` で名前入力
4. `pw_type("input[name='custtel']", "090-1234-5678")` で電話番号入力
5. `pw_type("input[name='custemail']", "test@example.com")` でメール入力
6. `pw_type("textarea[name='comments']", "This is a test comment")` でコメント入力
7. `pw_screenshot()` で入力状態のスクリーンショット確認
8. `pw_click("button[type='submit']")` で送信ボタンクリック
9. `pw_text()` で送信結果ページのテキスト確認
10. `pw_close()`

## 検証ポイント

- [ ] 各フォームフィールドにテキストが入力できる
- [ ] pw_type の clear=True（デフォルト）で既存値が上書きされる
- [ ] ボタンクリックでフォーム送信ができる
- [ ] 送信後のページ内容が取得できる
- [ ] 操作ごとにスクリーンショットが更新される
