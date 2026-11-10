# 公式beforeinfo：2コース展示STと気象の「別レース時点」問題（11/9–10 原本4レース）

**研究担当 #1692 / 研究のみ。** #1694の同一レース正式T−12審査・#1699起動監査を再実装しない。PR Draft、main自動統合禁止。予想ロジック、Render、サイト、収集Cron、予想原本不変更。

## 本回の独立バイト監査
- 11/9 [定期収集run 42567310743](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42567310743)の公式beforeinfo＋odds保存artifact **13652131213** 元ZIP **28,063B**、SHA256 `99f02ff306307dd945f27c225e18ff8341be2832232b7dd0f2751e1d8935f451`。
- 11/10 [定期収集run 42769768447](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42769768447)の同artifact **13740574410** 元ZIP **32,936B**、SHA256 `cdfdeae53222a5b7852ba5cf5b6b44080247ec074c8d3dbaf53c4a32fe9706dd`。
- **固定原本ZIP 2/2の全体SHA、全ZIP CRC、原本beforeinfo JSON4/4のbytes/SHA・manifests、odds HTML4/4のbytes/SHA・manifestsの組を検証**。元原本を改変・後日HTTP再取得したものではない。
- [研究専用の厳格な一次原本リプレイCI #42784964547](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42784964547) **completed/success**、exact head `9eb9e9497eb7476fb1b5f575b9f8980b05ba4eec`。読み取り専用[研究抽出器](../../scripts/research_official_beforeinfo_wall_witness.py)、[13件のST・欠損・測定時点安全テスト](../../tests/test_research_official_beforeinfo_wall_witness.py) **13/13 PASS**。CIで元ZIPを実GitHub APIから2本再取得した。
- CIの**派生・集計のみのartifact 13749365551** は約2,155B、ZIP SHA256 `11ed63624490361b33ca34bb7f748409c176255eef8a25d6d3cc5966dc5b25bc`、JSON SHA256 `dba675c60140792ff41271fe8912ac90597c7eac03a044f654f15ba3728675dc`、CRC正常。GitHubの保存期限は **2026-11-17**。元HTML／選手名・登録番号・他レース原本を派生ZIPに入れない。

## 4つの保存済み原本で分かったこと

以下は **展示ST**（決まり手・本番ST・成績ではない）。差 `2C−3C` が負であれば2Cが展示ST上早い、正であれば2Cが遅い。

| 原本レース | 2C展示ST | 3C展示ST | 4C展示ST | 2C−3C | 2C−4C | 公式beforeinfo気象欄 | 気象の基準レース |
|---|---:|---:|---:|---:|---:|---|---|
| 202611091110 びわこ10R | .22 | .03 | .01 | **+0.19秒** | +0.21秒 | 風1m・波1cm | **9R時点** |
| 202611091710 宮島10R | .02 | .01 | .04 | **+0.01秒** | −0.02秒 | 風1m・波1cm | **8R時点** |
| 202611101202 住之江2R | .03 | .17 | .02 | **−0.14秒** | +0.01秒 | 風2m・波1cm | **1R時点** |
| 202611102211 福岡11R | **未取得** | 未取得 | 未取得 | **unknown** | **unknown** | 風4m・波4cm | **9R時点** |

- **展示進入6コース＋展示ST6値が揃う原本は3/4**。福岡11Rのbeforeinfoには6艇登録情報等と気象があるが、`sttenjiinfolist=[]`、展示タイム6件も空文字。欠測を `0.00` や `2C=2号艇` に補填しない。
- 気象 `weatherinfo.measuretime` が全4件とも**対象レース前のR番号**（差1/2/1/2）。これは「1R/8R/9R時点」という**ラベル**であって、気象計の正確な計測時計・当該レース直前の最新値・同一レース実測を証明しない。風の有効年齢（分）も unknown。
- `weatherinfo.northdirec` / `winddirec` の**数字コード**（13, 15等）は原本にあるが、コード→地理的FROM/TO・各競艇場の相対向かい/追いの正しい変換は正式に認定していない。文字列コードをベクトル角度に当てはめない。
- **展示ST差は壁性能そのものではない。** 3コースの攻め、4カド、進入変更、2C選手過去の逃がし/差し、機力、風/潮、実レースのSTとの比較に正式な将来検証が必要。
- 既存の#1694監査で11/9びわこ・宮島、11/10住之江について展示・odds原本のペアは確認されていても、**公式racelist三本目の同レース原本、モデルが原本を消費したSHA、独立した予想初回Git遠隔受領は未認定**。この抽出器は三原本の正式認定器ではなく、新しい正式認定の件数は **0**。

## 導入不可の明示
`official_wind_arrow_FROM_TO_verified=false`、`weather.actual_measurement_timestamp=null`、`same_race_racelist_original_verified=false`、`source_consumed_by_new_forecast_proven=false`、`first_forecast_remote_acceptance_proven=false`、`formal_T12_certified=false`、`predictive_wall_effect_proven=false`、`approved_for_production=false` を全原本で維持。

**④ #1693、⑥ #1698への受け渡しは**「展示STを実際に取得できた3件、欠測1件、気象の前レース由来ラベル4件、予測補正として利用禁止」のみ。全4モードの順位/確率への風・壁加算、0埋め、後付け採用を禁止。#1694は継続して同一レース三原本＋source→model→予想初回保存の正式証拠を担当する。

**本番で利用可能と認定した新規水面・壁・風特徴量は0件。** 今回の成果は原本受領内容の同一レース別の精密な欠損／時点管理と再現性の証明である。
