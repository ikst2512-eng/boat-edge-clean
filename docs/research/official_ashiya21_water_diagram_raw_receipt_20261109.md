# 芦屋21・公式水面図原PNGの初回HTTPS受領成功と独立バイト監査（2026-11-09）

**研究専用・Draft PR #1692。main・Render・本番4モード・UI・保存済み予想・既存CI/cronには未接続。自動統合禁止。**

## 結論：初めて実原本の取得に成功（1/24場）

**11月9日20:38 JST頃**、Draft研究ブランチの**専用単発pushワークフロー** [GitHub Actions #42610527366](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42610527366) で公式水面図 [芦屋21 PNG](https://www.boatrace.jp/static_extra/pc/images/img_water1_21.png) をHTTPS直接取得し、PNG原バイト・HTTP応答情報を同一証拠束に保存できた。

- HTTP **200**、初回リクエストURLと最終URLは同じ `www.boatrace.jp/static_extra/pc/images/img_water1_21.png`、Content-Type `image/png`、Content-Encoding `identity`。受信UTC **2026-11-09 11:38:18.239473～11:38:18.568708**（日本時間20:38:18）。
- 元の `original_response.png` **28,684バイト／580×227px／RGB／PNG**。SHA-256：
  `7a8b50f685f738e3625bdf6bc212074ba78af34bcdea7ac350e5e3422ee357cf`
- 元サーバー応答ヘッダー：`Date: Mon, 09 Nov 2026 11:38:18 GMT`、`Last-Modified: Wed, 04 Jan 2023 12:31:46 GMT`、`ETag: "700c-5f16f5e1d43ab"`。場データの公表「2023/01/01現在」は**公表版日付**、HTTP `Last-Modified` は**ファイル更新日時**であり、同じ意味として上書きしない。
- 取得ジョブで、研究専用のPNG健全性テスト**16/16**、HTTP拒否テスト**16/16**成功。取得・成果物アップロードの各ステップも成功、**job status completed/success** を確認した。

## 取得したままのZIPを別の環境で開いて再検証

公式PNGと受領JSONを含むGitHub Actions artifact **13670072140**（名前 `official-ashiya-21-png-one-shot-research-only`）を、GitHub接続から実際にダウンロード。ZIP **30,625バイト**、SHA-256 `b1f3dec7393aec3673bbe9664d09161f34d5bd260730309ed14c2e831d8bbd94` を独立計算し、**ActionsアップロードログのZIP SHAと完全一致**した。

ZIP中の3ファイル（`original_response.png`・`receipt.json`・`COMPLETE`）を確認し、ZIPのCRC、PNG SHA-256とJSON/SHA、PNG署名、Pillowでの画像デコード・verifyを独立に実行。**PNG SHA＝受領JSON SHA＝GitHub Actionsログ SHAで3点一致**。これまでの「画像がブラウザに見えるだけ」「ローカルDNSが失敗するだけ」から**公式ホストHTTPSでの生バイト受領・保存成功**へ進んだ。

**アーティファクト保存期限：2026-11-10 11:38:18 UTC（日本時間20:38:18）**。期限後はGitHubのZIPが消えるため、別途ダウンロード済みの原画像は厳重に保管し、メタデータ台帳を原本そのものの代用としない。研究用台帳JSON：[`official_ashiya21_water_diagram_raw_receipt_20261109.json`](official_ashiya21_water_diagram_raw_receipt_20261109.json)。

## 公式水面図の読み取りと「認定」の差

原PNGには右上に北方位の記号があり、第2ターンマークは図の左側、第1ターンマークは右側に描かれている。従前の芦屋「スタート→1マークは東系統」仮説と**模式図の目視上は整合**する。しかしこの図は測量座標の完全な証明ではない。**別の独立レビュアーによる原画像の方位読取り・2026年水面配置差異・気象矢印FROM/TOの元画像確認は未完了**。

証拠ゲートを混ぜない：
1. **公式PNG原バイトの保存成功1/24場**：今回の成果。これはクライアントが公式HTTPSから受け取った原応答の証拠であって、外部の独立公証までは実施していない。
2. **方位・第1マーク方向の正式認定0/24場**：別レビュアー、同一版、マーク位置、場別設備変更との整合が未検証。
3. **同一レース公式風向矢印・FROM/TO確認0/24場**：2方向以上の公式K結果と運営者画面の原バイト・日付・レースID紐付けは未了。
4. **T−12の直前予想入力認定0件**：公式Kは事後データで、取得した公式水面図にも前レース時点の気象・展示6艇・オッズ120通り・予想初回遠隔保存を証明する機能はない。
5. **風補正の予想精度改善正式認定0件**：③ #1693・⑤ #1698の独立前向き評価へ接続していない。

## GitHub Actions単発隔離の安全条件

新規ファイルは **`.github/workflows/research-water-diagram-receipt-once.yml`** のみ（既存ワークフローのコード変更なし）。研究ブランチ `research/venue-environment-factor-baseline-20261106` における**このワークフローファイルのpush差分**だけで起動し、芦屋21の1 URLにだけアクセス。権限 `contents: read`、checkout後の認証情報は保持しない、secret不要。**schedule・cron・workflow_dispatch・本番への配備は存在しない**。後続の研究文書だけの更新ではこの単発ワークフローは再起動しない。デフォルトmainには反映せず、Draft未統合を維持。

## 次の確実な作業

(1) 元画像の別担当による北方位・第1/2マークの二重読取り、(2) 芦屋の同一レース公式風向矢印原画面と公式K生方向・FROM/TOの独立一致、(3) 原画像を含む証拠束の長期的な保存方法・保存権限の決定、(4) 2場目以降の原PNGを**同一の安全ゲート**で受領。これらを満たすまで正式な風向補正は行わない。

**実受領1/24場。相対風向の正式認定0/24場。本番補正0件。main統合0件。**
