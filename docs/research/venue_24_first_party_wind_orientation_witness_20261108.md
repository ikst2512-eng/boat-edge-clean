# 24場風向の一次資料照合台帳（2026-11-08）
**Draft PR #1692／水面研究限定。予想本体・Render・UI・cron・T−12収集・公式結果原本・過去予想・mainの変更禁止。main自動統合禁止。**

## 成果（前回より進展、未認定は未認定のまま）
公式Kの8方位×24場・実1C適格13,112件における、二次方位A/Bの相対風向ラベル不一致8,837件（67.40%）は**前回の研究結果**。本回はそのA/BのうちAを裏付けるかを、**運営者/BOAT RACE公式の説明と水面図**で独立に探索した。

- **一次運営者等の説明文がAの頭方位と具体的に一致する場：6/24**（戸田、江戸川、平和島、蒲郡、尼崎、唐津）。ただし多くは過去の公式解説記事であり、2026年の図の位置・版と受領SHAまで認証していない。
- **部分的一次証拠が見つかった場：2/24**（徳山は南東風を「左斜め後方からの追い風」と説明。Aが南東をちょうどtailとするのとは**方向帯だけ一致し、斜め分類は一致しない**。福岡は公式ガイドPDFの図に方位記号と1/2マークが見えるが、2021年版・原画面SHAは未保存）。
- **今回独立に一次方向を確認できなかった場：16/24**。未確認を否定判定とはしない。公式サイトに水面図自体が掲載されていても、「図の北・進行軸と原レースの風向矢印を独立照合済み」とは呼ばない。
- **最終認定：0/24場。** 各場の公式水面図・北矢印・第1マーク位置の同一版・原画面SHA・風矢印の「吹いてくる向き/吹いていく向き」・同一レース複数風向の突合がそろっていない。二次方位を本番には流用しない。

## 具体的な一次資料（事実の種類を明示）
| 場 | 公式の説明・図から確認したこと | A仮説との整合 | 一次資料 | 注意 |
|---|---|---|---|---|
| 戸田02 | 春は東からの向かい風 | 明示的整合 | [戸田公式・水面/OB解説](https://www.boatrace-toda.jp/data/suimen_guide.html) | 季節の解説であり原結果矢印ではない |
| 江戸川03 | 北＝向かい、南＝追い | 明示的整合 | [江戸川公式・2021年展望](https://www.boatrace-edogawa.com/sp/index.php?day=20210115&page=soutenbo-tenbokiji) | 2021年の記述 |
| 平和島04 | 北＝向かい、南＝追い | 明示的整合 | [BOAT RACE公式・2020年解説](https://www.boatrace.jp/owpc/pc/extra/race/04_20200317/monthly/keitai.html) | 2020年の記述 |
| 蒲郡07 | 南西＝向かい、北東＝追い | 明示的整合 | [蒲郡公式・2026年SG冊子](https://www.gamagori-kyotei.com/classic61/pamphlet.pdf) | PDFテキストは確認、該当ページの画像取得は失敗。原画面SHA未取得 |
| 尼崎13 | 六甲山からの西風＝向かい | 明示的整合 | [BOAT RACE公式・2015年解説](https://www.boatrace.jp/owpc/pc/extra/race/13_20150317/monthly/guide.html) | 古い解説 |
| 徳山18 | 南東風＝左斜め後方からの追い風 | **大まかな追い方向のみ** | [徳山公式・水面データ](https://www.boatrace-tokuyama.jp/modules/datafile/index_suimen.php) | Aでは南東は正面の真逆、tailと算定。斜めという公式記述と厳密なラベルは未整合 |
| 福岡22 | 公式ガイドに北方位・2マーク・1マークの水面図がある | **図の予備的目視のみ** | [福岡公式・2021年舟券ガイドPDF](https://www.boatrace-fukuoka.com/uploads/pdf/keikotaisaku.pdf) | PDF3ページ目を目視。図の版・真方位・SHA未確定 |
| 唐津23 | 北からの海風＝追い風 | 明示的整合（過去の図） | [唐津公式・2020年攻略BOOK](https://www.boatrace-karatsu.jp/uploads/info/karatsu_capture_book.pdf)、[2025年12月以降のピット変更について](https://www.boatrace-karatsu.jp/modules/datafile/?page=index_suimen) | 古い公式図を2026年の幾何・進入仕様へ直接再利用不可 |

**ソースの格付け**：これらは**主催者/BOAT RACEサイトによる一次説明・公式図**。ただし「2026年8〜10月の各レース公式原本K」「公式水面方位の原画面SHA」「締切前のbeforeinfo原本」はそれぞれ異なる証拠である。解説の方向や過去の着率を2026年にそのまま移すことはできない。

## 全24場の現状
Aは二次資料で提示された進行方向を「仮向かい風方位」にしたもの、Bはスタンド向きを「仮追い風方位」に読み替えたもの。両者の定義は同じではないため、差があることだけでBの誤りとは断定しない。
| 場 | A仮head方位 | B仮head方位 | 今回の一次資料の証拠レベル | 完全認定 |
|---|---:|---:|---|---|
| 01 桐生 | 135° | 270° | no_first_party_orientation_evidence_checked_in_this_round | 未認定 |
| 02 戸田 | 90° | 180° | first_party_text_explicit | 未認定 |
| 03 江戸川 | 0° | 20° | first_party_text_explicit | 未認定 |
| 04 平和島 | 0° | 90° | first_party_text_explicit | 未認定 |
| 05 多摩川 | 270° | 0° | no_first_party_orientation_evidence_checked_in_this_round | 未認定 |
| 06 浜名湖 | 180° | 270° | no_first_party_orientation_evidence_checked_in_this_round | 未認定 |
| 07 蒲郡 | 225° | 270° | first_party_text_explicit | 未認定 |
| 08 常滑 | 270° | 90° | no_first_party_orientation_evidence_checked_in_this_round | 未認定 |
| 09 津 | 270° | 270° | no_first_party_orientation_evidence_checked_in_this_round | 未認定 |
| 10 三国 | 135° | 90° | no_first_party_orientation_evidence_checked_in_this_round | 未認定 |
| 11 びわこ | 180° | 180° | no_first_party_orientation_evidence_checked_in_this_round | 未認定 |
| 12 住之江 | 180° | 180° | no_first_party_orientation_evidence_checked_in_this_round | 未認定 |
| 13 尼崎 | 270° | 180° | first_party_text_explicit | 未認定 |
| 14 鳴門 | 135° | 180° | no_first_party_orientation_evidence_checked_in_this_round | 未認定 |
| 15 丸亀 | 315° | 180° | no_first_party_orientation_evidence_checked_in_this_round | 未認定 |
| 16 児島 | 180° | 180° | no_first_party_orientation_evidence_checked_in_this_round | 未認定 |
| 17 宮島 | 225° | 270° | no_first_party_orientation_evidence_checked_in_this_round | 未認定 |
| 18 徳山 | 315° | 180° | first_party_text_sector_only | 未認定 |
| 19 下関 | 225° | 180° | no_first_party_orientation_evidence_checked_in_this_round | 未認定 |
| 20 若松 | 270° | 180° | no_first_party_orientation_evidence_checked_in_this_round | 未認定 |
| 21 芦屋 | 90° | 180° | no_first_party_orientation_evidence_checked_in_this_round | 未認定 |
| 22 福岡 | 90° | 180° | first_party_diagram_visual_preliminary | 未認定 |
| 23 唐津 | 180° | 180° | first_party_text_explicit_historical | 未認定 |
| 24 大村 | 90° | 180° | no_first_party_orientation_evidence_checked_in_this_round | 未認定 |

## 完了までの必須条件（fail closed）
1. 同一版の**公式水面図の原画像**に、北矢印・第2ターンマーク・第1ターンマーク・スタート側の位置があり、方位を数値化できること。URL・閲覧時刻・原ファイルSHA256・資料版を保持。変更履歴を確認。図の解釈は別担当が独立確認。
2. 同じ場の異なる風向2レース以上で、公式Kの**風が来る方角の原文8方位**と、公式結果の風向矢印画像を、同一日・同一レース・取得時刻・SHAで照合。矢印の意味（FROM/TO）と図の画面回転を確定。
3. この二つがそろっても事後研究のみ。予想特徴量としては、公式beforeinfo気象・展示6艇・120通りオッズ・締切T−12以前の遠隔受領・予想初回保存の一貫した証拠を別に要する。
4. ③ #1693 と⑤ #1698に**一次解説で裏付いた範囲と未認定の範囲を区別して共有**。固定した予測候補・順位付け・過去原本の再学習・結果後リークは禁止。

## 検証台帳
[全24場JSON・公式URL・原文要旨・二次A/B方位・欠損と承認フラグ](venue_24_first_party_wind_orientation_witness_20261108.json)。

**新たな風向補正0件、正式な実予想改善0件、main・Render・UI変更なし、PRはDraft・未統合。**
