# Test 09: Configuration File Management

設定ファイルを調査・比較・編集する。環境構築やデプロイの日常タスク。

## Scenario

"本番用configとステージング用configの差分を確認して、ステージングを本番に合わせる"

## Steps

1. 2つの設定ファイルを作成:
   ```
   write_new_file("/tmp/config_prod.json", ...)
   write_new_file("/tmp/config_staging.json", ...)
   ```
   prodは `{"db_host": "db-prod.internal", "cache_ttl": 3600, "debug": false, "workers": 8}`
   stagingは `{"db_host": "db-staging.internal", "cache_ttl": 60, "debug": true, "workers": 2}`

2. `run("diff /tmp/config_prod.json /tmp/config_staging.json")` で差分確認
3. `run_output()` で差分を読む
4. `open_file("/tmp/config_staging.json")` でステージング設定を開く
5. `replace("60", "3600")` で cache_ttl を本番に合わせる
6. `replace("true", "false")` で debug を無効化
7. `replace("2", "8")` で workers を本番に合わせる (db_hostは変えない)
8. `commit_edit("/tmp/config_staging.json", "Align staging config with prod")`
9. `run("diff /tmp/config_prod.json /tmp/config_staging.json")` で再度diff — db_hostだけが違うはず
10. `run_output()` で確認
11. `run("python3 -c \"import json; [print(f'{k}: {v}') for k,v in json.load(open('/tmp/config_staging.json')).items()]\"")` でJSON parse確認

## 検証ポイント

- [ ] JSONファイルの部分編集ができる
- [ ] replaceで意図した値だけが変わる（"2"→"8"でworkersだけ変わるか注意）
- [ ] diff→edit→diffの確認サイクルが回る
- [ ] 編集後もJSONとして有効
