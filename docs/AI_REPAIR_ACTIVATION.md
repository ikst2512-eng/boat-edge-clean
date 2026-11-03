# AI修正エージェントの利用・検証手順

1. GitHub リポジトリの Settings → Secrets and variables → Actions に `OPENAI_API_KEY` を設定する。キーをチャットやコードへ貼り付けない。
2. Actions → **AI repair proposal (manual and review-gated)** → **Run workflow** で、具体的なUI/ナビの不具合を入力する。
3. `tests` ジョブと `propose` ジョブの結果を確認する。キーがない場合は `Require configured AI credential` で失敗と明示され、AIを動かした成功とは扱わない。
4. 提案された変更は **draft PR** としてのみ作成される。ソース内の不審なコード、誤修正、予想への影響、差分とCIを人が確認するまでマージしない。

## 制限
- AIが変更できるのは `index.html`、`navigation.js`、`secondary_navigation.js` のみ。テスト、予想ロジック、データ、ワークフローの編集は不可。
- 1回の手動実行で最大2箇所の完全一致置換。失敗した場合はPRを作らず停止。
- GitHub標準の `GITHUB_TOKEN` によって作られたPRは、通常、push/pull_requestの別ワークフローを自動起動しない。したがって **AI生成PRはCIが自動で走ったとみなさない**。必要な検証を別途実施する。
- APIの実リクエスト、API認証・残高、料金、修正PR作成成功は、実際の workflow_dispatch 成功ログで初めて確認できる。

## AI生成PRを独立に再検証する
Actions → **Validate AI repair draft PR** → Run workflow にAI生成PR番号を入力する。
この検証は GitHub Secrets を受け取らず、PR番号からGitHub APIで取得した該当コミットをcheckoutする。下書きPR・同一リポジトリの `ai/repair-` ブランチ・変更ファイルの許可リストを確認し、ナビゲーション／サイト回帰テストを再実行する。成功してもmainへの自動マージはしない。
