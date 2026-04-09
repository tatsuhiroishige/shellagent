# Test 04: Browser Deep Navigation

ブラウザで複数ページを辿り、情報を収集する。

## Steps

1. `browse_open("https://news.ycombinator.com")` でHNを開く
2. `browse_text(30)` でトップページ確認
3. `browse_scroll("down")` でスクロール
4. `browse_search("Show HN")` でShow HN記事を検索
5. `browse_search_next()` で次のマッチに移動
6. `browse_text(10)` で現在位置確認
7. `browse_follow(1)` でリンクを辿る
8. `browse_text(20)` で遷移先の内容確認
9. `browse_back()` でHNに戻る
10. `browse_url()` でURL確認
11. 同時に `browse_dump("https://news.ycombinator.com/newest")` でnew記事をテキスト取得
12. `browse_close()`

## 検証ポイント

- [ ] ページ内検索が動く
- [ ] リンク追跡→戻るの往復ができる
- [ ] browse_dumpがインタラクティブセッションと独立して動く
- [ ] 全操作でtmuxフォーカスがbrowseウィンドウにある
