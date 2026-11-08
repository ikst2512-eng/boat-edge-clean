# 同一レース・予想生成と一次風／APIオッズの時系列照合（2026-11-08）

**研究専用：Draft PR #1692。main、Render、本番4モード、保存予想、Cron、AI自動統合は変更しない。**

## 再検証した同一レース

- `202611040111`：2026年11月4日・桐生11R。公式 `beforeinfo` 原本のレースコード、公開締切 `20:03 JST`、保存済み4モード予想、公開オッズAPI応答をレースコードと締切で相互照合。
- 固定した読み取り専用mainコミット：`6409443d6487b5c175eec4ed2a7f4bf136f69da4`。予想：`four_mode_forecasts/202611040111.json`、JSON原本SHA-256 `57ec2a455727be8999b09b9613ffa077f55574880e8106369999a3d9697c3a1f`。
- 公式気象・展示原本：`docs/observations/official_preview_20261104/beforeinfo.json`、メタデータ：同フォルダ `manifest.json`。受信HTTP原本 **4,608バイト、SHA-256 `40e7859d3841f6a9b6329b1a7426cad46dd65f98562a38e3f06cc4fa24a02d01`**。
- オッズAPIの保存応答：`docs/observations/live_odds_replay_20261104.json` の当該レースのBase64復元バイト。**2,005バイト、SHA-256 `4d85f464a064f59ff43be8b48571512ad20ed8dd81e82cc84969e8c9eab3c430`**。三連単の異なる120組み合わせを検証。**これは独立したBOAT RACE公式3連単オッズ原本ではない**。保存記録の `trigger.event` は `local_manual`、`formal=false`。
- GitHub Actions研究実行： https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42460867885 。実行ステップ `Audit Nov 4 same-race provisional forecast vs two later pre-T12 HTTP receipts` 成功、証拠アーティファクト `same-race-nov4-wind-public-odds-forecast-timeline-not-certified`、ID `13609428204`、レポートJSON SHA-256 `35c0ed4f70526fccb133a921252f7dbe353e68cc6e535f5d32f0a52a0a2f93c5`。

## 受信時刻・生成時刻（日本時間）

| 対象 | 実測JST | T−12（19:51）以前 | 保存予想生成（11:09:10）以前 |
|---|---|---|---|
| Title原本の受信メタデータ | 11:09:09.933511 | はい | はい |
| Racecards原本の受信メタデータ | 11:09:10.057543 | はい | はい |
| **4モード暫定予想生成** | **11:09:10.149831** | はい | 基準時刻 |
| 公開オッズAPIのHTTP受領 | 19:37:23.766414 | はい | **いいえ** |
| 公式beforeinfoのHTTP受領 | 19:39:21.767860 | はい | **いいえ** |
| T−12境界 | 19:51:00 | 境界 | — |
| 公式締切 | 20:03:00 | いいえ | — |

オッズ応答は予想生成より**30,493.617秒（約8時間28分）後**、公式風・展示原本は**30,611.618秒（約8時間30分）後**。**T−12以前の受信と、同じレースの既存予想への利用可能性は異なる。**

## 公式気象の内容と未確定部分

公式 `weatherinfo`：`wind="2m"`、`wave="1cm"`、`measuretime="10R時点"`、`winddirec="02"`、`northdirec="14"`。6艇展示・スタート展示の行は受信原本に存在。

`measuretime` は10R時点のラベルであり、11Rの風観測日時（分秒）でも絶対地理風向の認定でもない。レース終了後の公式K（事後風）と混ぜない。

## 独立ゲートと残件

- **PASS**：同一レースコード、公開締切の一致、公式beforeinfo生原本SHAと受信時刻、APIオッズ復元応答のSHA、三連単120組み合わせ、すべてT−12以前の受信。
- **FAIL**：公式beforeinfoとAPIオッズはいずれも既存予想より**後**。入力だった証拠にはならない。
- **未認定**：APIオッズの独立公式オリジン、別の公式出走表HTTP原本の独立SHA、最終進入、複数一次元の完全一致、予想入力fingerprintへの気象・オッズ原本登録。
- **正式T−12予想認定0件**、補正の期待的中率・回収率・Brier/LogLoss改善認定0件、本番採用0件。

再現コード：`scripts/research_t12_same_race_receipt_join.py`。失敗系テスト：`tests/test_research_t12_same_race_receipt_join.py`。改ざん、レース不一致、締切不一致、120組欠落、時系列逆転は成功扱いしない。

次の実測は、**予想生成以前に独立公式原本3系統と風が同一レースで揃い、かつ保存予想の入力SHAに結びつく新規事前観測**を対象とすること。すでに保存された予想へ後から事後または遅受信データを付与して精度改善とみなしてはいけない。
