# BOAT RACE公式レース結果ページと二次速報CSVの独立スポット照合（2026-11-07）

**分類：研究専用 / 公式結果ページのサンプル照合のみ / T−12認定不可 / 本番予想・風補正・正式研究認定に転用禁止。**

## 照合対象と結論

既存の92日・13,970レース研究（2026-08-01〜2026-10-31）に対する**独立一次ソースの小規模検査**。BOAT RACE公式レース結果ページを一次表示資料、BoatraceCSVの `data/results/realtime/YYYY/MM/DD.csv` を二次速報資料として、**公式集計との1C率差が残る重点4場（唐津6件、浜名湖1件、江戸川1件、宮島2件）の計10レース（8月6件、9月2件、10月2件）**を同一 `YYYYMMDDjjrr` レースコードで手作業・コード抽出を併用して比較した。

**サンプル10件の照合結果：指定した着順・実進入・決まり手・ST・風速・波高は10/10一致。不一致0件。** この10件は便宜抽出であり、無作為抽出でも24場代表でもない。**92日・13,970件全体、除外139件、公式統計の分母を独立認定したことにはならない。**

| レースコード | 公式着順1〜3着 | 決まり手 | 実進入（1C→6Cの艇番） | 実進入順ST（秒） | 風速 / 波高 | 突合 |
|---|---|---|---|---|---|---|
| `202608012301` 唐津8/1 1R | 1-2-3 | 逃げ | 1,2,3,4,5,6 | .17,.20,.28,.27,.19,.17 | 3m / 3cm | 一致 |
| `202608312302` 唐津8/31 2R | 4-1-5 | まくり | 1,2,3,4,5,6 | .28,.27,.29,.32,.37,.35 | 3m / 3cm | 一致 |
| `202608312304` 唐津8/31 4R | 1-5-3 | 逃げ | 1,2,3,5,4,6 | .07,.23,.17,.15,.07,F.04 | 2m / 2cm | 一致、6号艇F |
| `202608312308` 唐津8/31 8R | 4-2-3 | 差し | 1,2,3,4,6,5 | .14,.18,.11,.12,.14,.06 | 4m / 4cm | 一致、5/6C入替 |
| `202609302301` 唐津9/30 1R | 1-6-3 | 逃げ | 1,2,3,4,5,6 | .20,.14,.11,.12,.11,.14 | 1m / 1cm | 一致 |
| `202610012301` 唐津10/1 1R | 1-4-3 | 逃げ | 1,2,3,4,5,6 | .19,.27,.28,.24,.29,.38 | 2m / 2cm | 一致 |
| `202608010601` 浜名湖8/1 1R | 2-1-5 | 差し | 1,2,3,4,5,6 | .11,.10,.09,.09,.17,.07 | 3m / 2cm | 一致 |
| `202608151701` 宮島8/15 1R | 2-1-4 | まくり | 1,2,3,4,5,6 | .25,.15,.18,.17,.22,.30 | 0m / 1cm | 一致、無風時の方位欠測 |
| `202609300301` 江戸川9/30 1R | 4-1-5 | まくり差し | 1,2,3,4,5,6 | .25,.25,.21,.22,.16,.26 | 4m / 5cm | 一致 |
| `202610201701` 宮島10/20 1R | 1-5-3 | 逃げ | 1,2,3,4,5,6 | .16,.20,.21,.16,.18,.20 | 0m / 1cm | 一致、無風時の方位欠測 |

`F.04` は公式画面のフライング表示。速報CSVは `6コース_F=F`, `6コース_スタートタイミング=-0.04` で対応する。4Rは公式画面の6着が空欄（F）である。風向そのものは公式画面では画像表示であり、数値コード `風向` の対応は**今回未確認**。

### 公式一次表示への参照

- [8/1 唐津1R](https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20260801&jcd=23&rno=1)
- [8/31 唐津2R](https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20260831&jcd=23&rno=2)
- [8/31 唐津4R、6号艇F・返還](https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20260831&jcd=23&rno=4)
- [8/31 唐津8R、進入5/6C入替](https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20260831&jcd=23&rno=8)
- [9/30 唐津1R](https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20260930&jcd=23&rno=1)
- [10/1 唐津1R](https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20261001&jcd=23&rno=1)

- [8/1 浜名湖1R](https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20260801&jcd=06&rno=1)
- [8/15 宮島1R](https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20260815&jcd=17&rno=1)
- [9/30 江戸川1R](https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20260930&jcd=03&rno=1)
- [10/20 宮島1R](https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20261020&jcd=17&rno=1)

### 二次速報原本

- [BoatraceCSV 2026-08-01 CSV](https://raw.githubusercontent.com/BoatraceCSV/boatracecsv.github.io/main/data/results/realtime/2026/08/01.csv)
- [BoatraceCSV 2026-08-31 CSV](https://raw.githubusercontent.com/BoatraceCSV/boatracecsv.github.io/main/data/results/realtime/2026/08/31.csv)
- [BoatraceCSV 2026-09-30 CSV](https://raw.githubusercontent.com/BoatraceCSV/boatracecsv.github.io/main/data/results/realtime/2026/09/30.csv)
- [BoatraceCSV 2026-10-01 CSV](https://raw.githubusercontent.com/BoatraceCSV/boatracecsv.github.io/main/data/results/realtime/2026/10/01.csv)

- [BoatraceCSV 2026-08-15 CSV](https://raw.githubusercontent.com/BoatraceCSV/boatracecsv.github.io/main/data/results/realtime/2026/08/15.csv)
- [BoatraceCSV 2026-10-20 CSV](https://raw.githubusercontent.com/BoatraceCSV/boatracecsv.github.io/main/data/results/realtime/2026/10/20.csv)

既存92日シャードのGit blob SHA全件一致は別研究成果物に記載。今回の10件はこれら公開CSVの**現時点の読み取り内容**と公式ページを対照したもので、公式HTTP応答バイトの保存・ハッシュ化は未実施。

## 重要な限界と次の監査

1. 公式サイトは全国24場の**競走成績ダウンロード**（日次LZH）を提供する：[公式入口](https://www.boatrace.jp/owpc/pc/extra/data/download.html)。今回は実際の公式日次LZHを**取得・解凍・行単位照合していない**。公式結果**ページ**のサンプル照合であり、日次公式**成績ファイル**の監査とは分ける。
2. 公式場別1C1着率と研究集計の差は江戸川・浜名湖・宮島・唐津で残る。10例中のF 1件（6号艇F）から**1C統計のF除外規則を推定しない**。公式定義、F/L、失格、欠場、不成立の区別、公式日次原票の実測が必要。
3. 風向の8方位コード、スタンド方位と進行方位の区別は未確認。風向補正係数の導入を禁止。
4. 公式結果ページの風・波・STは**結果後情報**。同レースの締切T−12以前に取得可能だったことは証明しない。T−12判定は公式beforeinfoの内容と受領/初回Git保存時刻の別監査のみで行う。
5. 8〜10月の観測は学習・仮説生成に留め、**11月以降の未使用レースを結果前に凍結した研究候補**と、現行4モードを同一レース・同点数で比較。Top1/3/5/10、Brier、LogLoss、層別・欠測を併記する。既存の他研究PRとの重複実装は避ける。
6. この資料は既存 **Draft PR #1692** の研究メモだけ。main/Render/4モード/保存済み予想/cron/UI/自動統合の変更なし。人手レビュー・未統合維持。

**暫定認定：公式レース結果ページとのスポット照合は10/10一致。92日全件の公式一次原票照合は未完了。本番採用可能な新補正は0件。**
