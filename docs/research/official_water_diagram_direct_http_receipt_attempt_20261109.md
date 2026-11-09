# BOAT RACE公式水面図PNG・直接HTTPS原本取得を試行し、安全な研究専用受領器を作成（2026-11-09）

**Draft PR #1692限定。main、Render、4モード、予想・結果原本、UI、T−12、収集cron、既存CI設定、③ #1693・⑤ #1698の固定候補を変更しない。自動統合禁止。**

## 今回実際に判明したこと

1. [芦屋21のBOAT RACE公式PNG](https://www.boatrace.jp/static_extra/pc/images/img_water1_21.png) はWeb画像閲覧経路で図として表示できる。一方、この作業コンテナから同じURLの**原バイト**を取得する方法を実行したが、直接ダウンロードは失敗、Python \`requests\` と新しい \`urllib\` 研究受領器はいずれも **NameResolutionError / DNS \`Temporary failure in name resolution\`** に至った。**HTTP 403/404/5xxとは認定しない**。失敗時に画像バイト・SHA256・成功受領台帳は生成していない。
2. 前回追加した研究CI [#42602348182](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42602348182) は **completed/success** であることをGitHubから確認した。ただしその研究CI内に今回の新しい受領器の12テスト専用ステップが含まれたと**主張しない**。GitHub成功とローカルテスト成功は別。
3. 既存の[ローカルPNGバイト健全性検証器](../../scripts/research_water_diagram_byte_gate.py)はオンラインHTTP原本の来歴まで検証できない。この欠落を補うため、**明示的に1場だけ起動する、手動・研究専用のHTTPS受領器**を追加した。24場の自動巡回・監視・予定起動は実装していない。

## 新規実装と検証

- [\`scripts/research_water_diagram_http_receipt.py\`](../../scripts/research_water_diagram_http_receipt.py): \`--jcd\` で指定された1場の正規公式URLにHTTPS GETする。HTTP 200、転送後の同一場公式URL、\`Content-Type: image/png\`、非変換 \`Content-Encoding\`、\`Content-Length\`、最大5MB、PNG内部署名・IHDR/IDAT/IEND・チャンクCRCを検証し、原バイトのSHA256、受信開始／完了UTC、応答Date・ETag・Last-Modifiedを**研究出力に限って記録**する。
- 受領後は \`original_response.png\`、\`receipt.json\`、\`COMPLETE\` を固有名ディレクトリに保存。出力ルートのシンボリックリンク、既存の同一出力名への上書き、偽のT−12/方位認定フラグ、受領時刻文字列からのディレクトリ脱出を拒否。
- [\`scripts/test_research_water_diagram_http_receipt.py\`](../../scripts/test_research_water_diagram_http_receipt.py): HTTP 403、外部／別場転送、HTML応答、gzip変換、Content-Length不一致、PNG CRC破損、バイト改ざん、既存名上書き、偽の公式方位・公式矢印・T−12・本番承認、危険な時刻文字列、出力シンボリックリンクを**オフラインの偽応答で模擬**して拒否をテスト。**ローカル14テスト／14成功（保存直前の偽PNG・メタデータ改ざん2件を追加）**。
- 保存後のGitHub Git blob SHAと、テスト時に使用したローカルのGit blob SHAが**2/2完全一致**。
  - 受領器: \`824b7036e3e655bc1938d2e92ff517ae2651636f\`
  - オフラインテスト: \`1a2e7acac5db89829218589b4685f5d91d1e543c\`

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

## 追加の保存直前監査：偽PNGをSHAだけ一致させる欠陥を実証し修正

11月9日の独立ローカル監査で、初版 `write_bundle` に**保存直前にPNG実体を再検査しない**抜けを発見した。攻撃的なテストとして任意の `<html>not a PNG</html>` バイト列に合わせ `receipt["png_sha256"]` を再計算し、元プログラムの `write_bundle` に直接渡すと、**HTMLが `original_response.png` として保存され、`COMPLETE` も作られることを実際に再現**した。これは「ネットワーク実受領」の再現ではなく、受領関数を呼ぶ側に渡せる内部パラメータの整合性検査不足である。

**修正:** `write_bundle` の保存前に `png_dimensions(raw)` によるPNG構造/CRCを再検査し、`png_bytes == len(raw)`、`png_dimensions`、`Content-Type=image/png`、`Content-Encoding=identity` に相当するレシート値との完全照合を追加。SHAが一致していても非PNGなら拒否し、出力フォルダーを作らない。

**同じファイルをオフライン再実行**し、以前の12件＋「SHA一致偽PNG」「レシート画像長/寸法/型・変換フラグ偽装」の2件、**14/14成功**。GitHubにコミットした2ファイルのGit blob SHAも、実行したローカル2ファイルと一致（上記SHAを最新化済み）。

**証拠の限界:** この修正を通過しても公式PNGをインターネットから実際に受信・日時・HTTP署名を第三者検証した証拠にはならない。作業コンテナでは外部DNSが失敗しており、公式水面図原画像の**実受領とSHA原本固定は今も0/24場**。GitHub研究CIはローカル14テストとは別に状態を確認する。今回の追加は既存研究スクリプトと単体テストと研究メモの変更のみで、main・収集ワークフロー・Render・UI・予想4モードの変更なし。
