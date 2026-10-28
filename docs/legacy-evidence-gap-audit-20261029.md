# 旧サイト証拠の残存差分・移行判定（2026-10-29）

## 確認方法
GitHub main の recursive tree にある blob ファイルのみ集計。両リポジトリ間の内容ハッシュ照合・保存時刻の裏取り・完全移行の認定は**未実施**。パス一致がないだけではデータ重複の有無は判定できない。

| 旧サイト保存区分 | 件数 | CLEAN側の異なる保存区分 | CLEAN件数 |
|---|---:|---|---:|
| data/site_prediction_snapshots/ | 2,054 | four_mode_forecasts/ | 133 |
| data/site_prediction_audit/ | 1,174 | four_mode_performance/verified_races/ | 124 |
| data/site_prediction_history/ | 1,165 | confirmed_results/ | 293 |
| data/site_results/ | 3,397 | （上記の確定結果） | 293 |

いずれもファイルの粒度・対象日・スキーマが異なる可能性がある。**件数差を移行漏れ数、または削除可能数として扱わない**。

## 選別ルール
- KEEP: 締切前予想の初回追加Git SHA、締切時刻、当時の予想/入力、変更履歴、結果ソース、払戻金照合、正式Freshの監査証拠。
- DEDUP: race_key・予想生成時刻・source_sha・入力原本と確定結果をキーにCLEAN内の同等物を比較。完全一致が証明されたものだけ追加コピー省略。
- DO NOT PORT: 旧HTML、旧サイトの自動公開やリカバリー、研究途中の生成物。ただし証拠の参照元であれば削除延期。
- BLOCK DELETE: 旧サイトのActions・Pages・Fresh証拠の依存調査、移行対象のハッシュ付きマニフェストと復元試験、CLEAN単独稼働確認が未完了。

## 次に必要な実データの作業
1. 旧ファイル名から日付・場・Rを正規化してCLEANのrace_codeと突き合わせる。
2. マッチしたものは原本SHAと予想締切前の保存時刻を検証し、CLEANの事前予想原本との整合を比較。
3. マッチしないものは独立した read-only evidence archive に保存し、正式FreshとV13の再現検証だけに利用。
4. manifest の件数・重複・ハッシュ・復元試験が一致するまで旧リポジトリはアーカイブも削除もしない。

この文書は一次調査結果であり、データコピーや旧サイト停止は行っていない。
