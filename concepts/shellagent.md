# shellagent

**"Manusは結果をくれる。shellagentは過程を見せる。"**

---

## What

tmux上で動くAIエージェント操作基盤。
人間が使っても便利、AIが操作しても便利。
全ての操作がターミナル上でリアルタイムに可視化される。

## Why

AIエージェントは便利になったが、何をやっているか見えない。
Claude Codeは結果をdiffで返すだけ。Manusはスクショをブラックボックスで処理する。
開発者は結果だけでなく「過程」を知りたい。なぜその判断をしたか、途中で何を試したか、どの順番で考えたか。

見えなければ、信頼できない。学べない。介入できない。

shellagentは、AIの操作を人間がターミナルで作業するのと同じように見せる。
隣の席の同僚が作業しているのを覗き込むように、AIの作業を見守れる。

## How

```
┌──────────────────────┐     ┌──────────────────────────────┐
│ Claude Code Terminal  │     │ 操作ターミナル（tmux）         │
│                      │     │                              │
│ 人間が指示を出す      │────▶│  nvimでカーソルが動く          │
│ AIがMCPツールを呼ぶ   │     │  w3mでページが開く             │
│                      │     │  コマンドが打たれ出力が流れる   │
│                      │◀────│  全部、目の前で起きる          │
└──────────────────────┘     │                              │
                             │  人間はいつでも介入できる       │
                             └──────────────────────────────┘
```

AIエージェント → MCPサーバー → tmux pane内のCLIツール → 人間が見ている

---

## Core Principles

### 1. 過程の可視化

結果だけでなく過程を見せる。
nvimのカーソル移動、コマンド入力、出力の流れ。
人間が作業しているのと同じ速度、同じ見え方で。

### 2. 構造化された操作ログ

MCPサーバーを通る全操作が自動的に記録される。
SDKの計装不要。ツール名・引数・結果・タイムスタンプ。
後からフィルタ、集計、リプレイ可能。

### 3. テキストファースト

スクリーンショットではなくcapture-pane（テキスト）。
画像で数千トークン消費する代わりに、テキストで数百トークン。
コスト桁違い。速度も桁違い。

### 4. 介入可能

人間はいつでもtmux paneに入って操作を奪える。
特別な介入機能は不要。tmuxの既存の仕組みがそのまま介入メカニズム。
Ctrl-Cで止めて、自分で直して、またAIに渡す。

### 5. 人間の操作に見せる

AIの操作を、人間がターミナルで作業しているのと区別がつかないレベルまで近づける。
適度なディレイ、カーソル移動の可視化、コマンド入力→出力の自然な流れ。
見せ方のデザインそのものがプロダクト価値。

---

## Competitive Positioning

### コーディングエージェント市場（実行側）

Claude Code, Codex CLI, Devin, Cursor, Aider, Cline, AgenticSeek, Goose

→ shellagentはこれらの競合ではない。Claude Codeと**組み合わせて使う拡張レイヤー**。

### エージェントObservability市場（監視側）

LangSmith, Langfuse, AgentOps, Arize Phoenix, Maxim AI, Datadog LLM Observability

→ 一番近い競合だが、全て**API/SDK経由のログ収集ツール**。
計装が必要。事後のデバッグ・分析が主目的。

### shellagentの空白ポジション

| | 既存Observabilityツール | shellagent |
|---|---|---|
| データ取得 | SDK計装が必要 | MCPサーバー通過で自動記録 |
| 可視化 | ダッシュボード（事後） | tmuxライブ操作（リアルタイム） |
| 介入 | 不可 | paneに入ってその場で |
| コスト | SaaS課金 | ほぼゼロ |
| 対象 | LLMアプリ全般 | ターミナル操作全般 |

**「軽量 × リアルタイム可視 × ターミナルネイティブ × 介入可能」の組み合わせは誰もやっていない。**

---

## Manus/Devin との比較

| | Manus/Devin | shellagent |
|---|---|---|
| 実行環境 | VM/サンドボックス | tmuxセッション |
| ブラウザ操作 | Chromium + スクショ | w3m + capture-pane |
| 情報取得方式 | Vision API（画像→数千トークン） | テキスト（数百トークン） |
| インフラコスト | VM課金 | ほぼゼロ（既存マシン） |
| 透明性 | ブラックボックス | 全操作可視 |
| 介入 | 不可 or 制限的 | tmux paneで即座に |
| 操作の見え方 | 結果が返ってくる | 人間が作業しているように見える |

---

## UX Philosophy: 人間の操作に近づける

### なぜ重要か

AIがAPIコールで瞬時に結果を返すのは「魔法」。
魔法は信頼されない。理解できないから。

人間の同僚が目の前で作業しているのは「作業」。
作業は信頼される。過程が見えるから。

shellagentは魔法を作業に変える。

### 具体的な手法

**操作速度の調整**
- send-keysにディレイを挟み、人間が目で追える速度にする
- 一括バーストではなく、段階的な操作

**文脈の見える化**
- `:e filename` → ファイルが開く → 該当行に移動 → 編集開始
- `cd dir` → `ls` → `cat file` → 内容確認 → 判断
- 一連の流れが自然に見える

**pane構成のデザイン**
- エディタ、ターミナル、ブラウザが同時に見える
- 今どこで何が起きているか、一目で分かるレイアウト

---

## Target Users

### Primary: ターミナルで日常作業する開発者
- tmuxユーザー全体
- AIの操作を見たい、理解したい、学びたい人
- 「丸投げ」ではなく「協働」したい人

### Secondary
- **DevOps/SRE** — 透明性＋安全装置付きのサーバー操作
- **研究者** — CLIベースのクラスタ環境、予算制約
- **セキュリティ意識の高い組織** — 監査可能な操作ログ
- **チーム開発** — AIの操作を共有・レビュー・引き継ぎ

---

## Feature Scope

### Core: tmux操作プリミティブ（MCP Tools）

```
tmux_create_pane   — pane作成
tmux_send_keys     — キー送信
tmux_capture_pane  — 出力取得（テキスト）
tmux_status        — 状態一覧
tmux_kill          — プロセス中断
```

### Tools: CLIアプリ統合

```
エディタ    nvim       open_file, replace, delete_lines, insert_after, bulk_insert, commit_edit
ブラウザ    w3m        browse_open, browse_text, browse_dump, browse_scroll, browse_follow
メール      neomutt    mail_read, mail_draft, mail_send          [Phase 2]
ファイル    ranger     file_navigate, file_preview               [Phase 2]
Git         lazygit    git_status, git_commit, git_push          [Phase 2]
タスク      taskwarrior task_add, task_list, task_done            [Phase 2]
カレンダー  calcurse   cal_view, cal_add                         [Phase 2]
PDF         termpdf.py pdf_open, pdf_extract                     [Phase 2]
データ      csvkit/jq  data_query, data_transform                [Phase 2]
```

### Control: ポリシーエンジン

**ハード制御（MCPサーバー内部のhooks/middleware）**
- 破壊的コマンドの検知・ブロック
- 承認ゲート（メール送信、git push、削除等）
- 構造化操作ログの自動記録

**ソフト制御（CLAUDE.md / rules）**
- 行動指針、確認ルール
- ワークフロー定義

---

## Current Implementation (as of Phase 1+)

`scripts/mcp_server.py` — FastMCP (Python) ベースのMCPサーバー。**49ツール動作済み**。

**アーキテクチャ:**
- Transport抽象化レイヤー (LocalTransport / RemoteTransport)
- 構造化操作ログ (JSONL自動記録: seq, timestamp, tool, args, result, duration_ms)
- Human-likeディレイ (SHELLAGENT_DELAY=instant|normal|slow)
- ウィンドウ自動フォーカス切替 (browse_open→browse窓, run→main窓)
- レイアウトプリセット (dev, review, multi, reset)

**動作済みツール群:**
- セッション管理: init, status
- ターミナル: run, run_output, run_busy, run_kill
- nvim編集: open_file, replace, delete_lines, insert_after, bulk_insert, read_file, write_new_file, commit_edit
- タブ管理: tab_open, tab_list, tab_switch, tab_next, tab_prev, tab_close
- 並列ウィンドウ: term_new, term_send, term_output, term_busy, term_kill, term_close, term_list
- ペイン管理: pane_split, pane_send, pane_output, pane_busy, pane_kill, pane_close, pane_focus, pane_list
- ブラウザ(w3m): browse_open, browse_text, browse_dump, browse_scroll, browse_follow, browse_back, browse_search, browse_search_next, browse_url, browse_close
- レイアウト: layout
- 操作ログ: log_path, log_tail

---

## Roadmap

### Phase 1: MCP Server MVP ✅
MCPサーバー化。Local/Remote Transport。Claude Codeから操作ターミナルを叩ける。

### Phase 2: ツール拡充 (in progress)
w3m完了。neomutt, ranger, lazygit等のCLIアプリ統合。

### Phase 3: 制御層
hooks/middleware（一部完了: block-dangerous, post-edit-reminder）。承認ゲート強化、操作ログのエクスポート・リプレイ。

### Phase 4: UX磨き込み
操作速度の調整（human_delay基盤完了）。paneレイアウトのプリセット（基盤完了）。操作リプレイ機能。

### Phase 5: 公開
pipパッケージ、ドキュメント、設定テンプレート、setup.sh。

---

## One-liner

**shellagent — AIの操作が、人間の作業と同じように見えるターミナル統合基盤。**
