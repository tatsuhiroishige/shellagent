# Playwright Test 03: Scroll and Content Extraction

スクロール操作と大きなページからの情報抽出テスト。

## Steps

1. `pw_open("https://en.wikipedia.org/wiki/Tmux")` でWikipediaのtmux記事を開く
2. `pw_text()` でページ上部のテキスト確認
3. `pw_scroll("down", 1000)` で大きくスクロール
4. `pw_screenshot()` でスクロール後の表示確認
5. `pw_scroll("up", 500)` で少し戻る
6. `pw_eval("document.title")` で JavaScript によるタイトル取得
7. `pw_eval("document.querySelectorAll('h2').length")` で見出し数を取得
8. `pw_eval("Array.from(document.querySelectorAll('h2')).map(h => h.textContent)")` で全見出しテキスト取得
9. `pw_close()`

## 検証ポイント

- [ ] ピクセル単位のスクロールが動作する
- [ ] 上下両方向のスクロールができる
- [ ] pw_eval() で任意のJavaScriptが実行できる
- [ ] pw_eval() の結果がJSON形式で返る
- [ ] スクロール後もスクリーンショットが更新される
