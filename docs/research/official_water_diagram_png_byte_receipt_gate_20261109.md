# 公式水面図PNG・原バイト受領の安全ゲートと未取得証拠（2026-11-09）

**Draft PR #1692研究専用。main・Render・本番予想4モード・UI・T−12収集・GitHub Actions/cron・既存予想/結果原本・③ #1693／⑤ #1698の固定研究候補は変更禁止。自動統合禁止。**

## 今回の成果と現時点で取得できなかったこと

前回の公式水面図は画像表示や公式記事の文字説明を確認できたが、**PNG原本のバイト列をこの実行環境にダウンロードしていなかった**。本回、戸田02の公式PNG `https://www.boatrace.jp/static_extra/pc/images/img_water1_02.png` に対して実際にコンテナへ直接取得を試みたが失敗した。別途Python HTTPSリクエストも名前解決エラーとなった。これらは**実HTTP 403/404/5xxを確認したという意味ではない**。公式画像の閲覧経路では02戸田・21芦屋等の表示自体は可能だった。

**原画像の独立取得とSHA固定：0/24場、同一レース公式矢印の原本SHA：0/24場、公式図と矢印を両方満たす相対風向の正式認定：0/24場、T−12予想入力認定：0。**

この未解決の証拠不足を偽装せず、**後で取得できた原バイトを安全に照合できるオフライン専用検証器**を追加：
- `scripts/research_water_diagram_byte_gate.py`：24場の公式PNG URLの厳密一致（HTTPS、会場コード、ファイル名、query・他ホスト拒否）、PNG署名/チャンクサイズ/IHDR/IDAT/IEND/CRC、上限5MB、ファイルsymlink拒否、原バイトSHA-256、画像幅高さ、同一結果ファイル上書き拒否。**ネットワークにアクセスしない研究用プログラム**。PNG画像の色・座標の解釈は行わない。
- `scripts/test_research_water_diagram_byte_gate.py`：署名がPNGでないHTML、CRC破損、IEND欠損/末尾ゴミ、別会場・偽ホスト、原画像バイト差し替え、架空の公式矢印認定、シンボリックリンク、版日付書式を検査。**同じソースでローカル単体テスト10/10成功**。
- GitHub保存後、ローカルのソース2件のGit blob SHAとGitHubのblob SHAが**2/2一致**：
  - 検証器 `df4d5d177bea84afefd06eae1bb4dcffe317cfd6`
  - テスト `4114436648b2cb28e6792cebf61d0981942e1f3e`

**厳密な証拠ラベル分離**：`file_integrity_verified=true` は指定ファイルの**ローカルバイト列**が読み取れる意味に限定する。誰かがファイルを公式URLから受領したHTTP通信、取得時刻、改訂履歴、独立二者の北方位読取り、結果レースの風向矢印、T−12原本を証明したわけではない。ゆえに出力は `official_http_original_response_proven=false`、`source_url_claim_cryptographically_verified=false`、`official_diagram_north_axis_second_review_passed=false`、`same_race_official_arrow_original_sha_verified=false`、`t12_weather_input_verified=false`、`production_transform_authorized=false` で固定される。日付 `claimed_page_revision` も文字列の書式チェックであって真偽の認定ではない。

## 最小再現手順（原画像バイトが別経路で実際に取得できたときだけ）

```bash
python -m unittest -q scripts.test_research_water_diagram_byte_gate
python scripts/research_water_diagram_byte_gate.py \
  --jcd 21 \
  --png /verified_original_source_bytes/ashiya_21.png \
  --source-url https://www.boatrace.jp/static_extra/pc/images/img_water1_21.png \
  --claimed-page-revision 2023-01-01 \
  --out /tmp/research_ashiya_local_png_receipt.json
```

**この例は受領実績ではない。** 実行するには本物の画像バイトを予め所持している必要がある。CRCのチェックはPNG圧縮画素の完全なデコード・視認・来歴証明の代替ではない。

## 公式サイトの版管理で判明した注意例：唐津23

- [BOAT RACE公式の唐津・場データ](https://www.boatrace.jp/owpc/pc/data/stadium?jcd=23) は水面図を**「2025/12/08現在」**として表示している（今回閲覧したWeb側のインデックスは3か月前の取得であり、2026-11-09の生HTTP本文原本SHAではない）。
- [唐津主催者の水面特性](https://www.boatrace-karatsu.jp/modules/datafile/?page=index_suimen)は**「2025年12月よりピット位置が変更」**と記し、[2025-12-14からの具体的な設備/待機時間変更案内](https://www.boatrace-karatsu.jp/uploads/pdf/syussou/20251214_01.pdf)も公表されている。
- このため**図の公開版日付と実際の設備変更の適用日を別列に管理**し、古い図だけで2026年のピット・助走・進入深度を確定することを禁止する。ピット移動が第1マークへの進行**真方位**そのものを変えたとは証明していない。
- [戸田02公式場データ](https://www.boatrace.jp/owpc/pc/data/stadium?jcd=02) と[芦屋21公式場データ](https://www.boatrace.jp/owpc/pc/data/stadium?jcd=21) は図の公表版表示が2023/01/01。図の閲覧成功と2026年の独立再検証済みは別物。

## 残る原本の独立受領ゲート

1. 公式サイトが現時点で返した**元PNGそのもの**とHTTPステータス/最終URL/応答ヘッダー・取得開始/完了UTC・保存元URL・SHA-256を同じ証拠束に固定。認証外ホスト・エラー・圧縮解凍やスクリーンショットから作り直した画像を原本扱いしない。今回この証拠束は**0件**。
2. 図の北方位記号・第1/2マーク・スタート側を**二者が独立**に読取り、図の公表版と会場の設備変更履歴を突合。図があるだけでは公式相対風向を認定しない。
3. 同じ会場で**異なる風向2レース以上**、公式K生方位/レースIDと運営者の結果後風向矢印の**原画面バイト・SHA**を照合し、矢印のFROM/TOを証明。前回の芦屋の動的モーター台帳はURLが同じでも履歴表示が動くため、過去検索表示だけで恒久原本と認定しない。
4. 結果後Kの風速/風向/ST/波高は同じレースの**T−12前予想には使わない**。予想特徴量への採用は公式beforeinfo原応答と受信時刻・6艇展示・120オッズ・独立予想初回保存の証拠が揃い、③の固定した前向き300+300や⑤の条件付き順位の非劣化をクリアしてから。

今回の追加は**この研究Markdown＋研究用Python検証器＋その単体テストのみ**。本番設定、モデル、データ収集、定期ワークフロー、main、CI設定、他PRの候補は変更なし。**本番風補正0、正式改善認定0、方位正式認定0/24。**
