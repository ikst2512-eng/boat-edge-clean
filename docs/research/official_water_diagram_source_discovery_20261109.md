# 24場公式水面図：画像表示と「正式方位認定」を分けた監査（2026-11-09）
**研究専用／Draft PR #1692。main・Render・予想4モード・UI・T−12・cron・過去予想・③⑤の固定候補は変更しない。自動統合禁止。**

## 今回の増分（既存18場の「公式解説文の手掛かり」とは異なる）
- BOAT RACE中央サイトで**水面図の画像を実際に表示できたのは6/24場**：戸田02、多摩川05、尼崎13、若松20、芦屋21、唐津23。
- 桐生01は図の取得がタイムアウト、江戸川03・常滑08・住之江12は図の取得経路エラー。**これらは公式HTTPエラーステータスと同義ではない**。他14場は未取得。
- 画像を表示した**6/24**は「図を見つけた」進捗であり、画像原本受領バイトとSHA256を固定できた場**0/24**、図の北向き・第1ターンマークを別担当が独立に再読した場**0/24**、公式K風向と同一レースの公式風向矢印の原画面まで揃った場**0/24**、相対風向の**正式認定0/24**。
- 既存の[公式一次文章の24場台帳](venue_24_first_party_wind_orientation_witness_20261108.md)には、歴史的公式説明の**明示11場・部分7場・未発見6場**が既にある。今回の画像表示6場を11+7に足して「24場のうち24場を認定」と誤算しない。**異なる証拠の次元**。

## 実際に表示した公式水面図（リンクは原画像の出所、**受領SHAではない**）
- [戸田02](https://www.boatrace.jp/static_extra/pc/images/img_water1_02.png)
- [多摩川05](https://www.boatrace.jp/static_extra/pc/images/img_water1_05.png)
- [尼崎13](https://www.boatrace.jp/static_extra/pc/images/img_water1_13.png) と[尼崎運営者図](https://www.boatrace-amagasaki.jp/cdn/pc/images/datafile/img_watermap.png)
- [若松20](https://www.boatrace.jp/static_extra/pc/images/img_water1_20.png)
- [芦屋21](https://www.boatrace.jp/static_extra/pc/images/img_water1_21.png) と[芦屋運営者図](https://www.boatrace-ashiya.com/cdn/pc/images/datafile/suimen_PC.png)
- [唐津23](https://www.boatrace.jp/static_extra/pc/images/img_water1_23.png) と[唐津運営者の新版図](https://www.boatrace-karatsu.jp/modules/datafile/images/img-s25-map.png?v=20251208)

**芦屋の前進**：北のコンパスが図上方、第2ターンマークが左、第1ターンマークが右の図から、スタート→1マークの**概ね東向きという暫定読取り**が可能。既存の[主催者レース別一次説明とK原本との7件参考照合](official_relative_wind_ashiya_operator_K_crosscheck_20261108.md)の「東風は向い風」とも方向上整合。ただし**原画像の保存SHAと独立読取りは未取得**。目視1回だけでhead=90°を公式認定しない。

**唐津の重要な版差**：[主催者水面説明](https://www.boatrace-karatsu.jp/modules/datafile/?page=index_suimen)では**2025年12月のピット位置変更**が明記された。2026年8〜10月のK研究は2025年12月以降の現行版図と照合すべきだが、図の保存SHA、厳密角度、風矢印の意味まで確定したわけではない。

## 24場・視覚的図面取得状況
一次資料文章のレベルは既存台帳から取り込み、新規の画像受領状況だけを追記した。二次A/Bの方位には**19/24場の不一致**が残る。

| 場 | 公式水面図表示 | 既存の一次文章・図の証拠分類 | 図の仮読取り | 正式 |
|---|---|---|---|---|
| 01 桐生 | 取得経路エラー（HTTP未検証） | first_party_text_sector_only | 未確定 | 未認定 |
| 02 戸田 | 公式水面図を表示（原本SHAなし） | first_party_text_explicit | 未確定 | 未認定 |
| 03 江戸川 | 取得経路エラー（HTTP未検証） | first_party_text_explicit | 未確定 | 未認定 |
| 04 平和島 | 今回未取得 | first_party_text_explicit | 未確定 | 未認定 |
| 05 多摩川 | 公式水面図を表示（原本SHAなし） | first_party_text_explicit | 未確定 | 未認定 |
| 06 浜名湖 | 今回未取得 | first_party_text_explicit | 未確定 | 未認定 |
| 07 蒲郡 | 今回未取得 | first_party_text_explicit | 未確定 | 未認定 |
| 08 常滑 | 取得経路エラー（HTTP未検証） | no_first_party_orientation_evidence_checked_in_this_round | 未確定 | 未認定 |
| 09 津 | 今回未取得 | first_party_text_sector_only | 未確定 | 未認定 |
| 10 三国 | 今回未取得 | no_first_party_orientation_evidence_checked_in_this_round | 未確定 | 未認定 |
| 11 びわこ | 今回未取得 | no_first_party_orientation_evidence_checked_in_this_round | 未確定 | 未認定 |
| 12 住之江 | 取得経路エラー（HTTP未検証） | first_party_text_explicit | 未確定 | 未認定 |
| 13 尼崎 | 公式水面図を表示（原本SHAなし） | first_party_text_explicit | 未確定 | 未認定 |
| 14 鳴門 | 今回未取得 | no_first_party_orientation_evidence_checked_in_this_round | 未確定 | 未認定 |
| 15 丸亀 | 今回未取得 | no_first_party_orientation_evidence_checked_in_this_round | 未確定 | 未認定 |
| 16 児島 | 今回未取得 | first_party_text_explicit | 未確定 | 未認定 |
| 17 宮島 | 今回未取得 | first_party_text_sector_only | 未確定 | 未認定 |
| 18 徳山 | 今回未取得 | first_party_text_sector_only | 未確定 | 未認定 |
| 19 下関 | 今回未取得 | no_first_party_orientation_evidence_checked_in_this_round | 未確定 | 未認定 |
| 20 若松 | 公式水面図を表示（原本SHAなし） | first_party_text_sector_only | 未確定 | 未認定 |
| 21 芦屋 | 公式水面図を表示（原本SHAなし） | first_party_operator_per_race_text_explicit | 東向き暫定 | 未認定 |
| 22 福岡 | 今回未取得 | first_party_diagram_visual_preliminary | 未確定 | 未認定 |
| 23 唐津 | 公式水面図を表示（原本SHAなし） | first_party_text_explicit_historical | 未確定 | 未認定 |
| 24 大村 | 今回未取得 | first_party_text_sector_only | 未確定 | 未認定 |

## T−12原本は独立のゲート
2026-11-09芦屋8Rの公式 [beforeinfo](https://www.boatrace.jp/owpc/pc/race/beforeinfo?hd=20261109&jcd=21&rno=8) をこの経路で直接開く試行は**cache miss**。**実HTTP 403/404を観測した証拠ではなく、公式気象をT−12以前に取得した証拠でもない**。競走結果Kの風はレース後であり、同じレース予想入力として再利用禁止。

次のチェックは次の順序で必要：**(1) 生画像の取得時刻/バイトSHAと図版日付、(2) 独立の北矢印と1マーク方位の二重読取り、(3) 風向が異なる同一場2レース以上の公式風矢印原画面とK生風向の一致、(4) FROM/TO意味の公式裏付け、(5) その先のT−12前受領と前向き予測評価**。いずれも欠けたら認定しない。

**今回追加は資料と監査台帳のみ。予想機能の改変・本番リリース・自動統合・予想改善の正式認定はいずれも0。CIは新コミットの実行を別に確認するまで成功扱いしない。**
