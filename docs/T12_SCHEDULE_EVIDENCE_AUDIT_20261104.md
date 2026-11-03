# T-12 実schedule証拠監査 — 2026-11-04 JST

## 判定基準
この報告は`Check real live predeadline racecard`のGitHub Actions `event=schedule`だけを対象に、実行ジョブ原本の出走表・展示・T-12判定を集計する。PR CI、手動実行、研究用保存値、スケジュール予定時刻からの推測、過去の保存済み研究予想は成功件数に含めない。

## 確認した直近4回の実schedule

| Run ID | 実開始（JST） | 出走表PASS / 検査3件 | 6艇展示PASS | T-12 PASS | 根拠・不成立理由 |
| --- | --- | ---: | ---: | ---: | --- |
| [41400724125](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/41400724125) | 11/02 15:34 | 2/3 | 0 | 0 | 2レースのtkz/stt/suiはrace_not_published、1レースのRender APIがタイムアウト |
| [41489725625](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/41489725625) | 11/03 02:17 | 2/3 | 0 | 0 | 翌11/3の出走表を参照、tkz/stt/suiはsource_unavailable、別1レースのAPIがHTTP502 |
| [41593838820](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/41593838820) | 11/03 16:03 | 3/3 | 1 | 0 | 11/3 `202611030103`の6艇展示は検証成功、ただしAPI受領と両元証拠がT-12を満たさず`T12_UNVERIFIED` |
| [41663438908](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/41663438908) | 11/04 00:23 | 3/3 | 0 | 0 | 翌11/4の出走表3件成功、tkz/stt/suiはsource_unavailableで展示0 |

**合計（この4実行だけ）**：schedule実行 4回、ジョブsuccess 0回 / failure 4回、出走表10/12試行、6艇展示1件、実T-12成立0件。出走表失敗2件のうちHTTP502が1件、読み込みタイムアウトが1件。

日本時間09:00〜22:59のレース調査帯で起動した実行は2/4回。残る2回は02:17と00:23で、翌日の未公開展示を調べることになった可能性がある。cronは09:30、12:30、14:30、16:30、18:30、21:30 JSTの6枠だが、各runの予定枠IDはGitHub応答に存在せず、**個々の遅延秒数を特定できない**。この4回の出現は過去数日の実行履歴であり、日ごとの全枠の発火有無を網羅的に証明するものではない。

## データの限界とコード改修後の検証
- この4runが動いたmainはすべて異なる古いコミットで、後続PR #1541（T-12候補優先）、#1543（時間帯外判定・HTTP受信時計）、#1547（期限切れ候補除去・tkz/stt個別障害）、#1550（**Render本番**のtkz/stt/suiごとのHTTP受信時計）の全改修を備えた新規無人schedule実証にはならない。
- 11/03 16:03の1件は展示確認の成功でありT-12成功とは別。古いrunは独立tkz/stt受信時刻や各T-12否定ゲートが十分にログ化されていない。後から埋めたり成功と再認定しない。
- 現行T-12成功は、レース固有の締切から12分差し引いた境界に対して、**API応答受領時刻と独立tkz/stt元の取得日時**がすべて境界以前、6艇の展示・6艇のスタート展示・1〜6コース置換・SHA256等がすべて妥当であることを要する。Render側の`source_audit.beforeinfo.sources[kind].received_at_jst`も新しく保存されるが、この属性の存在は新規live API実レスポンスで別途検証する必要がある。
- 現時点で確認できる11/4の日中schedule実行について成功証拠なし。確認時点でGitHub APIが示す直近の同名実scheduleは`41663438908`。**未来の日中ジョブを起動済みとは記載しない**。

## 次の実運用判定
1. 11/4の日中に実際に出たschedule runを必ず`event=schedule`、run ID、GitHub UTC run_started_at/JST変換、実head SHAで特定する。cron枠の欠落・深夜発火は元データ障害と別集計する。
2. 現行コミットで、`PREVIEW_SOURCE_RECEIVED/UNAVAILABLE`をtkz/sttごとに記録できたか、`RACECARD_CANDIDATES_EXPIRED_DURING_SOURCE_PROBE`数、`T12_SAMPLE_STARTED`対象を検査する。
3. T-12成功を主張する場合のみ、T-12境界、tkz/sttの`observed_at`、`received_at_jst`（Render API経由）、実API応答時刻、6艇完全性を同じレースコードで照合する。PR/手動runは分母に入れない。
4. コード修正は上記実ログで新しい原因を再現できる場合に限る。GitHub cron欠落・遅延が主因なら、別の実運用起動経路の費用・権限を確認する前に、有料cronや重複ジョブを勝手に作らない。

この報告は監査用記録であり、正式予想の的中率・レース後データ混入・取得時刻の推測を認定するものではない。
