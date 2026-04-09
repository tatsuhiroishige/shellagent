# Test 12: Live Monitoring Setup

複数ペインでモニタリングダッシュボードを構成する。SRE向け。

## Steps

1. まずダミーのログ生成スクリプトを作成:
   ```python
   write_new_file("/tmp/gen_log.sh", """
   while true; do
     STATUS=$((RANDOM % 3))
     case $STATUS in
       0) echo "$(date +%H:%M:%S) INFO  request processed in $((RANDOM % 100))ms" ;;
       1) echo "$(date +%H:%M:%S) WARN  high latency: $((RANDOM % 500 + 500))ms" ;;
       2) echo "$(date +%H:%M:%S) ERROR connection timeout" ;;
     esac
     sleep 1
   done
   """)
   ```

2. `layout("multi")` で main + agent-1 + agent-2 の3ペイン
3. agent-1でログ生成: `pane_send("agent-1", "bash /tmp/gen_log.sh")`
4. agent-2でエラーだけフィルタ: `pane_send("agent-2", "bash /tmp/gen_log.sh | grep ERROR")`
5. 数秒待つ
6. `pane_output("agent-1", 10)` でログストリーム確認
7. `pane_output("agent-2", 10)` でエラーだけ確認
8. mainで `run("bash /tmp/gen_log.sh | head -20 | awk '{print $3}' | sort | uniq -c | sort -rn")` で集計
9. `run_output()` で集計結果確認
10. `pane_kill("agent-1")` + `pane_kill("agent-2")` で停止
11. `layout("reset")`

## 検証ポイント

- [ ] 3ペインが同時にそれぞれ別のプロセスを動かせる
- [ ] 各ペインのoutputが独立して取得できる
- [ ] pane_killで個別にプロセスを止められる
- [ ] tmux上でリアルタイムにログが流れるのが見える（shellagentの「過程の可視化」）
