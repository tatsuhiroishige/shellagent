# shellagent — Terminal-integrated AI Agent Infrastructure

## Overview
tmux上で動作する透明・低コストなAIエージェント基盤。
全操作がtmux pane上で実行され、人間はリアルタイムで監視・介入可能。

## Environment

| Key | Value |
|-----|-------|
| Mode | `local` (default) or `remote` |
| Session | `shellagent` |
| MCP Server | `scripts/mcp_server.py` |
| Transport | `LocalTransport` / `RemoteTransport` |

## Quick Start

1. `init()` — tmuxセッション作成
2. `run(cmd)` — コマンド実行
3. `run_output()` — 出力取得
4. `open_file(path)` → edit → `commit_edit()` — ファイル編集

## MCP Tools Reference

### Session
| Tool | Description |
|------|-------------|
| `init()` | セッション初期化 |
| `status()` | セッション状態表示 |

### Terminal (Main Pane)
| Tool | Description |
|------|-------------|
| `run(cmd)` | コマンド実行（nvim自動終了） |
| `run_output(lines)` | 出力キャプチャ |
| `run_busy()` | プロセス実行中か確認 |
| `run_kill()` | Ctrl+C送信 |

### File Editing (nvim)
| Tool | Description |
|------|-------------|
| `open_file(path)` | ファイルを開く |
| `goto_line(n)` | 行ジャンプ |
| `replace(old, new)` | 単一行置換 |
| `delete_lines(start, end)` | 行削除 |
| `insert_after(line, text)` | 行挿入 |
| `bulk_insert(line, text)` | ブロック挿入 |
| `write_new_file(path, content)` | 新規ファイル作成 |
| `read_file(path, offset, limit)` | ファイル読み取り |
| `commit_edit(path, summary)` | 保存・レポート |

### Tabs
| Tool | Description |
|------|-------------|
| `tab_open(path)` | 新タブで開く |
| `tab_list()` | タブ一覧 |
| `tab_switch(n)` | タブ切替 |
| `tab_next()` / `tab_prev()` | 次/前のタブ |
| `tab_close()` | タブを閉じる |

### Parallel Sessions
| Tool | Description |
|------|-------------|
| `term_new(name)` | ウィンドウ作成 |
| `term_send(name, cmd)` | コマンド送信 |
| `term_output(name, lines)` | 出力取得 |
| `term_busy(name)` | 実行中確認 |
| `term_kill(name)` | Ctrl+C |
| `term_close(name)` | ウィンドウ削除 |
| `term_list()` | 一覧表示 |

### Browser (w3m — text browsing)
| Tool | Description |
|------|-------------|
| `browse_open(url)` | w3mでURL表示 |
| `browse_text(lines)` | 画面テキスト取得 |
| `browse_dump(url)` | w3m -dumpでテキスト取得（非対話） |
| `browse_scroll(direction, pages)` | ページスクロール |
| `browse_follow(n)` | リンクをたどる |
| `browse_back()` | 戻る |
| `browse_search(query)` | ページ内検索 |
| `browse_search_next()` | 次の検索結果 |
| `browse_url()` | 現在のURL取得 |
| `browse_close()` | ブラウザ終了 |

### Playwright Browser (headless Chromium — full web操作)
| Tool | Description |
|------|-------------|
| `pw_open(url)` | URLを開く（スクリーンショット自動表示） |
| `pw_click(selector)` | CSSセレクタで要素クリック |
| `pw_type(selector, text)` | フォーム入力（clear=Trueで上書き） |
| `pw_scroll(direction, amount)` | スクロール（ピクセル単位） |
| `pw_text()` | ページテキスト取得（JS実行後） |
| `pw_accessibility()` | アクセシビリティツリー取得 |
| `pw_screenshot()` | 手動スクリーンショット更新 |
| `pw_eval(js)` | JavaScript実行 |
| `pw_back()` | 戻る |
| `pw_url()` | 現在のURL取得 |
| `pw_close()` | ブラウザ終了 |

tmux上の `pwbrowse` ウィンドウに2ペイン表示:
- 左 (65%): chafaでスクリーンショット表示（操作ごとに自動更新）
- 右 (35%): 操作ログのリアルタイム表示

依存: `playwright`, `chafa` (`brew install chafa`), 初回 `playwright install chromium`

## Hooks
- **PreToolUse**: `run`, `term_send` → `block-dangerous.sh` (rm -rf等ブロック)
- **PostToolUse**: 編集系 → `post-edit-reminder.sh` (commit_edit忘れ防止)
- **Stop**: タスク完了チェックポイント

## Environment Variables

| Var | Default | Description |
|-----|---------|-------------|
| `SHELLAGENT_MODE` | `local` | `local` or `remote` |
| `SHELLAGENT_SESSION` | `shellagent` | tmux session name |
| `SHELLAGENT_WORKDIR` | `~` | Working directory |
| `SHELLAGENT_LOG_DIR` | `~/.shellagent/logs` | JSONL operation log directory |

## Architecture

```
Claude Code → MCP Server (shellagent)
                ↓
            Transport Layer
            ├── LocalTransport (直接tmux + ローカルI/O)
            └── RemoteTransport (LOCAL_PANE中継 + SSH)
                ↓
            tmux session (人間が監視)
                ↓
            Operation Logger (JSONL自動記録)
```

## Layout Presets
| Preset | Description |
|--------|-------------|
| `layout("dev")` | main (60%) \| terminal (40%) |
| `layout("review")` | main (60%) \| diff + log (40%) |
| `layout("multi")` | main (50%) \| agent-1 + agent-2 (50%) |
| `layout("reset")` | 全ペイン閉じてmainのみ |

## Operation Log
| Tool | Description |
|------|-------------|
| `log_path()` | 現セッションのログファイルパス |
| `log_tail(n)` | 直近n件のログエントリ表示 |

ログ形式: JSONL (seq, ts, tool, args, result, duration_ms)
