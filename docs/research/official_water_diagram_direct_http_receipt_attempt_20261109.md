# BOAT RACE公式水面図PNG・直接HTTPS原本取得を試行し、安全な研究専用受領器を作成（2026-11-09）

**Draft PR #1692限定。main、Render、4モード、予想・結果原本、UI、T−12、収集cron、既存CI設定、③ #1693・⑤ #1698の固定候補を変更しない。自動統合禁止。**

## 今回実際に判明したこと

1. [芦屋21のBOAT RACE公式PNG](https://www.boatrace.jp/static_extra/pc/images/img_water1_21.png) はWeb画像閲覧経路で図として表示できる。一方、この作業コンテナから同じURLの**原バイト**を取得する方法を実行したが、直接ダウンロードは失敗、Python \`requests\` と新しい \`urllib\` 研究受領器はいずれも **NameResolutionError / DNS \`Temporary failure in name resolution\`** に至った。**HTTP 403/404/5xxとは認定しない**。失敗時に画像バイト・SHA256・成功受領台帳は生成していない。
2. 前回追加した研究CI [#42602348182](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42602348182) は **completed/success** であることをGitHubから確認した。ただしその研究CI内に今回の新しい受領器の12テスト専用ステップが含まれたと**主張しない**。GitHub成功とローカルテスト成功は別。
3. 既存の[ローカルPNGバイト健全性検証器](../../scripts/research_water_diagram_byte_gate.py)はオンラインHTTP原本の来歴まで検証できない。この欠落を補うため、**明示的に1場だけ起動する、手動・研究専用のHTTPS受領器**を追加した。24場の自動巡回・監視・予定起動は実装していない。

## 新規実装と検証

- [\`scripts/research_water_diagram_http_receipt.py\`](../../scripts/research_water_diagram_http_receipt.py): \`--jcd\` で指定された1場の正規公式URLにHTTPS GETする。HTTP 200、転送後の同一場公式URL、\`Content-Type: image/png\`、非変換 \`Content-Encoding\`、\`Content-Length\`、最大5MB、PNG内部署名・IHDR/IDAT/IEND・チャンクCRCを検証し、原バイトのSHA256、受信開始／完了UTC、応答Date・ETag・Last-Modifiedを**研究出力に限って記録**する。
- 受領後は \`original_response.png\`、\`receipt.json\`、\`COMPLETE\` を固有名ディレクトリに保存。出力ルートのシンボリックリンク、既存の同一出力名への上書き、偽のT−12/方位認定フラグ、受領時刻文字列からのディレクトリ脱出を拒否。
- [\`scripts/test_research_water_diagram_http_receipt.py\`](../../scripts/test_research_water_diagram_http_receipt.py): HTTP 403、外部／別場転送、HTML応答、gzip変換、Content-Length不一致、PNG CRC破損、バイト改ざん、既存名上書き、偽の公式方位・公式矢印・T−12・本番承認、危険な時刻文字列、出力シンボリックリンクを**オフラインの偽応答で模擬**して拒否をテスト。**ローカル12テスト／12成功**。
- 保存後のGitHub Git blob SHAと、テスト時に使用したローカルのGit blob SHAが**2/2完全一致**。
  - 受領器: \`04dc64bd00feda6f580c5cb78b8274c3ebb3ad52\`
  - オフラインテスト: \`615cccb345e6f8d98f1e9571f5f77b73db658beb\`

**テスト成功はダミーPNG/HTTP応答に関する安全性の確認であり、実際の公式PNG受領成功・HTTP原本の第三者認定・北方位の認定・予想精度改善の証拠ではない。**

## 実際の取得を行う最小手順（ネットワークが利用できる研究環境に限る）

\`\`\`bash
python -m unittest -q scripts.test_research_water_diagram_http_receipt
mkdir -p /tmp/boat_diagram_receipts
python scripts/research_water_diagram_http_receipt.py \
  --jcd 21 \
  --output-root /tmp/boat_diagram_receipts
\`\`\`

**実行成功は未確認**。今の作業環境で実行すると \`NO_RECEIPT: URLError: ... Temporary failure in name resolution\` となり、\`COMPLETE\` やSHAを含む証拠束は生成されない。エラーを無理に成功扱いして取得数を増やさない。

\`receipt.json\` には \`http_200_final_url_and_png_integrity_passed\` という**その研究クライアントの検査結果**のみを記録し、\`source_attested_by_independent_service=false\`、\`diagram_bearing_independently_verified=false\`、\`same_race_wind_arrow_original_verified=false\`、\`t12_beforeinfo_source_verified=false\`、\`production_wind_use_authorized=false\` を明記する。原URLへのHTTPS接続自体が成功しても、別担当による**原画像SHAの独立照合**と図のN／1・2マーク位置の読取り、公式同一レース矢印のFROM/TO照合は別ゲート。

## 24場研究の未解決ゲート（前回から変えない）
- 公式水面図原PNGの日時付き保存・SHA・HTTP出所証拠: **0/24場**（前回の閲覧成功10場は別クラス）。
- N方位とスタート→1マークの二者独立読取り、レース別公式風向アイコンとK生風向のFROM/TO整合: **正式認定0/24場**。
- 芦屋の運営者8方位の文字表示と東90°の仮headingは[既存研究](operator_ashiya_eight_wind_heading_inference_20261109.md)で8/8例整合だが、動的ページの過去版HTML SHAと水面図の原バイトが未取得なので**方位正式認定ではない**。
- 公式Kの結果後風向・ST・波高を同じレースの事前入力に使用しない。T−12前の公式beforeinfo・6艇展示・120通りオッズ・候補予想初回遠隔保存、③/⑤の前向き非劣化確認を完了するまで、本番採用禁止。

今回追加は**研究用Pythonスクリプト1件、研究用オフラインテスト1件、この研究メモ1件のみ**。GitHub Actions/収集cronの新規起動・既存ワークフロー編集は行わない。**本番風補正0件、正式改善認定0件、main自動統合0件。**
