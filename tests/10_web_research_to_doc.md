# Test 10: Web Research → Documentation

複数のWebソースを調べて、まとめドキュメントを作る。技術調査タスク。

## Scenario

"Python の match文（3.10+）の使い方を調べてチートシートを作れ"

## Steps

1. `browse_open("https://docs.python.org/3/whatsnew/3.10.html")` で公式ドキュメント確認
2. `browse_search("Structural Pattern Matching")` で該当セクションに飛ぶ
3. `browse_text(40)` で内容を読む
4. `browse_scroll("down", 2)` で続きを読む
5. `browse_text(40)` で追加情報取得
6. `browse_dump("https://peps.python.org/pep-0636/")` でPEP 636のチュートリアルをテキスト取得
7. `browse_close()`
8. 収集した情報を元に `write_new_file("/tmp/match_cheatsheet.md", ...)` でチートシート作成
9. `open_file("/tmp/match_cheatsheet.md")` でnvimで確認・微調整
10. `commit_edit("/tmp/match_cheatsheet.md", "Python match statement cheatsheet")`
11. `run("cat /tmp/match_cheatsheet.md")` でターミナルで表示確認

## 検証ポイント

- [ ] ブラウザのインタラクティブ操作とdumpモードの使い分けができる
- [ ] 複数ソースの情報を統合してドキュメントを作れる
- [ ] browse_close()後にmainに戻ってファイル作成に移行できる
