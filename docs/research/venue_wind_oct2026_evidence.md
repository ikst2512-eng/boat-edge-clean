# 研究専用：2026年10月・全国24場の風速別成績（原結果再集計）

**2026-11-06検証。Draft PR #1692研究分離。main/Render/4モード生成/公式T−12/既存保存原本には一切非接続。**

## 2026-11-06独立照合：既存の主分析より厳しい感度分析である

**この資料は6着まで完走順が確認できるレースに限る感度分析（subset）であり、1コース1着率の主集計ではない。**

同一10月原ファイルについて、既存の3か月主集計 `venue_wind_202608_202610_24venues_research_only.json` が採用した **4,663件** と再照合。主集計は「6艇の実進入と1着（風速有効）」で足りるのに対し、本資料は「1〜6着の全順位完全性」を追加要求し、**296件多く除外**していた。6着の欠測は1着・逃げの観測を必ずしも無効化しないため、本資料の採否条件は1コース1着率の母集団として不必要に厳しい。

|結果記録風速|主集計 N|主集計 1C勝ち|主集計 1C率|本資料 N|本資料 1C勝ち|本資料 1C率|追加除外|
|---|---:|---:|---:|---:|---:|---:|---:|
|0〜2m|2,464|1,377|55.88%|2,302|1,296|56.30%|162|
|3〜4m|1,598|869|54.38%|1,496|824|55.08%|102|
|5m以上|601|294|48.92%|569|279|49.03%|32|
|合計|4,663|2,540|54.47%|4,367|2,399|54.93%|296|

**扱い：** 1着・実進入の実績判断は既存3か月主集計（同一10月分4,663件）を優先し、本CSV/再集計スクリプトは**完全6艇着順が必要な下流分析の感度チェック**に限定。両集計を重複サンプルの独立検証のように扱わない。どちらも結果後の風でありT−12入力ではない。除外296件の詳細理由と傾向差は未解明。完全6艇条件による選択バイアスを解消するまで本分析から補正係数を提案しない。

## 対象母集団・厳格な除外
- [BoatraceCSV](https://boatracecsv.github.io/docs/data/results.html)の2026-10-01〜10-31 **31日すべて** の `data/results/realtime/YYYY/MM/DD.csv` を読み、原文列から集計。31日合計 **4,715レース行**。
- **4,367件採用**、52件は`1〜6コース_艇番`が6艇の正しい順列でない、296件は`1〜6着_艇番`が完全な6艇順列でない（欠場・失格・不完走などの内訳は**未確認**）。この除外は偏りを生む可能性がある。空欄を0として扱わない。F有りの独立除外は0件（先に完全6艇条件を適用）。
- レースコード重複は日内0件、風速欠損0件、24場すべてに少なくとも1レース。取得したGitHub CSVの内容は後から変わり得るため、2026-11-06に取得した値の比較資料として扱う。GitHub初回受領時刻、独立原本固定、公式発表との全行照合は **未実施**。
- 風速は結果行の`風速(m)`で **0〜2 / 3〜4 / 5m以上** に分類（風速0の「無風」も0〜2）。`1着_艇番 == 1コース_艇番`を「実1コース1着」とする。**枠番1号艇の勝利とは別**。`決まり手`から空白を除去して「逃げ」と一致した件数を別集計。
- 結果記録の風速は**レース後の気象**。締切前の時点に存在した特徴量ではないため予想データに入力しない。結果から予想へのリークは禁止。
- 95% Wilson区間は統計的不確実性の目安。観測選手・開催・風向・潮・季節の交絡を制御しておらず、30件以上でも因果効果や一般化を証明しない。30件未満は特に標本不足として分類。

## 全国集計（全て結果記録時の気象）

|風速|n|実1コース勝ち|実1コース1着率|逃げ|逃げ割合|
|---|---:|---:|---:|---:|---:|
|0〜2m|2,302|1,296|56.3%|1,258|54.6%|
|3〜4m|1,496|824|55.1%|785|52.5%|
|5m以上|569|279|49.0%|262|46.0%|

**差は相関（wind=5+ と0〜2mの1C率−7.3ポイント）であり、風による増減の推定値ではない。**

## 24場別の件数と実1コース1着率

|場|0〜2m (件/1C率)|3〜4m (件/1C率)|5m以上 (件/1C率)|5m以上の標本|
|---|---:|---:|---:|---|
|10 三国|88件/46.6%|50件/46.0%|60件/51.7%|30件以上|
|11 びわこ|90件/60.0%|65件/56.9%|24件/33.3%|不足|
|12 住之江|136件/61.0%|49件/55.1%|16件/56.3%|不足|
|13 尼崎|117件/64.1%|89件/58.4%|31件/45.2%|30件以上|
|14 鳴門|112件/55.4%|66件/47.0%|26件/30.8%|不足|
|15 丸亀|100件/55.0%|37件/43.2%|21件/66.7%|不足|
|16 児島|118件/55.1%|91件/41.8%|16件/43.8%|不足|
|17 宮島|42件/64.3%|19件/68.4%|8件/62.5%|不足|
|18 徳山|91件/59.3%|110件/61.8%|19件/57.9%|不足|
|19 下関|101件/51.5%|50件/52.0%|7件/100.0%|不足|
|20 若松|104件/53.8%|49件/61.2%|14件/50.0%|不足|
|21 芦屋|62件/74.2%|34件/55.9%|6件/50.0%|不足|
|22 福岡|77件/45.5%|106件/63.2%|15件/40.0%|不足|
|23 唐津|93件/64.5%|91件/65.9%|49件/44.9%|30件以上|
|24 大村|133件/59.4%|55件/69.1%|21件/76.2%|不足|
|01 桐生|150件/48.7%|35件/34.3%|16件/43.8%|不足|
|02 戸田|114件/44.7%|31件/35.5%|5件/40.0%|不足|
|03 江戸川|58件/43.1%|80件/50.0%|55件/38.2%|30件以上|
|04 平和島|113件/51.3%|52件/48.1%|16件/43.8%|不足|
|05 多摩川|96件/51.0%|23件/56.5%|6件/50.0%|不足|
|06 浜名湖|49件/57.1%|116件/56.0%|40件/47.5%|30件以上|
|07 蒲郡|71件/69.0%|65件/61.5%|3件/66.7%|不足|
|08 常滑|101件/62.4%|55件/61.8%|33件/48.5%|30件以上|
|09 津|86件/65.1%|78件/50.0%|62件/54.8%|30件以上|

5m以上の標本が30件以上あるのは **江戸川・浜名湖・常滑・津・三国・尼崎・唐津の7場のみ**。三国は微風46.6%→強風51.7%と逆方向の観測。下関は強風7件で7件とも実1コース勝ちだったが、n=7のため特殊要因を分離できず、**100%イン勝利傾向とは判断禁止**。従前の第三者集計「強風−14.6pt」等とは期間・指標・採否条件が異なり直接比較しない。

## 2026-11-05の締切前気象適格性（別サンプル）

- 結果144件、同日の`data/previews/sui/2026/11/05.csv`気象144レース一致。
- `取得日時 <= レース固有の締切時刻−12分`を確認したところ **0/144件**。ここでいう取得日時はCSV配布側の記録値であり、BOAT EDGEの自独立初回Git受領や公式beforeinfo原本ではない。別ソースの正式T−12可否と混同しない。
- 例：芦屋1R (202611052101)、締切08:35、sui取得08:25:24+09:00、T−12=08:23で不適格。別日・別ソースまで未取得だったと一般化しない。
- 結果ソースGit blob SHA1 `18b057831a07bd6f6f381774a165f834125c41f9`、sui SHA1 `4059f8952879eb8063a1d01949cba6b7b5772172`（取得時点の内容識別子）。

## 再現用の31日分ソースURL・原行数

|日付|原行数|公開原データ|
|---|---:|---|
|2026-10-01|168|[結果CSV](https://github.com/BoatraceCSV/boatracecsv.github.io/blob/main/data/results/realtime/2026/10/01.csv)|
|2026-10-02|168|[結果CSV](https://github.com/BoatraceCSV/boatracecsv.github.io/blob/main/data/results/realtime/2026/10/02.csv)|
|2026-10-03|156|[結果CSV](https://github.com/BoatraceCSV/boatracecsv.github.io/blob/main/data/results/realtime/2026/10/03.csv)|
|2026-10-04|156|[結果CSV](https://github.com/BoatraceCSV/boatracecsv.github.io/blob/main/data/results/realtime/2026/10/04.csv)|
|2026-10-05|143|[結果CSV](https://github.com/BoatraceCSV/boatracecsv.github.io/blob/main/data/results/realtime/2026/10/05.csv)|
|2026-10-06|155|[結果CSV](https://github.com/BoatraceCSV/boatracecsv.github.io/blob/main/data/results/realtime/2026/10/06.csv)|
|2026-10-07|143|[結果CSV](https://github.com/BoatraceCSV/boatracecsv.github.io/blob/main/data/results/realtime/2026/10/07.csv)|
|2026-10-08|143|[結果CSV](https://github.com/BoatraceCSV/boatracecsv.github.io/blob/main/data/results/realtime/2026/10/08.csv)|
|2026-10-09|143|[結果CSV](https://github.com/BoatraceCSV/boatracecsv.github.io/blob/main/data/results/realtime/2026/10/09.csv)|
|2026-10-10|156|[結果CSV](https://github.com/BoatraceCSV/boatracecsv.github.io/blob/main/data/results/realtime/2026/10/10.csv)|
|2026-10-11|155|[結果CSV](https://github.com/BoatraceCSV/boatracecsv.github.io/blob/main/data/results/realtime/2026/10/11.csv)|
|2026-10-12|167|[結果CSV](https://github.com/BoatraceCSV/boatracecsv.github.io/blob/main/data/results/realtime/2026/10/12.csv)|
|2026-10-13|131|[結果CSV](https://github.com/BoatraceCSV/boatracecsv.github.io/blob/main/data/results/realtime/2026/10/13.csv)|
|2026-10-14|155|[結果CSV](https://github.com/BoatraceCSV/boatracecsv.github.io/blob/main/data/results/realtime/2026/10/14.csv)|
|2026-10-15|156|[結果CSV](https://github.com/BoatraceCSV/boatracecsv.github.io/blob/main/data/results/realtime/2026/10/15.csv)|
|2026-10-16|156|[結果CSV](https://github.com/BoatraceCSV/boatracecsv.github.io/blob/main/data/results/realtime/2026/10/16.csv)|
|2026-10-17|167|[結果CSV](https://github.com/BoatraceCSV/boatracecsv.github.io/blob/main/data/results/realtime/2026/10/17.csv)|
|2026-10-18|155|[結果CSV](https://github.com/BoatraceCSV/boatracecsv.github.io/blob/main/data/results/realtime/2026/10/18.csv)|
|2026-10-19|131|[結果CSV](https://github.com/BoatraceCSV/boatracecsv.github.io/blob/main/data/results/realtime/2026/10/19.csv)|
|2026-10-20|143|[結果CSV](https://github.com/BoatraceCSV/boatracecsv.github.io/blob/main/data/results/realtime/2026/10/20.csv)|
|2026-10-21|143|[結果CSV](https://github.com/BoatraceCSV/boatracecsv.github.io/blob/main/data/results/realtime/2026/10/21.csv)|
|2026-10-22|167|[結果CSV](https://github.com/BoatraceCSV/boatracecsv.github.io/blob/main/data/results/realtime/2026/10/22.csv)|
|2026-10-23|167|[結果CSV](https://github.com/BoatraceCSV/boatracecsv.github.io/blob/main/data/results/realtime/2026/10/23.csv)|
|2026-10-24|167|[結果CSV](https://github.com/BoatraceCSV/boatracecsv.github.io/blob/main/data/results/realtime/2026/10/24.csv)|
|2026-10-25|167|[結果CSV](https://github.com/BoatraceCSV/boatracecsv.github.io/blob/main/data/results/realtime/2026/10/25.csv)|
|2026-10-26|144|[結果CSV](https://github.com/BoatraceCSV/boatracecsv.github.io/blob/main/data/results/realtime/2026/10/26.csv)|
|2026-10-27|168|[結果CSV](https://github.com/BoatraceCSV/boatracecsv.github.io/blob/main/data/results/realtime/2026/10/27.csv)|
|2026-10-28|125|[結果CSV](https://github.com/BoatraceCSV/boatracecsv.github.io/blob/main/data/results/realtime/2026/10/28.csv)|
|2026-10-29|120|[結果CSV](https://github.com/BoatraceCSV/boatracecsv.github.io/blob/main/data/results/realtime/2026/10/29.csv)|
|2026-10-30|144|[結果CSV](https://github.com/BoatraceCSV/boatracecsv.github.io/blob/main/data/results/realtime/2026/10/30.csv)|
|2026-10-31|156|[結果CSV](https://github.com/BoatraceCSV/boatracecsv.github.io/blob/main/data/results/realtime/2026/10/31.csv)|

公開URLは最新mainを参照するためファイル更新の可能性がある。再計算する際は各ソースのGit blob SHA・取得日時・結果CSV内容ハッシュをその時点で記録して差分を明示。

## 次の研究ゲート
1. 結果CSVとレース締切前`sui`の同一レース突合を過去期間へ拡大。T−12以前に**実際に受領済み**のデータだけを別母集団にする。11/05の配布ソースは0件であり、T−12用研究はこのソースだけでは進まない。
2. 風向1〜8コード→各場のスタート方向の実測方位（公式確定まで未指定）→向かい・追い・横・斜め風。既存外部`build_sui_params.py`は24場の`STADIUM_FACING`に概算が含まれるため、係数を無条件転用しない。[該当コード](https://github.com/BoatraceCSV/boatracecsv.github.io/blob/main/scripts/build_sui_params.py)
3. 実進入、2コースST、3・4コース勝者、波高、潮位、選手・モーターを同一条件で集計。まず6艇完全性/休場の除外による標本バイアスを検証する。
4. 当日予想の入力としての採用は、全ソース受領・初回Git証拠・結果との時間差・公式T−12適格性を満たした新規レースだけ。過去回帰の係数調整後、独立の将来期間でTop1/3/5/10、Brier/LogLoss、コース別校正を比較。効果未証明なら本番は変えない。
