# 旧サイトActions稼働状況・安全整理（2026-10-29）

## 直接確認した事実
- 旧 `ikst2512-eng/boat-edge` main の `.github/workflows/*.yml`：105件。
- 最新100ワークフロー実行の中で登場した旧ワークフローYAML：29件（動的Pagesビルド1系統は別）。
- 最新100実行に出てこなかったYAML：76件。**未使用・無依存の証明ではない。**
- 実行を確認した主な経路：`auto-update.yml`, `pages-controlled-publish.yml`, `capture-pre-result-evidence.yml`, `fresh-core7-readonly-audit.yml`, `research-final15m-source-audit.yml`。
- 失敗している実行もあるため、直近の成功率だけで削除・停止しない。

## 原本保全の実測
- Actions 40739572811: アーカイブ原本292件、復元292件、SHA-256一致、監査成功。
- 90日保管のActions artifactは永続・外部保管の代替ではない。
- 正式Fresh/締切前予想の移行・復元は未了。

## 削除の優先度
1. 実行履歴が見つからない76件を、YAMLの `on`, `workflow_run`, `workflow_call`, `uses`, `needs`、外部URL、既存証拠と照合し「依存なし・置換済み・監査対象外」の条件を満たすものだけ削除候補へ。
2. `fresh-*`, `capture-*`, `research-*`, `pages-*`, `auto-update.yml` など、現行稼働・証拠・公開の可能性があるものは原則保持し個別判定。
3. 移行確認前の旧repoの全体無効化・削除は禁止。Actionsの停止自体も本番影響のある変更。
4. CLEAN内の監査・正式予想は現状維持。

今回の**旧ファイル削除数は0件**。証拠を失う危険があるので、根拠のない機械的な一括削除は行わない。
