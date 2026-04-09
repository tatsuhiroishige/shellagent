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

## Hooks
- **PreToolUse**: `run`, `term_send` → `block-dangerous.sh` (rm -rf等ブロック)
- **PostToolUse**: 編集系 → `post-edit-reminder.sh` (commit_edit忘れ防止)
- **Stop**: タスク完了チェックポイント

## Architecture

```
Claude Code → MCP Server (shellagent)
                ↓
            Transport Layer
            ├── LocalTransport (直接tmux + ローカルI/O)
            └── RemoteTransport (LOCAL_PANE中継 + SSH)
                ↓
            tmux session (人間が監視)
```
