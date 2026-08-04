# 開発チーム基盤(サブエージェント7ロール)

参考: https://qiita.com/su3-hokkaido/items/89fcfd2702ecba65c74d

## 導入手順

1. このフォルダ内の7つの `.md` ファイルを、プロジェクトの `.claude/agents/` にコピーする
   (全プロジェクト共通で使いたい場合は `~/.claude/agents/` に置く)
2. 展開先の `CLAUDE.md` に、エージェント一覧と品質ゲートのコマンド(lint/test等、プロジェクトごとに実体は異なる)を追記する
3. プロジェクト固有の情報(技術スタック・コマンド・規約)は、エージェント定義ではなく展開先の `CLAUDE.md` や `.claude/rules/` に書く
   → これにより同じ7ロールをどのプロジェクトでも使い回せる

## 体制

```
人間(あなた)
│
├── 相談(プロジェクト外・独立)
│    └── em-support (Opus)
│
└── メインセッション(オーケストレーター)
     ├── product-manager (Opus)
     ├── project-manager (Opus)
     ├── solution-architect (Opus)
     ├── designer (Opus)
     ├── developer (Sonnet)
     └── quality-assurance (Sonnet)
```

サブエージェント同士は直接会話できないため、
- **Project Manager**が「どのロールを・どの順で・何を入力に動かすか」を計画として文書化し
- **メインセッション(あなたとの対話)**がその計画に沿って各ロールをAgentツールで順次起動し
- **受け渡しはすべてファイルベース**で行う

という構成にしています。

## ワークスペース構成

各プロジェクトごとに以下のようなフォルダを作り、番号順に成果物を積み上げます。

```
.claude/documents/projects/{yyyy-mm-dd}_{slug}/
├── 00_request.md          # 人間の依頼(原文)
├── 10_product_brief.md    # Product Manager
├── 20_project_plan.md     # Project Manager
├── 30_architecture.md     # Solution Architect
├── 40_design_brief.md     # Designer
├── 50_implementation.md   # Developer
├── 60_qa_report.md        # Quality Assurance
└── 90_completion.md       # Project Manager(完了報告)
```

小規模な修正なら `00 → 20 → 50 → 60 → 90` に短縮できます。

## 人間ゲート

| タイミング       | 内容                          |
| ---------------- | ----------------------------- |
| ゲート1(計画承認) | スコープ・工数・リスクの承認後に着手 |
| ゲート2(完了承認) | 完了報告の確認。git commit/pushは人間が実行 |
| 随時             | `STATUS: NEEDS_HUMAN_INPUT` で即停止 |

## 次のステップ(案)

- `.claude/agents/` に配置後、既存プロジェクト(または見積収支計算書プロジェクト用の新規リポジトリ)の `CLAUDE.md` にロール表と品質ゲートコマンドを追記する
- Project Managerがdispatch planを出力する `/run-project` 的なスキル(オーケストレーター)を別途整備すると、記事の構成により近くなる
