# 旧研究ワークフローの実際の出力利用者（2026-10-30）

旧 `boat-edge` mainの実ファイルをGit blob SHAで読取専用確認。CLEAN予想への旧モデル移植を承認しない。

| 出力経路・研究系ジョブ | 確認できた読み手 | 根拠 | 判定 |
|---|---|---|---|
| `data/site_racer_actual_course/v155_fresh/**` (V155) | `BOAT_EDGE_V156_FRESH_WATCH.yml`, `BOAT_EDGE_V157_COVERAGE.yml` | V156はpush pathsの監視、V157はpush pathsとPythonの入力ROOTに指定 | **削除・無効化不可（依存確認済）** |
| `data/site_racer_actual_course/v156_watch/audit.json` (V156) | V156自身の監査出力は確認。外部利用者の網羅は未確認 | V156 YAMLのOUTPUT定義 | **削除未承認** |
| `data/site_autopilot/v236_frozen/**`, `v236_scored/**`, `v236_pre_current.json`, `v236_score_current.json` (V236) | `v236.yml` の保存・採点コマンド、サイトの研究ページ群は別途参照を要確認 | `v236.yml` の `git add` と`score`、`assets/boat_edge_v253_misses.js` のv236レーン処理 | **研究データ保全・停止未承認** |
| `data/site_autopilot/v253_miss_diagnostics_current.json` (V253) | `assets/boat_edge_v253_misses.js` の `fetch`、`autopilot.html` にJS読込 | `v253-miss-attribution.yml` のGit add / JS 192行のfetch / HTML 162行のscript | **現行旧画面に依存・削除不可** |

## 補足
- V253が作るJSONの実際の画面利用者は特定できた。`autopilot.html` が旧JSをロードし、そのJSが `v253_miss_diagnostics_current.json` を取得するため、**更新ジョブのみ削除すると旧画面が古いデータを表示する可能性がある**。
- V155にはV156以外にも**V157の依存**が見つかった。直前の調査から依存関係を拡張。
- V236のスケジュールは別研究モデルの前日までの結果/凍結であり、CLEANの正式予想への置換を示す証拠ではない。
- 上記は検索・実ファイル照合で確認できた経路の範囲。**全105本の網羅的な参照グラフ確定ではない**。旧サイトの直接編集、削除および旧データの自動移植は行わない。

## 削除判断
今回の4ジョブ中、実ファイル依存から**安全に削除できると証明されたもの：0件**。将来の停止にはCLEANでの代替検証、旧サイト利用終了、復元手段の3点の実証が必要。
