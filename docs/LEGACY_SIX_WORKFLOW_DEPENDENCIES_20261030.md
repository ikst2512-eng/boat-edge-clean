# 旧サイト主要6ワークフローの実ファイル調査（2026-10-30）

対象は `ikst2512-eng/boat-edge` のmain上の実ファイル。これは削除許可ではない。

| ファイル | Git blob SHA | 起動条件（実ファイル確認） | 観測した関係 / 判定 |
|---|---|---|---|
| `auto-update.yml` | `2b70ae8577df0475f44dc30f2ddfda2e55c75461` | 5分間隔、手動、オッズ更新完了 | 公式入力の生成元。**保留** |
| `site-odds.yml` | `a72ea0f8226f1dd3f31824cb23943344bae1fbc2` | 5分間隔、手動、限定push | オッズ生成元。auto-update・V235・V229から完了監視。**保留** |
| `V235.yml` | `6c5e21daf57ceac158d83fd803c39cab72d9c813` | 定期、手動、push、公式入力/オッズ完了 | 凍結・採点処理の一経路。**保留** |
| `BOAT_EDGE_V229_ATOMIC_FREEZE_AUDIT.yml` | `79d0e7e1de8df894ab3cc1a5401a2c2812952322` | 定期、手動、push、公式入力/オッズ完了 | 原子的初回保存の経路。Pages公開から完了監視。**保留** |
| `pages-controlled-publish.yml` | `4e02995f3cf612de902b6df86fa3db7590b612cd` | 定期、手動、push、PR、V229完了 | 公開/配信の候補。Pages設定・稼働は別途確認。**保留** |
| `boat-edge-v350-actions-evidence.yml` | `434199faa7c29023515e0339793bd101c95e1dbe` | 毎日、手動 | Actionsの独立監査。**保留** |

## 現時点の依存方向
`site-odds` → `auto-update` の完了監視、`auto-update` / `site-odds` → `V235` / `V229` の完了監視、`V229` → `pages-controlled-publish` の完了監視を実ファイルで確認。

## 結論と次の条件
- **主要6本の削除可能判定：0本。** 実行条件ありを即「稼働中」と断定せず、代替実行の成功と参照元の完全網羅が必要。
- 旧repoへの変更は禁止。CLEANへ旧モデルの取り込みも禁止。
- 残りの旧ワークフローは全件の参照・トリガー・成果物・GitHub Pages接続を棚卸しし、明示的な依存がなくCLEAN側に必要機能があることを実測確認してから限定的に整理。
