# 4モード保存原本のT−12風・展示受領証拠監査（2026-11-08）

**既存研究Draft PR #1692専用 / 本番4モード・Render・main・cron・予想原本・AI自動統合を変更しない。**

## 対象と独立ソース

- 本番mainの**固定コミット** `6409443d6487b5c175eec4ed2a7f4bf136f69da4`。研究Draftの履歴とは別のmain上に存在した保存済み `four_mode_forecasts/` を、`git fetch` + `git show <固定SHA>:<path>` だけで読み取り専用検査した。
- 日付を固定：2026-11-06〜11-08。予想レコードをレースコードと同名ファイルで一意照合し、`deadline_jst` から12分差し引いた境界と、title/cards受領日時および予想生成日時を比較。
- CI： https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42456391477
- 証拠Artifact：`four-mode-frozen-main-wind-t12-metadata-gap-research-only`
- 検査ソース群SHA-256：`395f24777fca48a6428f9f49ef03a89033ee6a09e69593ea14b1da1963838921`。
- 成果物JSON SHA-256：`1a2d0d22ade90718686ec8345b91a23052e12bf2149a5e288ee49dd1f896fcb5`。

## 固定mainの368レースの実測

| 指標 | 11/6 | 11/7 | 11/8 | 合計 |
|---|---:|---:|---:|---:|
| 予想保存レース数 | 130 | 122 | 116 | **368** |
| title/cards受領と予想生成がT−12以前 | 130 | 122 | 116 | **368** |
| `beforeinfo` の生原本が保存予想中に存在 | 0 | 0 | 0 | **0** |
| 保存予想に風/weatherの明示属性あり | 0 | 0 | 0 | **0** |
| `validated=true` | 0 | 0 | 0 | **0** |
| 保存予想だけで公式風・展示のSHA、受領時刻を原本確認可能 | 0 | 0 | 0 | **0** |

368件すべてで `beforeinfo="optional_not_in_snapshot"`、`status="provisional"`、`validated=false`。予想の`source_sha256`はtitle/cards用であって、公式beforeinfoの気象原本を保証しない。

**正しい読み方**：この固定期間の保存予想では、出走表のtitle/cards受信と予想生成は12分前に間に合っていた。それでも独立した公式気象、展示、進入、オッズの一次原本を同一予想のT−12適格入力として確認した件数は0である。**外部に気象原本が存在しないという主張ではない**。外部に保存した受信ログやAPI原本の別経路調査は独立に行う。

## 追加：11月4日桐生11Rの独立公式beforeinfo原本

固定mainの368予想とは**別の、以前保存した2026-11-04の一次原本**を独立に検査した。

- レースコード：`202611040111`（桐生11R）。
- 原本：`docs/observations/official_preview_20261104/beforeinfo.json`、4,608バイト、SHA-256 `40e7859d3841f6a9b6329b1a7426cad46dd65f98562a38e3f06cc4fa24a02d01`。受信メタデータ：同ディレクトリの `manifest.json`。
- 公式ソース：`https://www.boatrace.jp/owsp/sp/spdata?type=beforeinfo&hd=20261104&jcd=01&rno=11`。取得要求開始：`19:39:13.821804 JST`、実受領：`19:39:21.767860 JST`。
- 原本締切：`20:03 JST`、T−12境界：`19:51 JST`。**公式beforeinfoの受領時刻は境界以前**。
- 6艇の出走・スタート展示データ行は原本に存在。
- `maindata.weatherinfo.wind="2m"`、`wave="1cm"`、`measuretime="10R時点"`。風向ソース値は`winddirec="02"`、`northdirec="14"`として保存（地理的な絶対風向や場ごとの風向軸は未照合）。
- 生の`measuretime="10R時点"`には**実測日時の時分秒がない**。したがって11RのT−12時点と同時に計測された風と見なさない。
- この例では原本受領時刻が早いことを確認したが、**3種類の独立一次原本の同期や、その時刻に凍結した4モード予想に実際に使われたことは証明できない**。正式なT−12予想認定ではない。

実測CI： https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42456605544 、証拠Artifact：`official-beforeinfo-weather-raw-receipt-20261104-research-only`。成果物JSON SHA-256：`33030713efa39ad0c89d66a1250a72c88491aa12ed319daff43bc11cd30e9f08`。

## 採用・評価に必要な残件

1. 同一レースコードで公式気象の**受信原本バイト・SHA・HTTP受領時刻・風測定時点**と、6艇の出走表・展示・進入・オッズ等の独立元を**締切−12分**までに照合する。
2. 当該原本が**予想保存より前**に受領され、予想プログラムが使用した入力のfingerprintに含まれることを証明。結果後のK原票の風速や実STで穴埋めしない。
3. 別期間の予想と独立確定結果が集まるまで、Top1/3/5/10・Brier・LogLoss・勝負度などの改善を正式採用しない。オッズ実収益も後知恵で書き換えない。
4. 今回は一次気象受信の実例を1件証明したにすぎず、**2026-11-06〜08の368件には気象の原本認定0件**。風補正・本番採用0件、main/Render/4モード変更0件を維持。

関係する研究コード：
- `scripts/research_four_mode_pre_t12_wind_inventory.py`
- `scripts/research_official_beforeinfo_wind_receipt_gate.py`
- `tests/test_research_four_mode_pre_t12_wind_inventory.py`
- `tests/test_research_official_beforeinfo_wind_receipt_gate.py`

**CIの成功表示は各ステップ・Artifactの原本と分離して扱う。** この研究ブランチはPR #1692をDraft・未統合で維持。
