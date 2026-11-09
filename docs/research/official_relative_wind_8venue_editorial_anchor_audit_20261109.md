# 24場相対風向：公式記事8場の直接方向アンカーと原本認定ゲート（2026-11-09）

**Draft PR #1692／研究専用。main、Render、UI、4モード、T−12取得、cron、既存予想、正式採点、③/⑤固定候補には未接続。自動統合禁止。**

## 結論：公式記事の明示的な風向方向は8/24場、完全な一次原本認定は0/24場

- 以前の[二次方位基準の差](official_k_relative_wind_dual_axis_risk_audit_20261108.md)は、公式K原本の事後風向を2種の候補方位に当てはめると、**8,837/13,112R（67.40%）で相対風向分類が異なる**という安全上の警告だった。その数値は、どちらの二次方式が正しいかの証明ではない。
- 今回は第三者表を根拠にせず、**各競艇場の公式サイト／BOAT RACE公式特集記事が「○風＝向かい風／追い風」と明言する8例**を個別に確認した。これらは「公式記事による特定方位の一次表現」であるが、**元の水面図画像・北方位矢印・2026年の水面配置の改訂履歴・同一レース風向矢印の保存原本ではない**。
- 8記事の特定方向で比較すると、二次A＝「スタートから1マークの進行方位」候補と**8/8例が整合**。二次B＝スタンド基準をそのまま追い風と仮置きした候補では**2/8例が整合**。ただしBには**座標系の意味の違い**があり、整合率をもってB方式が誤りと断定しない。
- **風向の研究用の完全認定は0/24、T−12予想入力認定0/24、本番補正0**。原本SHAを持たない8記事アンカーだけでは、24場の5分類を承認しない。

## 8場の公式編集記事に書かれた個別風向

|場|公式の説明から特定した方向|二次A方位候補との照合|原本水面図・同レース矢印|公式出典|
|---|---|---|---|---|
|02 戸田|東からの風＝向かい風|整合|未取得・未認定|[戸田公式の水面特性](https://www.boatrace-toda.jp/data/suimen_guide.html) ※記事掲載年は確認できず|
|03 江戸川|北風＝向かい風|整合|未取得・未認定|[江戸川公式の開催振り返り（2021）](https://www.boatrace-edogawa.com/modules/gallery/?gid=741)|
|04 平和島|北風＝向かい風|整合|未取得・未認定|[BOAT RACE公式の平和島水面分析（2020）](https://www.boatrace.jp/owsp/sp/extra/race/04_20201215/monthly/bunseki.html)|
|05 多摩川|西系統＝向かい風|整合|未取得・未認定|[BOAT RACE公式の多摩川特集（2019）](https://www.boatrace.jp/owpc/pc/extra/race/05_20190618/monthly/funaken.html)|
|06 浜名湖|南風＝ホーム向かい風|整合|未取得・未認定|[BOAT RACE公式の浜名湖特集（2018）](https://www.boatrace.jp/owpc/pc/extra/race/06_20180316/monthly/course_motor_guide.html)|
|07 蒲郡|南西・南からの風＝向かい風|整合（南西で判定）|未取得・未認定|[BOAT RACE公式の蒲郡特集（2015）](https://www.boatrace.jp/owsp/sp/extra/race/07_20150825/monthly/guidance.html)|
|12 住之江|北風＝ホーム追い風|整合|未取得・未認定|[BOAT RACE公式の住之江水面分析（2018）](https://www.boatrace.jp/owpc/pc/extra/race/12_20181219/monthly/suimen.html)|
|13 尼崎|西風＝向かい風|整合|未取得・未認定|[BOAT RACE公式の尼崎解説（2015）](https://www.boatrace.jp/owpc/pc/extra/race/13_20150317/monthly/guide.html)|

残る**16場**（桐生、常滑、津、三国、びわこ、鳴門、丸亀、児島、宮島、徳山、下関、若松、芦屋、福岡、唐津、大村）は、今回の調査で8方位の具体的向かい／追い風を直接示す**公式記事の有効なアンカーを採録できていない**。これらの場に公式資料が存在しないと断言する意味ではない。

## 資料の時点差と誤認防止

- 「公式記事の方位の一例」と「全風向8方向の公式変換規則」は別。斜め45°や横風90°の区分は、**原画像の向きと元の気象風向コードの意味**が両方独立に認定されるまで未確定。
- 江戸川の北風・向かい風は歴史的大会の記事であり、同じレースの公式K風向矢印と照合したものではない。戸田ページの掲載年は断定しない。
- 唐津公式の[水面特性ページ](https://boatrace-karatsu.jp/sp/index.php?page=datafile-suimen)には**2025年12月からピット位置が変わった**旨が載る。風向の進行基準が変わったとまでは言えないが、歴史的な水面図を2026年へ無条件に継ぎ足すことの危険例になる。
- 大村の[公式解説](https://www.boatrace.jp/owpc/pc/extra/race/24_20171226/monthly/bunseki.html)は北風を「ホーム左横方向からの向かい風」と表現する。「北＝厳密な正面向かい風」と機械的に読み替えることは避け、**24大村は今回8場の厳密方向アンカーに数えない**。
- 公式Kの日別LZH・解凍後SHA照合92/92日は以前完了しているが、**それは結果後気象の証明であり、水面図・beforeinfoの初回受信SHAの証明ではない**。

## 研究側の検証器を追加（本番とは独立）

- [24場の監査台帳](relative_wind_official_editorial_anchor_24venue_20261109.json)：全24場に①歴史的公式記事の明示方向または欠測、②二次A/Bの仮方位、③公式水面図SHA／同一レース公式風向画像SHA／T−12気象SHAの未取得、④本番承認falseを記録。
- [オフライン監査器](../../scripts/research_relative_wind_official_anchor_gate.py)：24場が揃っているか、8つの公式記事URLが実際の公式ホストに属するか、方向と説明に矛盾がないか、未取得の原画像／T−12証拠を取得済みと偽装していないかを **fail closed** で確認する。二次A/Bとの一致件数は**候補比較だけ**に限定。
- [9件の単体テスト](../../scripts/test_research_relative_wind_official_anchor_gate.py)：24場、8場対16場、A8/B2、原本0、T−12 0、偽の図SHA・矢印認定・T−12・偽公式URL・重複場・未知方位の拒否を確認。既存収集・本番予想・GitHub Actionsには組み込まない。

実行例（PR内の研究ファイルのみ、外部アクセスなし）：

```bash
python scripts/research_relative_wind_official_anchor_gate.py \
  --ledger docs/research/relative_wind_official_editorial_anchor_24venue_20261109.json
python -m unittest scripts/test_research_relative_wind_official_anchor_gate.py
```

**完了の意味の区分**：記事方向が分かった8場 ≠ 2026水面図と矢印が独立認定された0場 ≠ 締切12分前に実受信した公式beforeinfo気象0場。正式な予想精度改善0件。本番/モデル/cron/main変更0件、Draft維持。
