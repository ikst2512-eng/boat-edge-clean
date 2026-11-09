# 公式水面図PNG原本・CRC一致でも壊れたIDATを拒否する研究監査（2026-11-09）

**Draft PR #1692限定。main・Render・予想4モード・UI・T−12・公式レース原本・採点・収集cron・GitHub Actions設定は変更しない。③ #1693・⑤ #1698の既存凍結比較対象に接続しない。自動統合禁止。**

## 今回、実際に再現した未検査経路

旧 `scripts/research_water_diagram_byte_gate.py` はPNGの8バイト署名、IHDR/IDAT/IENDチャンク、CRC32、画像寸法を確認していたが、**IDAT内部のzlibストリームを展開していなかった**。サイズ2×1・色形式RGBのIHDR、`IDAT=b"not-deflate-data"` とする偽画像を組み、IDATチャンクCRCを正規に再計算すると、旧検証器は**(2,1)として受理**した。一方、画像デコーダー(Pillow)は破損したデータとして拒否した。これは以前の「HTMLを自己一致SHA付きで偽PNGとして保存できた」問題とは**別の検証不足**。

## 修正内容と失敗時の扱い

既存 `scripts/research_water_diagram_byte_gate.py` に以下を追加した。画像のHTTP出所や予想利用資格を認定する変更ではない。

1. IDATを連結し、標準ライブラリ`zlib.decompressobj`で**最大80MBの展開予算・最大2000万画素**を上限に、実画像のbit depth/color/channels・縦横・Adam7インターレースから計算した行データ長へ一致するか照合。CRCだけ正しい壊れたzlib、途中終了、想定外の後続データ、サイズ超過を拒否。
2. 展開された各行の先頭フィルター値が0〜4の範囲にあるかを確認。画像の完全な色空間表現や水面図の北方位の意味を「独立検証済み」と誤認しない。
3. PNGのcolor typeとbit depthの適法な組み合わせ、indexed画像のPLTE必須条件、IDATチャンク連続性、PLTEの配置/長さを検査。不正な画像構造を拒否。
4. 既存のHTTPS原本受領器は`fetch_once`時も`write_bundle`時もこの強化されたPNG検証を呼ぶ。**見かけ上SHAとHTTPメタデータが一致していても、壊れた画像を原本保存せずCOMPLETEを作らない**。

## 同一ソース・ローカルテストとGitHub再取得

| 検証対象 | 変更前 | 変更後 | 追加検証 |
|---|---:|---:|---|
| PNG原バイト検証器 | 10件 | **16/16成功** | 壊れたzlib、展開サイズ不整合、無効フィルター、膨張データ、palette/IDAT規則、Adam7正常例 |
| 単一場HTTP原本受領器 | 14件 | **16/16成功** | 外側CRCが正しい壊れたPNGのHTTP受信拒否と保存直前拒否 |
| 合計 | 24件 | **32/32成功** | すべて**オフライン**、公式HTTP受領の成功ではない |

`python -m unittest -q scripts.test_research_water_diagram_byte_gate`
`python -m unittest -q scripts.test_research_water_diagram_http_receipt`

今回のテスト対象は以下の3ファイル。GitHub保存時のblob SHAと、ローカルで実行した内容のblob SHAを**3/3一致**まで照合済み：
- 検証器 `scripts/research_water_diagram_byte_gate.py` → `08b13b4e5eabbfd1fc798ca8a27a1898cf10d2d2`
- 検証器テスト `scripts/test_research_water_diagram_byte_gate.py` → `2371fb5e441a582340a89f412378cb2b81e2c641`
- HTTP受領器の回帰テスト `scripts/test_research_water_diagram_http_receipt.py` → `ce508c34949a8a5c24be79642078d105d6ccb3bc`

HTTP本体 `scripts/research_water_diagram_http_receipt.py` は変更していない。追加確認として、生成した一般的なRGB/RGBA/L/P/1モードのPNGそれぞれを強化後の関数が読み取れることをローカルで確認した。この5画像は**試験用画像であって公式水面図ではない**。PNG完全仕様の認定テストでもない。

## 公式ソース取得の現状（変更なし）

- [芦屋21の公式水面図](https://www.boatrace.jp/static_extra/pc/images/img_water1_21.png)はWebの画像表示経路で閲覧できるが、**本実行コンテナからHTTP原画像を保存する直接取得はDNS名前解決エラー**。別の非公式画像を公式原本として代用したり、Webのレンダリング結果からSHAを作ったりしない。
- 公式Kの8〜10月原本92日/14,249RのSHA検証は別の研究証拠であり、公式水面図PNG、同一レース公式風向矢印、公式beforeinfoの初回受領を代替しない。
- **公式水面図原PNGのバイト受領0/24場**、北方位と第1マークの二者検証0/24場、レース別風向矢印FROM/TOの原画像SHA認定0/24場、相対向かい/追い風正式認定0/24場、T−12予想適格0件、本番採用0件。
- 新規コミットのGitHub Actions CI完走とは独立にローカルテスト成功を報告。CIは完了・結論を別途確認する。

**この追加は、研究用PNG検証器1件＋研究用テスト2件＋この研究レポートの計4ファイルのみ**。既存水面研究・他PR・本番予想コード・Render・main・CI設定には接続していない。
