# 24場公式水面図の再表示＋芦屋運営者の風向表示粒度の確認（2026-11-09）
**Draft PR #1692研究専用。main・Render・本番4モード・UI・T−12収集・cron・既存原本・③ #1693／⑤ #1698の固定候補に一切触れない。main自動統合禁止。**

## 今回の一次サイト確認
従前の水面図10/24場表示報告を上書きせず、**今回の再表示試行**を別台帳に追加した。BOAT RACE公式の静的水面図 `img_water1_XX.png` を23場で開こうとし、**図として視認可能8場、配色・透過の表示崩れ1場（唐津23）、取得経路エラー14場、今回未再試行1場（鳴門14）**。これらはブラウザ取得の状態であり、HTTPステータス403/404/5xxを観測したという意味ではない。前回確認できたびわこ11が今回エラーでも、前回の事実は維持。

今回の8図のうち、**戸田02・多摩川05・浜名湖06・芦屋21**では「第2マーク→スタート→第1マーク」の図上配置とN方位記号を目視し、**それぞれ東/西/南/東へ進むという二次Aの仮方位**と大まかに整合した。これら4場には、別系統の一次運営者/BOAT RACE文字説明もある。
- [戸田02 公式水面図](https://www.boatrace.jp/static_extra/pc/images/img_water1_02.png)：図では1マークが右、Nは概ね上。[戸田公式文章](https://www.boatrace-toda.jp/data/suimen_guide.html)は「春の東からの向かい風」と説明。東の仮向かい方位と整合。
- [多摩川05 公式水面図](https://www.boatrace.jp/static_extra/pc/images/img_water1_05.png)：図では1マークが右、Nは概ね下。[BOAT RACE公式記事](https://www.boatrace.jp/owpc/pc/extra/race/05_20190618/monthly/funaken.html)は西系統＝向かい風／東系統＝追い風と説明。西の仮向かい方位と整合。
- [浜名湖06 公式水面図](https://www.boatrace.jp/static_extra/pc/images/img_water1_06.png)：図では1マークが右、Nは概ね左。[BOAT RACE公式記事](https://www.boatrace.jp/owpc/pc/extra/race/06_20180316/monthly/course_motor_guide.html)は南風＝ホーム向かい風と説明。南の仮向かい方位と整合。
- [芦屋21 公式水面図](https://www.boatrace.jp/static_extra/pc/images/img_water1_21.png)：図では1マークが右、Nは概ね上。[芦屋運営者のレース別ページ](https://www.boatrace-ashiya.com/modules/datafile/?motor_no=46&page=index_motor_histdtl&select=6)には2026-11-08東＝向い風の表示があり、東の仮向かい方位と整合。

**重要：公式図の原画像バイト・SHA256、別の人による独立角度読取り、同一レースの公式風向矢印原画面は全場未取得。**「4場の暫定照合」は「4/24場の方位正式認定」ではない。正式認定は今も**0/24場**。Bのスタンド座標をtailと解釈する処理は依然として公式認定されない。

## 新発見：芦屋の「向い風」「追い風」は厳密な5分類より広い
運営者の同一レース・モーター台帳表示に、異なる方位が同じ相対語へまとめられる例が確認できた（**当日原HTML/SHAは未保存、動的ページの現時点検索表示**）。

| レースID | 運営者の生方位 | 運営者の相対表示 | 風速 | 二次A（東90°仮head）の5分類 | その3分類への集約 |
|---|---|---|---:|---|---|
| 202611082102 | 南西 | 追い風 | 1m | oblique_tail | 追い風 |
| 202611082105 | 東 | 向い風 | 4m | head | 向い風 |
| 202611082111 | 東 | 向い風 | 5m | head | 向い風 |
| 202611092103 | 南 | 右横風 | 1m | cross | 横風 |
| 202611092110 | 北東 | 向い風 | 1m | oblique_head | 向い風 |

- **2026-11-08 芦屋2R：南西＝「追い風」** は、仮heading=東90°では **135°差の「斜め追い風」** に当たる。[主催者ページ](https://www.boatrace-ashiya.com/modules/datafile/?motor_no=2&page=index_motor_histdtl&select=6)
- **2026-11-09 芦屋10R：北東＝「向い風」** は、同じ仮headingでは **45°差の「斜め向かい風」** に当たる。[主催者ページ](https://www.boatrace-ashiya.com/modules/datafile/?motor_no=46&page=index_motor_histdtl&select=6)
- **2026-11-09 芦屋3R：南＝「右横風」** は、同じ仮headingでは横風。左右の正確な符号の意味までは認定しない。
- 東のレースは厳密なheadと主催者の「向い風」が整合。**5件中5件は仮headingに基づく広いhead/cross/tailの3分類では整合**するが、**厳密head/tail/crossだけに一致するのは5件中3件**（北東と南西は斜め）。ここで「5分類で斜めでない件数」は3/5（東2件＋南の横風1件）。さらに**原文の字面が「向い風／追い風／横風」と完全一致**するのは東の2/5件だけ（南は「右横風」）。この3つの評価軸を混同しない。この5件は恣意的に選んだ参考例であり、対象全レースでの一致率ではない。
- 外部の公式運営者ページに表示された「向い風」という文字だけから斜め向かい風を厳密headとして保存すると、**分類粒度の情報落ち**が起きる。方向は原文8方位で保持し、相対方位候補は別列に隔離する。

## 今回の公式水面図再表示の24場台帳
| 場 | 今回の表示状態（観測内容） | 今回の暫定方位 | 別系統の公式説明 |
|---|---|---|---|
| 01 桐生 | web_fetch_error_not_http_status | 保留 | — |
| 02 戸田 | rendered_legible | east | [公式説明](https://www.boatrace-toda.jp/data/suimen_guide.html) |
| 03 江戸川 | web_fetch_error_not_http_status | 保留 | — |
| 04 平和島 | web_fetch_error_not_http_status | 保留 | — |
| 05 多摩川 | rendered_legible | west | [公式説明](https://www.boatrace.jp/owpc/pc/extra/race/05_20190618/monthly/funaken.html) |
| 06 浜名湖 | rendered_legible | south | [公式説明](https://www.boatrace.jp/owpc/pc/extra/race/06_20180316/monthly/course_motor_guide.html) |
| 07 蒲郡 | rendered_legible | 保留 | — |
| 08 常滑 | web_fetch_error_not_http_status | 保留 | — |
| 09 津 | web_fetch_error_not_http_status | 保留 | — |
| 10 三国 | web_fetch_error_not_http_status | 保留 | — |
| 11 びわこ | web_fetch_error_not_http_status | 保留 | — |
| 12 住之江 | web_fetch_error_not_http_status | 保留 | — |
| 13 尼崎 | rendered_legible | 保留 | — |
| 14 鳴門 | not_rechecked | 保留 | — |
| 15 丸亀 | web_fetch_error_not_http_status | 保留 | — |
| 16 児島 | web_fetch_error_not_http_status | 保留 | — |
| 17 宮島 | web_fetch_error_not_http_status | 保留 | — |
| 18 徳山 | web_fetch_error_not_http_status | 保留 | — |
| 19 下関 | web_fetch_error_not_http_status | 保留 | — |
| 20 若松 | rendered_legible | 保留 | — |
| 21 芦屋 | rendered_legible | east | [公式説明](https://www.boatrace-ashiya.com/modules/datafile/?motor_no=46&page=index_motor_histdtl&select=6) |
| 22 福岡 | web_fetch_error_not_http_status | 保留 | — |
| 23 唐津 | rendered_but_color_or_alpha_corrupted | 保留 | — |
| 24 大村 | rendered_legible | 保留 | — |

- `rendered_legible`＝画像を読めた、`rendered_but_color_or_alpha_corrupted`＝画像は出たが読取り不適、`web_fetch_error_not_http_status`＝こちらの表示取得失敗、`not_rechecked`＝今回未試行。**表示状態を原本SHA受領と混同禁止。**
- 本研究の資料区分：水面図と運営者レース別表示はBOAT RACE/主催者の一次サイト表示。風が来る方向/吹く方向の矢印定義（FROM/TO）、図の版日付、K原本とoperator画面の同一レース独立バイト受領、T−12以前のbeforeinfo受領は**未検証**。
- 芦屋の11/9公式運営者ページは動的で更新される。表示した5レースの情報のURLを残したが、恒久的な二重一次原本認定とはしない。11/9当日の公式K原本をこの調査では再取得していない。公式Kの8〜10月14,249Rの過去監査と**別期間**の例示である。

## 採用停止ゲートと次の検証
1. **原画像のバイト列SHA256**と取得時刻、北記号、第1/2マークのピクセル位置、別レビュアーによる独立方位、図の改訂履歴を確保。取得エラー場は運営者側の公式画像へ切替。
2. 芦屋で風が異なる2レース以上の**公式K原本**と、主催者レース別画面の風向・風速・波高・相対風ラベル・同一レース公式矢印を、原バイトSHAと締切/結果時刻で紐付ける。今回の5件は風原文ラベルの参考、K同期データではない。
3. 24場への一般化は、公式図＋2方向以上の実レース照合＋FROM/TO矢印確認の全条件が完了した場に限る。公式**結果後**のKデータを同一レースのT−12予想に戻さない。
4. ③ #1693と⑤ #1698の固定比較対象、Top1/3/5/10・Brier/LogLoss・事前登録は現状のまま。**風補正の正式認定0、プロダクション導入0、main統合0。**

[今回の構造化台帳](official_relative_wind_visual_operator_semantics_20261109.json) / [旧24場画像表示調査](official_water_diagram_source_discovery_20261109.md) / [歴史的公式風向記述](venue_24_first_party_wind_orientation_witness_20261108.md)。
