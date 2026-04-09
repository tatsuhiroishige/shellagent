# Test 07: Bug Investigation → Fix → Verify

バグ報告を受けて、原因を調査して、修正して、動作確認する。

## Scenario

"calculate_tax()が消費税10%のはずなのに8%で計算している"

## Steps

1. `write_new_file("/tmp/tax.py", ...)` でバグ入りコードを用意:
   ```python
   TAX_RATE = 0.08  # Bug: should be 0.10
   
   def calculate_tax(price):
       return int(price * TAX_RATE)
   
   def total_with_tax(price):
       return price + calculate_tax(price)
   
   if __name__ == "__main__":
       print(f"Price: 1000, Tax: {calculate_tax(1000)}, Total: {total_with_tax(1000)}")
   ```
2. `run("python3 /tmp/tax.py")` で現状を確認 — "Tax: 80" が出る
3. `run_output()` でバグ確認
4. `open_file("/tmp/tax.py")` でソース確認
5. `read_file("/tmp/tax.py")` で全体を見る
6. `replace("0.08", "0.10")` で修正
7. `replace("# Bug: should be 0.10", "# Fixed: 10% consumption tax")` でコメント修正
8. `commit_edit("/tmp/tax.py", "Fix tax rate: 8% -> 10%")`
9. `run("python3 /tmp/tax.py")` で再実行
10. `run_output()` で "Tax: 100, Total: 1100" を確認

## 検証ポイント

- [ ] バグ再現→修正→検証のサイクルが途切れない
- [ ] replaceが正確に狙った箇所だけ変える
- [ ] run()でnvim自動終了→コマンド実行がスムーズ
