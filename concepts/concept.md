# shellagent: ターミナル統合AIエージェント基盤

## ビジョン

「日常タスクをtmuxで完結させ、人間もAIエージェントも同じインターフェースで操作できる環境」を作る。

### 背景にある課題

- Claude Code等のAIエージェントはやっていることの中身が見えない（ブラックボックス問題）
- Manus等のGUIベースエージェントはVM+Chromium+Vision APIでコストが高い
- 既存のCLIツール群（neomutt, browsh, ranger, lazygit等）は豊富だが、統合・自動化するレイヤーがない
- tmuxは唯一、エディタ・ブラウザ・メール・git・ファイル管理を全部同じ画面に並べられる環境なのに、それらを繋ぐ仕組みが存在しない

### コアコンセプト

- **透明性**: 全操作がtmux pane上で実行されるため、人間はリアルタイムで全てを監視できる
- **低コスト**: capture-paneはテキスト（数百トークン）。Manusのスクショ方式（数千トークン）と桁違い
- **軽量**: VM不要。tmuxセッション+CLIツールだけで動作
- **汎用**: MCP準拠で、Claude Code/Cursor/Aider等どのエージェントからも使える
- **人間にも便利**: TUIアプリ群として人間が直接使っても生産的

---

## アーキテクチャ

```
┌─────────────────────────┐     ┌─────────────────────────────────┐
│  Claude Code ターミナル  │     │  操作ターミナル（tmux）          │
│  ─────────────────────  │     │  ┌───────┬───────┬───────┐      │
│  人間が指示を出す        │────▶│  │ nvim  │browsh │neomutt│      │
│  エージェントがMCPを呼ぶ │     │  │       │       │       │      │
│                         │     │  ├───────┼───────┤       │      │
│                         │     │  │ranger │lazygit│       │      │
│                         │◀────│  │       │       │       │      │
│  結果を受け取る          │     │  └───────┴───────┴───────┘      │
└─────────────────────────┘     │  ← 人間がリアルタイムで監視     │
                                │  ← いつでもpaneに入って介入可能  │
                                └─────────────────────────────────┘
```

### 3層構造

#### 1. コア層: tmuxセッション管理（プリミティブ）

最小限のtmux操作。これだけで原理的にはあらゆるCLIツールを操作可能。

| MCP Tool | 機能 |
|----------|------|
| `tmux_create_pane` | pane作成 |
| `tmux_send_keys` | paneへキー送信 |
| `tmux_capture_pane` | pane出力取得（テキスト） |
| `tmux_status` | 各paneの状態一覧 |
| `tmux_kill` | プロセス中断（C-c） |

#### 2. ツール層: CLIアプリのラッパー

各ツールの「起動→操作→結果取得」を統一インターフェースで提供。

| カテゴリ | ツール | MCP Tool例 |
|---------|--------|-----------|
| エディタ | nvim | `vim_open`, `vim_replace`, `vim_save`, `vim_view` |
| ブラウザ | browsh/carbonyl | `browse_open`, `browse_extract_text`, `browse_scroll` |
| メール | neomutt | `mail_read_inbox`, `mail_draft`, `mail_send` |
| ファイル管理 | ranger | `file_navigate`, `file_preview`, `file_copy` |
| Git | lazygit | `git_status`, `git_commit`, `git_push` |
| タスク管理 | taskwarrior | `task_add`, `task_list`, `task_done` |
| カレンダー | calcurse | `cal_view`, `cal_add_event` |
| PDF | termpdf.py | `pdf_open`, `pdf_extract_text` |
| データ処理 | csvkit/jq | `data_query`, `data_transform` |

#### 3. 制御層: ポリシーエンジン（hooks + rules）

MCPサーバー内部にガードを仕込む。エージェントが迂回できない構造的な安全装置。

```
rules/skills（エージェントの行動指針 → CLAUDE.md等）
    ↓ エージェントがMCPツールを呼ぶ
MCP Server（ここにhook/middlewareを仕込む）
    ↓ ガードを通過したものだけ実行
tmux（実際の操作）
    ↓ 人間が見てる
```

**ハードな強制（hooks/middleware in MCP Server）:**
- 破壊的コマンド検知（rm -rf, git push force, メール送信等）→ 実行前ブロック
- 承認ゲート: 人間の確認なしでは通さない操作リスト
- 全操作のタイムスタンプ付きログ記録

**ソフトなガイド（rules / CLAUDE.md）:**
- 「破壊的操作の前に確認を取れ」
- 「一度に複数ファイルを消すな」
- 「エラーが出たらcaptureでログ取得してから判断しろ」

**状態把握（skills的パターン）:**
- 作業開始時にsnapshot
- 定期的なstatus確認
- エラー時のログ取得手順

---

## 既存コード: ifarm_cli.sh

すでに動作しているシェルスクリプト。MCPサーバーから呼び出す形でそのまま使える。

### 実装済み機能

- **セットアップ・状態確認**: `setup`, `status`
- **キー送信**: `send`, `sendl`, `type`
- **出力取得**: `capture` (行数指定可)
- **プロセス制御**: `busy` (idle/busy判定), `kill` (C-c)
- **nvim操作**: `vim-open`, `vim-cmd`, `vim-save`, `vim-replace`, `vim-replace-save`, `vim-goto`, `vim-top`, `vim-bottom`, `vim-pagedown`, `vim-pageup`, `vim-view`
- **検索**: `findlines` (リモートgrep)
- **並列セッション**: `term-new`, `term-send`, `term-output`, `term-busy`, `term-close`, `term-list`

### 設計ポイント

- LOCAL_PANE経由で全操作を実行（透明性確保）
- `_ensure_nvim`でエディタの状態を自動検知・起動
- `_rtmux`で並列セッション管理（リモートtmux直接操作）
- grep/filterでノイズ除去（Loading, WARNING等）

---

## Manusとの比較（コスト優位性）

| | Manus | shellagent |
|---|---|---|
| 実行環境 | VM (毎セッション起動) | tmuxセッション |
| ブラウザ操作 | Chromium + スクショ | browsh + capture-pane |
| 情報取得 | Vision API (画像→数千トークン) | テキスト (数百トークン) |
| インフラコスト | VM課金 | ほぼゼロ (既存マシン) |
| レイテンシ | スクショ+推論で数秒 | capture即座 |
| 透明性 | ブラックボックス | 全操作可視 |

---

## ターゲットユーザー

1. **tmuxで日常作業してる開発者** — 統合・自動化レイヤーとして
2. **DevOps/SRE** — 透明性＋安全装置付きのサーバー操作エージェント
3. **研究者** — CLIベースのクラスタ環境、予算制約
4. **セキュリティ意識が高い組織** — 監査可能な全操作ログ
5. **コスト意識の高い個人/小規模チーム** — Manusの安価な代替

---

## 実装計画

### Phase 1: MVP（MCPサーバー化）

ifarm_cli.shをMCPサーバーでラップする。

- [ ] MCP Server基盤（TypeScript or Python）
- [ ] コア層ツール定義: `tmux_send`, `tmux_capture`, `tmux_create_pane`, `tmux_status`, `tmux_kill`
- [ ] エディタ層ツール定義: `vim_open`, `vim_replace`, `vim_save`, `vim_view`
- [ ] 並列セッション: `term_new`, `term_send`, `term_output`, `term_close`
- [ ] Claude Codeから接続して動作確認

### Phase 2: ツール層拡充

- [ ] ブラウザ: browsh連携（`browse_open`, `browse_extract_text`）
- [ ] PDF: termpdf.py連携（`pdf_open`, `pdf_text`）
- [ ] メール: neomutt連携（`mail_read`, `mail_draft`）
- [ ] ファイル管理: ranger連携（`file_navigate`, `file_preview`）
- [ ] Git: lazygit連携（`git_status`, `git_commit`）

### Phase 3: 制御層

- [ ] 破壊的コマンドの検知・ブロック（middleware）
- [ ] 承認ゲート機能
- [ ] 操作ログの記録・エクスポート
- [ ] CLAUDE.md用のルールテンプレート

### Phase 4: プロダクト化

- [ ] インストーラー / セットアップスクリプト
- [ ] ドキュメント
- [ ] 設定ファイル（どのツールを使うか、承認ルール等）
- [ ] npm / pip パッケージとして公開
