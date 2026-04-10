# Playwright Test 05: Error Handling and Edge Cases

エラーケースと境界条件のテスト。

## Steps

1. `pw_text()` をブラウザ未起動で呼ぶ → エラーメッセージが返ること
2. `pw_url()` をブラウザ未起動で呼ぶ → エラーメッセージが返ること
3. `pw_accessibility()` をブラウザ未起動で呼ぶ → エラーメッセージが返ること
4. `pw_open("https://example.com")` でブラウザ起動
5. `pw_click("#nonexistent-element")` で存在しないセレクタをクリック → タイムアウトエラーが返ること
6. `pw_type("#nonexistent", "text")` で存在しないフィールドに入力 → エラーが返ること
7. `pw_open("https://httpbin.org/status/404")` で404ページを開く → エラーにならずページは開くこと
8. `pw_text()` で404の内容が取れること
9. `pw_close()` でブラウザ終了
10. `pw_close()` を再度呼ぶ → "Browser not open" が返ること

## 検証ポイント

- [ ] ブラウザ未起動時のツール呼び出しが安全にエラーを返す
- [ ] 存在しないセレクタへの操作がタイムアウトで適切にエラーを返す
- [ ] HTTPエラー（404等）でクラッシュしない
- [ ] 二重closeが安全に処理される
- [ ] エラー後もブラウザは使い続けられる（5, 6の後も7以降が動く）
