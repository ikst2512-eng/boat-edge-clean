## 2026-11-10 夜｜19:35公式展示検証の失敗時リトライと公開Pages/Render実ブラウザ証明
- **既存watchdogの1回救済を実装**：[main `23502763`](https://github.com/ikst2512-eng/boat-edge-clean/commit/23502763ee93093d79d2116db16d3b1598480172) は `scripts/entry_course_activation_watchdog.py` の既存 `official_live_probe_fallback` のみ修正。19:35 JSTの主`verify-real-beforeinfo.yml`が明確に`completed/failure`になった場合、19:50〜19:59 JSTに既存watchdogから**最大1回だけ**同じWorkflowへ`workflow_dispatch`救済。成功・未確定・実行中・既存dispatchあり・scheduleが複数・時刻範囲外は救済しない。実行有無と24値証拠は別記録。新Cron・新PR・予想結果原本への変更なし。
- **本番CI合格**：[Actions #42825986204](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42825986204) はmain `b50da623` のwatchdogテスト29件すべてPASS。追加検証で一次19:35失敗からの単発救済、および成功・不明・進行中・既存救済・複数schedule・19:43の不要な再起動拒否を確認。本番で実際の主schedule失敗を検出して救済した事実は**まだ未確認**。11/11 20:15 JSTの既存自動監査にschedule/dispatch/救済の別集計を追記済み。
- **公開画面の実アクセスを独立証明**：[読み取り専用のPR診断 Actions #42824633355](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42824633355) は `success`。実公開PagesとRenderの`index.html`/`navigation.js`はmain `1ddb26bf` 時点の内容と4ファイルすべてバイト一致。公開Render CORS 200/404/422をChromium・WebKitで、過去レース4モード5/10/16/22点/確率表示、履歴/戻る/進む/4主タブを**モックなし**で確認。診断PRを公開変更としてマージする必要はない。これが証明するのは公開フロントと限定的なAPI動作であり、Renderの**最新版backendデプロイSHA**、実機iPhone Safari、当日公式24/24一致、正式T−12リモート初回保存を証明しない。
- **次の実測**：2026-11-11 08時台T−12のschedule/救済/原本Git初回保存を独立監査。19:35公式展示検証（失敗時19:50台1回だけ救済）→20:15の自動監査で6艇×4値の公式→Render→Pages一致ログ、全受領時刻、LIVE PASSまたは未認定原因を確定。12月10日V1期限を維持。

## 2026-11-10 夜｜公式STの取得・診断パーサを一致させる（既存コード修正）
- **本番ブランチへ最小修正**：`official_preview.py` [`08449539`](https://github.com/ikst2512-eng/boat-edge-clean/commit/084495390f90550112215e7ffc9075283e53a347) と `scripts/verify_real_beforeinfo_source.py` [`0f0a9638`](https://github.com/ikst2512-eng/boat-edge-clean/commit/0f0a9638572b6547cf4a19876199b209912cb73a) の展示ST判定を既存 `scripts/inspect_official_beforeinfo_json.py` と同期。正規値 `F.01`／`L.02`／`.08`／`0.08` を認め、`F01`／`L02`／`F.01x`／`6.999` は拒否。公式監査が有効とする `L.02` をRender側が誤拒否する不整合を修復。
- **回帰テスト追加**：`tests/test_official_preview.py` [`8be832cc`](https://github.com/ikst2512-eng/boat-edge-clean/commit/8be832ccbf38d49bc50c1e87afb3c88e3789415f)、`tests/test_real_preview_probe.py` [`083c7fc4`](https://github.com/ikst2512-eng/boat-edge-clean/commit/083c7fc401e6470e7a57e5bf6b92cd1f1a34858d) に正常4種・不正値の判定を追加。Python `re.fullmatch` の独立正規表現アサーションはPASS。更新されたGitHub main上で4ソース/2テストの保存blobを再取得して一致確認。**関連 [PR #1730](https://github.com/ikst2512-eng/boat-edge-clean/pull/1730) の [Actions #42823715951](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42823715951) は、今回のST修正を含むheadで3+10単体テストをPASS、2026-11-04桐生11Rの保存済み公式JSON・Render応答を同一検証器に通した24値/6艇と不正入力10条件もPASS（LIVE実測ではない）。修正後のRender最新デプロイSHA、当日実レースLIVE 24値PASS、物理iPhone Safariは未確認。**
- **変更していないこと**：Cron（19:35 JST）、24値の公式→Render→実Pages照合基準、予想原本、結果・払戻、既存データ、Web UI構成。新PR・新Cronなし。公式展示の当日ライブ24/24一致は未実測、実機iPhone Safari・正式T−12とは別。
- **次のゲート**：2026-11-11の19:35 JST schedule／watchdog救済runと20:15 JST自動監査で、`LIVE_OFFICIAL_PAGES_E2E_EVIDENCE`／`LIVE_OFFICIAL_PAGES_E2E_PASS` の有無、CSV診断、実測レース・受領時刻・Render/Page公開SHAを照合。合格ログなしなら未達として扱う。

## 2026-11-10 夜｜CSVソース障害と公式展示LIVE 24値の判定を分離（#1727後続）
- **実変更**：[main `8f815b5b`](https://github.com/ikst2512-eng/boat-edge-clean/commit/8f815b5b5570137cf57eff0dbc3f93057b189aad)で既存 `.github/workflows/verify-real-beforeinfo.yml` の**CSVソースプローブ1ステップのみ独立診断**へ変更。過去定期 [#42713908162](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42713908162) はCSVファイルHTTP 404でジョブが失敗していた。今後はその原因を `CSV_SOURCE_PROBE_OUTCOME` とGitHub警告に明示し、CSV障害のみで「実レース公式→Render→Pages 24値が不一致」と見なさない。
- **ハードゲート維持**：実レース `LIVE_OFFICIAL_PAGES_E2E_PASS` の厳密な24値・締切前照合を**非ブロッキングにはしない**（`continue-on-error` は従来どおりPR診断時のみ）。公式ソース未公開、Render不一致、Pages未表示、締切超過、開催対象なしは `LIVE_OFFICIAL_PAGES_E2E_UNVERIFIED` として失敗のまま。Actionが緑でもCSV診断失敗は別表示し、保存・正式T−12の証拠に算入しない。
- **確認範囲**：workflow blob `8e80bae2` のmain保存を再取得。19:35 JSTの**既存Cron維持**、新PR・Cron・採点/予想原本/結果/払戻・本番UIコード変更なし。実LIVEレース24/24 PASSは**まだ0件**、この修正後の該当Workflow schedule/dispatch実測は未実行。11/11 20:15 JSTの有効な既存監査タスクにCSV判定・公式/Render/Pages 24値・受領時刻の別照合を追加、時刻は維持。V1期限12/10維持。

## 2026-11-10 夜｜公式展示LIVE 24値の誤認定防止・監査出力強化（既存Workflow）
- **main `8daf1e2c08ddda8e658af852f224d14a161d82ff`**：既存 `.github/workflows/verify-real-beforeinfo.yml` のみ修正。元の `19:35 JST` schedule、既存 `workflow_dispatch`、比較範囲（公式beforeinfo JSON→Render API→実Pagesブラウザ6艇×4測定値）、締切前PASS条件は維持。新PR・Cron・予想原本・結果・払戻・保存ソースの変更なし。
- **見つかった監査穴**：旧式 `Date.parse(source_audit.beforeinfo.fetched_at)>=deadline` は、日時空欄・不正値で `NaN` となっても条件が偽になるため、`status=ok` など他の条件が揃えば不正な受領時刻を通してしまう。タイムゾーン付きISO 8601で日時が実際に解釈でき、締切より前である場合だけ認める `validPredeadlineReceipt` を追加。空・文字列不正・時刻帯欠落・締切同時刻を拒否し、締切1秒前の小数秒付き正例を許す回帰チェックを既存JSに内包。
- **合格時の再監査性**：`LIVE_OFFICIAL_PAGES_E2E_EVIDENCE` に対象レース、日程締切、公式HTTP受信時刻、Render HTTP受信時刻、Renderの公式ソース受信時刻とSHA256、Pages比較時刻、6艇の登録番号および公式／Render／Pagesそれぞれの展示タイム・チルト・展示ST・進入コースを出力。成功判定 `LIVE_OFFICIAL_PAGES_E2E_PASS` は従来どおり24値全一致かつ締切前のみ。ソース／ブラウザ時刻とGitHubへの予想原本初回保存は別証拠であり、T−12正式認定とは混同しない。
- **その場の確認と未完了**：修正した埋込みJSの構文確認と5種の不正受領時刻・1種の正常受領時刻の回帰判定PASS、GitHubのmainへ反映された同一blobを再取得して確認。関連する既存push監視Actionsは成功したが、`verify-real-beforeinfo.yml` の**修正後・開催中・実レースLIVE E2E実測PASSはまだ0件**。既往の #1727 PR検証 `42820455202` は夜のレース終了後で `NO_STILL_OPEN_RACE_WITHIN_60_MIN` の診断、正式LIVE合格ではない。
- **次の単一判定**：2026-11-11 19:35 JSTの既存schedule実行と20:15 JSTの登録済み監査で、実際のrun event・source/Render/Pages受信時刻・`LIVE_OFFICIAL_PAGES_E2E_EVIDENCE` の全24値、公開SHAを確認。実行なし・対象なし・締切不一致・不完全ソース・API/DOMミスマッチは理由ごとに未認定。実機Safari・正式T−12・予想精度は別課題。

## 2026-11-10 夜｜Pages再実行時の実公開停止を修復・2回目の本番再現に成功
- **発生した本番障害**：[Pages Action #42814644627](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42814644627) の再実行（`run_attempt=2`）が、同じrun ID配下の `github-pages` 成果物二重登録により `actions/deploy-pages@v4` で失敗。公開後ブラウザ検査は全スキップされた。これはGitHub Pagesの再実行設計不備であり、展示や予想の数値不一致と混同しない。
- **最小修正・公開**：`55c67dcfe97d64be5a8f597d4670f5a2cc8f4dfa` で既存 `deploy-pages.yml` の upload `name` と deploy `artifact_name` を同じ `github-pages-${{ github.run_attempt }}` に指定。再実行でも同名競合しない。`1f2f32ec1347c0b3b1cbf2df4de9eefb9cd1e4bb` で共有Pages同時実行 `cancel-in-progress: false` に変更し、データ更新が公開後検査をキャンセルしないようにした。GitHubはアクティブ実行中も最大1つの最新待機実行を扱う。新PR・Cron・予想/データ変更なし。
- **本番E2E実証**：[Pages #42816351420](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42816351420) success。次に [Pages #42816513058](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42816513058) を同じrun IDで**意図的に2回目再実行**、GitHub artifacts `github-pages-1` と `github-pages-2` が明確に別ID・別名で共存。2回目の `Deploy to GitHub Pages` と公開後ブラウザ検査を含むジョブが `success`。失敗した元の再実行条件を本番で再検証した。対応main SHAのRender `dep-dbpgtau417fc739muf4g` も `live` を確認。
- **公開サイトの継続合格範囲**：オリ展4レース×6艇×3項目=72の独立CSV一致、びわこ実CSV6件欠測の「—」表示、桐生公式展示過去原本6艇×4項目=24の保存済み再現、候補/レース選択/4主タブ/結果。公式展示の当日ライブ前締切24値一致、正式T−12、実機iPhone Safariはこの公開復旧で**達成扱いにしない**。

## 2026-11-10 21:12 JST 既存watchdog救済起動の判別可能化・日次監査
- **リリース済みコード**：main `c2822120f379b2af251cf84f756105fda13ce04b`。既存`entry-course-activation-watchdog.py`が独立研究用`research-live-preview-evidence.yml`を救済起動する場合だけ、`workflow_dispatch.inputs.rescue_origin`に`entry-course-activation-watchdog`を指定。T−12・T−2の起動ペイロードは以前どおり。研究元Workflowの`display_title`に`[watchdog-requested]`を表示できるようにし、既存`audit_preview_scheduled_runs.py`に`watchdog_tagged_dispatch_runs`と`untagged_dispatch_runs`の別指標を追加。**タグは自己申告の要求記録であり、保存・Git初回受領・締切前入力の独立証明にはならない。**
- **CI実測**：[watchdog #42813617965](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42813617965) SUCCESS・21単体テスト合格。[研究日次監査 #42813617841](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42813617841) SUCCESS・13単体テスト合格。JST21:11時点の観測はCron`schedule`1件／`workflow_dispatch`5件（すべて新タグ導入前の無印）であり、新しい`[watchdog-requested]`表示の**実稼働中のエンドツーエンド観測は未確認**。次回起動時に別途検証。
- **本番収集との区別**：[T−12研究起動 #42813396811](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42813396811) は21:09 JST時点で`eligible_count=0`/`stored_count=0`、[独立プレビュー #42813405346](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42813405346) は`upstream_candidate_count=0`/`saved_count=0`。11/10保存済み開催日程の最終締切は20:45 JSTであり、21時台は締切前の有効対象が存在しない。Actions成功とレース原本保存の認定を混同しない。
- **時刻設計のオフライン再検算**：11/10保存済み日程13場156Rについて、T−12厳密選択窓（締切−26分〜締切−14分）と既存10分watchdogの名目発火時刻（JST08:03以降、毎時03/13/23/33/43/53）を照合。156/156で理論上の窓との重なりを確認。ある名目発火時刻に該当する最大対象数は6件で、seedの1回10件上限以内。ただしGitHub Cronの欠落/実行遅延、実際の受領とGit永続保存は保証しない。
- **次の判定**：11/11 08時台の実測により`schedule`起動、watchdog-tag救済（あれば）、生データ受領、原本Git初回追加、正式認定を分離して数える。研究原本の上書き・後付け作成なし。

## 2026-11-10 21:12 JST サイト担当：実公開Pages×WebKit 6艇欠測再現PASS
- 新PR/Cronを増やさず、既存 `scripts/smoke_four_mode_mobile.cjs` のWebKit側へ公開GitHub Pagesの実CSVデータ試験を追加。main `1c723a81e5e2a2201e515214fc1da62815c67711`。[Actions #42813366511](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42813366511) SUCCESS、ログ `LIVE_PUBLIC_WEBKIT_SPARSE_EXHIBITION_PASS`。
- 実例 `202611101106`（びわこ6R）：公開Pagesに標準WebKit 390×844・deviceScaleFactor 3でアクセスし、オリ展原本18項目中6空欄→6艇内の「—」6件、値あり12件は保持、`一部欠測：6/18項目`、横はみ出し0pxを確認。APIやCSVのレスポンスをブラウザ上で偽装していない。別にChromium/WebKitで保存4モード・レース切替・オッズ保留/再試行もSUCCESS。
- 既存 #1719 により公式展示JSON→Render API→公開Pagesの締切前ライブ24値照合は実装済みだが、成功した**本当のライブ実レース**は現時点で0件。`verify-real-beforeinfo.yml` の19:35 JST定期診断を2026-11-11夜に実行・調査する作業をこの会話のタスクへ登録。成功ログがなければLIVE実測PASS扱いにしない。
- Renderは上記テスト変更の `1c723a81` がLIVEになったことを確認。その後は別担当の独立研究監査更新でmainとデプロイが進むため、各トークは必ず最新SHAを再取得すること。ソフトウェアWebKit実測は物理iPhone Safariの代替にはならず、正式T−12原本・実測的中率とも別。

## 2026-11-10 21:02 JST 公開スマホ：びわこ6R実CSVの部分欠測表示を独立照合
- **コード修正と公開**：既存 `index.html` の6艇統合オリ展に元CSVの空欄件数を表示し、該当艇の値を `—`、`data-source-value-state=missing` とする（`40f93b55`）。CSV未配信・取得失敗・締切時刻差異とは区別し、欠測＋締切差異は両警告を保持。予想/結果/払戻/CSV原本は未変更。新PR・新Cronなし。
- **公開Pages実証**：[Actions #42811670005](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42811670005) 全ステップsuccess。`202611101106`（びわこ6R）について独立BoatraceCSV 2026/11/10原本の6艇×3項目中6件空欄を実確認。公開390px Chromiumで6艇18欄、空欄6つが `—`、値あり12欄はそのまま、`一部欠測：6/18項目`、横はみ出し0を一対一照合。既存4レース72値、2026-11-10予定156件/CSV156件一致、公式展示過去原本再現24値、欠落4分類、4主タブも同じrunでsuccess。
- **回帰**：[Actions #42811340928](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42811340928) success。欠測のみ・欠測と締切時刻不一致の併発・号艇ごとの値保持を検査。現行mainが別担当のデータ保存更新を受けるため、都度最新コミットを再取得する。
- **未完了**：開催中の公式beforeinfo→Render API→Pages公開ブラウザで6艇×4値を締切前に同時照合する正式LIVE gateは独立実証0。既存 `verify-real-beforeinfo.yml` の19:35 JST定期実行で将来確認（現在結果を先取りしない）。物理iPhone Safari、T−12予想原本、長期API稼働は別判定。

## 2026-11-10 20:58 JST 研究Cron/救済起動の分離監査を本番実行
- **実装main**：`f6c16123ee38ddbb2ee517e6a011b4f8f2834695`。既存`scripts/audit_preview_scheduled_runs.py`に、`research-live-preview-evidence.yml`をJST日付で全ページ確認する*独立*集計を追加。既存`late-preview-capture.yml`の日次監査は保持。研究対象の`schedule`と`workflow_dispatch`を分離し、mainブランチ、実行ID、JST受信日、APIの`total_count`を検査。途中ページ欠落は監査を成功扱いにしない。
- **実行証拠**：[Actions #42811862768](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42811862768) SUCCESS／12ユニットテスト合格。2026-11-10 JST 20:58時点の設定上の5分Cron枠144、観測した`schedule`起動**1件**、`workflow_dispatch`起動**3件**。計画枠との差143件。workflow_dispatchには人手とwatchdog救済が混在し、GitHubイベントだけで帰属を決定しない。毎日全時間が経過すれば予定156枠。Cronの予定は実行保証ではなくGitHub側の未起動原因は未断定。
- **夜間の監視**：既存1日1回`audit-preview-scheduled-runs.yml`を再利用。定期起動の観測数が予定枠の半分未満なら、`RESEARCH_PREVIEW_CRON_SEVERELY_SPARSE`で診断NG（`push`/PRによるテストは警報を上げず、観測件数を出力）。T−12原本や正式認定・的中率を一切生成しない。
- **次の判断**：11/11朝08時台のT−12実行・保存・初回Git証拠監査を優先。直前研究はCron実行数、救済run数、出典別取得件数、締切前原本保存数を別指標で記録。保存0を精度0%と解釈しない。

## 2026-11-10 夜・研究直前データの実起動不足を補う既存watchdog改修
- **現況**：GitHubの独立研究元`research-live-preview-evidence.yml`はCronが5分ごとでもJST11/09にschedule実行2件、11/10 20:41まで1件。起動が不足している事実と、GitHubスケジューラー内部原因の断定を区別。
- **mainに修正済み**：`e9684c3a1f9d70f56d6dccc5205db8ac817068eb`で既存10分watchdogのT−12/T−2救済を維持しつつ、独立研究元も必要時にworkflow_dispatch。追加プレビュー側のAPI障害がT−12/T−2の先行救済を阻害しない。プレビュー側に同一refの同時ジョブ抑止を設定。既存Cronは増やしていない。
- **実行証拠**：[watchdog #42810131813](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42810131813) 20ユニットテストPASS/研究用dispatch発行、[研究元 #42810162379](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42810162379) 実行SUCCESS、[次watchdog #42810195733](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42810195733) は`research_run_recently_started`で重複発行を抑制。
- **原本の実数**：新しい20:46救済実行は`upstream_candidate_count=0`/`saved_count=0`、T−12独立証拠0。11/10 15:37頃のschedule [#42769768447](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42769768447) は研究候補`202611100702`を1件保存、当該runの完全なT−12事前6艇ペアは0。ジョブSUCCESSは保存やT−12正式認定ではない。
- **次の実測ゲート**：2026-11-11 08時台のT−12自動Cron/dispatcherの実行有無、対象レースの締切と受領時刻、Git初回保存を別々に確認。Cron未実行ならmissed、dispatchのみならfallback、原本のfirst-addとソースが欠ける場合は未認定とする。研究収集の丸一日実行数/保存数を日別に集計し、12月10日のV1公開を優先。

## 2026-11-10 20:48 JST サイト本番：13開催場156レースのオリ展原本監査・締切差異表示
- [公開Pagesブラウザ Actions #42810195670](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42810195670) は成功。既存公開ワークフロー内で、2026-11-10の保存日程 `schedule_snapshots/20261110.json` と独立BoatraceCSVの日付CSVを全件照合。予定13開催場・156レースとCSV156行がレースコード一致、欠落レース0。
- これは157件以上の展示値の存在を意味しない。CSV測定対象2,736項目のうち2,638項目は非空欄、98項目は空欄、17レースに欠測。空欄は11場30項目／12場2項目／17場66項目。開催予定にない11場を「非提供」と判定しない。CSV内選手名・レースコード・場番号の一致と値の欠測は別。
- 締切時刻は17場 `202611101702`〜`202611101706`の5レースで、保存日程10:42/11:09/11:34/12:04/12:34、CSV10:44/11:11/11:35/12:05/12:35と1〜2分相違。原本や過去予想を書き換えず、6艇のオリ展実測欄に両時刻と時刻照合不一致の警告を出す最小修正（main `f44b780e`）。別の復旧回帰テスト追従 `7f8467b4` / [#42810271861](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42810271861) success。
- 同じPages Actionsで実レース4/4、24艇×3項目72表示値のCSV完全一致、桐生11Rの公式展示過去原本再現24値一致、4つの欠測/非提供以外のエラー状態分岐、公開24場/12R/4主タブの操作が継続PASS。公式展示は固定された実際の過去保存原本のブラウザ再現であり、当日全レースの実際の公式展示値の証明ではない。
- 対象はサイト表示・出典と検証コードのみ。公式T−12到達、GitHubリモート初回受領、独立予想精度、実機Safariの全保証には用いない。新PR/新Cronなし。

## 2026-11-10 20時台・候補アーティファクト完全走査とT−12研究原本の実照合
- **GitHub mainで実検証：** \`scripts/evaluate_previous_day_late_artifacts.py\` の全repoアーティファクト20ページ打切りを廃止し、信頼する \`research-live-preview-evidence.yml\` の日時指定済みmain/schedule・dispatch実行と、その実行に紐付くアーティファクトを照合。GitHub Actions [#42807166116](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42807166116) SUCCESS、9試験合格。JST 2026-11-09 00時〜11/11 00時の検索範囲に信頼できる実行4、原本4、11/09に適合する保存候補0、欠落/期限切れ/打切り0。確定レース対照は0のため的中率算出不可。5分Cronに比べ実行数不足であり、保存候補0と収集安定を混同しない。
- **研究T−12初回Git追加2件：** \`202611101912\` は20:38締切、20:26基準、初回追加コミット \`2ba3597d\` 記載時刻20:16:55 JST。[実行 #42806151821](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42806151821)。\`202611101212\` は20:45締切、20:33基準、初回追加コミット \`a2597375\` 記載時刻20:23:47 JST。[実行 #42807094674](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42807094674)。Gitの実ファイルは\`added\`、それぞれ不変研究原本に照合。初回コミッター時刻は独立したサーバー受領時刻ではない。両方の予想生成・title/cards受領記録は13:21 JST、ライブT−12公式直前データが取り込めたと証明できない。原本に明記された\`formal=false\`・\`independent_first_seen_verified=false\`を維持。
- **残件・次の実務：** ①11/11の08時台T−12 Cron/dispatch有無、対象レースごとの入力受領・締切・Git初回証拠を照合、②研究用source workflow 5分設定と実行4/48hの乖離を特定、③形式上成功したジョブ件数と実際の保存候補件数を別々に報告。新Cron・旧予想後付け・上書き・未検証モデル本番投入は禁止。

## 2026-11-10 19:53 JST 既存サイトの公開6艇展示・候補履歴の実測アップデート
- ①サイト制作：既存PR #1707・#1703 はともにmainへ統合・公開済み。公開ブラウザで4主タブ、出走表内連対率、11/8候補117件・確定結果・買い目の参照を確認。14日/1698件の日別候補マニフェストはPages配信で生成。
- 公開Actions #42802645236 はsuccess。対象4実レース：202610280101 桐生1R、202610310708 蒲郡8R、202611021905 下関5R、202611031911 下関11R。公開Pagesの6艇カードに表示された独立BoatraceCSVオリ展3項目を、元CSVの号艇別値と全件照合。4/4レース・24艇・72項目一致、ミスマッチ0。公開DOMで公式展示5項目×6艇の配置も確認。ただし公式値と独立ソースの直接比較は別途必要。
- オリ展の元CSVは概ね締切数分前の観測であり、T-12事前入力の正式証拠ではない。非提供場、未公開/通信失敗、全24場、iPhone Safari実機、公式展示の厳密な値対応を未完了として残す。旧予想原本・結果・監査記録・収集ジョブは変更しない。
- main/Render LIVE は19:53 JST時点で 409cce6c09a4ea591c576052197adfa4ebd007c0。READMEの最新引継ぎを更新したため後続コミット/Renderデプロイがあり得る。着手時は静的記録でなくGitHub/Pages/Renderを再照合。

## 2026-11-10 JST UI #1707 本番配信・6艇統合展示の表示検証（公開済み範囲）
- PR #1707をmain `9087b2ea312e966a73440c1e306c1cece8ad5da9` にsquash統合。Render `dep-dbpestjbc2fs73bgjjf0` は同SHAで `live`、Pages公開 `42797423327` は同SHAでsuccess。公開HTMLとnavigation.js、確定結果3件・日程2件のバイト同一性を実確認。既存4主タブ＋出走表内「基本／連対率・展開」、4モード買い目中心、通常展示＋展示進入＋オリ展の6艇別統合と文字縮小を公開。
- PR `42797012956` Chromium/WebKitとも390px幅の6艇×公式5項目＋オリ展3項目、CSVの1号艇=11/12/13・6号艇=61/62/63、展示進入1C〜6C、横はみ出し0px、4主タブ・戻り等をテスト用固定データで成功。正式な当日ソースの完全取得・予想原本認定とは分離。
- Pages `42797423327` の公開ブラウザは過去4レースの出走表6艇・未検証展示の正しい空状態、当日 `20261110-21-01` の4主タブと6艇表示を確認。ただし当該レースの展示は未取得/未検証、保存予想は未作成であり、実データ充足を達成と扱わない。iPhone Safari実機は未検証。
- 同公開診断では候補ページに締切前保存研究予想6件が表示されたが、従来テストが「6レース表示」の文字列を要求したため、現仕様「6レース（70%研究条件...）」を誤ってUNVERIFIEDとした。今回既存の`deploy-pages.yml`診断のみ、先頭の研究予想合計を明示的に抽出して表示件数と照合するよう修正。正式候補や将来実測70%の認定ではない。
- 未完了: #1703保存済候補・予想・結果の全件日付別履歴、実データに基づくオリ展提供/未配信区分、実機Safari、本番公開APIの長期安定性。4モード予想モデル・Git初回原本・収集ジョブ/正式採点は本UIリリースで変更しない。

## 2026-11-10 JST 展示ページ：通常展示＋各場オリ展の号艇別統合（Draft PR #1707）
- 展示ページでは1〜6号艇の同じカード内に「展示タイム／展示ST／チルト／平均ST」と「オリ展の配信計測項目（最大3項目）」を縦に統合。独立したオリ展の6艇一覧は廃止。上部の水面情報・実進入の保存証拠表示は維持。
- `index.html` の `loadOriginalExhibition` は従来のCSV独立ソースを利用。対象レースのコード一致、ユニークなCSVヘッダ、計測数1〜3、6艇すべての計測列の存在を確認してから個別の号艇カードを更新。欠測は「—」、未配信/検証失敗は「オリ展：未取得」、レース切替/タブ移動後の古いHTTP応答は描画拒否。元CSVの取得時刻・T−12保存は未証明として、予想や正式採点に流用しない。
- `tests/site-regression.cjs` の本番関数VMテストで、6艇の一対一の値対応、404、欠落列、古いレスポンス抑止を確認。CLEAN regression checks は `40f0c6c2` と `5bc7d6a8` の実行でsuccess（各完了時点）を確認。main統合・Render/Pagesの公開表示・iPhone実機は未検証。
- この変更と併せて、直前のPR検証で検出したWebKitの再描画時履歴書き換えを `render()` 内で防止。本番の元データ、買い目、モデル、収集ロジックは変更せず、既存Draftのままブラウザテスト待ち。

## 2026-11-10 JST UI・候補研究の表示監査（Draft PR #1707、main未統合）
- ユーザー指示により、4つの上部レースタブ（予想／出走表／展示・直前／結果）を維持し、「連対率・展開」は出走表内の独立サブタブへ移す。BOATERSの情報設計を参考にした比較表と先頭艇切替は残し、固有素材は流用しない。予想タブには4モード買い目と結果の導線を残す。
- 研究用70%閾値は `selection_dual.py` の「1着候補上位2艇の予測確率合計>=0.70」。3連単的中確率70%以上でも、過去の実測的中率70%以上でもない。本日の保存済み研究予想一覧は別経路であり、70%を通過した正式な購入候補の一覧と呼ばない。保存予想と結果の新規履歴表示は `four_mode_forecasts/` と `four_mode_performance/history-10000.json` の既存原本を読み取り専用で照合する。原本のない予想や結果を後付け生成しない。
- `index.html` と `navigation.js` を修正し、WebKit履歴対策 #1706 の `restoreNavigationLocation` と `setView` ガードを維持。 `selection.html` に日付選択・ページ送り付きの参考照合履歴と70%定義を追加。ブラウザ/回帰の既存テスト2種とワークフロー2種を更新。研究予想生成/収集/採点/既存原本/旧repoには変更なし。
- 判定: Draft PR上のコード修正のみ。CIは変更途中の回帰アサーションが古い予想画面仕様を参照して失敗したため更新中。公開Render/Pagesの最新版反映・実機Safari・候補70%の予測校正・正式的中率は未検証。main自動統合禁止。次はPRテストの全成功とmain競合解消、公開前のブラウザ検証、保存原本欠損の正確な表示。

## 2026-11-06 JST 収集・保存最優先監査：CLEAN初回Git時刻ガードをmain適用
- 11/05の基準はCLEAN=111件、4モード=106件（Git tree実列挙）。CLEAN原本111件のGit初回コミッター秒時刻はgenerated_atのサブ秒を区別できず証明未達。既存分類・原本は変更しない。
- 11/06の01時台JST、main Git tree列挙で新規初回保存CLEAN=0件・4モード=0件。07時台からの本収集前につき、新規収集・生成件数は実ログ未取得で未計測。収集ジョブ失敗は観測0件（成功証明ではない）。
- PR #1690 head efe17878f0bb9d729b99a9f32a848bccd4985850 のCI #42058807358 は57件成功（取得と保存はPRイベントでskip）。mainとの間の2コミット38変更ファイルはPRの3変更ファイルと重複0。2026-11-06 JST、squashでmain 489ceb404f67f810a6fe21d6a791b073f5aae1a8へ統合。main push CLEAN CI #42069789862 success（テストのみ）。
- CLEANはステージ済み原本を検査し、実際の次秒を待ってGit commitし、HEAD実コミッター時刻を検査。rebase後に再検査して90秒余裕・append-only・既存T−12ゲートを保持。原本、予想・T−12判定ロジック、UIは不変更。ローカル時刻合格だけで遠隔初見・公式T−12・正式採点を承認しない。
- Render workspace tea-db8svlcs728c73avi3h0 は boat-edge-clean Web service 1件のみ。Render cronサービスは未存在。外部wake-up entrypoint scripts/render_capture_wakeup.pyは実行資源がなく、重複の本番稼働証拠なし。既存GitHub 4モードwatchdogのCLEAN救済ロジックは維持、新cronは作らない。
- 残る実証: 11/06 07:04 JST以降のscheduled/救済 capture run ごとに取得ログ、生成件数、append-only Git first-add件数と時刻、push後remote main継続、失敗内訳を別々に確認。Render autoDeploy完了とmain SHA一致を検査。未証明の保存・採点を成功に昇格しない。

## 2026-11-04 20:15 JST 実証：公式展示6艇＋オッズ120通りがT−12前に揃った1レース
- PR #1628初期head `82e821fdbd7f4b65da00b40a829b19510c00c6b1` の既存CI `41819205922`（event=pull_request）success。下関7R `202611041907`、締切20:25/T−12=20:13に対し、公式beforeinfo JSON受信20:11:46.513411、公式odds HTML受信20:11:55.812353。展示タイム・チルト・ST・展示進入6艇、120通りが全て原本から検証され、both_complete_before_t12=true。桐生12Rは同runで展示未完成、falseのまま。
- Artifact `13315119405` `independent-late-preview-41819205922`（28,215 bytes）を実ダウンロード。ZIP SHA256 `6f5ee2e9ead169dad4bed4b3ed314507ccf3d77c931c12ece0088a6d0ddb1616` をGitHub digestと一致確認、安全展開して既存`audit_joint_official_receipts.audit_pair`で両レースを独立再監査。下関7Rの全7component checks=true、missing_components=[]を再確認。
- ダウンロードしたZIPと再監査JSONは `docs/observations/official_joint_ci_41819205922.zip` / `official_joint_ci_41819205922_recheck.json` に非期限切れのGit原本として保存。最初の20:07手動負例も別名ZIPのまま保持し、成功例へ書き換えていない。
- これはPR実行による2ソースの実測であり、scheduleの無人実行成功ではない。公式出走表原本と最終実進入は別未達のため、full_t12_source_certified=false、forecast_usable=false、t12_eligible=falseを維持。予想原本・買い目・正式採点分母は変更なし。CSV収集独立性を追加した最新headのCIを確認後に統合する。

## 2026-11-04 20:08 JST 継続：公式原本の定期保存接続（PR検証待ち）
- 既存の `Research independent late preview evidence` はCSV原本行だけを保存し、#1617で表示可能になった公式展示JSONを定期保存していなかった。新しいcron/Workflowを増やさず、既存5分間隔ジョブへ公式ソースペア収集を追加。
- `scripts/capture_joint_preview_batch.py` は当日・ソース日程一致・締切まで12分40秒超/1時間未満の最大2レースだけを選定。既存beforeinfo JSON / official odds HTML collector、atomic publish、joint原文再監査、T−12 decisionを再利用。公式JSONから得た締切以外をオッズ判定に使わず、受信中にT−12を跨げばオッズ取得を止める。上書き禁止・symlink root拒否・失敗時もbatch reportを保存。
- 公式取得の失敗で既存CSV処理を止めないよう、公式stepの失敗を一時保持してCSV収集・既存研究archiveを独立に実行し、その後に専用stepでジョブをfailさせる。artifact uploadはalwaysを維持。
- 原本は `official_joint_evidence/` に隔離し、既存artifact（90日保持）に同梱。既存CSV由来late_research_candidates、予想原本、モデル、採点、旧サイト、Render APIには接続しない。source_capture_failedはジョブを失敗させ、候補なし/未完成/取得失敗/完全ペアを区別。完全ペアでも公式出走表・最終進入は別なので full_t12_source_certified=false、forecast_usable=falseを維持。
- ローカル手動実測20:07 JST: 下関7R・桐生12Rの公式JSON2件と公式オッズHTML2件（各120通り）を原文保存、SHA256と原文再監査一致。両方ともT−12前に受信したが展示/STが未完成でcomplete_pairs_before_t12=0。未完成を成功へ昇格しない。summaryは `docs/observations/official_joint_batch_20261104_2007.json`、原文＋manifest9ファイルは同名ZIPへ保存。
- ローカル回帰: batch orchestration7件、CSV paired coverage4件、official joint audit7件成功（計18件）。PR CIと実ジョブartifactを確認してから統合・定期保存の反映を判定する。これは無人オッズ監視#1593の復旧認定ではない。

## 2026-11-04 19:58 JST 継続完了：公式展示補完をRender API・画面で実証
- オッズ記録 #1615 を `b58734f38b818de9ee91505a32489d65744fc592` で統合。exact-head `deeec31428f525229ace9f3d5f5b3ac40dcfb6f5` / CI `41816503204` 成功（27+18+42+9件）。PRイベントの実サンプルも3/3 HTTP200、原応答120通り再検証3、ソース締切T−12相対2。PR/manualを無人実行へ算入しない。最初のPRイベントでCI未起動・mergeable unknownが続いたため、同PRのclose/reopenを1回だけ行い既存CIを再起動。新規重複PR/cronなし。他担当の #1618（14日集計の原応答再検証）もmainに保持。
- 公式展示補完 #1617 は最新head `d3e99714c44981aa895072e2e0fcef51d3055c3c` の6ワークフロー全てsuccessを確認し、`a80cce16a459f117e5cdbd773d023fc13a368cc4` でmain統合。Navigation `41817312504` のChromium/WebKit成功。実ソース検査 `41817312224` job `126531237592` は19:54:39 JST 下関6R（19:56締切）の公式展示6艇・ST6艇を実取得して成功。過去時刻の偽装や未取得の成功化なし。
- Render deploy `dep-dblguhuct3oc73a9dnv0` は `a80cce16` で LIVE（2026-11-04T10:56:58Z）。公開API桐生11R（20:03締切）は19:57:23 JSTにHTTP200・出走表6艇・展示6艇・展示ST6艇・チルト6艇を公式補完で返した。CSVでは当該レース未掲載のまま。公式応答SHA256=78d8b71f24f5addd2fe56b90ee63a4b2beeee95c00ddf2b5c0607f8f90da1b14。HTTP原文・ハッシュを `docs/observations/official_preview_production_202611040111.json` に保存。
- 公開ブラウザで桐生11Rの展示画面を確認。展示タイム6.66/6.68/6.59/6.81/6.63/6.67、ST F.01/F.03/F.06/.08/.03/.06、チルト全艇−0.5が表示。実進入の認定とは別で、UIの「実進入：未取得・未検証」は維持。iPhone Safari実機ではなく公開Chromium＋CI WebKit。
- 同時観測の下関7R（20:25締切）は公式展示が未完成のためpreview=nullのまま、出走表6艇をHTTP200で保持。reason=incomplete_official_exhibition。負例の原応答も `docs/observations/official_preview_production_202611041907.json` に保存。未完成の6艇値を捏造しない。
- 残課題は #1593 の11/05無人3枠の実証、公式T−12の独立証明、4モード元仕様と新規予想の適格保存、旧P0原本独立保全。展示表示復旧や手動/PR実測を、正式予想・予想精度・無人監視復旧と混同しない。予想原本・モデル・採点ゲート・旧サイトは変更していない。

## 2026-11-04 JST 継続：オッズ監視の再検証可能な原応答とT−12区分
- 確認した不足: `sample_race` は120通りのHTTP200を実行時に検証していたが、保存artifactはstate/timestampsのみで、原応答・締切を保存していなかった。後から120通りとT−12を独立に再計算できない。
- 既存 `scripts/probe_live_odds_health.py` に20KB以下のHTTP200原応答をBase64・SHA256で保存。同じレース・120通り・取得日時を原文から再検証し、保存された検証済みフラグを信用せず再計算する。大きすぎる応答・欠損・改変・119通りは再検証件数に入れない。
- `source_deadline_jst` は同レースのソース時刻が一意な場合のみ保存。欠損・矛盾はunknown。締切ソースの受信時刻・digest・種別も保存する。
- 通常のvalid HTTP200件数とは別に `replayable_120_odds_races` と `before_source_t12_races` を出力。後者は原応答のfetched_at≦HTTP完了時刻＜ソース締切−12分を要求する。**非公式ソース締切を用いた相対時刻検査であり、公式T−12認定・正式予想・無人監視復旧認定ではない**。formal=false、formal_t12_certified=falseを明示。既存cron・fallback admission・サンプリング枠・operational verdict・過去artifactを変更しない。
- 手動実測（2026-11-04T19:36:53.852908+09:00、event=local_manual）: 3レース全てHTTP200、原応答から120通り再検証3件、ソース締切−12分より前の受信2件。`docs/observations/live_odds_replay_20261104.json`へ原文・hash・ソース時刻を保存。無人実行成功件数に算入せず、公式T−12認定もしない。
- ローカルodds関連96テスト成功（sampler18件を含む）。PR CI・現行スクリプトの実レース測定とmain統合は後続記録で確認する。#1593の11/05無人3枠の実測ゲートは継続。

## 2026-11-04 19:26 JST 引継ぎ実行：503・トップ締切表示の修正と本番実証

- **統合済み #1606 / main `67173f32b1365419fb1b215a25c7768e6c484ce7`**: Render `/api/signal70-holdout-status` の恒常503を実ログから特定。`bulk_first_add` が浅いGit履歴を拒否していた。Render限定の既存バックグラウンドworkerで固定CLEAN Git URLを `fetch --unshallow --no-tags`、90秒上限・対話無効で補完する。checkout/reset/予想原本変更なし、失敗時の監査停止を維持。exact-head `7a1ade2602976178c8f6824c53eadc0cafaa2074` CIは12成功・1skip。Navigation run `41813248601`、Cross-model `41813248159`成功。既存bulkテストの浅い履歴ガード未追随も修正。
- **本番503実測**: Render `2026-11-04T10:22:02Z` log は `holdout_refresh_finished duration_seconds=27.81 outcome=ready`。HTTP200で later_holdout_days=6、archived_candidates=762、audit_rejected_races=762（全て source_receipt_after_generation）、evaluated_holdout_races=0。過去不適格原本を合格に変更していない。デプロイでcacheが消えるため初回集計中は従来どおり `HOLDOUT_PENDING` 503となり得る。サイト全体の障害と混同しない。
- **統合済み #1610 / main `2f7e88975c2a123de7376fed4e32197e87fe9a50`**: `loadHeldVenues` 成功後に削除済み `loadHomeRaceCards()` を呼ぶ残骸がReferenceError→catch→正常日程消去を起こしていた。呼出1箇所だけ除去。新規画面なし。既存navigation workflowへ、成功日程4レース→次3レース表示・開催場より上の位置を検証する390px Chromium/WebKit試験を追加。CI `41813672504` job `126518904757`: `CLEAN_HOME_SCHEDULE_CHROMIUM_PASS` / `...WEBKIT_PASS`。対象head `6f0e19a2654629622700cf1c5f12a1b6fa50b0ac` は8成功・1skip。
- **本番トップ実測 19:24 JST**: Render deploy `dep-dblgf8ln7bfs7389k6m0` LIVE（10:24:28Z）、commit=`2f7e8897`。実ブラウザで12開催場、開催場の上に下関5R19:30・丸亀10R19:39・大村10R19:48の3件を表示。保存日程が11:40取得のため30分超の古さ警告は残る。iPhone Safari実機は未検証（WebKit試験と区別）。
- **実レース取得**: 19:15 JST 大村9R（締切19:16）で出走表6艇、展示タイム6艇、展示ST/進入/気象とソース別取得時刻・SHA256をAPI応答から確認。ただしT−12ではない。19:22台の桐生10R・下関5R・丸亀10Rは各出走表6艇とオッズ120通りHTTP200、展示は当時not_published_or_unavailable。`docs/observations/production_receipts_20261104.json` は手動read-only観測で、後続raw UTF-8応答とSHA256も保存。無人監視・公式原本・T−12証明として使わない。
- **候補レース**: 19:16 JST実ブラウザで締切前18件を検査、表示安全条件を満たす保存済み研究予想0件。空欄のUI故障とは区別。時刻逆転原本を修正して埋めない。11/05の新規scheduled保存・初回Git・遠隔初見・候補DOM検証が必要。
- **#1593 無人監視**: public Actions RESTでevent=schedule履歴4件全件を確認。最新11/03 `41624217156`、11/04直接scheduleは0件。workflowはactive。PR/manualの成功を監視成功に数えない。既存#1603等の修正を重複実装せず、既存11/05 12:25/14:25/16:25 JST（各90分猶予）の実行・artifact実sample検証を継続。新規重複cron/automationなし、復旧未認定。
- **#71/#958/#294 4モード**: 現行アーカイブ120件を既存`four_mode_historical_cohort.run()`でread-only再集計。Top3/5/10件数: 絞り18/30/30、本命18/30/46、バランス19/29/45、穴2/4/13。`formal=false`、歴史研究であり独立前向き精度ではない。厳密点数の元合意は追加検索でも未回収。`絞り < 本命 < バランス < 穴`と矛盾する5/30/20/12を勝手に正とせず、復元未完了。原本・モデル不変更。
- **#708/#329 移行**: 既存artifact `13280103552` / run `41738920306` のZIPを再ダウンロード・解析。SHA256=`a8434d92a9eaf27363c7e36ad50b83b53b1ccd06a6d348e026cac619af38fd19`、matched1200 / compared124 / uncomparable1076 / unresolved0 / copy_authorized=false / delete_authorized=false。P0 5,578原本の独立保全・復元は未達。旧repo・書込・Pages停止/削除なし。
- **競合保護**: main進行中の#1607/#1609を維持し、用途別worktreeとSHA固定PRで作業。#1560/#1563のAI修正Draft、#1559保全Draft、#1558/#832等の研究PRは未統合のまま保護。#722と#832は旧/代替関係であり両方を機械的に統合しない。古いブランチの強制push/閉鎖なし。
- **次の最優先**: 11/05新規収集・無人オッズの実証、T−12で展示を取得できる範囲の確立、4モードの元仕様回収、P0原本の独立復元。正式採点ゲート・予想原本・既存証拠は維持。

## 2026-11-04 JST サイト担当：当日候補「保存済み原本」と「公開描画」の切り分け（PR・公開検証待ち）
- 16:25:42 JSTの開催日程 `schedule_snapshots/20261104.json` では締切前40レース、候補UIが先に照合する締切順18レース中、保存済み研究予想JSON存在16件／404が2件。16件はいずれも3連単10点・研究候補で、正式予想として採用しない。
- **重要な時刻証拠のギャップ**: 16件の `generated_at=2026-11-04T11:01:33.627045+09:00` が `source_cards_received_jst=2026-11-04T11:01:33.766393+09:00` より約0.139秒前。従来のUIは `recordedBeforeInput` 警告付きで表示し得るが、入力後生成を証明できず「購入候補が16件ある」「予想精度が検証済み」とは扱わない。原本・初回Git時刻は書き換えず、別担当のPR #1571／#1569と競合しない。
- `/selection`のHTML存在と、実際の予想カード描画は別。既存Pages公開ワークフローに **任意診断** を追加し、公開Render候補ページの実ブラウザ390pxで表示カード数、警告、保存済み買い目表示、JS例外をログ・step summaryに独立記録。外部データの取得失敗時はUNVERIFIED、ゼロ件の場合も成功した候補数に計上しない。
- 変更は既存 `.github/workflows/deploy-pages.yml`、`tests/site-regression.cjs`、本ステータスのみ。新規ワークフロー・予想生成/原本/収集/holdout監査/旧サイト変更なし。公開実測の後に件数と本番確認を追記。

## 2026-11-04 JST サイト担当：公開Pagesの「候補レース」導線をブラウザ実証（PR #1577）
- 最新main `a820c42d`、Render同commit LIVE。候補ページとトップへの修正PR #1576を維持。
- 初期調査でroot相対 `/selection` と `/review` がPages上で不正に見えたが、既存 `navigation.js` がPages時に前者をRender `https://boat-edge-clean.onrender.com/selection`、後者をPagesの `screen=review` へ正しく置換する実装を確認。HTML直接書換は `test_navigation_contract` に違反していたため破棄（main未統合）。
- PR #1577は既存 `deploy-pages.yml` の公開390pxブラウザ検証で、上記2リンクの**JS初期化後**の移動先を確かめ、候補ページのHTTP200と候補領域HTMLを照合する検査に切替。予想/原本/監査API/旧repoの変更なし。
- CI・公開実ブラウザ証拠・Render反映前は完了判定しない。旧サイトの削除/停止は引き続き禁止。

## 2026-11-04 JST サイト担当：候補レース・トップ開催場表示の実用復旧（PR検証中）
- ユーザーが、候補レースに実際の買い目がなく、トップページの締切前3レース・開催場が見えないと報告。既存`selection.html`は当日候補を固定「未確認」とするだけで、実際の`prospective_predictions`へ一切接続していなかった。11/4当日の日程保存ファイルと研究予想JSON多数がmainに実在。
- 既存`selection.html`の候補セクションから、その日の日程スナップショット（失敗時CLEAN schedule API）を読み、まだ締切前のレースの保存済み研究用3連単1〜10点を日程時刻順に最大6件表示する。生成日時、ソース受信日時、締切・レースID、非正式・採点不可の保存条件を確認し、時刻逆転／Git初回登録未検証は明示。**予想の正式認定・購入推奨・確率捏造は行わない**。レース詳細タブへの遷移リンクを付加。
- `index.html`にホーム「開催場・締切」への明示的な戻りリンクを配置（GitHub Pages・Renderで共通に動くRender URL）。日程GitHub Raw取得が404以外のHTTPエラー・ネットワーク失敗でもCLEAN schedule APIへフォールバックして、開催場や次3Rを空欄のままにしない。既存サイトの単一ページ・4タブを維持。
- サイトUI3ファイルのうち現状修正は`index.html`、`selection.html`、既存回帰テスト`tests/site-regression.cjs`のみ（`navigation.js`非改変）。旧repo、予想生成・原本・収集ジョブ・旧Pagesは非改変。今後はCIと公開ブラウザで今日の買い目・3R・開催場の実際の可視性を検証。実機Safariは未検証。

## 2026-11-04 JST サイト担当：未検証展示の誤表示文言を是正（CI・本番検証は別途）
- 11/4 芦屋1Rの公開ブラウザ実測では展示用6艇カードは描画されたが、直前の6艇・締切前の測定記録が未検証。`index.html` 内に展示がないとき「CLEANの直前データ収集が未実装」と断定する古い文言が残存。一方、`clean_racecard.py` には締切前の元データ取得・6艇完全性ゲートが実装済み。**未取得と未実装を混同する誤表示**。
- 展示ソースそのもの・予想・原本・取得時刻・判定・API処理は変更せず、画面説明を「当該レースの締切前6艇分の記録を検証できていない」「数値を推定表示しない」へ変更。既存サイト退行テストに古い断定表現の再発防止を追加。
- 旧repoと旧Pagesは維持、原本削除なし。PR/CI/Pages/Renderの後続結果を確認してから本番反映完了とする。

## 2026-11-04 JST サイト担当：実開催日の公開Pagesブラウザ観測を既存ワークフローへ追加（PR #1565）
- 未完了ゲート: 当日レースのRender API HTTP200（例：2026-11-04 桐生1R・芦屋1R）は取得済みだが、同じ当日レースの公開Pages 4タブ実ブラウザ表示は未証明。既存Pages成功run #41684583216 は保存済み過去レースの4タブ・結果・390px Chromiumを検証済み。iPhone Safari実機の証拠ではない。
- 新しいワークフローを増やさず、既存 `.github/workflows/deploy-pages.yml` に当日JST開催日程→Renderの同一レース6艇HTTP200確認→公開Pagesで選択レース一致・6艇カード・4タブ切替を観測する**診断ステップ**を追加。外部取得源が未公開・障害の場合は `UNVERIFIED` と実行サマリーに明記し、診断失敗だけでは既存Pagesの過去レース公開試験を失敗にしない。
- PR #1565 head `5b4badacb3495b73cacbbd614ec42fa1af1f7e1a` の公開スモーク／チェックCIは成功。現時点で当日実ブラウザの `VERIFIED`、iPhone Safari実機、予想・展示・結果データの全件実証は**未取得**。PRのmain統合と公開後の当該診断ログを確認して結果を追記する。
- 予想モデル・精度検証・原本・旧repo・旧サイト・旧scheduled workflowsは未変更。旧サイト停止は独立原本保存・復旧・公開同等性を証明するまで禁止。

## 2026-11-04 JST サイト担当：部分開催日程で出走表を誤って遮断しない（PR準備）
- 既存PR #786の開催場・レースピッカー修正はRender `40f4c8ed` live。今回の読取では当日2026-11-04の `schedule_snapshots/20261104.json` はmainに存在せず、Renderの `/api/clean-schedule` 200 と住之江1R/5R `/api/clean-racecard` 404 を記録。API 200だけで全開催の完全性・住之江開催有無は断定しない。
- `index.html` の `loadRaceData` が `partial_coverage!==true` だけで存在しないレース扱いしており、選択ガード側が除外している `historical_result_only===true` の部分的な結果復元まで誤遮断する不一致を確認。すでに導入済みの共通 `completeHeldSchedule()` を出走表経路でも使い、事実未確認で404扱いや「開催なし」表示をしない。
- 前後レースの矢印を既存の選択制限に合わせて無効表示し、日程の非同期読込後にも更新。既存4タブや予想・原本・検証・旧サイトには変更なし。
- 既存`tests/site-regression.cjs`にこの共通ゲートと矢印の退行検査を追加。PR CI・公開Pages/Render実ブラウザ確認は別途判定する。

## 2026-11-04 JST サイト担当：既存PR #786の競合解消と開催場選択の安全ガード（レビュー中）
- Render My WorkspaceでCLEAN main `d88fa2e` がlive、HEAD/GETルート200を確認。これはレースAPI全件正常の証拠ではない。
- 既存draft PR #786は旧mainとの競合があり、そのまま統合できないため、同じPRブランチを元コミットを保存したmerge commitで現行mainへ追随。現行`index.html`で全件確認済み開催日程の場合のみ、非開催場・非開催レースを選べないようにする。日程の一部取得・過去結果からの復元・未公開・取得失敗は選択可能のままとし、存在しないデータを作らない。
- 対象は`index.html`と既存`tests/site-regression.cjs`のみ。予想モデル、原本、検証、旧リポジトリ、収集ジョブは変更しない。
- PR CIと公開ブラウザでの同一レース4タブ動作・iPhone Safari実機・旧サイト移行ゲートは完了判定前に確認。PR作成だけを本番修正完了とはしない。

# BOAT EDGE CLEAN — 作業引き継ぎ / WORK STATUS

更新日: 2026-11-01 (JST)
この文書は会話をまたぐ運用上の引き継ぎ。下記の「過去会話による報告」は今この文書を作成した時点での本番再検証を意味しない。実際のGitHub/CI/Render/公開URLの状態を調べ、確認できた証拠で更新する。

## 2026-11-03 オッズ代替起動のPR由来in-progress誤抑止修正
- PR #1439をmainへsquash統合（`eabadf9520ca543ec16bb2c1c611d3e8a6e8329a`）。`scripts/gate_live_odds_event.py` の prior_fallback_guard が、運用対象と別concurrency groupで実行中のPR由来no-opを無条件に「先行監視あり」としていた問題に対応。既存の #1424 の operational-group直列化を前提に、未完了runを重複成功証拠として扱わず、完了runの有効HTTP200 artifact検証は維持。
- `tests/test_gate_live_odds_event.py` の回帰ケース更新と、in-progress no-opの後ろにある完了済み有効fallbackを検出する新規テストを追加。PR CI `41635745512` / job `125916357820` success（PRイベントであり無人監視成功には算入しない）。
- 2026-11-04 12:25/14:25/16:25 JSTの実際のschedule・fallback・有効HTTP200・二重計上は未実証。既存18:00 JST自動監査（ID `6ae9b1a3021481919940f077e05cf620`）は有効。独立Render Cron Jobは未作成、追加料金発生なし。
- 次の最優先: 11/4実測で3枠の時間内起動、GitHub代替起動、HTTP200、artifact、重複を確認。独立スケジューラの導入は遅延再発や費用判断を踏まえて別途行う。

## 2026-11-03 オッズ監視の直接PR・手動起動を定時監視キューから分離
- PR #1444 を main にsquash統合（`0b5a632e468906b038ae35a5934037054ff6c993`）。既存 `.github/workflows/live-official-odds-probe.yml` では、前回 #1424 で上流PR/push-origin workflow_run は分離済みだったが、同workflowの直接 `pull_request` と `workflow_dispatch` は通常schedule/正規fallbackと同じconcurrency groupに残っていた。PRや手動実行の増加による定時監視遅延リスクを低減するため、それぞれ固有run IDの独立groupに分離。
- 正規 `schedule` と上流schedule由来 `workflow_run` は同じoperational groupを維持し、`queue: max` と `cancel-in-progress: false` を維持。既存 `tests/test_gate_live_odds_event.py` にPR/手動分離アサーションを追加。
- PR CI `41636820914`, job `125919997271` 結果success。**これはPRイベントの成功であり無人監視成功としては計上しない**。11/4の12:25・14:25・16:25 JST実起動と有効HTTP200/artifact/重複なしの実証は引き続き未完了。Render有料Cron Jobは作成していない。
- 11/4 18:00 JST既存の自動監査タスクにより実レースで監視する。次の変更は実測エラーに基づく最小修正のみとする。

## 2026-11-03 オッズHTTP試行時刻の原本保存を強化
- PR #1457をmainへsquash統合（`aa89335932f33bd7da29f55b63b9dec16ba155dc`）。`scripts/probe_live_odds_health.py` の各HTTP試行に、UTCタイムゾーン付きの `started_at_utc` と `finished_at_utc` を追加。HTTP 202/timeoutの再試行も各試行ごとに保持し、実際の取得時刻とワークフロー起動時刻を分けて照合できるようにした。既存 `http` / `state` / `latency_ms` / 判定 / 再試行回数は変更なし。
- `tests/test_probe_live_odds_health.py` に時刻の範囲・UTC・前後関係と202→200の各試行時刻の回帰検査を追加。PR CI `41639712885` job `125929823560` success（テスト16+14+34+5件。PR実オッズHTTP200は2/2、ただし無人取得成功には計上不可）。
- 旧artifactは試行単位のUTCタイムスタンプを持たないため、過去の取得時刻を推定・捏造しない。11/4 12:25/14:25/16:25 JSTの新しい無人schedule/正規fallbackだけ、artifact内試行時刻・event・上流created_atを照合して時間内監視と有効HTTP200を別々に監査する。
- 別系統のRender Cron Jobは作成していない。実運用の定時起動復旧は未実証。

## 2026-11-03 オッズHTTP時刻証拠の整合性監査
- PR #1460をmainへsquash統合（`27a683b4e5904c90f1ffca90e0fadd06cb2005a9`）。PR #1457で追加した `started_at_utc` / `finished_at_utc` は保存済みだが、監査の共通 `consistent_attempts` では未検証だったため、既存の共通判定処理で全試行の時刻フィールド完全性、UTCタイムゾーン、開始<=終了、再試行間の時間順序を検証するよう変更。不完全・矛盾データを有効HTTP200の監査証拠として採用しない。
- 旧artifactのタイムスタンプ無し試行はレガシー記録として従来どおり評価対象。ただし精密な時刻を証明する資料ではないことを維持。
- 回帰試験で時刻欠落、時系列重複、逆転、非UTC、無効形式、旧形式受理を確認。CI run `41640266343` / job `125931722696` success（既存/追加72件のテスト成功、PR実測オッズ2/2 valid_200）。**PR実行は無人起動成功に算入しない。**
- 11月4日の実schedule/正規fallbackの時刻内成功・artifact原本・二重計上なしの確認は引き続き未完了。費用を伴う独立Render Cronは未作成。

## 2026-11-03 オッズ試行時刻と監視実行開始の照合
- PR #1464をmainへsquash統合（`ef22fe6f52d08c010c8359aaa9df29623df74f06`）。前回のHTTP試行UTC時刻の整合検証に加え、新形式の試行開始・終了時刻が記録全体の `checked_at_jst` に結びつくことを共通 `consistent_observation_times` で確認する。過去runのHTTP200を別のrunへ取り違えて成功扱いする誤監査を防止。既存の履歴・厳格な運用判定・fallback重複判定の3経路に適用。
- 監視開始時刻から1分前〜60分後を許容境界とし、日付・タイムゾーン矛盾、別runのHTTP試行は除外。旧保存成果物に時刻項目が完全にない場合は従来どおりのlegacy観測として維持し、正確な時刻内カバレッジには使用しない。
- PR CI `41640853800` / job `125933713506` success。16+14+39+5件のテスト成功、PR実測HTTP200は2/2。**PR実行は11/4定時監視の証拠に算入しない**。GitHub自身のschedule起動遅延は引き続き未実証・未解消。
- 11/4 12:25/14:25/16:25 JSTの実運用で、実起動時刻、HTTPの実取得時刻、有効200、各監視枠のcoverage、代替起動の二重計上防止を確認する。新しいRender Cron Jobは作成していない。

## 2026-11-03 22:14 JST オッズ監視cron登録の更新（実行数・時刻は不変）
- 直近の14日保存監査では、対象の直接schedule監視10枠のうち90分以内の発火確認0枠。PRテストでの有効HTTP200は確認されているが、PR実行は無人監視成功として計上しない。
- GitHub公式では、定時ワークフローが停止してもworkflow_dispatchは動く場合があり、write権限を持つユーザーによるcron構文の変更コミットがワークフローを再有効化することがあると説明。今回の原因がactor停止だったと確定したわけではない。
- PR #1469 をmainへsquash統合（`ea405fe7d0d58cdf5955d8339b6b245015456de9`）。`.github/workflows/live-official-odds-probe.yml` の一つのcron `25 3,5,7 * * *` を、同じ3時刻の `25 3 * * *` / `25 5 * * *` / `25 7 * * *` に分割。起動時刻・回数・queue・代替起動条件・API/保存方式は変更していない。既存テストに監視時刻の不変性を明示するチェックを追加。
- 初回PR CI run `41642430787` は新規テストの正規表現エスケープミスで失敗したため修正。再実行CI `41642522805` / job `125939365698` はsuccess、テスト17+14+39+5件、PR実測HTTP200は1/1。**PRの成功は本番定時復旧の実証ではない**。
- 次: 2026-11-04 12:25/14:25/16:25 JST の実際のschedule run ID、作成時刻、HTTP試行時刻、artifact、90分以内カバレッジ、fallback・重複を直接監査。失敗継続時はGitHubに依存しない起動経路を検討。Render Cron Jobは毎月最低$1の有料サービスのため、現時点で未作成。

## 2026-11-03 22:21 JST オッズ監視の採取優先化
- PR #1474 をmainへsquash統合（`2a35e765ca5faea3c6c8a9073250205e13069eb4`）。定時schedule/正規上流fallbackの8分制限で、従来は回帰テスト4群を実行してからHTTP採取、14日履歴収集後に厳格な運用判定を行っていた。この順序では検査やGitHub履歴APIの遅延が締切前のHTTP測定・判定を妨げるため、イベントゲート→HTTPサンプル採取→無人イベント厳格判定を最優先に変更。
- 回帰テスト4群はPR/手動QAのみ実行し、定時・正規fallbackでは実施しない。既存の履歴集計はその後で実行し、`if: always()`の原本artifact保存は維持。**GitHubのcron発火時刻そのものの問題は本変更では解決できない**。
- 初回PR CI `41643399710` は追加テストの改行表現誤りにより失敗し、修正後CI `41643529189` / job `125942790872` はsuccess。回帰試験18+14+39+5件、PR HTTP200 1/1を確認。PRは無人監視の分子に含めない。
- 2026-11-04 12:25/14:25/16:25 JSTの本番検証では、schedule/fallback eventの発火と、起動後HTTP試行が診断テストより先に実施されることを別々に検証。Renderの独立Cron Jobは未作成・追加費用なし。

## 2026-11-03 22:26 JST 無人オッズ監視失敗時の履歴証拠保存修正
- PR #1481をmainへsquash統合（`d8268ae3138917f4dc834475317315135a8ca84e`）。直前の #1474 によるHTTP採取→厳格判定の先行処理後、厳格判定が失敗するとGitHub Actionsの暗黙の`success()`条件で14日履歴集計がスキップされる不具合を修正。
- 既存の`.github/workflows/live-official-odds-probe.yml`で履歴集計に`if: always() && steps.gate.outputs.collect == 'true'`を指定し、**無人の無効HTTP/取得失敗でも履歴比較を作成**する。厳格な無人HTTP200判定失敗はそのまま赤（失敗）を維持し、PR/手動QAの実行条件、always raw artifact保存、cron時刻3枠は不変。
- CI run `41644291458` / job `125945428231` はsuccess。テスト19+14+39+5件成功、PR実測HTTP200 1/1。ただしPRは本番無人監視のカバレッジに算入しない。**実際に失敗した無人ジョブで履歴成果物が残ることは未実証**。
- 11月4日の無人実測は、schedule run created_at、HTTP開始/終了、厳格な判定、raw odds metricsと14日履歴artifactの有無を、成功・失敗にかかわらず照合する。Cron起動遅延そのものは未解決、独立Render Cronなどの有料ジョブは未作成。

## 2026-11-03 22:35 JST オッズ14日間履歴集計の時間上限を追加
- PR #1484をmainへsquash統合（`1e652e4295ed6da5a90059e6e77cba12f984f8a8`）。オッズ無人監視のジョブ制限`timeout-minutes: 8`に対し、任意の14日履歴集計は最大250件の過去run成果物をGithub APIで確認し、期限超過すると後続の`if: always()` artifact upload自体がジョブ打ち切りで実行できないリスクがあった。
- 既存履歴集計コマンドのみ`timeout --signal=TERM --kill-after=5s 60s python scripts/summarize_live_odds_history.py`に変更。履歴集計がタイムアウトした場合は明示的に失敗させ、後続の常時アップロードステップによる`live_odds_metrics.json`原本保存の機会を確保する。履歴監査を成功したことにはしない。監視の先行する厳格HTTP200判定・cron時刻・代替起動・収集APIは不変。**ジョブ全体の8分上限による証拠欠落可能性は完全には排除できない**。
- PR CI run `41645484616` は従来回帰テストがコメント全文固定チェックを行うため失敗し、コメント変更に依存しないテストへ改善して再実行。`41645584262` job `125949925323` success、20+14+39+5=78件の回帰テスト成功、PR HTTP200は1/1（無人定時起動成功には含めない）。
- 11/4の実測では無人schedule/正規fallbackの成功・失敗runから、開始時刻、HTTP証拠、履歴ステップの実行時間、タイムアウト失敗時のartifact有無を確認。Render有料Cronは未作成。

## 2026-11-03 22:45 JST 過去日の開催場表示フォールバック拡張（P0）
- PR #1488 main統合（`2094545487ddf4ce0fda4b400946f4fbdadb9b43`）。`index.html`の`loadHeldVenues`で、GitHub Rawの日付別`schedule_snapshots`取得が通信例外やHTTP 403/429になると、**過去日でも既存のCLEAN日程API→日付一致の結果CSV開催場復元へ進まない**コード分岐を修正。過去日に限り、アーカイブの通信エラーまたは任意の非OK HTTPレスポンスで既存の代替経路を試す。正規アーカイブ200優先、当日/未来の404未公開表示・結果混入防止・予想締切前判定は不変。
- 既存`tests/site-regression.cjs`を更新し、GitHub Rawの通信障害・403/429・5xxで過去日の代替分岐が存在することを静的に確認。PR CI `41646893137` のcheckとpublish-smoke成功、`41646893036` のnavigation-contractとbrowser-pr-smoke成功。ほかにDaily findings/official odds/cross-model/dual verification/entry-orderのPR checksも成功。CIは**公開本番ブラウザの実測ではない**。
- RenderでこのPRコミットに対応したデプロイ成功、本番APIとPagesの公開画面実機確認は別に行う。2026-10-31等の過去レースで開催場→出走表→予想→結果が通し表示されるか未実証のため、P0は完了扱いにしない。
- 旧リポジトリ`boat-edge`削除なし。現在確認されたRender workspace内Webサービスは`boat-edge-clean`1件で、現行フロント主要API・スナップショット通信先はCLEAN系。旧GitHub Pages/外部リンク/古い資産の参照関係が完全に除去済みとはまだ確定しないため、破壊的な整理は保留。

## 2026-11-03 22:56 JST 公開Pages P0過去レース実ブラウザ検証・公開ジョブ修復
- 10/31蒲郡8R（race `202610310708`）のGitHub main原本に日程 `schedule_snapshots/20261031.json`、研究予想 `prospective_predictions/202610310708.json`、確定結果 `confirmed_results/202610310708.json` が存在。予想は研究・未検証・正式採点不可。確定結果原本は`1-4-6`。
- Render実リクエストログに2026-11-02 UTC 11:24以降、同日程API、蒲郡8R `/api/clean-racecard`、`/api/four-mode-archive` のHTTP200履歴あり。HTTP200単体は描画証拠ではない。
- PR #1488のPages本番公開run `41647288225` は、deployと公開ファイルのバイト同一性チェックが成功し、**公開ブラウザ**の10/31研究予想注意、6艇の出走表、展示の未検証状態表示、確定結果`1-4-6`の全検査に成功。しかし最後の`Browser-check deployed page`が`shortcuts.locator(...)`を用いてボタン内に別のボタンを探す誤セレクタで30秒タイムアウトし、ワークフロー全体はfailure。
- PR #1493をmainへsquash統合（`d579caaf1029035b5a6de48ea59270b97d393d1e`）。既存`.github/workflows/deploy-pages.yml`の公開ブラウザ4タブ操作を`page.locator('.race-detail-shortcuts button[data-race-view="'+view+'"]')`に修正し、`tests/site-regression.cjs`に退行防止チェック追加。PR CI run `41648593757` のsite-regression/checkとpublish-smokeが成功。
- main push後の**実Pages公開run `41648715496` / job `125960842659` がsuccess**。GitHub Pagesへdeploy、公開HTML/JS/確定結果2件のバイト同一性検証、公開Chromiumブラウザ上で10/31蒲郡8R研究予想（時刻証拠未検証表示）、6艇出走表、展示の未検証状態、確定結果`1-4-6`、4タブの実操作、390px幅のナビ検査が全て成功。10/27の確定結果`1-2-5`も公開ブラウザで成功。公開URL `https://ikst2512-eng.github.io/boat-edge-clean/?date=2026-10-31&venue=07&race=8&view=forecast`。
- **P0の過去レース表示は当該サンプルで本番実証成功**。全過去日・全24場についての可用性や、展示値の独立した事前取得証明は未実証。正式予想の初回Git受信時刻・的中率も引き続き未検証。旧リポジトリの削除は依存調査完了前なので未実施。追加料金・追加Pages workflowはなし。

## 2026-11-03 22:58 JST 旧サイト参照の限定監査（削除なし）
- 現行`index.html`と`server.py`を検査し、`github.com/ikst2512-eng/boat-edge`（末尾に`-clean`が付かない旧リポジトリ）や旧GitHub Pagesへの実際のURL参照は今回確認した範囲では見つからなかった。`index.html`には旧互換の選択UI DOMに関するコメントがあり、依存・利用状況確認前に削除しない。
- Render workspace `tea-db8svlcs728c73avi3h0`のサービス一覧で、Webサービス`boat-edge-clean` 1件を再確認。GitHub Pagesの現行公開先は`https://ikst2512-eng.github.io/boat-edge-clean/`で、2026-11-03 main push Pages run `41648715496` が成功。
- これは**現行フロント/サーバーの限定的な旧URL参照監査**であり、全ブランチ、別サービス、外部ブックマーク・DNS・外部参照元まで旧サイト依存がゼロと証明したものではない。旧リポジトリ`boat-edge`と互換DOMの破壊的削除は引き続き行わない。

## 2026-11-03 23:17 JST 過去日・前日・複数会場の公開Pages実証（P0）
- PR #1497をmainへsquash統合（`a191f382ab1b4d13fc7f0c6ad1b8ccc41e021ba1`）。既存Pages公開ワークフローの実ブラウザ検証を、2026-10-28 桐生1R `202610280101`、2026-10-31 蒲郡8R `202610310708`、2026-11-02 下関5R `202611021905`に拡張。GitHub本体に日付別の研究予想10点と確定結果原本が存在することを個別確認。結果はそれぞれ4-1-3、1-4-6、1-3-4。研究予想は未検証・正式採点対象外、結果から予想を再生成しない。
- 初回main Pages run `41651237227` は公開ページ・3レースの研究予想の未検証警告・6艇の過去出走表・展示の未検証状態のブラウザ検査まで成功。しかし結果JSON `202610272301` のPages一時HTTP503で結果チェックが失敗。失敗runの単純な再実行は同名`github-pages` artifactが2個作られ、deploy-pagesが二重artifactを拒否したため不可。
- PR #1502をmainへsquash統合（`af5098d100b23bfb148598d60c064a2e2d56c4b2`）。既存Pages公開ジョブの**結果JSON配信検証だけ**に429/500/502/503/504対象、最大4リクエストの短い再試行を追加。404・結果相違・取得失敗は不合格とし、別ソースへのすり替えなし。PR CI run `41651731854` の静的チェック・公開ブラウザ相当スモーク双方success。
- 新規main push Pages run `41651910901` / job `125971983717` は**complete/success**。実際の公開URL `https://ikst2512-eng.github.io/boat-edge-clean/`でHTML/JS/確定結果原本のバイト一致、3レースそれぞれの研究予想未検証表示・6艇出走表・展示の未検証状態・確定3連単4-1-3/1-4-6/1-3-4をChromiumブラウザで検証成功。既存10/27の結果1-2-5の表示と全4タブ操作も成功。PR CIを本番証拠に代用せず、main pushの実Pages検証を正本とする。
- この3レースは歴史的出走表・研究予想・結果の表示成功実例。**全24場/全日/当日レース、iPhone Safari実機、展示測定値の独立した締切前取得、正式的中率は未実証**。次の最優先は当日/前日の非表示再発例を別途確認し、旧サイト/互換DOMの不要資産は利用箇所を証明してから安全に整理する。旧リポジトリ削除なし、新規ワークフロー/有料サービスなし。

## 2026-11-03 23:37 JST 当日締切済みレースのP0表示修復・公開Pages実証
- 11/3下関11R（`202611031911`）のGitHub原本に当日日程、研究予想10点 `prospective_predictions/202611031911.json`（`formal=false`, `validated=false`）、確定結果 `confirmed_results/202611031911.json`（1-5-3）が存在することを確認した。当初Pages本番run `41653231507` では研究予想注意文を表示できたが、出走表6艇が0件。Render log `GET /api/clean-racecard?hd=20261103&jcd=19&rno=11` HTTP422。原因は`clean_racecard.py` が過去レースを日付が昨日以前かで判定し、11/3の22:20締切後も23時台に締切前証拠を要求する誤判定だった。
- PR #1513をmainへsquash統合（`1fc55a544eac01452b15e73c9296f68a219760ee`）。レースの確定締切時刻と現在時刻を比較し、**当日でも締切後は`HISTORICAL_READ_ONLY`、`historical_reference_only=true`、`scoring=false`** とする。取得した出走表を締切前に取得済みと偽装しない。`tests/test_preview_completeness.py` に締切直前/同時/直後/翌日/タイムゾーンなしの境界テストを追加。ナビ契約、6艇パーサー、代替feed等のPR CI成功。Renderデプロイ `1fc55a54` live確認。
- 公開判定を強化したPR #1516をmainへsquash統合（`227472997352b27ac221e9451ab36203c8e8396f`）。Pages公開ブラウザの11/3下関11R出走表テストで`verifiedRaceCache`に受理された現物を読み、HISTORICAL_READ_ONLY/正式採点不可/締切前取得未証明を必須確認。最初の本番run `41654514126` は10/31蒲郡8Rの出走表が一時取得失敗し、下関11R確認前に終了。
- PR #1520をmainへsquash統合（`9a8d343c34791ca198fd35ed9f327c78edbebf26`）。既存`index.html`の`loadRaceData`でRender出走表APIの通信例外/HTTP429/500/502/503/504のみ最大3回の短い再試行を導入し、非同期レース切替のtoken/同一race keyを毎回チェック。404/422・証拠不正・6艇不完全は許容しない。PR初回CIは静的テスト抽出範囲ミスで失敗、修正後CI run `41655232585` のcheck/publish-smoke成功。
- **main push Pages本番run `41655377223` / job `125984145558` complete/success**。GitHub Pages公開URLのChromium 390px幅実ブラウザで、11/3下関11Rの研究用予想注意表示、6艇出走表、`CLEAN_SAME_DAY_CUTOFF_READ_ONLY_BROWSER_PASS`、展示の未検証状態表示、確定結果`1-5-3`を確認。以前の10/28桐生1R・10/31蒲郡8R・11/2下関5Rの3実レースも予想注意文/6艇出走表/結果全て成功。10/27の確定結果も表示成功。公開HTML/JS/保存済み確定結果のバイト一致と4タブ操作も成功。
- P0の**当日締切済みレースと複数過去日**で公開ブラウザ表示成功の証拠を確保。ただし当日締切前の実表示・全24場・iPhone Safari実機・展示タイムの真正な締切前証明・正式Top3/5/10的中率は未実証。研究予想は未検証のままで採点しない。旧リポジトリ削除なし。新規有料サービス・重複ワークフローなし。

## 2026-11-03 23:48 JST 締切前展示の予定実行でゼロ証拠を誤成功扱いしない
- GitHub Actions実行原本を再確認：`Check real live predeadline racecard` の2026-11-03 JST16:04頃の予定実行 `41593838820` / job `125776466301` は `CARD_PASS` 3レース、`EXHIBITION_PASS` 1レース（`202611030103`）だが、締切12分前のAPI受領・2元展示がそろった証拠がなく`T12_UNVERIFIED`でfailure。2026-11-02のrun `41400724125` も正規締切前展示は未実証。2026-10-31のrun `41190323532` は一度PASSしたが、その1件だけで継続安定稼働とは認めない。
- 別系統 `CLEAN today's predeadline exhibition source probe` の11/3無人schedule run `41631033275` / job `125900347136` は、実CSV tkz/stt/sui の各151行を読めたが、すべて `eligible_future 0`、アダプタの検証も0件なのにジョブがsuccess。これは**実HTTP CSV取得成功と、締切前の6艇展示データ取得成功を混同する誤った緑判定**。
- PR #1528をmainへsquash統合（`3a6c794acca6885bebaa941b6895eb2b79ec0b22`）。既存 `scripts/probe_today_beforeinfo.py` をHTTP実行せずimportできる`run(now,event_name)`に整理。**schedule実行では**「全情報源不通」「締切前のtkz/stt同一レース一致ゼロ」「アダプタで6艇検証ゼロ」を別々のRuntimeErrorで失敗扱いにし、6艇検証>=1でのみ `SCHEDULED_PREVIEW_VERIFIED` を出す。手動workflow_dispatchとPRは診断専用で従来どおり0件でも診断結果を返す。T-12基準は緩和していない。
- 新設 `tests/test_today_beforeinfo_probe.py` で、0件、アダプタ不完全、全情報源不通、6艇証明成功、手動0件の5パターンを独立時計/モックで検証。既存 `.github/workflows/today-beforeinfo-probe.yml` のPR実行にテストを追加。PR CI run `41657163439` job `125990433208` success、5テストPASS。PR上の実CSV取得は23:47頃JSTですでに締切前レース0件であり、**PR成功を当日締切前の運用証拠とは呼ばない**。
- 既存 schedule は 13:15 / 15:15 / 17:15 / 19:15 JST のまま。GitHub cron遅延により締切後に起動する可能性は引き続き未解決。次は11/4の実schedule run ID・開始時刻・同一レースの両展示ソース時刻・6艇完全性・T-12成立可否を実観測する。新しいジョブや有料サービス、予想ロジック変更なし。

## 2026-11-04 JST 締切前展示の実検証完了時刻を再チェック
- 2026-11-03 schedule実行の独立検証で、`CLEAN today's predeadline exhibition source probe` は実行開始時点`now`で今後の同一レースtkz/sttを抽出してから`_fetch_preview`を実行していた。取得処理がレース締切をまたいだ場合、実データの検証完了時刻と締切時刻を再比較せず`SCHEDULED_PREVIEW_VERIFIED`に昇格する経路があった。発生頻度は未実測だが、ロジック上の誤証明可能性がある。
- PR #1534 main squash `a6c80d5f2ffe6d3ba333dda3fd7fde83e5d4f7ce`。`scripts/probe_today_beforeinfo.py`でアダプタ戻り直後のタイムゾーン付き実時刻を再取得し、締切以上・タイムゾーンなしを`cutoff_passed_before_receipt`として6艇の締切前成功に数えない。成功時は`received_at_jst`をログに残す。既存ソース照合、6艇完全性、T-12判定ロジックを緩めない。時計を注入可能にし、締切直前成功・締切同時拒否の境界回帰を追加。
- PR CI run `41661183224` job `126004484149` success。7回帰テストPASS、実CSVのPR診断は夜間のため締切前レースが無く、**本番scheduleやT-12実証ではない**。
- 次の実運用監査は11/4予定13:15/15:15/17:15/19:15 JSTのschedule run ID、起動時刻、6艇検証完了ログ`received_at_jst`、同レースの期限、tkz/stt原本、T-12取得・API返却の各時刻を照合する。旧リポジトリ、予想、UI、スケジュール回数は変更なし。

## 2026-11-04 JST 締切前展示CSVの情報源別HTTP受信時刻を採用
- PR #1538をmainへsquash統合（`2b886487aabd3a3982af0324d49a525c4ada3418`）。`scripts/probe_today_beforeinfo.py`では、対象日を決めたスキャン開始時点の`now`に対して、後で逐次取得した`tkz/stt/sui`CSV行の独立取得時刻`取得日時`を比較していたため、ネットワーク取得中に新しく公開された正規の締切前スナップショットを未来時刻として誤除外する可能性があった。
- 各`_preview_rows` HTTP完了の直後に時計を再読込し、情報源ごとに`source_received_at_jst`を記録。スナップショットの公開時刻 <= 実HTTP受信完了時刻、公開時刻 < レース締切時刻、HTTP受信完了時刻 < レース締切時刻を同時に必要とする。締切をまたいだアダプタ検証の事後時刻拒否（PR #1534）、同一レースtkz/stt・6艇完全性・予定実行ゼロ成功拒否（PR #1528）は維持。T-12判定の緩和なし。
- 既存`tests/test_today_beforeinfo_probe.py`へ「取得中に公開された正しい新データ」「HTTP受信後に公開されたように見える未来データ」「締切ちょうどの受信」の3パターンを追加し、もともとの7件を含め計10件。初回PR CI run `41662839171`は時刻注入テストが取得元も締切後の設定になっていたため1件失敗。正しく取得元3件だけ締切前・アダプタ後締切後に直し、再CI run `41662956963` / job `126010681112` success、10件全成功。PRで実CSVを取得した成功は無人運用T-12成功に含めない。
- 最新GitHub APIのevent=schedule上位実行履歴では、確認時点で11月4日分の`CLEAN today's predeadline exhibition source probe`および`Check real live predeadline racecard`実runを発見できず、**11/4の実行が発火しなかったと断定できる時刻・十分な検索範囲とは限らない**。11月4日の本番T-12成立は未実証。既存の22:00 JST自動監査で対象run、受信時刻・期限・GitHub起動遅延を独立照合する。
- 既存スケジュール・予想ロジック・買い目・4タブ・ソースURLを変更せず、追加費用なし。

## 2026-11-04 00:30 JST 実レースT-12検証対象の選択順と不成立理由の可視化
- PR #1541をmainへsquash統合（`5cfaa9a935d065da6085379bf48df964d86f8561`）。既存`scripts/verify_live_racecard_e2e.py`は、候補に「締切まで2分超」のみ要求し、プレビュー一致→早い締切順で最大3件を選ぶため、まだT-12実測可能なレースを他候補が押し出す問題があった。T-12のAPI受信には**検証時点で締切まで12分超**が必要であり、標本選択による機会損失の修正。
- 新しい純粋選択ヘルパー`scripts/live_racecard_candidate_priority.py`で、T-12時刻枠が残る候補を最優先、次にtkz/stt一致プレビュー、次に締切時刻で並べる。T-12不可能な候補も出走表・展示診断用に保持し、成功の偽装なし。
- 選択した最大3レースについて`T12_SAMPLE_STARTED`を出し、締切・候補時点のT-12機会有無を記録。6艇展示がそろってもT-12不成立の場合、`T12_PAIR_NOT_VERIFIED`に各tkz/stt公開時刻、API応答受信時刻、T-12境界、どの時刻条件が不成立だったかを記録。`T12_COMPLETE_PAIR_PASS`には従来通り両元時刻とAPI受信時刻の実際の条件を必須とする。
- 既存`.github/workflows/live-racecard-e2e.yml`のPR syntaxジョブに4件の決定的な回帰テストを追加。PR run `41664174030` はsyntax/過去出走表/確定結果/オッズの4ジョブsuccess、**e2e-live-raceはPRのためskipped**。CIが成功しても無人実レースT-12取得成功とは扱わない。GitHubの予定実行が予定時刻から遅れる問題と情報源の公開遅延は未解決。
- 既存ジョブの予定時刻09:30/12:30/14:30/16:30/18:30/21:30 JST、買い目、予想ロジック、画面、有料サービスは不変更。次は11月4日の実scheduleで選択対象・受信証拠・T-12成立数を独立監査する。

## 2026-11-04 JST 実schedule深夜起動とT-12展示候補の受信時刻整合性
- GitHub Actionsのschedule event実行 `41663438908`（run start 2026-11-03 15:23:45 UTC = 11/4 00:23:45 JST、head `9cd5cd9e7aab4be5137a848422189c584201a004`）では、11/4の出走表3レース `202611042101`、`202611041001`、`202611042102` はCARD_PASSだが、tkz/stt/suiはいずれも`source_unavailable`、展示/進入0レースで`NO_SIX_BOAT_PREDEADLINE_EXHIBITION_VERIFIED`のfailure。予定cronは09:30/12:30/14:30/16:30/18:30/21:30 JSTだが、このrunがどの予定枠に対応するかの原本は未特定。前日21:30 JST予定からの遅延である**可能性**は高いが、遅延時間の確定値にはしない。
- PR #1543 main squash `ca041863997ecaf5c70bb88962fdff18cf9265fa`。`scripts/verify_live_racecard_e2e.py`は無人scheduleの日本時間09:00〜22:59以外で`SCHEDULED_LIVE_SAMPLE_OUTSIDE_JST_RACING_WINDOW`を出し、適格性なしとして失敗。日付が変わった後の翌日未公開展示を通常の展示ソース障害成功/失敗と混同しない。手動診断での時間帯制約は追加しない。
- 以前の`PREVIEW_CANDIDATES`評価では独立したtkz/sttの各HTTP読込後の`取得日時`を開始時刻とではなく最新の評価時刻で複数回比較していた。これを各情報源のHTTP読込完了直後の`source_received_at_jst`で固定し、取得日時<=受信完了時刻、両時刻が締切より前かつ当日レース一致の場合だけ候補にする。受信後時刻や締切後のデータを成功扱いしない。ソース取得終了後`selection_at_jst`で候補を再順位付けしてT-12残余時間を確認する。API側の締切12分前受領、tkz/stt両観測が締切12分前である実証条件は維持。
- 既存`tests/test_live_racecard_candidate_priority.py`は8件へ増強。PR CI `41665568784` のsyntax+8テスト/歴史出走表/結果/オッズ成功。e2e-live-raceはPR由来のためskippedで、**無人実レースT-12の成立を認定しない**。新規scheduleや有料サービス、予想買い目/モデル変更なし。
- 次は11/4以降の正規schedule発火時刻・runごとのイベント・CSV元2系統のHTTP受信時刻・API受信時刻・T-12可否を照合。時刻外の実行はcoverage失敗として数え、データ不足だけに転嫁しない。

## 2026-11-04 未明 T-12実レース候補の再選別と展示元の部分障害可視化
- PR #1547 main squash `3699a13e5f50a600eb67739e728e556b5f09d3ff`。既存`scripts/verify_live_racecard_e2e.py`では開始時刻`now`で締切まで2分超の候補を生成し、独立tkz/stt HTTP取得後に優先順位だけを再計算していた。取得中に締切まで2分以下となったレースも上位3件に残るため、実T-12の検証枠を消費する可能性があった。今回`fresh_candidates_at_selection`でHTTP完了後に再度2分超を必須とし、期限切れ候補は`RACECARD_CANDIDATES_EXPIRED_DURING_SOURCE_PROBE`へ別記録して対象から除外。既存のT-12境界は締切12分前を維持。
- tkz/sttの取得が一括tryだったため、片方のHTTP/変換エラーが他方の取得を抑止し、異常元が見えなくなる問題にも対応。各元を独立取得し、成功時`PREVIEW_SOURCE_RECEIVED`（受信時刻、件数、SHA256）、失敗時`PREVIEW_SOURCE_UNAVAILABLE`（元、エラー型）を出す。**両方の独立取得が成功して初めて**同一レース候補にする。実API受信時刻・元観測時刻・6艇完全性・締切前時刻の拒否ルールは不変。
- 回帰テストを6件追加し、従来8件と合計14件。PR CI run `41666855620` syntax job `126024373021` 14/14成功、過去出走表・結果・オッズ成功、実e2e-live-raceはPRなのでskipped。**実無人T-12の成功は未実証**。main統合後の本番RenderデプロイやGitHub schedule成功をPR CI成功と混同しない。
- 次は11/4の日中無人scheduleで、期限切れ候補数、tkz/sttの独立取得成功・失敗、`T12_SAMPLE_STARTED`と`T12_PAIR_NOT_VERIFIED`の時刻別原因、および実`T12_COMPLETE_PAIR_PASS`件数をチェックする。新規ジョブ・費用・予想ロジック・買い目・画面変更なし。

## 2026-11-04 未明 本番Render展示アダプタの各ソース受信時計を修正（P1）
- PR #1550 main squash `9bbc2a3f07ce5e6e9e0de43bb3fe3e4d5fec16c8`。`clean_racecard._fetch_preview`でtkz/stt/suiを並列HTTP取得**する前**の`observed_now`だけを使い、HTTP通信中に公開された締切前CSV行の観測時刻を未来扱いで拒否する実装が残っていた。PR #1538/#1543は別の監視ジョブ側のみの修正だったため、Render実API側の取りこぼし可能性を解消。
- 各ソースの`_preview_rows`が実際に返った直後の`received_at`を独立取得し、元CSV行の`取得日時` <= 実HTTP受信完了時刻、CSV時刻 < 該当レース締切、HTTP受信完了 < 該当締切をすべて必要とする。妥当な6艇・6コース・ST/展示タイムの完全性条件は不変更。`source_audit.beforeinfo.sources[kind].received_at_jst`を独立観測時刻として追加し、従来の`observed_at`とSHA256を保持。履歴レース用`not_verified_historical`分岐も不変更。T-12の成立閾値は緩和なし。
- `tests/test_preview_completeness.py`に通信中公開の正常データ、締切同時受信拒否、HTTP受信より未来の記録拒否の3テストを追加。過去日時の合成原本の`test_clean_racecard.py`も、仮想HTTP受信時計を対象レース締切前に固定してテスト条件を維持。PR初回run `41668148759`等は既存の歴史合成テストが受信時刻条件未対応で失敗。修正後PR CI run `41668409248` fixtures成功、`41668409271` V236処理成功、`41668409327` syntax+過去出走表/結果/オッズ成功、`41668409358` ナビ/ブラウザ両ジョブ成功。
- 同PRの`Verify REAL beforeinfo source` run `41668409466` は `REAL_BEFOREINFO_NO_VERIFIED_RACE` でfailure。これは実ソースから6艇一致サンプルを確認できなかったという正しい未実証で、他CI成功を根拠に上書きしない。締切12分前の実観測成功、実行元GitHub schedule、Render新コードliveも引き続き独立検証が必要。
- 新しいジョブ、有料サービス、4モード、予想ロジック、買い目、公開画面骨格の変更なし。ロールバックはPR #1550のsquash差分revert。次回は実日中レースで各元`observed_at` / `received_at_jst`、API受信、締切時刻を突き合わせ、T-12成立を判定する。

## 2026-11-04 未明 T-12無人運用4実行の独立集計と実障害切り分け
- 新規監査文書`docs/T12_SCHEDULE_EVIDENCE_AUDIT_20261104.md`（main直接記録 `716d8a263170885a438d975d0e535561558c5c80`）にGitHub `event=schedule`の`Check real live predeadline racecard`実run `41400724125`、`41489725625`、`41593838820`、`41663438908`のジョブ原本を個別照合して記録。
- **4無人実行 / success 0 / failure 4、出走表10/12試行、完全6艇展示1件、T-12成立0件**。出走表2件の失敗はRender API HTTP502とタイムアウト各1件。実開始JSTは11/02 15:34、11/03 02:17、11/03 16:03、11/04 00:23。4件中2件が夜間の予定外調査時間帯。個々のrunの元cron予定枠は未特定で遅延時間の数値は推定しない。
- 実run `41593838820` は11/03 16:03に6艇展示1件`202611030103`を取得済みだが`T12_UNVERIFIED`。ほかの3runでは元CSV不在/翌日未公開/HTTP502/タイムアウト等。これらは修正PR #1541/#1543/#1547/#1550の全改修を同時に使っていないため、**改修後の本番性能評価へ流用しない**。
- 再発防止策を増やす前に、11/4の日中実scheduleのID・実head SHA・開始時刻、tkz/stt元HTTP受信、Render APIレスポンス/各元監査フィールド、T-12ゲートごとの実失敗数を記録する。ジョブ予定枠の欠落・深夜遅延はデータ源障害と分ける。取得がないものを予想・的中率に算入しない。T-12無人実証は依然**未完了**。本監査はドキュメントのみ、追加ジョブ・課金・モデル・4タブ・買い目変更なし。

## 2026-11-04 JST T-12失敗の収集経路別切り分け（実ログ監査・コード変更なし）
- `Check real live predeadline racecard`で最新mainの11/4日中実scheduleの成功は、調査時点のGitHub APIには存在せず未実証。前回の実schedule4件（`41400724125`, `41489725625`, `41593838820`, `41663438908`）では出走表10/12、6艇展示1件、T-12=0。最新修正コードの成功率とは混同しない。
- 独立した`Preview capture (schedule)`の実原本も追加照合：`41574478481`（11/03 12:49 JST）はstt/tkz各59行、完全6艇ペア1件`202611030906`、両方の実受信は12:49:41頃で`t12_gap_counts.both_too_late=1`、T-12=0。`41627186144`（11/03 20:23 JST）は5ソース各148行取得、`too_late`各148・締切前該当0、完全ペア0、T-12=0。`41647178739`（11/03 22:45 JST）の独立遅延研究では完全ペア0/T-12 0。
- `late_preview_capture.py`の保存処理は`margin_minutes=2`と`before_deadline_minus_2min_buffer`を正式に採用する「締切2分前バッファの後半展示証拠」用。これは`scripts/collect_late_preview_evidence.py`にある通り12分前研究スナップショットへ統合しない。後半展示取得成功は正式T-12成功へ算入しない。現行T-12は`scripts/preview_timing_integrity.py`にある通り元スナップショット時刻とHTTP受信時刻の両方が締切12分前以前である必要あり。
- 追加監査記録は`docs/T12_SCHEDULE_EVIDENCE_AUDIT_20261104.md`へ追記（`f8d1f5c4bfc4cce777edbd705f6d0498a4b0a884`）。この回は**コード・監視時刻・予想ロジックの変更なし**。次は最新mainの11/4日中`event=schedule`実runで、予定枠の欠落、元CSV公開の早遅、API受信、T-12成立を別のKPIとして監査する。ソースが根本的に遅ければ既存の別公式JSON取得実証の独立結果を評価し、改修や新規課金を先に増やさない。

## BOATERSモデルを全担当の固定方針とする（2026-11-01 ユーザー指示）
- 正本は AGENTS.md の「UI・情報設計の最優先固定方針」。メイン開発／予想研究／データ収集の全トークに適用。
- BOATERSをモデルにした1レース1ページ：確定結果を予想より上へ、AI展開予想、先頭艇別条件付き2着/3着率、6艇別イン逃げ/3連対/決まり手率、展示・進入・気象、最終3連単予想とオッズ。
- 既存ドラフトPR #725 はUI土台。未取得が多く、数値連携・CI・実機・本番確認は未完了。**完成扱い禁止**。メイン開発が重複PRを作らず内容を整理・統合する。
- 収集担当：選手・コース別/先頭艇条件付き成績の期間・分母・出典を検証して保存。研究担当：実測率とAI予測確率を分離して予想寄与を検証。メイン担当：表示・1ページ統合・回帰試験・本番確認。無関係な変更でUI方針を覆さない。

## 現在の最優先作業
| 優先 | 作業 | 状態 | 完了条件 |
| --- | --- | --- | --- |
| P0 | 旧サイト・不要コード・旧導線の参照/依存を調査し安全に撤去 | 未完了・要調査 | 現行本番への参照とデプロイ依存を確認し、不要物の削除後も回帰テスト成功。旧リポジトリは無断削除しない |
| P0 | 当日/昨日/過去日の出走表・予想の非表示不具合 | 過去3日付＋当日締切済み下関11RのPages本番Chromium実証成功（run 41655377223）。当日締切前と全場網羅は未完了 | 未締切実レースと追加会場で出走表/展示/予想を検証、正式予想/研究用と欠損理由を区別 |
| P1 | 4タブのみ・概要なし・トップ出走表なし・戻る導線 | 部分実施と報告あり・要本番実機確認 | iPhone Safariを含む公開画面で重複なし、タブ切替・戻る操作正常 |
| P1 | 締切前の6艇展示・進入・オッズ | 一部取得例あり・時刻条件未証明 | 取得時刻と締切を検証し、事前予想への安全利用可否を確認 |
| P2 | 保存済み予想Top3/5/10の的中率検証 | 未完了 | 初回保存証拠を満たすレースのみで集計し、後付け評価しない |

## 既知の経緯（過去の会話報告、要現況確認）
- PR #545: 旧7メニュー除去、画面の重複ナビ整理。main統合と報告あり。
- PR #367: 出走表APIのレース番号×HTTPエラー記録。10/30実レース3件の出走表API成功との報告あり。
- PR #632: 保存元の展示データを再読込して6艇未満は不合格。蒲郡8R（202610310708）で両展示の保存例との報告あり。締切前利用可能性は未証明。
- PR #533: 戸田2Rの保存済み研究予想10点を公開表示、CI成功、main統合 e0d03100 と報告あり。
- 2026-11-01: ユーザーより「昨日の予想・出走表を見られない」「旧サイト削除を優先」「不要コード撤去」「作業を分断せず引き継ぐ」と再要請。これらは解決済みとは扱わない。
- READMEにはサイト仕様と完成条件の記述あり。運用上の具体的な未完了事項はこの文書を優先する。

## 次の作業開始チェック
1. mainと未統合PR、CI、デプロイ先を照合。類似作業との重複を排除。
2. P0の旧サイト参照箇所とRender/GitHub Pagesへの依存、現行データ導線を洗い出す。
3. P0の過去レース非表示を再現し、API・保存データ・フロント描画のどこで欠落するか切り分ける。
4. 安全な関連修正をまとめ、変更テスト→公開デプロイ→実ブラウザ検証まで試みる。
5. このファイルに検証日時、URL、PR/commit、CI結果、残作業、具体的な次の一手を反映する。

## 作業ログ（更新テンプレート）
- 日時（JST）:
- 対象/原因:
- 変更ファイル・PR/commit:
- テスト/CI（成功・失敗・未実施）:
- 公開サイト実測（URL・レースキー・結果）:
- 残る課題/次の一手:

禁止: 未確認のCI・公開デプロイ・実ブラウザ結果を成功と記載すること。

## 2026-11-01 現況再調査（GitHub API確認、公開実測とは区別）
- 最新確認mainコミット: `9bc33f9242b916df83cb57d4018b983cc5b709b9`（#721、過去出走表の参照専用表示）。#718（履歴詳細から出走表へ移動）、#717（未使用model-lab.html削除）、#710（履歴タブ再取得）、#709/#707（重複研究ワークフロー削減）はコミット履歴で統合確認。過去出走表の表示自体は公開実測未確認。
- open PR（検索時）: #654、#652、#646。#646と#652は双方独立したモバイルDOMオッズ検証ワークフロー・テスト追加で重複候補。両方を無条件統合せず、差分統合・不要PR整理を優先。
- 既存の古い3ペイン画面PR #536は現行4タブ仕様と矛盾するためクローズ済み。再作成しない。
- ブランチ検索で62件＋継続カーソルを確認。統合済みか未確認なので無断削除しない。
- P0旧サイト: 旧リポジトリ削除は依存/Render/Pages確認未完了のため未実施。P0過去予想: #721の参照専用出走表対応と予想表示の根拠は区別し、本番の過去レース1件以上で再確認が必要。
- CI: 全workflowと最新mainの完了状態の通し確認は未完了。Render: ワークスペース未選択でサービス状態を確認できず、本番成功を主張しない。
- 次アクション: (1)現行/旧サイトの公開URLと依存関係を検証 (2)実際の2026-10-31レースで出走表/保存予想/結果/展示の4タブを確認 (3)#646/#652の重複解消 (4)CIとデプロイ確認。調査だけの重複PRは作らない。

## 2026-11-01 メイン開発・実行記録
- GitHubで未統合PR #646 / #652 の重複を差分照合。双方のCIは失敗。#646を重複としてクローズ、#652を既存の検証PRとして継続。
- #652 CI run `41210366375` は、現行4タブ仕様により非選択 `#forecast` が hidden なのに可視状態を待つテストがタイムアウト。PR #652 の `tests/forecast-odds-rendered.cjs` を `state:'attached'` へ修正（commit `5100581dfc32249156af57aef7bb882c829b7873`）。この変更のCI再検証は未完了、main未統合。
- 旧サイトの削除と過去レース表示の公開実測は未完了。#654はデータ収集担当のPRとして変更対象外。
- 次の優先作業: #652 CI修正の確認、旧サイト/現行サイトのデプロイ依存照合、2026-10-31の公開過去レース表示確認。

## 2026-11-01 メイン開発追加確認（既存テスト再利用）
- 現行mainの `.github/workflows/forecast-mobile-browser.yml` に `tests/forecast-odds-rendered-dom.cjs`, `tests/live-odds-to-dom.cjs`, `tests/saved-prediction-auto-odds.cjs` が既に登録されていることを直接確認。`state:'attached'` で非選択DOMに対応する既存実装も確認。
- #652 はmainの既存モバイルオッズ検証との実質的重複、かつ `mergeable=false` のためクローズ。前ターンの#646クローズと合わせ、重複PRを増やさず既存ワークフローに一本化。#652の変更はmainに未統合。
- 旧サイト撤去: Render workspace未選択のためデプロイ依存を実証できず、破壊的削除は未実施。旧リポジトリを無断削除しない。
- 過去レース: mainの履歴出走表既存修正はあるが、2026-10-31の公開UI実測は未完了。公開サイトの到達・DOM・保存結果・予想の対応を次に検証する。
- #722（予想研究）、#723/#654（データ収集）は担当別PRのため未変更。新規PRの乱発なし。

## 2026-11-01 P0追加調査（サイト本体・デプロイ）
- Render `list_workspaces` は `My Workspace` (`tea-db8svlcs728c73avi3h0`) の存在を返した。ただしユーザーの対象選択が未確認のためサービス一覧・旧サービス削除は未実施（別ワークスペース誤操作防止）。
- 現行 `index.html` は過去日も `schedule_snapshots/YYYYMMDD.json` → CLEAN `/api/clean-schedule` → `historicalHeldVenues` の順に扱い、旧リポジトリの `today.json` を他日付に流用しない実装。出走表は `/api/clean-racecard` の `HISTORICAL_READ_ONLY` を受け入れる。研究予想は `prospective_predictions` → `research_snapshots` → CLEAN `/api/predictions` の順に照会する。これらはコード確認であり実データ正常表示の証明ではない。
- 現行フロントの画面状態はURLパス `/forecast`, `/card`, `/exhibition`, `/results` に対応。`setView` は `view` クエリパラメータを消去する。READMEの `view` で復元可能という説明とは不一致。実際の旧サイト依存と本番表示不具合は引き続き公開ブラウザ検証待ち。
- Web経由の `https://boat-edge-clean.onrender.com/` と `/api/clean-racecard` への取得は環境側でアクセス不可。HTTP 200/表示正常とは判定できない。
- データ収集・精度研究のPRには触れていない。次: 対象Renderワークスペースの確認後に旧/現行サービスの依存を照合し、現行サイト公開URLで2026-10-31履歴を再現→必要な修正を既存コードに集約する。

## 2026-11-01 過去開催日程404フォールバック修正
- `index.html` の `loadHeldVenues` で、過去日のCLEAN日程API 404が `historicalHeldVenues` 実行前に `SCHEDULE_NOT_PUBLISHED` を投げていた分岐を修正。過去日の404時は公式確定結果のCSV由来の開催場復元へ進み、当日404は未公開のまま扱う。main commit `db62cf35be0af88ce3e768e522c1b35e4567cefb`。
- 修正した条件分岐について、過去日404/503・当日404/503の4例の期待値を実行して通過。ただしブラウザ上のCSV取得、公開デプロイ、過去日の出走表・予想表示は未確認。フルCIの結果は別途確認が必要。
- 旧サイト削除は依存未確認につき未実施。Render workspaceは1件見えるが、対象確定前の破壊的変更は避ける。

## 2026-11-01 追加実行（過去日フォールバック回帰検証）
- 既存の `tests/site-regression.cjs` に過去日程APIの404/503時に履歴CSVへ進む条件の静的回帰検査を追加。commit `ce037349b472dc65c313dc01bacef735d742d364`、mainへ直接コミット。新規PRや追加CIワークフローなし。
- `.github/workflows/site-regression.yml` は `tests/site-regression.cjs` のpush変更を検知する構成。コミットに対するPRトリガーのworkflow run検索結果は0件だったが、これはpush CI成功/失敗の証拠にはならない。Node回帰テスト実行・CI成功・本番ページ動作はいずれも未確認。
- 公開RenderのURLはWeb取得でアクセス不可のため、実ブラウザ上の10/31再現確認は未完了。Renderワークスペースは利用者の対象指定が未確定でサービス変更/旧サイト削除は実施していない。
- #725 は予想画面の別作業PRとして変更せず、予想精度/データ取得の独立PRも未変更。

## 2026-11-01 Render現況確認（管理API実測）
- Render workspace `My Workspace` (`tea-db8svlcs728c73avi3h0`) のWebサービス一覧を取得。取得されたサービスは `boat-edge-clean`（`srv-dbcthfrncjis73djj8qg`、`https://boat-edge-clean.onrender.com`）1件のみで、GitHub `ikst2512-eng/boat-edge-clean` の `main` を自動デプロイ。少なくともこのワークスペースには別名の旧Webサービスは存在しない。旧リポジトリそのものや他の公開先は未削除。
- Render deploy履歴で過去開催日程404修正 `db62cf35be0af88ce3e768e522c1b35e4567cefb` のデプロイ成功と、回帰テスト追加 `ce037349b472dc65c313dc01bacef735d742d364` のデプロイ成功を確認。最新確認のlive deploy `dep-dbj4k6dh3lcs7386e51g` は `0fdac4fe62381b422b8e841b388eac8a7cb71578`（2026-10-31 20:06 UTC終了）で成功。デプロイ成功はブラウザ描画確認ではない。
- 公開 `/api/clean-schedule?date=20261031` と公開ページをWeb取得で確認しようとしたが、この環境からアクセス不能。2026-10-31の出走表・予想・結果の表示は引き続き未検証。
- 次: GitHub Pagesの公開URL・旧リポジトリ依存と表示環境を検証、既存ブラウザCIの実行結果を取得。破壊的削除は依存確認後。

## 2026-11-01 GitHub Pagesナビゲーション公開欠落修正
- `index.html` の末尾は `navigation.js` をロードするが、既存 `.github/workflows/deploy-pages.yml` は `index.html` のみを `public/` にコピーしていた。公開HTMLからの外部スクリプト欠落がブラウザ上のナビ/履歴復元不具合に繋がるため、両ファイルを公開するよう修正（main commit `ee0e456ba891a2851d8d0a79aae8691503daf683`）。
- `navigation.js` の更新でPages公開が発火するようpath filterを追加し、デプロイ後に公開JSを取得してローカル配布物とバイト照合する検証を追加。既存 `tests/site-regression.cjs` に4つの必須条件を回帰確認するアサーションを追加（commit `e7de1db0b6fbdcecd8ccca10df282d658ffdee6f`）。main再取得で設定とテスト内容が存在することを確認。
- GitHub Pages Actionsの実際の成功、公開JavaScriptのHTTP応答、Safari操作、10/31過去レースの全タブの表示は未確認。Renderの単一CLEANサービスは前回確認済み。旧リポジトリ自体は削除しない。
- 次はPages Actionsの実行結果・公開URLの同一性チェック、10/31履歴表示のブラウザE2E。予想1ページ化の既存PR #725とは衝突しない公開設定・テストだけ変更した。

## 2026-11-01 公開ワークフロー・デプロイ再確認
- GitHub Pages `.github/workflows/deploy-pages.yml` のmainを再取得し、`navigation.js` がpushトリガー・公開ファイルコピー・公開URLからの照合のすべてに登録済みと確認。`tests/site-regression.cjs` に対応する回帰アサーションが存在。これはコード確認であり、Actions実行成功や公開ブラウザ動作の証明ではない。
- GitHubの取得可能な `fetch_commit_workflow_runs` はPRトリガーの実行のみ対象で、Pagesのpush workflowは検索結果0件でも成功/未実施の判定不可。Web・コンテナからGitHub Pages URLはアクセス不可。公開Pagesの成果物実測は未確認。
- Render管理APIで最新live deploy `dep-dbj4ma3m8hqs73fed5a0`（commit `df92a926162dba2ec922e898b25e69b56e2bbd12`、#726 clean racecard CSVフォールバック、2026-10-31 20:11:03 UTC終了）を確認。Renderはliveだが10/31のレース画面E2Eは未確認。
- 未統合#725は別の予想1ページUI作業のため維持。旧サイト/旧リポジトリの無断削除なし。GitHub Pagesの公開runを閲覧できる経路とブラウザ検証が必要。

## 2026-11-01 GitHub Pagesプロジェクト配下の検証リンク修正
- `navigation.js` は `/review` をRender用ルートとして持つが、GitHub Pagesプロジェクトサイト `/boat-edge-clean/` にはそのパスのページがない。Pagesホストでは既存 `screen=review` に置換し、プロジェクト配下での画面復元を受け入れるよう修正（main `51b2a3ba43fe181e93341341a5a454c6076816d3`）。Render用ルートは変更なし。
- 既存 `tests/site-regression.cjs` にPagesホスト・パス・screenクエリの回帰アサーションを追加（main `8b714fbb487403eecdcafd6e5e6136dcea2a7d5c`）。コードの再取得では修正存在を確認したがCI実行成功、GitHub Pages配布成功、実ブラウザ動作は未確認。
- Web側からPages/Render公開URLへ直接アクセス不可。Renderの要求ログ指定期間は0件（無通信の証拠とは扱わない）。旧サイト削除や担当外PRの統合は実施していない。
- 次：Pages Actionsのデプロイ結果と10/31履歴タブの実機再現。旧サイトのGitHub Pages/旧リポジトリの依存確認を継続。

## 2026-11-01 Pages公開CIの既存ブラウザsmokeを強化
- GitHub Pages公開workflowの既存 `Browser interaction smoke test` に、`navigation.js` の実行完了 (`dataset.cleanNavigationInit`) とレース4タブDOMが存在することをChromiumで検証する条件を追加。新規workflow/PRは作らずmain `d65c51c752c34987d0a9b60568ab776ade48ccc2` に統合。
- 既存workflowを再取得しアサーション存在を確認。GitHub連携のコミットworkflow一覧はPRイベントだけを扱うため、Pages push Actionsの成功判定には使えない。公開Pages/RenderへのWeb直接アクセスはこの環境で失敗。**CI成功・10/31の実画面表示は未確認**。
- 次: GitHub PagesのActions runでナビDOM smokeと公開静的ファイル照合がPASSした証拠を確認し、10/31日付の出走表・予想・結果をブラウザ上で検証。旧リポジトリの削除なし。

## 2026-11-01 旧サイト現物の特定・権限制約
- GitHubで旧 `ikst2512-eng/boat-edge` はpublic・未アーカイブ（default main）の別リポジトリと確認。旧 `index.html` は `BOAT EDGE v30` を持つ実在する旧UI。Render `My Workspace` は現行 `boat-edge-clean` のWebサービス1件だけで、旧Renderサービスは存在しない。
- `AGENTS.md` スコープは `boat-edge-clean` で、旧 `boat-edge` の無断変更/削除は禁止。この制約に沿って旧リポジトリへのリダイレクト変更・リポジトリ削除は行っていない。旧GitHub Pages公開状態も未確認で「旧サイト撤去済み」としない。
- GitHub Pages公開URLとRender公開URLへのWeb直接アクセス、コンテナからのgithub.com名前解決は失敗。公開DOMの2026-10-31実レース検証は未達。Render最終確認のlive commit `65447516f10b02282795c7900c0a6f1bf585ba00`。
- メインの次手は旧リポジトリ変更の許可範囲とPages公開サービス構成が確定次第、旧UIを新サイトへ安全移行すること。現行サイトは公開ブラウザ検証を別手段で行う。担当外#725/#722/#723/#654を勝手に統合しない。

## 2026-11-01 履歴出走表本番HTTP検証の実証結果
- 既にmain統合済みPR #727 のGitHub Actions run `41238365549` を実確認。head `b8412fdbac4c83ecd56e1c8eb07c78983ae1bdfc`、workflow `Check real live predeadline racecard` 結果 success。
- `historical-production-smoke` job `124646817195` success。実行スクリプトはRender本番 `https://boat-edge-clean.onrender.com/api/clean-racecard?hd=20261031&jcd=09&rno=12` をHTTP取得し、レースキー `20261031-09-12`、`historical_reference_only=true`、6艇の枠番1〜6・異なる4桁登録番号・race_card監査okをassert。workflowおよび該当jobの成功を確認したため、この対象の履歴出走表APIは**本番HTTP検証成功**とする。
- 同じrunの`syntax`はsuccess、`e2e-live-race`はPR上の仕様でskipped。前者は締切前実レース可用性の証拠ではない。ブラウザの出走表画面、10/31の予想・展示・結果、GitHub Pages発行の正常動作は引き続き未検証。
- 旧 `ikst2512-eng/boat-edge` は別repoかつAGENTS.mdが無断変更/削除を禁止。旧repoの公開停止・リダイレクトは実施せず、現行Renderに別名の旧webサービスは見つかっていない。安全な撤去のため旧Pages公開確認が残る。今回新規コード・PRは不要につき作成しない。

## 2026-11-01 10/31過去レース確定結果のRender実HTTP検証
- 既存PR #728（main merge `70b5231d4b2161be27a5fd7ed5e4dbb80ffc6f43`）の head `a47d83130c1c5b0fcdae9ca3290a8cb9f4c1c3e9` に対するActions run `41238603161` を確認。workflow完了 success。
- `historical-result-smoke` job success、`historical-production-smoke` job success。両者は2026-10-31 09場12Rを対象にRender本番の確定結果・6艇出走表APIをHTTP検証する。race identity/着順・source provenance・6艇/監査等を検査。これにより**当該実レースの出走表・確定結果API**は本番HTTP成功確認済み。ブラウザDOM・研究予想・展示の表示証明ではない。
- `e2e-live-race` はPR起動の仕様によりskip。締切前予想・展示の可用性の証明と混同しない。旧リポジトリの無断変更/削除もしていない。新規テスト/PRは既存#728と重複するため作らない。
- 次は2026-10-31保存済み予想の原本存在と展示の証拠を照合、公開ブラウザの表示を実測。旧サイト公開元の停止は所有データ/参照の安全性を確認してから。

## 2026-11-01 202610310912保存予想原本の直接照合
- mainの `research_snapshots/202610310912.json` と `prospective_predictions/202610310912.json` をGitHub APIで直接取得。どちらも同じ10点 `[1-2-4,1-2-3,1-3-2,1-3-5,1-2-5,1-4-2,1-3-4,1-4-3,1-2-6,1-3-6]` を保存。研究snapshotの `generated_at` は2026-10-31 10:49:20 JST、`cutoff_jst` 16:00 JST、`source_deadline_jst` 16:12 JST、`status=research`,`validated=false`。prospective candidateは同日10:27 JST、`formal=false`,`scoring=false`,`attestation=pending Git remote first-add verification`。
- この10点は存在するが、初回Git保存時刻監査は未完了。正式的中率/回収率への算入不可。過去レース出走表と結果のRender本番HTTP検証は#727/#728のCIで成功済み。展示・予想のブラウザ表示とオッズ、Pages公開正常性は未検証。
- 旧リポジトリはAGENTS.mdの変更禁止に従って未変更。担当外PRには干渉せず、次に公開ブラウザの10/31予想・展示表示と初回保存監査を優先する。


## 2026-11-01 過去レース「予想」ショートカット状態同期修正
- Render本番の `2026-10-31 津12R` で、出走表6艇（守屋美穂ほか）と確定結果 `2-1-3 / 6,230円` は表示できた。一方、予想内の「展示」を開いた後に上部「予想」を押すと、URLだけ `screen=forecast` へ戻り内部ペインは展示のまま残る不具合を再現。
- PR #729 で、上部「予想」から入る時だけ内部ペインを `prediction` へ戻す最小修正と回帰テストを追加。Navigation CI run `41238782673` は success。squash main commit `39c2172bb5a95481a3a7f5968df1e80813386a53`。
- ローカル: `python -m unittest tests.test_navigation_contract` 6件成功、`node tests/site-regression.cjs` 成功、`git diff --check` 成功。Playwrightローカル実行はブラウザ実体未導入のため未実施（CIと本番ブラウザで代替確認）。
- Render deploy `dep-dbj4t9qqphnc73dpt340` は後続main `75aafbffda84320751896610d4a4615dfe02be31` で live。GitHub比較でこのcommitは修正commit `39c2172` の1 commit後（behind 0）と確認。本番ブラウザで同じ津12Rを「展示→上部の予想」と操作し、`predictionVisible=true`、`exhibitionHidden=true`、内部選択 `prediction`、保存済み研究予想10点の表示を確認。
- 予想モデル昇格なし。正式的中率・回収率は未検証のまま。#722/#723/#654（研究・収集）と#725（UIドラフト）は未変更・未統合。
- 旧 `boat-edge` は別リポジトリ/別Pagesで、CLEAN Renderに旧サービスはない。ただし旧側の証拠保全・Actions依存が未解消で安全削除条件を満たさないため、停止・削除なし。残る最大障害は旧サイトの長期復元証拠/外部依存の未証明と、#725の実データ連携未完了。

## 2026-11-01 202610310912の研究予想と確定結果の照合
- GitHub mainに保存された `confirmed_results/202610310912.json` を取得。`finish_order=[2,1,3]`、`status=confirmed`、出典は2026-10-31確定結果CSV。`confirmed_at_jst` は公式の確定判定時刻ではなく取得時刻。
- 前回確認済みの `research_snapshots/202610310912.json` および `prospective_predictions/202610310912.json` の10点に `2-1-3` は含まれない。単なる保存データと確定結果の突合としてはTop3/5/10すべて圏外。ただし初回Git保存時刻の正式監査が未完了であり、**正式的中/不的中率には計上しない**。
- `preview_snapshots/202610310912.json` と `racecard_snapshots/202610310912.json` は指定パスで404。保存展示が存在しないという全体結論ではなく、正規保存先は引き続きデータ収集担当の証拠場所と照合が必要。
- 研究予想の初回Git保存を証明するコミットは今回のGitHubコミット検索（レースコード）で特定できず、未監査のまま。旧リポジトリ変更、予想研究改変、重複PRは行わない。

## 2026-11-01 メイン開発・引き継ぎ整合
- `README.md` のレース画面直リンク仕様に残っていた `view` 表記を、稼働 `navigation.js` の `screen` クエリに一致させた。commit `96354e35a4e14b319337f0ddf62e75ec97c97103`。アプリ実行コード変更なし。
- 以前の作業ログの「10/31ブラウザ未検証」という記録は**その時点の状態**。後段のPR #729検証ログでは2026-10-31 津12Rの本番ブラウザで出走表6艇・結果2-1-3・保存済み研究予想10点表示と、展示から予想への復帰成功が記録されている。展示実データ6艇の全値が検証されたという意味ではない。
- 旧リポジトリ `boat-edge` はAGENTS.mdで変更・削除禁止。旧Pagesの公開停止はこの制約と証拠・参照依存の未検証のため実行しない。データ研究・UIドラフトPRに変更なし。

## 2026-11-01 CIのナビ変更検証漏れを修正
- `.github/workflows/site-regression.yml` のpush/pull_requestの両方に `navigation.js` を追加。以前は `navigation.js` 単独変更で既存サイト回帰CIが起動しなかった。main commit `10eef36cf267b9a29ae8da7587d9af27e8601f2a`。mainから再取得し両トリガーに存在することを確認。
- 別に旧サイト撤去issue #708を確認。旧repoはアクティブなPages公開と多くのworkflowが存在、保存証拠の独立保全とCLEAN締切前E2E成功が停止条件。#731で早朝/夜間の検証枠が拡大したが、実行成功の証拠は今後のscheduled run確認が必要。**旧サイトの停止・削除は未実施**。
- このCI修正は実行されたテスト結果ではなく起動条件の修正。CI結果、旧公開の停止、展示の6艇・締切前証明は未完了。

## 2026-11-01 締切前実レースE2E応答時刻ゲート
- PR #731のhead `7e0b3c933c5cc7f4258f62070283e1511bff36a4` のActions run `41239093712` では、履歴出走表・結果・120通りオッズがsuccess。`e2e-live-race` はPR仕様でskipped。**締切前展示が成功した証明ではない**。
- 既存 `scripts/verify_live_racecard_e2e.py` が「候補選定時に締切前」という条件だけで応答の締切前性を判定していたため、本番HTTP応答後に `meta.deadline` を解析し再度JST現在時刻と比較、締切済みレスポンスを不合格にする修正をmain `0c119339f4bbe1d10862006b67d6508a297e0bac` に適用。main再読込で反映を確認。CI・実レースの定期job成功はまだ未確認。
- 旧サイト停止にはCLEAN定期jobによる締切前カード・展示の実測と、旧サイト保存証拠の独立保全が必要。旧リポジトリは変更/削除していない。

## 2026-11-01 データ取得・保存担当（独立PR、main未統合）
- 対象: `late_preview_capture.save_preview` のappend-only保存。既存の後続レースファイルとの衝突で、同一CSV内の先行レースだけ書き出してから `FileExistsError` となる非原子的バッチを発見。
- 変更: バッチ全件の保存先を事前計算し、既存証拠との衝突を全件preflight。衝突時は一件も新規保存せず、既存ファイルは変更しない。回帰テスト2件追加。
- 対象ファイル: `late_preview_capture.py`, `tests/test_late_preview_capture.py`。予想モデル・画面・main・既存PR #654の変更ファイルには手を加えない。
- 実測: GitHub mainの収集ワークフロー `late-preview-capture.yml` と `research-live-preview-evidence.yml` は別々の5分間隔スケジュールを持つ。役割（isolated evidence / late research candidate）が異なり、無条件の停止・削除は行わない。
- 取得品質: 2026-10-31蒲郡8Rの6艇保存実績は過去記録として存在するが、T-12時点の受信証拠は未確認。公式beforeinfo / BOATERS / 競艇日和 / 実オッズの6艇同期取得保証も未証明。T-12保証を宣言しない。
- テスト/CI: PR側CI実行結果で別途確認。公開本番の変更なし。
- 次: PRの回帰テストを確認し、予定実行artifactの受信時刻・HTTP失敗率・6艇ペア率を収集。#654のpaired coverage差分は重複実装せず取り込み判断をメイン担当に委譲。

### 2026-11-01 継続: 上流取得障害の明示
- GitHub Actions実測: run 41234665968（JST 2026-11-01 04:32頃）で STT/TKZ/SUI/original_exhibition/od3 がすべてHTTP 404。保存0、6艇ペア0、T-12証拠ペア0。Actions成功終了と取得成功は別。
- 修正(PR #723に追加): `collect_late_preview_once.py` が全源失敗時 `source_unavailable`、一部失敗時 `partial_source_failure`、全取得時 `sources_retrieved` と集計し、5源のavailable/unavailable数と保存件数を報告。`late-preview-capture.yml` Actions summaryに上流状態を明示。
- テスト: 404全件失敗・一部失敗の回帰テスト2件追加。今回の追記後CIは結果を確認するまで未検証扱い。
- 未完了: 実データのT-12完全6艇ペア、公式beforeinfo/BOATERS/競艇日和の可用性と時刻証拠、収集ジョブ依存関係の安全な整理。main未統合。

### 2026-11-01 続行: 404の公開時間帯判定
- 既存 `scripts/collect_live_preview_evidence.py` に上流CSV想定時間帯 `08:00-22:59 JST` の記述を確認。以前の04:32 JSTに観測された5件の404を恒常的な取得元障害と断定しない。
- PR #723で午前8時前の全HTTP 404を `not_yet_expected`、各ソースを `before_expected_publication_window` として明示する判定を追加。午前8時以降の404は未公開・欠落の可能性を別分類。既存のスケジュールは依存関係未確認のため停止しない。
- 回帰テスト: 午前4:32の全404を期待公開前と判定するケースを追加。実データ取得保証とは区別し、今回の追記後のCIは結果確認まで未検証。
- 次の実測: 08:00-22:59 JSTの実行でHTTP応答、CSV行、6艇STT+TKZ完全ペア、T-12受信・ソース時刻を照合する。結果がなければ成功扱いしない。

### 2026-11-01 取得レポートの空CSV識別（PR #723）
- 既存捕捉でHTTP成功かつCSVゼロ行を `sources_retrieved` と表現する曖昧さを確認。5源が取得できてもレース行が無ければ `sources_retrieved_no_rows` と表示し、`race_rows_total` を集計してActions summaryにも記録する修正とfixtureテストを追加。
- これは取得ジョブの分類精度改善であり、公式/BOATERS/日和の実ライブ取得を実証したものではない。main未統合。最新変更のCI実行結果は確認まで未検証。

### 2026-11-01 データ取得監査継続 — エラー原因分離
- PR #723に、HTTP/transport失敗 (`source_unavailable`) とローカル書込衝突・形式不正 (`capture_invalid`) を別の状態として報告する変更を追加。`sources_unavailable` に保存時 `FileExistsError` を誤計上しない。部分的な保存処理失敗は `partial_capture_failure` と区別する。
- 既存テストの同一バッチ再実行ケースに `capture_invalid=5`、`sources_unavailable=0` を検証する回帰アサーション追加。収集Actions summaryもエラー件数を区別。
- 実際のT-12/6艇取得保証は未成立。追加修正のCIは未確認。main統合なし。

### 2026-11-01 CIトリガー修正（PR #723）
- 原因: `late-preview-evidence-tests.yml` のPR pathsには `collect_late_preview_once.py` と `tests/test_collect_late_preview_once.py` が含まれておらず、収集レポートの続行修正コミットで対象CIが再実行されていなかった。
- 変更: 取得レポート・テストファイルをpathsへ追加し、同ワークフローで `test_collect_late_preview_once.py` を明示実行。既存CIを拡張し、重複CIは新設しない。
- 検証: 変更後Actions実行を確認するまで成功扱いしない。main未統合。

### 2026-11-01 CI実行証拠（データ収集PR #723）
- Actions run `41237387015` / job `124643904867` / commit `df04f6c0071e62541e0d814b853e40bb162bd2f3`: `Late preview evidence integrity` 成功。`test_late_preview_capture` 3件および `test_collect_late_preview_once.py` 6件の計9件が成功。URL: https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/41237387015
- 収集CIのpush対象に作業ブランチを追加し、対象コードの継続変更でも実行されるように修正した。PR作業完了・main統合時には一時的なブランチ指定を除去すること。
- ここで証明できたのはfixtureを含む保存・取得状態判定のテスト成功のみ。ライブ上流データのT-12完全6艇ペア、公開時間帯の取得成功、BOATERS・競艇日和の6艇確保は未証明。
- 別ワークフロー `cross-model-content-audit-tests.yml` の失敗は残存（担当範囲外）。main未統合。

### 2026-11-01 定期収集の公開前実行削減（PR #723）
- 実ログ: research independent late preview schedule run `41213415508` (2026-11-01 00:08 JST) は5源HTTPError、STT/TKZ完全ペア0、T-12ペア0、保存0。成功のCI結論は上流取得成功を示さない。
- 既存独立収集 `late-preview-capture.yml` は07:03-07:58 JSTにも5分刻みで起動する設定だった。CSVの想定公開窓が08:00開始であるため、この12回/日の公開前実行を除去し08:03-21:58 JSTに変更。`test_preview_schedule_jst.py` のUTC日跨ぎ回帰条件を更新。
- 新しいCIは作成せず `late-preview-evidence-tests.yml` の既存ジョブでスケジュール回帰テストを実行する。run `41237582288` の結果確認待ち。削減はスケジュール設定上の12回/日であり、GitHub実際の実行回数・コスト削減の実測値ではない。
- 公式beforeinfo、BOATERS、競艇日和、実レースT-12同時6艇取得は未確認。PR #654と予想/画面コードは未変更、main未統合。

### 2026-11-01 実データ時刻照合（Actions既存run確認、PR #723）
- `41192395459`（2026-10-31 19:21 JST頃）: `probe_today_beforeinfo.py` 実通信ログで2026-10-31のtkz/stt/sui各148行、future eligible各1、`VERIFIED_SIX_LANE 202610311510` を確認。6艇取得の実例であり、T-12受信時刻保証ではない。
- `41224135096`（2026-11-01 02:21 JST頃）: `verify_real_beforeinfo_source.py` のログで2026-10-31のtkz/stt/sui各156行、検査6レースすべて6艇項目検証済み。ただし予想保存がある6レースでpreviewが予想生成前に利用できた件数は **0/6**、予想生成後の観測が **6/6**。T-12正式予想への採用禁止を維持。
- `41206846846`（2026-10-31 22:43 JST頃）: live official odds probeは `NO_UPCOMING_RACE_TO_PROBE`。Actions成功を実オッズ120通り取得成功とは解釈しない。
- `41213415508`（2026-11-01 00:08 JST頃）: 5源HTTPError、完全6艇ペア0、T-12ペア0。時間帯とレース状況が異なるため日中の取得成功例と矛盾しない。
- 以上は既存Actionsログの実測であり、新しいライブT-12成功・BOATERS/競艇日和取得を証明しない。PR #723のみで記録。main未統合。

### 2026-11-01 T-12レース単位監査（PR #723）
- `scripts/audit_late_preview_evidence.py`: 完全6艇STT/TKZペアのレースコード、T-12以前に両ソース時刻・受信時刻を満たしたレースコード、STT/TKZ別の実受信・ソース観測時刻を監査JSONに明示。件数のみで証拠なしに成功と報告しない。
- `tests/test_audit_late_preview_evidence.py` でレースコードと時刻を検証する回帰テスト追加。重複CIは作らず既存 `late-preview-evidence-tests.yml` に監査テストとファイルパスを追加。
- run `41237820889` の対象テストステップ4件は成功を確認（job全体の完了判定は追確認が必要）。このテストは保存fixture検証であり、11/1の新たなT-12実データ成功を意味しない。
- 予想研究・サイト表示コードに触れず、main未統合。

### 2026-11-01 実データ監査の件数誤認防止（PR #723）
- `scripts/audit_late_preview_evidence.py` の既存 `rglob('*.json')` は `collection_summary.json` 等の非レースJSONを不正なレース証拠として数え得た。ディレクトリ種別と12桁ASCIIレースコードを先に検査し、監査集計対象からメタデータを除外。
- `tests/test_audit_late_preview_evidence.py` にサマリーJSONでinvalid/recordsが増えない回帰テスト追加。既存Actions run `41237934711` の4系統テストステップ成功を確認、全体終了判定は追確認。
- 新しい実ライブT-12完全6艇ペアを実証したものではない。PR #723のみ、main未統合。

### 2026-11-01 T-12不合格理由のレース別出力（PR #723）
- 6艇完全ペアであってもT-12時刻に間に合わないレースについて、STT/TKZそれぞれの時刻判定・受信時刻・レースコードを監査JSONの `paired_complete_but_not_t12` に出力するよう修正。完全性合格と予想時点の利用可能性を分離する。
- `tests/test_audit_late_preview_evidence.py` に不合格理由の回帰アサーション追加。Actions run `41238036094` の4種ユニットテストステップ成功を確認。実レースT-12完全ペア取得は未証明。
- main未統合、サイトとモデルは未変更。

### 2026-11-01 PR #723統合前の競合確認
- GitHub APIでPR #723は `mergeable=false`。未統合PR #654と `.github/workflows/late-preview-capture.yml` および `collect_late_preview_once.py` に変更範囲重複を確認。両PRのパッチ内容も照合済み。#654はペア保持・収集報告、#723は保存衝突対策・取得失敗分類・T-12監査なので、一方を無条件で削除/上書きできない。
- PR #723の対象テスト最新成功run `41238036094`、別系統 `cross-model-content-audit-tests.yml` は失敗履歴あり。現状でmain統合しない。
- 統合前に#654のペア保持ロジック、#723の状態分類・監査を両立させ、同一の収集ワークフローで回帰テストし、PRのmergeable/CIを再確認する。`late-preview-evidence-tests.yml` の一時的作業ブランチpush条件を統合前に削除する。

### 2026-11-01 収集系PR #654の機能取り込み（PR #723）
- `collect_late_preview_once.py`: #654が追加する `paired_six_lane_coverage(day,root)` をsource health分類と共存させ、既存のSTT/TKZ完全6艇ペア件数・T-12観測件数をレポートに残す。
- `late-preview-capture.yml`: Actionsログとステップサマリーに同ペア監査を追加。既存90日証拠保持設定は#654の14日要件を包含している。重複workflow/PRは追加していない。
- `tests/test_collect_late_preview_once.py`: ペア集計フィールドとデータ未取得時のペア0件を追加検証。
- CI: Actions run `41238539248` がcompleted/success、4種テストステップすべて成功。実ライブT-12成功を示すものではない。
- 残課題: #654/#723はGit上まだ別PRのため、mergeable再確認・#654の独立プローブ変更を失わない統合計画が必要。main未統合。

### 2026-11-01 収集PR #654・#723 の統合回帰検証
- PR #654 の `paired_six_lane_coverage` を #723 の取得分類と共存させた変更（`8e647b28`、`33d1e013`、`eb89a9c4`）について、Actions run `41238539248` の4系統テスト成功を確認。
- さらに `late-preview-evidence-tests.yml` の既存CIに `tests/test_late_preview_paired_coverage.py` を追加し、実際の完全/不完全STT/TKZペア、レース一致、T-12境界も同じCIで確認する（run `41238664430`）。新しいCIワークフローは増やしていない。
- PR #723 は `mergeable=false` を再確認。#654 とのGit競合解消、後継PRの統合順序決定および作業ブランチ専用CI条件除去は引き続き必要。main未統合。

### 2026-11-01 PR #723統合ゲートの再検証
- mainとの差分をGitHub compareで実測: #723作業ブランチはmainから `ahead=46`、`behind=27` のdiverged。`mergeable=false`。#654とも収集2ファイルが重複しており、単純にmainを親に置くGitコミット等で競合を隠すことは禁止。
- #654のペア集計は#723内で取り込み、5群のテストがrun `41238664430` で成功済み。作業ブランチのCIに入れた一時的なpush指定は `.github/workflows/late-preview-evidence-tests.yml` から解除（commit `7508662`）、mainのみを残した。
- 次の統合担当作業は#654の独立プローブ変更を保護したうえで競合を実際に解消し、最新mainとの差分と全CIを再検査すること。今回main未統合、実データT-12 6艇完全性未証明。

### 2026-11-01 収集PR #654差分の最終照合
- PR #654の変更3ファイルを差分照合。`scripts/research_preview_csv_probe.py` のimport修正は既にmainに存在し、#723ブランチとSHA一致。`collect_late_preview_once.py` の `paired_six_lane_coverage` と `late-preview-capture.yml` のpaired audit出力は#723に取り込み済み。#654の保持期間14日は#723の90日が包含する。
- #723は `mergeable=true` をGitHubで確認。統合後CIは `41238926355` integrity success / `41238926467` capture success / `41238926369` source diagnostics success。収集runでは `not_yet_expected`、5 HTTPError、保存0件、T-12ペア0件。
- #654自体は未統合で残す（別担当のPRを無断クローズしない）。二重統合は避け、メイン統合担当は#723の統合後に#654をclose/supersededで整理可能か確認する。mainは本担当から変更しない。

### 2026-11-01 最新main再取り込み・収集PR検証
- mainが進行中に前進したため、既存PR #723へ最新mainを保全して再取り込み。merge commit `c2076f3095c31fa630c87955f852c2d9662e7832`、GitHub `mergeable=true`、比較で `behind=0` を確認。main本体は変更していない。
- 統合後Actionsの実ジョブで `Late preview evidence integrity` run `41239159375` success、`Research preview CSV source diagnostics` run `41239159337` success、`Preview capture (pull_request)` run `41239159305` success を確認。これは収集処理/テストの正常終了であり、ライブT-12 6艇取得成功ではない。
- #654の処理は#723へ保持済み、#654の独立PRは無断終了しない。データ取得側main統合はメイン開発担当に引き継ぐ。

### 2026-11-01 6艇ペア欠損原因のレース別監査（PR #723）
- `scripts/audit_late_preview_evidence.py` の `incomplete_pair_reasons_by_race` を追加。T-12以前の要否とは別に、レースごとにSTT/TKZの `missing` / `incomplete` / `complete` を出力し、ペア不足の根本原因を区別。
- `tests/test_audit_late_preview_evidence.py` に受信時刻が無効なTKZを欠損扱いする回帰アサーションを追加（commit `eaf180902`）。今回変更を含むCIの成功はまだ未確認。過去CI成功を新修正の成功と混同しない。
- 現時点でGitHub Actionsの11/1 JST 08:00以降の公開時間帯に実行された定期preview保存を確認できず、実ライブT-12完全6艇ペアは依然未証明。main未統合。

### 2026-11-01 最新欠損診断のCI実証（PR #723）
- 専用CIが最新修正に反応しない問題に対し、既存 `late-preview-evidence-tests.yml` のpush対象へ作業ブランチを一時的に追加。run `41239801304` / commit `5aa3dee0` において保存・取得分類・JST日跨ぎ・T-12監査・6艇ペアの5系統すべてテストステップ成功、jobもsuccess。
- これは `incomplete_pair_reasons_by_race` を含む現行コードの回帰テスト成功であり、実競走のT-12データ取得成功ではない。統合前に作業ブランチ専用CI条件を除く必要がある。main未統合。

### 2026-11-01 PR #723 継続引き継ぎ（GitHub API再確認）
- 対象リポジトリは `ikst2512-eng/boat-edge-clean`。PR head `996a2b9` 時点で main から57コミットahead / 4コミットbehind、mergeable=false。mainの差分は `docs/WORK_STATUS.md` と `scripts/verify_live_racecard_e2e.py`。履歴を失うforce pushやmain直接統合はしない。
- 最新の専用CI通過は先行作業の報告に基づく。GitHub APIのcommit-PRワークフロー検索は `996a2b9` と今回の作業コミットで0件だったため、この検索だけで新たなCI成功を主張しない。
- 一時的なpushブランチ指定を `.github/workflows/late-preview-evidence-tests.yml` から除去し、`push: main` と `pull_request` の既存テスト経路を維持（commit `5066d1202d52fc1fde30e36ebc7baf20560d4742`）。
- 今回の作業はT-12実データ収集の成功を示さない。STT・TKZの同一レース・同一締切の6艇データ、受信JST時刻、ソース時刻、締切前12分の照合は未完了。
- 次: `docs/WORK_STATUS.md` のmain追加14行を保存したままPR側の記録と統合し、CIを再確認。実レースについて08:00以降の定期実行ログ・artifactを照合。モデル/UIは触らずメイン担当のmain統合判断に委譲。


## 2026-11-01 旧サイト撤去ゲート強化PR #733統合
- 既存PR #733を重複PR作成せずmainへsquash統合: `bd9b3e6ff11f79148096d2f367fb0a92f27fb49c`。既存 live E2Eで `tkz` と `stt` 双方の `observed_at` を独立照合し、各取得時刻が未来や締切後なら不合格、各source SHA256がない・不正なら不合格。mainのコード再取得で実装を確認。
- PR head `7da145c0c1d62b0cebf0d026c817732266fb27e6` のActions run `41239549160` は歴史出走表・結果・120オッズ・構文でsuccess、`e2e-live-race` はPR実行でskipped。締切前実測成功はなお未確認。
- PR #732のRender deploy `dep-dbj50gjil8vc73a6dom0` がliveと確認済み。今回統合した#733のRenderデプロイ・定期E2E結果はまだ未確認。独立証拠保全とCLEAN実レース6艇展示成功を満たすまで旧repo/Pagesは停止しない。

## 2026-11-01 #733本番反映とソース監査スキーマ確認
- Render `list_deploys` で `dep-dbj520ivcj2c73eknlh0` / commit `bd9b3e6ff11f79148096d2f367fb0a92f27fb49c` finished 2026-10-31 20:35:57 UTC、status `live` を確認。後続 `eb13773c` は確認時点で更新中であり、最新版のlive状態を同一視しない。
- main `clean_racecard.py` の `beforeinfo` source audit構造 `sources.tkz/stt.observed_at` および `sha256` が既存 #733 E2Eの検査対象と一致するとコード照合。コード・スキーマ一致は実レースの検証成功ではない。
- 旧repo/publicationは未停止。次はscheduleによる`e2e-live-race`の実行結果で `EXHIBITION_PASS` と独立時刻・SHA証拠を確認すること。旧データの独立保全も残る。

## 2026-11-01 締切前E2Eの独立締切照合
- main `6f06a63c051cd90ae678087af738ed109eea9567` にて既存の `scripts/verify_live_racecard_e2e.py` を修正。これまでAPI応答の `meta.deadline` が締切前かは確認していたが、独立した開催情報から得た締切と同じか検証していなかった。候補選定時の締切を保持し `response_deadline != source_deadline` は不合格にする。取得元不一致時の偽陽性を防止するためで、収集機構・モデルは変更なし。
- mainからコード再取得し修正の存在を確認。実スケジュールCIの成功、6艇展示データ取得成功は未確認。Render本番は前回 `eb13773c` がlive、最新mainに対するデプロイは別途確認が必要。旧Pagesや旧repoの停止なし。

## 2026-11-01 Render本番確認（01統合）
- Render workspace `My Workspace` の web service `boat-edge-clean` (`srv-dbcthfrncjis73djj8qg`) は **別repo `ikst2512-eng/boat-edge-clean` の main** をauto-deployする。旧 `ikst2512-eng/boat-edge` のPR/CIをCLEANの本番反映と混同しない。
- 2026-11-01 05:39 JST、Render deploy `dep-dbj5395h3lcs7386ofkg` が `live`。SHA `4659cbe66ff64b81a0d5874eafe8608f2d01d585` は確認時のCLEAN main最新commitと一致。Renderログでbuild successful、`python server.py` 起動、`HEAD /` と `GET /` が200を確認。
- これは**トップHTTP疎通とデプロイ一致の証拠**であり、過去日(2026-10-31)の出走表/予想/展示/結果4タブ、API成功、実機Safariの証明ではない。外部ブラウザからの取得はこの確認環境で未成立。
- 旧サイト停止は issue #708 にある証拠保全・移行後機能同等性・ロールバック条件の未達につき未実施。現在のRender一覧はCLEAN web service 1件で、旧公開は旧repoのPages側で管理。旧repoの証拠やpublishを無断破棄しない。
- **次のP0**: CLEANの10/31実レースに対するAPI/画面E2Eを既存テストで証明→旧予想原本・初回Git時刻/SHA・結果原本の復元可能バックアップ照合→旧Pages/writerを段階停止。新規の監査ワークフローを重複作成しない。


### 2026-11-01 main追記保全（PR #723）
- main側の#733統合・Renderデプロイ・締切照合・旧サイト停止条件の記録を原文保持してPR文書へ追記した。競合解消のコードマージやmain統合の完了を意味しない。


## 2026-11-01 12場の404原因確定（非開催）
- Renderログ `2026-10-31 20:30–20:36 UTC` で翌11/1の `jcd=12`、1R/5Rの404を観測。12場は住之江。BOAT RACE公式の開催予定は住之江11/5–11/10（高松宮記念特別競走）で、11/1は非開催。独立した11/1の開催場一覧も住之江を非開催としている。**この404は非開催日への問い合わせであり、開催中出走表の不具合ではない**。以前の疑義を訂正。根拠: https://www.boatrace.jp/ と https://boatrace-techo.com/?date=2026-11-01 。
- これは旧サイト撤去ゲートの締切前6艇展示・進入・時刻証拠の成立を示さない。実際の開催場で定期E2E実測成功を得る必要がある。旧repo/Pages停止・削除なし。

## 2026-11-01 T-12ゲート#734 の実行可否を確認
- 既存PR #734はmain commit `d7ebf6711a8dd5aa4a33b4b5c50a7c5590396c74` へ統合。独立 `tkz` / `stt` ソースの時刻がいずれも締切12分前以前なら `T12_COMPLETE_PAIR_PASS`、未証明なら `NO_T12_SIX_BOAT_PAIR_VERIFIED` で不合格とする検査が追加された。
- PR headのActions run `41240118410` では履歴出走表、結果、120オッズ、構文の4ジョブsuccess。一方 `e2e-live-race` はPR時の仕様でskipped。**T-12成功の証拠はまだない**。
- 本日最初の定期サンプルは09:30 JSTの設定で、05:43 JST時点ではこの時間に達していない。今回の調査で過去の実レースE2E成功の新証拠は得られなかった。実測に基づく停止判定は保留し、旧サイトは変更しない。


### 2026-11-01 PR #723 最新mainとの競合解消
- `docs/WORK_STATUS.md` のmain側追記（旧サイト停止ゲート・Render・非開催日の404判定）を失わずにPR側へ保全し、main側の `scripts/verify_live_racecard_e2e.py` を変更なしで保持。
- GitHub merge commit `2c7b6d2654bafff8753dff1d105239cd7594b637` をPR headへfast-forwardで適用。適用直後のcompareは mainからbehind=0、PR `mergeable=true`。**mainへは未統合**。
- merge commitに紐付くPR Actionsの検索結果は0件（取得時点）。従前の `41239801304` のsuccessはこのmerge commitの専用CI成功を示さない。今後CIが走れば該当head SHAとjob conclusionを確認する。
- 実レースT-12の完全6艇STT+TKZペアは未証明。対象レースキー・締切・双方の受信JST・source SHAと保存時刻の実測が必要。


## 2026-11-01 T-12証明の偽陽性防止
- main `f36432cabf032e4849bad33f86f1f183eb6e6903` で既存 `scripts/verify_live_racecard_e2e.py` を修正。以前の #734 は両ソースの観測時刻がT-12以前なら、API応答がT-12後でも `T12_COMPLETE_PAIR_PASS` となる可能性があった。APIのHTTP応答を読み終えたJST時刻 `response_received_at` を記録し、**ソース双方のT-12以前 + HTTP応答のT-12以前**が揃う場合だけ合格とする。main再読込で実装確認。
- 当該変更は実測成功の証明ではなく検証条件の修正。PR #734の履歴CIでは実レースE2Eがskip。次は開催中レースについてT-12以前のAPI応答ログで成功確認し、原本保全後に旧サイトを停止する。旧repoの変更なし。


## 2026-11-01 PR #723 統合後のRender・Actions検証
- GitHub PR #723 は squash merge `d3c6fbaa89c60011b4ecf747c4b7cf3f52231015`、merged=true。main の `collect_late_preview_once.py` に取得分類・6艇ペア監査が存在し、一時的なpush作業ブランチ指定は消えている。
- Render deploy `dep-dbj58a6417fc73aivi2g` は同一SHAで `live`（2026-11-01 05:49 JST頃）。デプロイ一致は本番実レースでのT-12取得成功の証明ではない。
- GitHubの `fetch_commit_workflow_runs` はPR-triggered runのみ検索するため、main squash SHAの空配列は「main CI未実行」の証拠にしない。PR head `87c6330` の4系統CI成功は既に検証済み。
- 実行log: Preview capture run `41240537819` / capture job `124653322037` は `capture_source_status=not_yet_expected`, available=0, unavailable=5, rows=0。STT/TKZ等5ソースはHTTP 404、`paired_complete_12min_observable=0`、保存0。04–05 JST付近の公開期待時間外での取得であり恒常的障害を意味しない。
- Audit scheduled preview capture runs `41240537814` / job `124653321344` はログ中 `scheduled_runs=0`、`latest_scheduled=null`。当該監査で観測した範囲の値でありGitHub全run不在の断定ではない。
- 次: 08:00 JST以降の独立scheduled captureの実run id / artifact / HTTP応答と `t12_evidence_by_race` の同一レース6艇STT+TKZ受信時刻を検証。取得されるまではT-12実証未達、旧repo/Pages停止禁止。

## 2026-11-01 重複PR #654の安全整理
- #654の変更対象3ファイルをmainと照合し、paired_six_lane_coverage、ステップ要約、import修正が#723統合済みであることを確認。証拠保持期間はPR案14日より強い現行90日。重複の#654へ根拠をコメントし、state=closed / reason=duplicate とした。#654の古いコードをmainに再適用していない。
- 実レースT-12 COMPLETE_PAIR成功は未証明。旧repo/Pagesや保存原本は変更していない。


## 2026-11-01 定期preview監査を日次自動化
- 既存 `.github/workflows/audit-preview-scheduled-runs.yml` は従来 `pull_request` / `workflow_dispatch` のみで自動定時監査がなく、実行ログ `41240537814` の `scheduled_runs=0` を翌日以降自動追跡できなかった。
- main commit `2bf7a5361f9bbb8b2efcd066c88a07f1741d28a7` で既存workflowへ `cron: '17 14 * * *'`（JST 23:17、収集予定終了後）を追加。新しいworkflow・取得writer・モデル変更は作っていない。main再取得でcron反映を確認。
- 注意: GitHub scheduled Actionsの起動は遅延・欠落し得る。設定反映のみ確認済みで、初回の定時実行成功・収集のT-12完全6艇ペアは未確認。監査はrun件数と状態のみ集計し、race evidence本体はcapture artifactで別途確認が必要。
- 次: 08:03–21:58 JSTのcapture scheduled run、23:17 JST以降のaudit scheduled run、それぞれのartifactで同一レースSTT+TKZ 6艇の締切・受信時刻を実測する。取得できなければ欠損原因とジョブ動作を分離して修正する。

## 2026-11-01 夜間監査で定期収集未実行を検知
- 既存 `scripts/audit_preview_scheduled_runs.py` は定期収集run 0件でも成功終了していた。main `c45566a7e274704bf767bc5de1cabf6f7d24f4d7` で、**監査自体がschedule起動された場合のみ**同日JSTの `late-preview-capture` scheduled runが0件なら`NO_SCHEDULED_PREVIEW_CAPTURE_TODAY`でexit nonzero。PR/手動監査は診断のままで失敗判定しない。main再取得で修正反映確認。
- これは収集データ成功の証明ではなく、ジョブが丸ごと未実行となる障害の検出強化。CIの最新実行成功と当日8時以降の完全6艇T-12証拠は未確認。旧サイト撤去の可否は変わらない。


## 2026-11-01 定期preview監査24時間鮮度チェック
- 既存 `scripts/audit_preview_scheduled_runs.py` に `scheduled_last_24h` と `schedule_health` を追加。手動起動は件数へ混ぜず、タイムスタンプ不正・24時間以前のrunも鮮度ありとしない。成功runの存在とT-12保存証拠は分離したまま。
- 既存 `audit-preview-scheduled-runs.yml` に回帰テストを追加、新ワークフローは作成していない。テスト `tests/test_audit_preview_scheduled_runs.py` は収集0件、古い実行、直近実行、不正日時の4ケース。
- main実装コミット: `f39c499`, `01419b1`, `8091efa`, `c96b172`。現時点では新規テストのGitHub Actions合格は未確認。実レースT-12完全6艇取得も未証明。
- 次: 監査workflowのCI結果と定期runを確認し、capture artifactの `t12_evidence_by_race` をレースID・6艇・受信JST・締切時刻と照合する。旧サイト停止なし。

## 2026-11-01 日次収集監査のコード整備
- 最新mainの実装を再点検し、`scripts/audit_preview_scheduled_runs.py` の `datetime` import重複（2行）を1行に整理。commit `460c614ce5a221fb7ede0803be9ebac3d1f76b79`、main再取得で確認。日次監査の既存ロジック・実行時刻・取得元は変更なし。
- 先行main `c96b1720` / `8091efa7` で直近24時間の定期実行分類テストは追加済み。これを重複実装しない。実レースT-12ペアの検証成功は引き続き未確認、旧公開を停止しない。


## 2026-11-01 定期監査の成功・失敗内訳
- 直近24時間のscheduled runを成功/失敗に分ける `successful_scheduled_last_24h` / `failed_scheduled_last_24h` を既存監査に追加（main `6bc9605`）。手動実行を成功数に混ぜない回帰テストを `tests/test_audit_preview_scheduled_runs.py` に追加（`2d6a1f6`）。
- 既存mainには夜間scheduled監査時に同日JSTのcapture scheduled runが0件なら失敗終了するゲートも実装済み。定期実行が0件の原因を「ソース404」と同一視しない。
- 変更後のGitHub Actions合格はまだ確認できていない。07時台以前の手動/PR captureが成功してもT-12証拠と扱わない。08時以降の実scheduled runと `late_preview_audit_report.json` を取得し、race code・6艇完全性・受信時刻を精査する。
- 予想モデル、UI、旧サイトは未変更。旧サイト停止ゲートは未達。

## 2026-11-01 夜間監査で全収集失敗を検出
- 夜間監査が当日の定期収集run数を数えるだけだったため、1回以上実行されたがすべてfailureの場合にも正常終了する可能性があった。main `d27ba36e8064a8f850c711bc6e1445edb86221ea` で、夜間schedule監査時のみ当日定期収集の全ジョブがcompleted/failureなら `ALL_TODAY_SCHEDULED_PREVIEW_CAPTURES_FAILED` として不合格にする。手動・PR監査は診断のまま。main再取得で反映確認。
- この変更のCI/実行結果およびT-12実レース完全6艇ペアは未確認。旧サイトは停止・変更していない。


## 2026-11-01 監査ワークフローのmain push起動漏れ対処
- `.github/workflows/audit-preview-scheduled-runs.yml` に `push: branches [main]` と監査スクリプト・テスト・workflowパスの絞り込みを追加。commit `6044c93f3790c119671a5ed832c8b4abf9dd4d9f`、main再取得でpushトリガーと回帰テスト登録を確認。
- 先行の監査コードは `scheduled_last_24h` と成功/失敗数を報告し、nightly scheduleで同日JSTのcapture 0件なら失敗する。CIの成功と6艇保存証拠は別物。
- コミット連動のPR run APIでは当該main pushの新規実行は表示されず、CI合否は未確認。main pushの実runをGitHub Actionsのworkflow履歴で別途確認する必要がある。
- 実レースT-12完全STT+TKZ 6艇ペアの根拠は未取得。08時以降のscheduled capture artifact（race code、source SHA、受信JST、締切）確認まで旧サイト停止不可。

## PR #725 integration gate a5d559d9
- 既存のBOATERS風ページ実装を最新mainを基点とした統合候補として準備。実測の個人長期率は未完成。統合後の本番動作は要検証。

## 2026-11-01 夜間監査の失敗ゲートに回帰テスト追加
- 日次判定を純関数 `daily_capture_health` に分離 (`4ddabd6da85c59372a459e86a7afd7be23885fa8`)。収集0件、scheduled全failure、成功混在、手動監査免除のテストを追加 (`d1dc847d0600400dd410ad8d2cf3f992516a8c38`)。push CIトリガーは既存mainに存在。
- CI成功、当日scheduled収集、実レースT-12完全6艇ペアは未確認。旧repo/Pagesは未変更。


## 2026-11-01 実artifact原本の内容照合
- GitHub Actions run `41240537819` の artifact `13056953412` ZIPを直接取得し、`late_preview_capture_report.json` と `late_preview_audit_report.json` を展開して内容確認した。単なるジョブログ推測ではない。
- 2026-11-01 JST 05:47:33のSTT/TKZ/SUI/original_exhibition/od3は各HTTP 404、status=`not_yet_expected`、sources_available=0、sources_unavailable=5、saved_total=0、race_rows_total=0。
- audit原本は records=0、invalid=0、paired_complete_6boat_stt_tkz=0、paired_complete_12min_observable=0、t12_evidence_by_race=[]。公開想定時間前の実行結果なので日中の失敗・T-12の成功のいずれも断定できない。
- 実scheduled captureの最新run一覧は現接続のGitHubアクションで取得できない。次の検証対象は08時以降に起動されたschedule eventのartifact。旧サイト停止禁止、モデル/UI変更なし。

## 2026-11-01 PR #741 四タブ公開Pagesブラウザ検証統合
- 既存PR #741を確認し、`deploy-pages.yml` のPlaywright公開テストが `card/exhibit/forecast/result` 4タブの可視状態（resultは `#resultSection`）を検証する修正を確認。PR head `652112dc7a1be359045c633578611dcb0643330d` のGitHub Actions run `41241757093` で `check` / `publish-smoke` ともsuccessを実確認。mainへsquash `98c08e2e728b22ab4fdf14286bb0b31958aee095` として統合。
- 成功したのはPRでの既存検証ジョブ。**統合後のGitHub Pages再公開とiPhone Safari実機操作は未確認**。実レースT-12展示6艇証拠も未確認であり、旧repo/Pagesは停止していない。

## 2026-11-01 PR #741 公開Pagesブラウザ再検証完了
- 統合済みPR #741（main squash `98c08e2e728b22ab4fdf14286bb0b31958aee095`）の GitHub Actions `Publish BOAT EDGE CLEAN` run `41241825770` / deploy job `124657111905` はsuccess。
- 実jobログに `DEPLOYED_BROWSER_PASS https://ikst2512-eng.github.io/boat-edge-clean/` を確認。公開URLのブラウザで24場、12R、`card/exhibit/forecast/result` 4タブの表示判定とJSエラー検査が成功。
- **前記「Pages再公開未確認」を今回解消**。ただしiPhone Safari実機、個別実レースの4タブ中身、Render APIの締切前6艇T-12証明は未確認。旧repo停止は禁止のまま。

## 2026-11-01 本番応答時切断ログの整理（PR #742）
- Render本番でレース切替中の `BrokenPipeError` が観測されていた。既存PR #742の `server.py` はレスポンス本文の `wfile.write` のみ `BrokenPipeError` / `ConnectionResetError` を捕捉し、無害なクライアント切断の例外ログを抑制する。HTTP状態・データ判定は変更しない。
- PR head `ba2017442d1ffc3ce8ebaa84959545a612ea523c` に対するCLEAN regression run `41241878387` がsuccess、Navigation regressionもsuccessと確認。main統合 `80b1adbc504a4450414e319b11ce812de5004c47`。統合後デプロイと実ブラウザ検証は未確認。
- #741の4タブ公開Pages smokeはPR CIで成功済み。公開後のiPhone Safari実機表示と実レースT-12完全6艇ペアは未証明。旧repo/Pages停止なし。


## 2026-11-01 PR #725統合後の過去日程5xx回帰修正（PR #740）
- 既存PR #725はmain `48b8e7f73ba543abfa8e9def115925f3e8837a6d` に統合済み。BOATERSを参考にした独自の1ページ予想UIを再実装せず、差分を監査した。
- #725で後退した過去日程APIのHTTP 5xxフォールバックと削除されていた回帰アサーションをPR #740で復元。当日5xxはfail-closedのまま。main squash `675a0bd4667f19549db08e2b8361a4a92e8ffca0`。
- ローカル: navigation contract 6件OK、site-regression全件PASS、diff-check PASS。PR head `09f31228995b7e36b9a573220330045f48a4f315` のNavigation `41241650214`、CLEAN regression `41241650136`、Cross-model `41241650186`、Daily findings `41241650193`、Official odds `41241650176`、Dual verification `41241650122`、daily schedule `41241650160` はsuccess。Mobile browserはpath filterでskip。
- 統合commitのpush ActionsはDaily findings `41241737540`、Dual verification `41241737526`、Mobile browser `41241737469`、CLEAN regression `41241737677`、Navigation `41241737610`、Official odds `41241737605`、Odds parser `41241737589`、Pages publish `41241737457` がsuccess。
- Render deploy `dep-dbj5f1e417fc73aj5fbg` は同一commitでlive到達。公開Render/Pagesの `2026-10-31 津12R` を実ブラウザ確認し、確定結果「2-1-3」/払戻6,230円が予想より上、Top10、展開、先頭艇別、6艇成績枠を表示。証拠不足値は「未取得」で捏造表示なし。
- モデル昇格・正式採点・仮想購入・精度向上主張なし。旧repo/旧Pagesは停止していない。最大の残件は締切前時刻が証明された6艇の実コース別率と先頭艇条件付き率の期間・分母・出典。


## 2026-11-01 T-12ソースの日付整合性を強化
- 取得日が前日などの古い `取得日時` でも、締切より12分以前なら `classify` が通過し得る日付不整合を修正。ソース取得日時とHTTP受信日時がレース締切のJST暦日と一致しなければ `unknown_time` に分類する。実装 `cf319c6`。
- 前日ソース・当日正常ソース・前日HTTP受信の境界を `tests/test_preview_timing_integrity.py` に追加（`a6b9b90`）。既存 `late-preview-evidence-tests.yml` のpush/PR対象へコード・テストを含め、テストを実行する設定を追加（`448c0c7`）。
- main上の更新確認までで、新規CI成功は未確認。実レースT-12完全6艇受信の実証も未達。既存取得ソースや公開UIは変更せず、旧repo停止もしない。


## 2026-11-01 T-12レースコードと締切日の整合性
- preview timingの追加ゲートとして、12桁レースコードの先頭8桁（日付）とCSV締切日時の日付が異なる場合は `unknown_time` とする（commit `6cf4f704f7fb8a5459a0f3c06ef37755bcd59991`）。既存の同日受信・ソース時刻ゲートと組み合わせ、誤った他日締切を根拠にT-12合格としない。
- 不一致の日付を不合格、日付が一致する正常例を合格にするテストを既存 `tests/test_preview_timing_integrity.py` に追加（commit `82b2f10fb45119cf2483d1b4f78f6d5bbe069bf0`）。既存preview CIが対象ファイルを監視する。
- **最新CIの成功と実レースT-12完全6艇保存成功は未確認。** 旧サイト・予想モデルは変更しない。


## 2026-11-01 T-12締切境界の回帰テスト
- main `9523560e0777b52f0c3fe7d6f82574e7e73d71ef` で、19:00締切のT-12に対しSTT/TKZのsourceとHTTP受信が18:47:59なら時刻条件合格、18:48:00ちょうどなら不合格となる既存 `classify` の保守的仕様を回帰テストに固定。
- 変更対象は既存 `tests/test_preview_timing_integrity.py` のみ。既存 `late-preview-evidence-tests.yml` がmain pushでこのテストを実行する設定は確認済み。**新しいコミットのCI成功と実レースT-12完全6艇取得は未確認**。
- 予想/UI・旧サイト変更なし。8:03 JST以降の定期収集実測が次の検証対象。

## 2026-11-01 PR #744：公開Pagesで確定結果3連単の実値検査を追加
- PR #744をsquashでmain `25501e5ae702750d04fde87cb3a970688025c58e` に統合。既存のPages Playwright検査を拡張し、2026-10-27・1場1Rの保存済みCLEAN確定結果（3連単3-4-1）について、結果タブの可視性だけでなく公開ページ上の1/2/3着数値と「CLEAN保存済み結果」状態まで確認。
- PR head `70bfface681b7234d9adf69096372000d85eb68c` のCLEAN CI `check` / `publish-smoke` はsuccess。main同コミットのCLEAN regression/odds parser CIもsuccess。
- mainの公開ワークフロー run `41242390056` は記録時点で実行中。公開ブラウザ `DEPLOYED_ARCHIVED_RESULT_PASS` の実行済みログは未確認、iPhone Safari実機・T-12六艇展示証明も未取得。予想・収集のパイプライン、旧サイトには変更なし。

## 2026-11-01 PR #747 本番および公開Pages検査の判定
- PR #744の公開Pages workflow run `41242390056`、job `124658770360` の実ログを確認。`Verify Oct 31 archived forecast and visible receipt warning`、`Verify published CLEAN confirmed result in browser` はsuccess。一方 `Browser-check deployed page` が `#resultDetail .result-summary` の30秒待機でfailureとなり、**workflow全体はfailure**。4タブ実データ全件の成功とはしない。
- PR #747の修正では、公開ブラウザ確認で結果レースを選んだ後に `await loadResult(true)` を明示して選択レースの取得完了を待つ。PR head `0d7ae7dfaa7d872c912a1a6b7f6a74ccb48686e2` に対する既存CLEAN回帰 `check` と `publish-smoke` はともにsuccess。squash main `f8a955d69690d22b333511667f55bdb0f45e455c`。
- Render `dep-dbj5kb2vcj2c73elciog` はこのmain SHAと一致して `live`。ただし **Pagesのmain pushデプロイ後テスト成功は本接続で未取得**。Render liveとPages公開ブラウザ成功を同一視しない。
- 次は既存Pages publish runで `Browser-check deployed page` の再実行成否と `DEPLOYED_ARCHIVED_RESULT_PASS` ログを直接確認。続いて2026-10-31の出走表・展示・結果・予想4タブを実データごとに検証。旧repo/Pages・原本は未変更、旧サイト撤去ゲートは未達。

## 2026-11-01 Top-N監査の二重計上修正（main独立統合）
- 開いている研究PR #722の二重計上問題を確認。現在mainの `aggregate_prospective_topn.py` に、除外理由を正規化前・正規化後に重複加算する不具合が残存。前者を削除して後者1回のみとした (`6b6addb0`)。
- 2日×2件の監査棄却を計4件として数える回帰テスト追加 (`88f543ec`)、既存 `research-forecast-tests.yml` に変更対象pathとテスト実行を登録 (`ea4a4792`)。既存PR #722に競合回避コメントを記録。
- この変更のGitHub Actions成功は未確認。研究PR #722の他の変更は未審査・未統合。T-12完全6艇実測なし、旧サイト停止なし。

## 2026-11-01 Pages公開スモーク重複解消 PR #750
- 既存の専用確定結果ブラウザテストが成功しても、別の4タブナビゲーション検証内の重複した保存結果取得がタイムアウトしてPages workflow全体を失敗させていた。PR #750では重複する後者のアーカイブ取得を除去し、専用実データ結果検証と4タブナビ検証を分離。
- 既存PRのコメント内にリテラル `\\n` が残っていたため、改行に修正 (`b22e5fe6dbd2212d3900ea44eb072e66f88a1bdd`)。PR head CI run `41243067518` の `check` と `publish-smoke` が両方success。mainへsquash `f367e7177f4384fecbffbf10bf1d3062b9fc6ab5` で統合。
- **統合後Pagesデプロイ結果・公開後ブラウザ検証は別途未確認**。実レースT-12完全6艇証拠と旧サイト独立保全も未完了。旧repo/Pages停止なし。


## 2026-11-01 定期収集ジョブにT-12時刻判定テストを組み込み
- 定期収集 `.github/workflows/late-preview-capture.yml` は従来、`test_preview_timing_integrity.py` を実行しておらず、時刻判定の境界や日付整合性の回帰を直接確認しないままCSV取得に進めた。既存のテストステップに同テストを追加（commit `5bdbed92c3e7aa2fad1ec3e874d6d2c4ee9e8afa`）。新規ジョブや独立PRは増やしていない。
- **main更新・設定確認まで完了。新しいCI成功・8:03以降の実データ完全6艇T-12成立は未確認。** 収集結果とCI結果を混同しない。旧サイト変更・停止なし。

## 2026-11-01 公開Pagesの確定結果配信補強（PR #751）
- PR #744に加えた旧の重複結果スモークは `202610270101` のRaw取得が404扱いとなり、公開run `41242390056` が失敗。PR #748ではレース選択を固定し、run `41242784562` のログで `key=20261027-01-01`, `view=result`, `status=CLEAN確定結果は未取得` を実測。これは「競艇結果が不正」の証明ではなくRaw配信依存の不達。
- PR #751 (main squash `7fc2e81e7e56a14ac96bada53d01113763219db8`) は、既存の保存済み `confirmed_results/` をGitHub Pages成果物に同梱し、Raw側取得失敗時のみ同一originの結果JSONへフォールバック。4か所の既存結果読込を共通化し、race codeを検査。モデル予想入力への確定結果混入なし。
- PR head の回帰CI（`check`,`publish-smoke`）成功、main Pages公開 run `41243190467` / deploy job `124661127242` はsuccess。実公開ブラウザログは `DEPLOYED_BROWSER_PASS` と `CLEAN_RESULT_PUBLISHED_BROWSER_PASS ...venue=23&race=1 ... 1-2-5` を確認。**202610270101の独立実ブラウザ合格を確認したわけではない。**
- 残る: iPhone Safari実機、追加レースの出走表／展示／予想内容、T-12の同一6艇STT+TKZ受信時刻証明。旧サイト停止条件は未達。


## 2026-11-01 重複証拠をT-12ペアから除外
- 保存済み監査 `scripts/audit_late_preview_evidence.py` で同一レース・種別の重複レコードが現れた際、単にinvalidに加算するだけでは先に受理した記録がペアとして残る可能性を修正。重複種別を拒否リストへ追加し、既存ペアからも除外（`22e488adc201a919915b9c59bed9836c14bfa38f`）。
- 監査時に重複参照を再現する既存テストを追加し、完全6艇ペア・T-12ペア共に不合格となることを確認する条件を記載（`77e4f3d35837b35eaa8339d79cf7acd1b06ec331`）。
- mainに反映済み。**CI実行成功および実レースのT-12完全6艇取得は未確認**。旧サイト・予想モデルは変更なし。

## 2026-11-01 PR #753 タブ相互排他とレース選択維持の公開テスト
- 既存PR #753はPages公開ブラウザテストで出走表・展示・予想・結果の各タブが相互排他であること、および切替中に選択レースキーが変化しないことを検証。PR head `df7f3c27505314bfcadb606297a6f1e55c83e4dc` のActions `41243276155` は `check` / `publish-smoke` ともsuccess。main squash `55c27520df386bb8cd1e6dff84e58f35b697ba7a` 統合。
- 統合後のPages再公開実行・iPhone Safari実機は未確認。収集T-12完全6艇ペア実測も未成立。旧サイト・原本の変更なし。


## 2026-11-01 破損した重複証拠もT-12合格から除外
- 監査で同一レース/種別の2件目が破損していた場合、JSON内容の検証より前に重複を認識しないと最初の有効レコードが残る不具合を修正。パスのrace code/種別の重複を読み込み前に検出し、受理済みレコードを除外する（main commit `c5a61f398a769ff362ef135fc662ab0b1ecfe700`）。
- 2件目を破損データとして返す重複参照の回帰テストを追加（`269f503796c2b0084471277e8d9f1f054c16538b`）。
- GitHub本番での**最新CI実行成功は未確認**。ローカルのgit cloneは名前解決不可で実行できず、テスト実行成功を主張しない。実レース完全6艇T-12証明も未取得。旧サイト・予想モデルは変更せず。

## 2026-11-01 PR #753 4タブ排他表示とレース選択保持
- PR head `df7f3c27505314bfcadb606297a6f1e55c83e4dc` のActions run `41243276155`: `check`、`publish-smoke` ともsuccess。選択タブのみ可視、タブ切替前後にrace keyが維持されるアサーションを既存Pagesブラウザ検証に追加。
- main squash `55c27520df386bb8cd1e6dff84e58f35b697ba7a` へ統合。Render deploy `dep-dbj5pplg1s2s73flbofg` は確認時点でbuild_in_progress。統合後の公開Pagesブラウザ実行成否は未確認。旧サイト撤去に必要なT-12完全6艇展示・原本独立保全・4タブ実データ完全性は未達。旧repoには変更なし。


## 2026-11-01 CSV締切日時形式の保存互換性
- `classify` が日時全体（例 `2026-10-31 11:20:00` / `2026-10-31T11:20:00+09:00`）を有効な締切時刻として受け入れても、`save_preview` の `%H:%M` 固定再解析が例外になって保存できない不整合を解消。共通 `parse_jst` を優先して使用し、HH:MMの場合だけレース日付を補って再解析（main commit `c078972d2624343a063c697942f2dda7a5233044`）。
- `test_late_preview_capture.py` に通常日時/ISOタイムゾーン付き締切での保存テストを追加（`7d7e9ef2e75345117fded558c0ce53ddc399fcba`）。既存 `late-preview-evidence-tests.yml` が当該ファイルを対象とし `test_late_preview_capture` を実行する設定。
- 環境からGitHubへ直接cloneはDNSエラーのため、**現時点で修正後CI成功を確認していない**。実レースSTT+TKZ完全6艇のT-12受信成功も未確認。旧サイト停止・予想モデル更新なし。

## 2026-11-01 公開Pages実ブラウザ成功ログの原本再確認
- 既存Publish Pages workflow `41243190467` のjob `124661127242` は completed/success。実ジョブログより `CLEAN_ARCHIVED_FORECAST_PROVENANCE_BROWSER_PASS 202610310708`、`CLEAN_RESULT_PUBLISHED_BROWSER_PASS https://ikst2512-eng.github.io/boat-edge-clean/?date=2026-10-27&venue=23&race=1&view=result 1-2-5`、`DEPLOYED_BROWSER_PASS https://ikst2512-eng.github.io/boat-edge-clean/` の各実行行を確認。ログ内コマンド文字列だけでなく、実際の実行結果行を根拠とする。
- このrunはPR #753統合前なので、#753の新規タブ排他・race key保持テストの**統合後公開合格とはしない**。別途PR head Actions `41243276155` の `check` / `publish-smoke` success、Render `dep-dbj5pplg1s2s73flbofg` のliveは確認済み。出走表/展示の実データ6艇表示とiPhone Safari実機は未証明。
- 旧Pages/原本の独立保全と、実レースT-12前のSTT+TKZ完全6艇受信証拠は未達。旧repo/Pages撤去禁止は継続。


## 2026-11-01 定期収集でCSV保存互換性テストを実行
- `.github/workflows/late-preview-capture.yml` は、mainで修正済みの日時全体・ISOタイムゾーン付き締切保存とappend-onlyテスト `test_late_preview_capture.py` を実行していなかった。既存の収集ジョブのテストステップに `python -m unittest -v test_late_preview_capture` を追加（commit `b7a03d5d234de0617a6b4de83598836d39fdc0e6`）。これによりCSV取得ステップ開始前に保存処理の回帰を検出する設定。
- 新規workflow・PR・ジョブの追加なし。**更新後のCI実行結果・8:03以降のSTT/TKZ完全6艇T-12受信は未検証**。旧サイト/モデル変更なし。

## 2026-11-01 PR #756 出走表6艇の公開E2E検証追加
- PR #756 head `8aa9652dba0364a885ea06909a83815b98ea9b1f` のActions run `41243938240` は `check` と `publish-smoke` ともsuccess。既存Pages公開後ブラウザworkflowへ2026-10-31蒲郡8RのCLEAN racecard API取得、出走表6行・艇番1〜6・Git初回登録時刻未照合の表示確認を追加。
- main squash `e1b4971dcca03df9e9f5a5e8bb0cfdd01e4b1141` 統合済み。追加のAPI実データ検証は**Pages公開後のみ実行**されるため、PR CI successでは実データ6艇PASSとしない。最新Renderのmain SHA反映とPages公開ジョブの実ログは現時点未確認。
- 展示の6艇実値・T-12完全ペア時刻・旧サイトの独立証拠保全は引き続き未証明。旧repo/Pagesの撤去なし。

## 2026-11-01 PR #757 展示タブ公開E2Eの取得状態監査
- PR #757 head `016a1611ff19d539d90de4f00d889b813d759b93` の既存Actions `41246412767` は `check` / `publish-smoke` ともsuccess。PR #756の蒲郡8R出走表6艇公開テストに、展示タブ可視、取得済/未検証の状態表示、取得済時の6/6艇件数表示を追加。未検証を実測6艇T-12成立として扱わない。
- main squash `df70cf2779b5fa9131fe0aca78635b0a2dabdbfe` へ統合。Renderログの `GET /api/clean-racecard?hd=20261031&jcd=7&rno=8` HTTP 200 は確認済みだが、返却JSONの6艇完全性まではサーバーログだけでは確定できない。Pages公開後の新しいE2E合否も未確認。
- 原本・旧サイトは未変更。T-12ペア実証、実機Safari、独立原本保全は未達。


## 2026-11-01 T-12収集元の公開時刻制約を特定
- 上流BoatraceCSVの一次仕様 https://boatracecsv.github.io/docs/data/previews.html を照合。 `data/previews/{stt,tkz,sui,original_exhibition}/YYYY/MM/DD.csv` は **「締切5分前のスナップショット」** を保存する方式で、更新ジョブはJST 08:00〜22:59に5分間隔で稼働する。既存 `collect_late_preview_once.py` は同CSVを参照しており、このソースだけではT-12時点の6艇展示・進入取得を証明できない設計上の制約がある。
- 今までの「定期実行を8:03から回せばT-12完全ペアが得られる」という前提を撤回。既存収集・監査は **T-5資料の観測・保存実験として維持** し、T-12達成を主張しない。T-12実行に必要な別の公開取得元（公式beforeinfo等）の実時刻・6艇揃い・安定性を独立に検証することを最優先へ変更。取得後の予想生成への混入は禁止。
- これは一次文書の仕様確認であり、本日8:03以降の実CSV到着・CI成功を確認したものではない。旧サイト停止・予想モデル変更なし。

## 2026-11-01 旧予想サンプル3件の継続的バイト同一性ゲート
- 保全済み3件（PR #758）について、manifestが指すCLEAN内JSON原本を実バイトで読み込み、Git blob SHA-1（blob header + NUL + body）を再計算し旧repoのsource_blob_shaと一致させる検証を `scripts/verify_legacy_preservation_samples.py` に追加。対象パス、race_key、重複・件数も照合。commit `89295bfa`, `f98df7d9`。
- 既存 `research-forecast-tests.yml` に検証コマンドを組み込み、サンプルまたはmanifest更新時にも実行する設定を追加（commit `63e717a9`）。新workflowは作成しない。
- **実Actionsの成功未確認**。Git blob同一性は初回Git追加時刻・締切前証明・全件保全・独立長期保管を意味しない。旧サイト停止不可。

## 2026-11-01 PR #759 展示の締切前証拠表示を厳密化
- `index.html` 展示の従来ラベル「直前データ：取得済み・締切前確認済み」は、`source_audit.beforeinfo.fetched_at` の時刻条件から初回Git登録まで証明したと誤解され得たため「直前データ：取得記録は締切前・Git初回登録未照合」へ修正。未検証表示・6艇カウントは維持。
- 既存 `.github/workflows/deploy-pages.yml` の同ラベル判定を更新。PR #759 head `023d3715792b1d02556670086ba590bf48b593a8` のCI run `41246633156` は `check` と `publish-smoke` がsuccess。main squash `5a9030935f53ff7bbb7a807da7e24a54158425db`。
- Render deploy `dep-dbj6cut659jc739hvpb0` は確認時点queued。Pages統合後の公開実データ表示は未確認であり、T-12実レース完全STT+TKZ 6艇原本、初回Git証拠、旧サイト独立保全は未達。旧repo/Pagesを変更・停止していない。


## 2026-11-01 公式beforeinfo独立HTTP観測経路
- BoatraceCSV直前CSVが締切約5分前のスナップショットであることを一次仕様で確認（https://boatracecsv.github.io/docs/data/previews.html）。公式サイトの `/owsp/sp/race/beforeinfo` の直前ページが別経路として存在することを確認。ただし公式側のT-12時点での6艇公開可用性は未実証。
- 実験用 `scripts/capture_official_beforeinfo_probe.py`（commit `b00d9a6`）を新設。指定レースの公式HTMLバイト、HTTP受信時刻、URL、SHA-256をappend-onlyで独立保存。**HTTP成功だけでは艇数を認定せず、`t12_eligible=false` / `forecast_usable=false` を固定**。URLホスト、サイズ、形式を検査し、取得失敗も成功と扱わない。
- `tests/test_capture_official_beforeinfo_probe.py` （`a986e9e`）に正常受信・取得失敗・不正レースコード・保存先衝突の回帰テストを追加。
- 既存の収集workflowにテストを組み込み、workflow_dispatchの任意 `official_probe_race_code` 指定時だけ公式HTMLの検証取得を走らせ、別artifactに含める（`8a0917e`）。定期収集と本番予想モデルの挙動は変更しない。新しい定期ジョブは増やさない。
- **新しいGitHub Actionsの実行成功、公式ページの実受信、T-12での展示・進入6艇の成立は未確認。** 次は公式取得原本の実時刻・6艇抽出を検証し、その後でT-12条件を別途判定する。旧サイト停止なし。


## 2026-11-01 公式beforeinfo原本のハッシュ整合性テスト
- 公式直前情報HTML保存の回帰テストに、保存済み `beforeinfo.html` 原本のSHA-256を実バイトから再計算して `manifest.json` の `sha256` と一致すること、実HTTP受信時刻、`forecast_usable=false` の保存状態を検証する条件を追加（main `f1649f6de4bb2898da04df480503137b39455332`）。既存の `late-preview-capture.yml` にテスト実行設定あり。
- 実公式ページの受信・6艇抽出・T-12成立・当該GitHub Actions成功は未確認。公式取得経路は引き続き実験専用で、正式予想に使用しない。

## 2026-11-01 PR #761 公式beforeinfo独立保存JSON修復
- `scripts/capture_official_beforeinfo_probe.py` のmanifest末尾をリテラルのバックスラッシュnから実改行に修復。既存テストで `json.loads`、返却manifestとの一致、HTML保存バイト同一性を確認。
- 既存preview証拠CIへテスト・pathトリガーを追加。PR head `ea48dfd1c68dd67b7a0c526a66816497cbd6bf9c`、run `41246854917` のvalidateはsuccess。main squash `d33e368ad0170ef477888a90ec1108b6a2dad760`。
- 公式HTMLの保存可能性のみでT-12・6艇・初回Git記録・予想利用適格の証明ではない。実レースprobeの取得成功は未確認。旧サイト変更・停止なし。


## 2026-11-01 公式直前情報の原本保存完了マーカー
- 公式beforeinfo実験の原本保存で、HTML本文を排他的に保存した後にのみ `manifest.json` を作成するよう変更。完了manifestの存在を保存手順の最終マーカーとする（commit `6c27e34023165e6536c9c9309707f55ed580186c`）。保存テストにHTML本体存在確認を追加（`cbf68485a8dc9be53e717b2ca3a1b30343943451`）。ただしマシン停止時のfsync/完全なatomicityは未実装。
- 公式ページ直接接続は実行環境のDNS名前解決失敗で断念。CI成功、公式6艇実受信、T-12時刻成立は**未確認**。既存の正式予想パイプライン・旧サイトは変更なし。

## 2026-11-01 PR #763 公式beforeinfo部分保存の失敗時清掃
- append-only公式HTML取得でHTML保存後のmanifest書込が失敗すると、不完全な保存ディレクトリが残り得た。書込みエラー時にmanifest・HTML・空ディレクトリを撤去する処理を追加。既存の成功時保存原本や予想生成は変更なし。
- manifest書込を強制失敗させる回帰テストを追加。PR head `90ab220a357cbbd9befc86997d02edc51afd6b01` の既存Late preview evidence integrity run `41247012805` はsuccess。main squash `abd2f6abac00b21abf5e0d1738c629b1535b7bd0`。
- 公式beforeinfoの実受信・6艇完全性・T-12時刻成立は未証明。旧サイト停止なし。

## 2026-11-01 旧予想原本19件の保全（PR #764）
- 旧repoの実在する予想JSONを8件追加取得し、保全サンプルを11件から19件へ拡張。8件を旧repoから再取得し保全先のGit blob SHAと一致することを検証。
- manifestを19件へ更新し、既存ハッシュ照合スクリプトの最低件数を19に変更。PR head `57f851ccffe7ff364b73efd7e506499ea3ff9768` の Research forecast checks run `41247126568` はsuccess。main squash `02453f445e7f1129c9bffac361ce235b531ab623` で統合。
- 保全対象はサンプル19件のみ。初回Git追加時刻・全件原本・オッズ・Fresh・独立長期ストレージでの復元は未検証。旧repo/Pagesは停止・変更なし。


## 2026-11-01 Pages確定結果の自動公開トリガー修正
- 公開workflowは `confirmed_results/` を公開成果物へコピーしていた一方、push path filterは `index.html` / `navigation.js` / workflow自身のみで、確定結果JSONだけのmain更新ではPages公開を起動しなかった。
- 既存 `.github/workflows/deploy-pages.yml` のmain push pathsへ `'confirmed_results/**'` を追加。main commit `c7b228f8cde99acedc6f87c8ed7fbb045d842634`。GitHubからの再取得で追加を確認。新規workflow・PRは作らず既存デプロイ経路を修正。
- `fetch_commit_workflow_runs` はPR起動runのみを返すため今回0件でもpush Pages workflowの成功とは言えない。公開URLの最新JSONと実ブラウザ表示、iPhone Safariは未検証。
- 次: Pages push runと公開後ブラウザE2Eで確定結果JSONの更新反映を確認。旧repo/Pagesの独立保全およびT-12完全6艇証拠が揃うまでは旧サイトを停止・削除しない。


## 2026-11-01 公式beforeinfo手動probeの失敗終了判定
- 既存公式probeのCLIは取得に失敗して `official_probe_failed` を出力しても終了コード0だったため、手動Actionsが「取得成功」と誤認され得た。main `3062096bc631c9cd73e07eccba5d7e636009802e` で、HTTP原本を実際に保存した `raw_http_observed_not_t12_certified` 以外は終了コード1に変更。既存の `if: always()` によるartifact保存は維持。
- CLI不正キーの非0終了とmanifest非作成を回帰テストへ追加（`8b8a36960088f67e68cb75493085ae6b9b3387b3`）。
- 既存PR #763 run 41247012805 の保存・時刻・重複監査など既存テストは成功を実ログで確認。ただし**今回の修正後CI・11月1日8:03以降のschedule実行履歴・公式直前情報の実取得・T-12完全6艇は未検証**。GitHub connectorにschedule workflow runsの一覧取得機能はなく、PR runを定期収集成功として扱わない。旧サイト・予想モデル変更なし。

## 2026-11-01 旧予想原本35件の保全拡張（PR #766）
- 旧repoの実在する `data/site_prediction_snapshots/` JSON原本を16件追加取得して保全専用パスへコピー。manifest計35件。追加16件は保全branchから再取得し元Git blob SHAと16/16一致。既存チェックは35件を下回ると失敗するよう変更。
- PR head `cbc9bae3aaa79130fb4304705424804ddcfac755` の Research forecast checks run `41260907739` はcompleted/success。main squash `bac5f069b4172122f514824b00257538c91beef6`。
- 依然として全数保全・初回Git保存時刻・締切前時刻証明・期限なし独立保存/復元は未達。旧サイトと予想モデルは変更せず、撤去ゲート未達。


## 2026-11-01 Pages確定結果JSONの公開後バイト照合
- 公開workflowはHTMLとnavigation.jsの配信バイト一致のみ検査しており、同梱した確定結果JSONの欠落・配信不一致を独立して検出できなかった。
- 既存 `.github/workflows/deploy-pages.yml` の `Verify deployed public page` に、実保存サンプル `confirmed_results/202610270101.json` の公開取得とローカル配布原本との `cmp -s` 一致ゲートを追加。main `aa425fff20e9a70b2ff1e0da7cc4bb4bb8809cd6`。GitHub上で実コード再取得済み。
- GitHub Actions push runの実行結果・公開JSONのHTTP実測はツールから未確認。サンプル1件の検証であり全結果JSONの保証ではない。新しいワークフロー・PRなし。旧サイトは停止・削除しない。
- 次はPages公開runの実ログでHTML/JS/結果JSONの照合を確認し、2026-10-31実レースの出走表・展示・予想・結果表示を確認する。

## 2026-11-01 PR #767 公式beforeinfoのリダイレクト元検証
- 公式beforeinfo実験用HTTP証拠保存で、転送後URLがboatrace.jpホストならHTTPダウングレードや別pathでも保存を許していた。HTTPS・公式ホスト・`/owsp/sp/race/beforeinfo` の3条件を全て要求し、不一致は `official_probe_failed` としてappend-only保存しないよう修正。
- HTTP /別path /他ホストへの転送をモックした回帰テスト追加。PR head `09c4f46d54f6266a55befda5e7e11ac77c6bb167` の Late preview evidence integrity run `41261621415` validate success。main squash `816d39d985bf43133bd592ae8774b81bd3266a3f`。
- **公式ライブページ受信・実レース6艇完全性・T-12受信前証明は依然未確認。** 公式probeの正式予想利用は禁止、旧repo/Pagesは未変更。


## 2026-11-01 Pages公開済み過去結果の2日付照合
- 既存Pages公開後のバイト照合を2026-10-27の `202610270101` に加え2026-10-31蒲郡8R `202610310708` に拡張。両方の `confirmed_results/*.json` はmain上に存在することを確認し、公開HTTP取得後にそれぞれ `cmp -s` で原本一致させる（main `54c336c8e12f77a2177bd5fa0a188fe5ef3ef426`）。既存ワークフローのみ変更、新規PRなし。
- Render管理APIでは `0b82ce7d` のlive deploy履歴を確認。ただしGitHub Pages公開CIのpush runはGitHub接続の取得機能外であり、Webアクセスも不可。今回の変更後のPages成功・iPhone Safari・過去日の4タブ実表示は未確認。変更内容はGitHubから再取得して確認済み。
- 旧リポジトリ撤去は依然として全件保全と独立保管の未達で保留。次はPages publish runログの成功確認と実ブラウザでの2026-10-31過去レース4タブ実データ照合。


## 2026-11-01 公式probe通信失敗のCLI終了コード回帰
- 既存mainの公式beforeinfo CLIはHTTP取得失敗時 `official_probe_failed` と終了コード1を返すが、従来のCLI回帰テストは不正レースコードのみだった。実際の `urlopen` タイムアウトを模擬してCLIの `SystemExit(1)` とmanifest未生成を検証するテストを追加（commit `1f046027`）。
- `runpy.run_module(...,run_name='__main__')` では別名前空間でモジュールを再実行するため、モック対象を `urllib.request.urlopen` へ修正（commit `3954436c`）。既存 `late-preview-evidence-tests.yml` に対象テストが含まれることを確認。
- PR #765 は同趣旨で既にmainへ取り込まれた部分があり、競合・重複回避のコメントを記録済み。PRを無条件にマージしない。**修正後のGitHub Actions成功・公式T-12六艇の実測は未確認**。旧サイト変更なし。

## 2026-11-01 旧予想原本47件へ追加保全（PR #768）
- `data/site_prediction_snapshots/` の実在JSONを12件追加し、CLEANの保全専用フォルダに計47件。追加分12件を再取得し元Git blob SHAと12/12一致。
- 既存の保全ハッシュ検証を最低47件へ引き上げ、PR head `59c360ab55d7ff1d22f111bdbbd0b4cef0f0ca8d` の Research forecast checks run `41261771107` はcompleted/success。main squash `f4220a4c2f3c2ce68a30ddae99d827bce6ec35aa`。
- 初回Git追加時刻と締切前性の証明、全旧予想・オッズ・Fresh証拠の網羅、期限なし独立バックアップの復元は未達。旧サイト停止・削除なし。


## 2026-11-01 Pages公開検証の伝播遅延対策
- Pages検証がHTMLの一致後にnavigation.jsや2件の確定結果JSONの一時的な取得失敗/不一致で即時失敗していたため、6回の既存リトライ内で全ファイル一致を判定するよう変更（main `d90be09c40e7cac96caba4852c1a84520acc051b`）。不一致を成功扱いせず最後まで一致しなければ失敗。新規PR・workflow追加なし。
- Pages push CIの実結果・iPhone Safariでの4タブ表示は未確認。旧サイトの独立保全が完了するまで削除禁止。


## 2026-11-01 公式beforeinfoの掲載項目を実ページで確認
- BOAT RACE公式の公開された過去レース直前情報ページを照合し、6艇の展示タイム・チルト・スタート展示の進入順・ST・気象データが表示される例を確認（https://www.boatrace.jp/owsp/sp/race/beforeinfo?hd=20261011&jcd=19&rno=12）。公式の展示タイム案内でも展示航走終了後の公表が説明されている（https://www.boatrace.jp/owsp/sp/extra/enjoy/guide/level2/l2_01_02_07.html）。
- これは**過去ページの項目存在確認**であり、ライブHTTP受信時刻、原本hash、完全な機械抽出、T-12以前の公開可否は実証していない。予想投入は禁止継続。次は公式HTML実原本に対する6艇抽出器と時刻・ハッシュ一致監査を既存probeに統合し、日中の手動workflow実行のartifactsで証拠を得る。
- 別担当のPR #765と同じCLI失敗判定を重複実装しない。旧repo/旧Pagesの撤去保留。

## 2026-11-01 PR #770 公式beforeinfo転送先のレース同一性を検証
- `scripts/capture_official_beforeinfo_probe.py` では転送先のHTTPS・ホスト・パスだけを検証しており、別日・別レースのHTMLを指定レースとして誤保全し得た。転送後URLの `hd/jcd/rno` が指定レースコードと一致し、余分なクエリもないことを保存前に要求。
- 他日・他R・余分なクエリのモック回帰を既存テストに追加。PR #770 head `cdb4c31e036928d4d8b66f9f9b523e9e1d227437`、Late preview evidence integrity run `41261901521` はsuccess。main squash `0a7f3c863655857de9fe643be22a0397e987177d`。
- 公式HTMLの実受信・T-12時刻・6艇完全性の実測は未達。旧repo/Pages停止なし。


## 2026-11-01 場コード12の出走表404を非開催として解消（PR #769 / #771）
- 本番 `/api/clean-schedule?date=20261101` を実取得。確認済み開催場は02/03/04/06/07/09/13/14/17/18/19/21/22/24の14場、各12Rで、場コード12（住之江）は日程に存在しない。従来の住之江1R/5Rの404は出走表欠損ではなく、非開催レースへの不要なAPI要求だった。
- PR #769でfrozen candidate日程にも既存レース由来の `venue_race_counts` を追加。schedule classification run `41261809524`、daily schedule run `41261809567` がsuccess。main squash `71d87b87d6235e92d48b4f3f9608fa921a27ee95`。
- PR #771で、UIが完全な確認済み日程を待ってから、日程にない場/レースでは出走表APIを呼ばず「この場/レースは開催されていません」と表示するよう修正。partial frozen scheduleは欠落を非開催証拠に使わず従来照会を維持。
- PR #771 head `f7ba593c125d07535a238cef65bd120a52ac8371`: CLEAN regression `41263333456`、Navigation `41263333468`、Cross-model `41263333467`、Daily findings `41263333494`、daily schedule `41263333457`、Dual verification `41263333476`、Official odds `41263333466` がsuccess。Mobile browserはpath filterでskip。main squash `ef7aa5b10f90f713e16c4f5e587a98e75cdd5cb4`。
- Render deploy `dep-dbj9qgbncjis73dd4e70` は同一commit `ef7aa5b` でlive。Render本番とGitHub Pagesの `2026-11-01 / 住之江 / 1R / 出走表` を実ブラウザ確認し、「この場は開催されていません」「確認済み開催日程」を表示。確認後のRenderログに `202611011201` / `racecard_title_missing` / `clean_racecard_not_found` は0件。
- モデル・予想研究・データ収集・正式採点は変更なし。旧repo/旧Pagesは全件独立保全が未達のため停止・削除なし。


## 2026-11-01 Pages公開前の2日付結果ファイル欠落ゲート
- 現行Pages workflowは配信後に2026-10-27と2026-10-31の2件を照合する一方、公開成果物作成時の存在確認は10/27分しかなかった。ステージング時に `public/confirmed_results/202610310708.json` の非空ファイル存在も検証する修正をmain `4633af41fadbeee704a703c2e9e06a671aa99029` へ反映。GitHub再取得で設定確認済み。
- Renderで非開催住之江1Rの修正公開済みである旨の既存実測記録を確認。今回は公開Pages URLおよびActions web一覧の取得が失敗したため、Pages CI成功・過去レース4タブ完全表示は未確認。CIを新規成功扱いしない。
- 旧サイト/旧Pages削除なし。次の優先は公開CIの実ログ取得と2026-10-31の4タブ実データ検証であり、単なるテスト追加を本番動作の代替にしない。


## 2026-11-01 公式beforeinfo原本の診断用HTMLラベル監査
- 公式HTTP原本について、manifestのSHA-256と実バイトを照合した後で可視HTMLテキストから展示タイム・チルト・スタート展示・進入・ST・気象ラベルの出現位置を抽出する**診断専用** `scripts/inspect_official_beforeinfo_html.py` を追加（`5826ded7`）。脚本・CSSは解析対象外。HTML掲載内容の文字列検査だけで6艇の値やT-12適格性を証明しない（出力は `six_lane_values=unverified,t12_eligible=false,forecast_usable=false` 固定）。
- HTML改ざん時のSHA不一致拒否、ラベル抽出と非認定状態の回帰テスト `tests/test_inspect_official_beforeinfo_html.py` を追加（`566c1a31`）。既存 `late-preview-evidence-tests.yml`（`2a531f88`）と `late-preview-capture.yml`（`4dc60656`）へテストを組み込み、新規workflowは作成しない。
- **mainへのファイル反映は確認済みだが、変更後のActions実行成功・公式実HTML保存・6艇値の構造解析・T-12実測は未確認。** 次に保存原本を取得できた時点でラベル・DOM形状を調査して抽出器を設計。旧repo/Pagesには変更なし。

## 2026-11-01 PR #772 公式beforeinfo転送後URL原本記録
- 公式HTML独立probeが検証済みの公式リダイレクトを許す一方、manifestには要求URLだけを記録して実際の応答URLを失っていた。`response_url` を保存し、正常な同一レース公式別ホスト転送も原本manifestから追跡できるよう変更。
- 回帰テストで転送後URLと要求URLの差、manifest同一性、およびT-12不適格の維持を検証。PR head `8bf32c60c833099b664e534c99dac2f21d7ade28` Actions run `41280534954` validate success。main squash `d5c83f50a223080d608fc350da776cfdfcc80d2a`。
- 公式実レースのライブHTTP受信・受信時刻T-12・展示進入6艇の機械的確認は未証明。本変更は原本の追跡性改善のみで、予想採点利用なし。旧repo/Pagesの停止なし。


## 2026-11-01 公式HTML手動取得後の診断artifact連携
- 既存 `.github/workflows/late-preview-capture.yml` の手動 `official_probe_race_code` 指定時、公式HTTP原本保存後に `scripts/inspect_official_beforeinfo_html.py` を実行し、SHA-256再照合・展示/進入/ST等のラベル位置を `official_beforeinfo_diagnostic.json` に出力して既存artifactへ追加（main `72ec14f1439c8a2222c8103978e2b4bb2315f6ee`）。公式HTTP取得に失敗すると取得ステップが非0で終了し、診断ステップは実行されない（artifactアップロードは `always()` で維持）。
- 追加した診断はHTMLラベルの位置のみを扱い、**6艇の数値完全性、取得レース整合、T-12適格性は未認定**。本番予想経路には接続しない。新しいworkflow・定期ジョブは作成していない。
- GitHub Actionsの新規実行成功および実HTMLの診断artifactはまだ未確認。旧リポジトリ・旧Pagesの停止や削除なし。

## 2026-11-01 旧予想原本51件まで保全（PR #773）
- 旧サイトの実ファイル4件を保全専用 `legacy_preservation/samples/` に追加し、マニフェスト51件へ拡張。追加4件は元Git blob SHAと保存先SHAが4/4一致。
- 保全検証の最低件数を51へ更新。PR head `6f4c13470ebfcbbcd7fbeda47fd84515eaf44f38` の Research forecast checks run `41280687961` はcompleted/success。main squash `9e26d263df94c45dd07b9b30d8ba26ffa28b4b95`。
- 初回Git保存時刻・締切前性、旧予想全件とオッズ/Freshの網羅、独立長期バックアップ復元は未証明。旧サイト停止・削除なし。


## 2026-11-01 重複PR #765整理と公開検証制約
- PR #765 は失敗時CLI終了コード1と通信失敗回帰テストを追加する差分だったが、mainの `scripts/capture_official_beforeinfo_probe.py` は既に失敗を非ゼロ終了とし、`tests/test_capture_official_beforeinfo_probe.py` にHTTP通信失敗の回帰テストが存在することを直接照合。PR #765を未統合のままclosedに整理（https://github.com/ikst2512-eng/boat-edge-clean/pull/765）。mainの実装は変更せず重複統合を回避。
- Actions一覧ページ・GitHub Pages公開HTML/確定結果JSONへは今回のWeb取得でアクセス不可。現行push CI結果や実レース4タブの公開後表示を成功と判定しない。旧サイト撤去条件も未達のため削除なし。

## 2026-11-01 PR #774 公式HTML手動取得後の診断自動化
- `late-preview-capture.yml` の手動 `official_probe_race_code` 指定時、原本保存成功後に `inspect_official_beforeinfo_html.py` を自動実行し `official_preview_probe/label_inventory.json` に診断用ラベル分布を保存。SHA照合後の原本のみを検査し、`t12_eligible=false`、`forecast_usable=false`、`six_lane_values=unverified` を強制する。既存artifact upload (`always()`) に含める。
- PR #774 head `27a5736313e01d1fb4a3969ea0e7829aedafee0a` で Preview capture run `41280725774`、Late preview evidence run `41280725753`、Audit run `41280725728` が全てsuccess。main squash `b76e5e927e1760f2a8f96f651f08db95fb0dfcfb`。
- PR時のworkflowは手動公式取得を実行していない。**実公式HTML取得・実レース6艇とT-12受信時刻の証明は未完了。** 旧サイト停止・削除なし。


## 2026-11-01 公式HTML診断ジョブの重複を統合
- 既存 `.github/workflows/late-preview-capture.yml` には公式HTML原本保存後の診断が2ステップ重複していた。単なるラベル抽出・別JSON保存ステップを撤去し、SHA一致、T-12/予想使用禁止、6艇未検証のassertを含む既存 `official_preview_probe/label_inventory.json` 出力の単一診断ステップへ統合（main `f1c5a9858735966b4ccde2ac0245a72f139a139b`）。既存artifact uploadで診断JSONを引き続き保存。
- 新しいworkflow/PR/定期ジョブなし。変更後CI実行・手動公式HTTP実受信・T-12実測は未確認。旧サイト/予想モデル変更なし。


## 2026-11-01 公式probe失敗レポートをartifact保存
- 手動 `official_probe_race_code` を指定して公式HTTP取得が失敗すると、従来は標準出力だけでartifactに失敗理由が残らなかった。既存 `late-preview-capture.yml` の公式probe実行を `set -o pipefail` と `tee official_preview_probe/attempt_report.json` に変更し、取得成功・失敗どちらの場合も受信時刻/エラー分類をartifactへ保全。元のCLIの終了コード1はpipefailで維持（main `e1960a48435a746eded7412edc9bfb557f04ef2d`）。artifactパスを明示（main `f94a07613f2e60345b0a1dbcf2d630690ee5692f`）。
- この環境からの `www.boatrace.jp` 直接HTTPアクセスはDNS名前解決失敗。GitHub Actionsからの公式HTML実受信、今回のCI成功、T-12 6艇数値は未確認。旧repo/旧Pages/予想モデルには変更なし。


## 2026-11-01 Pages確定結果の同一origin優先読み込み
- `index.html` の確定結果取得はPages上でもGitHub Rawを最初に最大15秒待ち、失敗後に同一サイトの保存JSONを読む順序だった。Pagesホスト `ikst2512-eng.github.io` では `confirmed_results/{race_code}.json` を先に試し、失敗した場合のみRawを照会する順序に変更。Render等では従来通りRaw優先。双方が失敗した場合はHTTPエラーとして維持し、結果を捏造しない（main `dc5f62a43776669d0a970889370e887afbea9d96`）。
- 変更後のGitHub Actions CI、Pages公開実ブラウザでの10/31蒲郡8R表示、iPhone Safariは未確認。旧サイト/原本削除なし。次は既存Pages CIと現物公開表示の確認。

## 2026-11-01 旧予想原本55件に保全拡張（PR #776）
- 旧repoの実在JSON原本4件をCLEANの隔離保全先へ追加。manifest計55件、既存のGit blob SHA検証CIの最低件数も55件へ変更。
- PR head `0a19d074009ca5910d56ed518278b371a1846686` の Research forecast checks run `41289827721` はcompleted/success。main squash `6364f3dff39474ac1ead7fd796a0050d97b22790`。
- **初回Git追加SHA/日時、全件、オッズ/Fresh、独立長期保管復元は未確認。** 旧サイト停止・削除なし。

## 2026-11-01 PR #777 公式beforeinfoのHTTP 200偽HTML拒否
- 公式beforeinfo観測でHTTP 200でもJSONエラー・通常テキストをHTML原本として保全してしまう問題を修正。UTF-8 BOM・前後空白を許容しつつDOCTYPE/html始まりの文書のみ保存。非HTMLなら `official_probe_failed`、保存manifestなし、予想利用不可。
- 既存テストへJSON・プレーンテキスト・空応答拒否とBOM付きHTML許容を追加。PR head `17ed518a13f832f9e86a63c974f5b8861084cc60` のLate preview evidence integrity run `41289864856` validate success。main squash `92133fc7713c8d6607d8c98610fb30b78dd0598d`。
- HTML形式の取得記録だけでは正しいレース内容・6艇・T-12を証明しない。公式実レースの時間証拠は未確認。旧サイト/予想モデル未変更。


## 2026-11-01 Pages同一origin優先変更に対応した回帰テスト修正
- 直前にmainへ反映した `fetchCleanResultArchive` のPages同一origin優先化 (`dc5f62a4`) に対し、既存 `tests/site-regression.cjs` が撤去済みの直書き `fetchTimed('confirmed_results/'+code+'.json'` を必須とする古い文字列アサーションを残していた。このため新しい実装が正常でもCLEAN回帰が失敗する構造的不一致を特定。
- 旧アサーションを、ローカル保存パスの存在・Pagesではlocal→Raw、RenderではRaw→localという新しい優先順序の照合へ変更。main `f5aa6fb22b0f5c0e3ba3ea52af890ec0c12f993b`。重複PRを作らず既存テストだけ修正。
- 実GitHub Actions CIの成功、公開Pages/Renderの実ブラウザ表示は未確認。旧サイトは削除しない。次はCLEAN regression runとPages公開後の実測を優先。

## 2026-11-01 PR #778 公式HTML診断の保存先レース同一性検証
- 公式HTML保存原本の診断で、manifest SHA-256照合に加え、`race_code` と保存先 `YYYYMMDD/YYYYMMDDjjrr/` の同一性、およびmanifestに記録されたバイト長と実HTMLサイズの一致を要求。不一致は診断拒否して、別レースの原本を誤って調査対象とすることを防止。
- 既存 `test_inspect_official_beforeinfo_html.py` にレースキー改ざん・バイト数不整合の回帰追加。PR head `18a47853667fcec0cb88966588b6ca37f22fcdca` のLate preview evidence integrity run `41303921018` validate success。main squash `095414528dc1a0c3b5b46126cc6c4af70f31802a`。
- **公式実受信・時刻T-12・完全6艇の機械抽出は未証明**。予想モデルと旧サイトには変更なし。


## 2026-11-01 公式HTMLの実BOM判定を修正
- 公式beforeinfo取得のHTML先頭判定で `b"\\\\xef\\\\xbb\\\\xbf"`（文字列としてのバックスラッシュ）を `lstrip` に渡しており、実際のUTF-8 BOMバイト `EF BB BF` を除去できない不具合を修正。実BOMを `bytes.fromhex("efbbbf")` で明示して除去後、空白を除いてDOCTYPE/htmlを検査する（main `8c04f5db536ddf4abf0be9b9a0932e6ba42d41fb`）。
- 従来のBOMテストもバックスラッシュ文字列だったため、実バイトを含むケースに差し替え（`e1c476f95254168eb17fd4452746325ded623922`）。変更前のPR #777 CI run `41289864856` は11テストステップ全てsuccessと再確認したが、**修正後のpush CI成功は未確認**。公式実HTTP受信/T-12完全6艇も未証明。旧サイト・モデル変更なし。


## 2026-11-01 蒲郡8RのPages公開後結果タブ実表示ゲート追加
- 既存 `deploy-pages.yml` の「Verify published CLEAN confirmed result in browser」は2026-10-27の1レースだけだった。2026-10-31蒲郡8R（`202610310708`）を同じPlaywright実ブラウザ検査に追加。GitHub保存結果の3連単1-4-6と公開結果タブの艇番3つの一致、および未検証事前予想を正式的中採点しない条件を検査する（main `a0d6ad2460d30e88858fec293701f995a903cd07`）。旧10/27検査は維持、新規PR/ワークフローなし。
- GitHub Actions push実行の最新ログと公開ブラウザ合否は現時点未取得。公開後検証を追加したことと、合格したことは区別する。旧repo/Pagesは削除しない。次は公開runの実ログで両件の `CLEAN_RESULT_PUBLISHED_BROWSER_PASS` を確認する。

## 2026-11-01 旧予想原本59件の保全追加（PR #779）
- 旧サイトの予想スナップショット4件を保全専用フォルダへ追加しmanifest59件。元repoと保存先のGit blob SHAは追加分4/4一致。
- 既存の保全CI件数下限を59に更新。PR #779 head `dddf3732e83fe4a8ae7d802e550e4bedb7e023b9` の Research forecast checks run `41304039718` 成功、main `9ca5586736d8ba54692d994337f9c446af5c36e6` に統合。
- 初回Git追加日時、完全保全、独立長期保存は未証明。旧サイト停止なし。


## 2026-11-01 手動公式HTTP観測をCSV取得から分離
- `late-preview-capture.yml` の手動 `workflow_dispatch` に `official_probe_race_code` を指定しても、これまでは先にBoatraceCSVの5種取得・監査・サマリーが実行され、4分タイムアウト内の公式HTTP観測に遅延と無関係な失敗リスクがあった。既存3ステップに `if: github.event_name != 'workflow_dispatch' || inputs.official_probe_race_code == ''` を追加し、**指定ありの手動probeだけCSV収集をスキップ**（main `c066fd5a6629beffc9e4a490b01dbf1e1a5dd975`）。スケジュール実行・通常の手動実行・PRテストでは従来通りCSV収集する。原本・失敗report・診断のartifactアップロードは維持。
- YAML内容をGitHubから再取得して3箇所の条件が存在することを確認。**修正後CI成功、手動公式実HTTP取得、T-12完全6艇は未確認**。新workflow/PR/旧サイト変更なし。

## 2026-11-01 PR #780 公式原本診断の受信時刻・認定状態の厳格化
- `inspect_official_beforeinfo_html.py` はレースキー・SHA照合だけでは受信日時が無い原本や誤ったT-12認定状態も解析できていた。JST `+09:00` の解析可能な `received_at_jst`、HTTP 200、`raw_http_observed_not_t12_certified`、`t12_eligible=false`、`complete_six_lanes=unverified` を確認し、不一致なら診断拒否。
- timezone不一致や偽のT-12合格を再現する回帰テスト追加。PR head `f44a1053d881de2fd430bea18ca2807de8910ee1` のLate preview evidence run `41304107698` validate success。main squash `171346d60c4361dd465092fa082ac8195c3e95e1`。
- これは保存済み原本の診断用整合性チェックであり、**公式ライブHTTP受信・6艇完全性・締切T-12成立を実証したものではない**。旧サイト停止・削除なし。


## 2026-11-01 手動公式probeで不要な事前単体テストをスキップ
- 手動 `workflow_dispatch` に `official_probe_race_code` を指定しても従来は収集前に8種の単体テストが走り、短い実行枠で実HTTP観測の開始を遅らせていた。既存 `late-preview-capture.yml` の先行テストステップに条件を付け、**公式レース指定ありの手動実行のみ**テストを省略して公式HTTP取得を先に実施するよう変更（main `8b260a0203c1b82ee180295ec6928cc11bddc8dc`）。schedule・PR・通常手動でのテスト動作は維持。独立の `late-preview-evidence-tests.yml` ではpush/PR時に公式probe・HTML診断を継続テストする。
- 本実行で公式ページの直接取得はweb経由でもアクセス不可。最新変更後CI成功、GitHub手動probe実HTTP受信、6艇完全性、T-12成立は未確認。旧repo・予想モデルは変更なし。


## 2026-11-01 Pages公開ブラウザ結果テストのRaw依存解消
- 既存Pages公開ブラウザ検証は、10/27・10/31の画面表示前にGitHub Rawへアクセスして期待値JSONを取得していた。ページ本体の結果読込は既に同一origin優先なのに、Raw障害で公開画面の合否を判定できない不整合を確認。
- `deploy-pages.yml` の結果画面テストの参照JSONを、公開済みPagesの同一origin `confirmed_results/{race_code}.json` に変更（main `53d170613cca5ea03af232d04039df5a7d6baaa1`）。直前の公開バイト一致ゲートがGitHub保存原本との一致を検査するので、ブラウザ検証は公開JSON→DOM表示の一致を検査する。期待する3連単10/27=1-2-5、10/31蒲郡8R=1-4-6、および正式的中採点禁止は維持。
- GitHub Pages Actions push run最新結果と公開サイトへの直接HTTPアクセスは取得制限により未確認。実装更新を本番合格としない。旧サイト停止・削除なし。

## 2026-11-01 旧予想原本63件の保全追加（PR #781）
- 旧サイトの予想スナップショット4件を保全専用ディレクトリへ追加し、manifest計63件。今回追加分は元repoと保存先のGit blob SHAが4/4一致。
- 既存保全CIの件数下限を63に変更。PR head `0870bf76033e5964389f75329d2c18a4fbad3b60`、Research forecast checks run `41304426947` completed/success。main squash `08e390cbc1d0116e377b8bf586aba9bbeaf3a365`。
- 初回Git保存時刻・締切前性、全旧予想/オッズ/Freshの網羅、独立長期バックアップは未証明。旧サイト停止なし。

## 2026-11-01 PR #782 公式HTML原本の要求URL・応答URLを診断時にも照合
- 公式HTTP観測時に取得元URLの同一性を確認していても、別途保存原本の診断ではmanifest `url` と `response_url` に誤ったレースが書かれている場合の拒否がなかった。診断時に両URLのHTTPS、公式ホスト、beforeinfo path、`hd/jcd/rno` と保全パスの一致を再確認。
- 保存manifestの別R `response_url` を検出する回帰テスト追加。PR head `f314c28ea998975987255f61b4b55e8f9612a0e3` のLate preview evidence run `41304441304` validate success。main squash `e7869d8730b8fc5c46b9f0e588b07d0c6015430f`。
- **公式ライブHTML取得とT-12での6艇完全性の実証は未達。** 新規の予想入力・旧サイト停止なし。


## 2026-11-02 結果JSON取得順序の実行型回帰テスト
- Pagesは同一origin→GitHub Raw、RenderはRaw→同一originの順序で `fetchCleanResultArchive` を使うが、既存回帰は文字列存在チェックのみ。`tests/site-regression.cjs` に本番関数をvmで実行する5ケース（Pages直接成功、Pages→Raw代替、Render直接成功、Render→ローカル代替、双方404）を追加（main `b0722f04cb4a564514090632a76bccac531d5110`）。新規PR/ジョブなし。
- GitHub Actions push CIの実行結果とPages公開画面の実ブラウザ合格は未取得。実装・回帰追加のみを本番修正完了とはしない。旧サイト停止なし。

## 2026-11-02 旧予想原本71件の保全（PR #783）
- 既存63件へ旧repoの実在するJSON原本8件を追加。新規8件は元Git blob SHAと保存先を再取得して8/8一致。保全manifestは71件、保全CIの最低件数を71へ更新。
- PR head `0beec3893797573289188073714cbb3734201f84` のResearch forecast checks実行 `41330148238` はcompleted/success。main squash `52c94fe8ab9b359bc393a380b2d0f21c71938d59`。
- 初回Git保存時刻・予想全件網羅・オッズ/Fresh・非期限付き独立ストレージ復元は未証明。旧サイト停止なし。

## 2026-11-02 PR #784 公式beforeinfoのHTTP開始・受信時刻の監査
- 公式HTML独立取得原本に `request_started_at_jst` を追加し、従来の `received_at_jst` と別に記録。両時刻のJST +09:00および受信時刻が開始時刻以上であることを取得時に確認。保存済み原本をラベル解析する際にも開始時刻の存在と順序を再監査し、逆転・欠損を拒否。
- 時刻逆転の取得失敗、保存manifestの改ざん検出の回帰テスト追加。PR #784 head `863abc53056aaec15b1cb02736ac4ed4927982fd` のLate preview evidence integrity run `41330162864` はsuccess。main squash `5e12bbd8454561e6b8015a6530acd4869c6b6c4d`。
- これは取得時刻の原本証拠準備であり、**実際の公式HTTP受信・T-12時刻・6艇値の完全性は未検証**。予想モデルと旧repo/旧Pagesは未変更。


## 2026-11-02 公式HTMLラベルの周辺テキスト診断
- `scripts/inspect_official_beforeinfo_html.py` に `label_context` を追加し、保全HTML原本にある展示・進入・ST等のラベル前後の短い実テキストを診断JSONへ含める。周辺断片の長さ/件数を制限し、script/styleは除外。main `0fc11e693d1949098bb0b863a23fe41e0805013c`、テスト `3e9ec1fb6ae526b9c680117604db23b579eaa70e`。
- GitHubで同ファイルとテストの現存を再取得して確認。別担当PR #784 のLate preview evidence integrity run `41330162864` はcompleted/successだが、**今回追加した周辺テキストの実レース診断・公式HTTP取得・T-12完全6艇の実証とはしない**。
- 正式予想と旧サイトは変更しない。次は手動probeの実行・artifactからHTML構造を検証する。

## 2026-11-02 PR #785 公式HTML診断artifactにHTTP実観測時間を出力
- 既存 `inspect_official_beforeinfo_html.py` は保存manifestの開始・受信時刻を検証しても診断出力から省略していたため、ラベル調査結果と観測時刻の照合が難しかった。`request_started_at_jst` / `received_at_jst` / `http_elapsed_seconds` を出力し、既存テストでJST・実経過秒数を確認。
- PR head `0193e2398e38d13d01607bb25346f446c99236ab` の Late preview evidence integrity run `41330415655` はsuccess。main squash `53c5cfe54e4db1b86372645b79bc2db7dbcd6e41`。
- **ライブ公式取得は未実行・実証なし。診断artifactに時刻が出ても6艇完全STT+TKZ/T-12成立の証明ではない。** 予想モデル・旧サイトの変更なし。

## 2026-11-02 旧予想原本79件の保全（PR #787）
- 既存71件へ旧repoの実在JSON原本を8件追加、保全manifest計79件。新規8件は保存先から再取得し元Git blob SHAと8/8一致。
- 既存ハッシュ検証の保全下限を79件へ更新。PR head `cec3fc43b84950f297826755f2e0f92eb0f4add0` のResearch forecast checks `41330509281` はcompleted/success。main squash `3edbe38dc18e093dbeb03598bdc9c7859f94e260`。
- 旧予想全件・初回Git追加時刻・オッズ/Fresh証拠・独立した期限なし保存の復元は未証明。旧サイトは停止しない。


## 2026-11-02 4モード研究比較の競合解消・main統合
- main `aa29ce431c53146b890896eff0725632c982a7df` に対し旧PR #851は111コミット遅延・競合。変更差分を確認し、現行mainからPR #954を新設して研究比較コード・テスト・既存研究CIのみ移植。
- #954 Research forecast checks run 41431766333 は completed / success。4モードごとに保存券の確定結果との一致、的中順位、Top3/5/10を読み取り専用で比較。予想生成・オッズ順位・モード仕様は不変更。
- #954 squash merge `826abf1e77d2295de79c61be4452c14e2a7d9336`。重複・競合した旧PR #851は後継PRへの置き換えとしてクローズ。
- 注意: この比較はGit初回公開時刻を独立検証していない研究用であり、正式的中率・ROI・精度向上の証明ではない。Render公開の実動作、Geminiの実データ実行も未検証。
- 次: 保存証拠を持つ4モードの真正性監査→レース別外れ原因分類→Geminiへの読み取り専用入力→実測比較。運用予想の自動書換禁止。


## 2026-11-02 4モード買い目取りこぼし分類（PR #956）
- 最新mainから分岐し、`four_mode_frozen_diagnostic.py` に `coverage_diagnostic` を追加。`covered` / `winner_head_absent` / `winner_second_pair_absent` / `winner_third_absent` の4分類を保存券と確定3連単のみに基づいて計算。
- `race_dynamics_cause=not_determined` を明示。逃げ/差し/まくり・展示・STの物理的原因を、結果のみで断定しない。予想券、予測値、4モード、オッズ順位、正式実測集計を変更しない。
- 回帰テストで1着欠落、1-2着ペア欠落、3着欠落、的中、結果欠損を検査。Research forecast checks run `41432055746` completed/success。
- PR #956 main squash `3edcde5de2b56964dc9db881ad48d645239f9820`。これは履歴研究用（formal=false、remote_first_seen_verified=false）であり、正式的中率・精度向上の実証ではない。本番公開ブラウザ・Gemini実データ実行は未検証。
- 次: 外れ分類の実レース例照合と、独立検証された締切前展示/進入/STの結合。Geminiへは読み取り専用で渡し、採用前に時系列holdout/正式prospective評価を行う。


## 2026-11-02 手動Gemini・4モードレース別研究ケース連携（PR #962）
- 既存 `ai_diagnostics.py` に任意 `--race-code` を追加し、`four_mode_frozen_diagnostic.compare_race` が `historical_comparison_only` と判定した保存原本だけを既存監査JSONに添付。結果欠損/不信頼/原本欠損なら Gemini HTTP以前にfail closed。
- 手動 `ai-operations-diagnostics.yml` に任意レース入力追加。入力は環境変数で安全に渡し、PR CIではAPIキーを渡さず模擬テスト実施。既存の手動未指定動作・APIの自動実行無効を維持。
- Geminiへの指示で、券種の構造的取りこぼし分類と実際の逃げ/差し/ST/展示要因を区別。未検証のまま正式的中率や予想ロジックを変更しない。
- PR #962 の AI operations optional diagnostics Actions run `41433384008` completed/success、main squash `475e6d51eaac8b28e247b76b36adac472c705026`。
- Gemini実APIへの手動送信、実レース1件の分析結果とRender動作、予想精度向上は未検証。次は実保存例の監査・公開前原本時刻証拠と照合し、手動解析結果の妥当性を評価。


## 2026-11-02 実保存レースを用いたGemini研究入力の検証（PR #964）
- 既存原本 `four_mode_forecasts/202610280101.json` と `confirmed_results/202610280101.json` を確認。確定結果は `4-1-3`。保存原本の `generated_at_jst` はファイル内の自己申告日時であり、独立したリモート初回保存証拠とは扱わない。
- `test_ai_diagnostics.py` に実保存レース固定テストを追加。本命/バランス/穴/絞り4モード、予想の取りこぼし分類、`formal_hit_rate_allowed=false`、`remote_first_seen_verified=false` を検査。
- 手動 `--race-code` 指定時にGeminiへ渡す研究比較部分を `ai_frozen_race_case.json` として出力。既存手動GitHub Actionsの90日間artifactにこのファイルを追加。自動API実行や予想ロジック書き換えは行わない。
- PR #964 の AI operations optional diagnostics CI run `41434090900` は completed/success。main squash `55c34045e53036e10026b3eb3aa4b1ca3128560d`。
- 本CIは模擬Gemini応答と実保存原本のオフライン検証。Gemini実APIによる分析成功・出力内容の妥当性・精度改善・Render本番挙動の証明ではない。
- 次: 手動Gemini runの実証と保存artifactの再監査、予想時点の独立初回保存証拠との結合、外れ原因仮説の時系列holdout検証。


## 2026-11-02 Gemini分析出力の証拠審査ゲート（PR #969）
- `ai_diagnostics.py` に `review_analysis_output` を追加。実AI出力を受領しても `improvement_proven=false`, `production_change_allowed=false`, `formal_hit_rate_allowed=false`, `independent_predeadline_receipt_verified=false` を固定し、`manual_evidence_review_required` として次の人手・時系列検証を要請。キー欠落・空出力・未検証レースは別状態へ分類。
- 実保存レース `202610280101` の研究比較を用いた回帰テストで、「的中率が改善する」というAI出力文字列でも自動昇格されないことを検証。PR #969 CI run `41434612141` completed/success。
- PR #969 main squash merge `10c28accc8719a8826e73816b868c27ef9ff3c7e`。予想券・4モード・予想ロジック・自動API実行を変更せず。
- Gemini実APIから返った実分析は今回実行していない。CI成功と分析内容の信頼性・精度改善・Render本番を混同しない。次: 手動Gemini実行のAPI可否と分析artifactを取得して人手証拠審査、独立締切前初回保存時刻と時系列holdoutの接続。


## 2026-11-02 手動Gemini分析の誤成功判定を防止（PR #972）
- 手動 `workflow_dispatch` でAPIキーがなく `status=disabled` となっても成功終了し得た問題を修正。`--require-analysis` により、結果JSON保存後に失敗として終了させる。通常PR検証は従来のオフライン模擬実行を維持。
- `test_ai_diagnostics.py` にAPIキー欠落時、手動必須分析が失敗しても `disabled` レポートを保存する回帰テストを追加。
- PR #972 AI operations optional diagnostics run `41434975368` completed/success、main squash `603b148676e1f3828617b83024937d4cbe02089b`。
- GitHubの手動Gemini実API run一覧は本ターンの接続では取得できず、API呼出実績・AI回答・分析効果・Render本番はいずれも未検証。モデル・4モード・原本は不変更。
- 次: 実手動runのアーティファクトを取得して、Gemini `status=analysis_proposed` と証拠審査の内容を照合する。


## 2026-11-02 Gemini実API/CI結果の分離表示（PR #976）
- GitHub Actions最新100件（確認時点）にある `AI operations optional diagnostics` 7件はすべて `pull_request` トリガー。手動実API解析の完了証拠はこの範囲で未発見。100件より古い履歴も含む完全な不在証明ではない。
- 手動診断失敗時も既存JSONを基に Actions summary で `API analysis status` と `Evidence review status` を明示するステップを追加。CI成功とGemini実API実行を混同しない。
- PR #976 Actions run `41435415754` completed/success、main squash `0f1dfa4b5660113a792c15980725175b015b9464`。自動API実行なし、予想原本・モデル・4モード変更なし。
- Gemini手動実APIの分析と結果内容、的中率向上、本番Render表示は未検証。次は手動dispatchの実行とartifactの取得・検査。


## 2026-11-02 Gemini手動実API検証の接続制約と失敗証拠保全（PR #978）
- GitHub接続はActionsの読み取り・一部再実行は可能だがworkflow_dispatch新規起動アクションを提供していない。実APIの新規手動実行を本ターンで開始したとは主張しない。
- 取得した直近100件のActionsにはGemini診断のPR検証はあったが手動 `workflow_dispatch` は見つからなかった。過去全件を網羅する不在証明ではない。
- `ai_diagnostics.py` でGemini HTTP失敗・レスポンス不正等の例外時、機密情報や生のエラー文字列を保存せず `status=api_error` と例外種類、証拠審査禁止状態を診断JSONへ保存してから手動実行を失敗扱いする。
- PR #978 CI run `41435673089` completed/success、main squash `ecf11c81ad455e33a8f348c1cd5bfbb457f3e4e6`。4モード・予想原本・モデル・API自動実行設定は不変更。
- Gemini実API分析成功・分析の正確性・正式的中率向上は未検証。次: GitHub Actionsから `AI operations optional diagnostics` を手動で `race_code=202610280101` で起動し、artifact の `ai_diagnostics_report.json` と実行summaryを確認（APIキー設定済みであることが前提）。


## 2026-11-02 Gemini研究入力ダイジェスト（PR #983）
- GitHub直近100件のGemini診断ワークフローを再確認。含まれていた実行はPRテストのみで、手動Gemini実API実行の成功証拠は未取得。利用可能GitHub連携に新規workflow_dispatch操作はない。
- Google公式ドキュメントに `gemini-3.5-flash-lite` モデルIDの存在を確認。モデル名は変更しない。
- `ai_diagnostics.py` に研究入力のJSONをキーソート・固定区切りで正規化してSHA-256記録（`research_input_sha256`）する処理を追加。これにより診断レポートと研究入力の一致を再照合しやすくする。入力ハッシュは独立した締切前Git保存証明ではない。
- PR #983 Gemini関連 Actions run `41436489755` completed/success、main squash `258eeef95e5c9ee92211f91308f5ab52153b4e61`。同じheadで別用途のfour-mode-capture-watchdog run `41436481351` はfailure（別件、未調査）。
- Gemini実APIの成功、実分析内容の妥当性、正式的中率改善、Render本番反映は未検証。4モード・予想原本・モデルは未変更。


## 2026-11-02 four-mode watchdogゼロジョブ失敗の追加切り分け
- GitHub Actions run `41436481351` は `push` イベント、workflow表示はパス名 `.github/workflows/four-mode-capture-watchdog.yml`、結論 failure。`/jobs` APIは `total_count=0`。監視スクリプト内の例外が原因と断定不可。
- 同一監視ワークフローのPR run `41436662291` は `Four-mode capture schedule watchdog`、`watchdog` ジョブ success。少なくともPRイベント上の監視チェック経路は動作した。
- 直近100実行の調査範囲では同監視の schedule 成功runを確認できず、**定期実行とfallback dispatchが実際に運用できている証明は未完了**。
- 不具合原因を確証できない状態で監視ジョブを重複新設・削除・再設計する変更は実施しない。次はschedule実行IDとActions実行時刻・fallback dispatch実行ログを照合して稼働証拠を取得する。正式予想、Gemini API、4モードのロジックは不変更。


## 2026-11-02 schedule実行の保存証拠・artifact実点検
- Actions `event=schedule` を用いた専用検索で、4モードprospective capture run `41396587415`（2026-11-02T05:53:05Z）completed/successを確認。test・captureの両ジョブ成功。PR実行と異なり実scheduleイベント。
- artifact `four-mode-capture-41396587415` を取得して解凍。`capture.log` は `new_saved` 48件、`eligible_forecasts_today` 48、`excluded={invalid six national win rates: 2}`、title/race_cards各156行 `available`。`capture_status.json` は `last_run_new_count=48` だが `production_success_proven=false`。
- 48件のうち `four_mode_forecasts/202611020211.json` は後続GitHub main取得で存在を確認。48件全件の独立Git初回追加・受信時刻監査や正式予想成立の証明ではない。capture artifactにはstaging/publish結果の記録がなく、48件全部の公開成否は未確定。
- 以前のwatchdog `push` failure/ゼロjobsと区別。定期captureが少なくとも1回起動し収集候補が生成された事実は実証済み。次は該当48件の初回Git追加タイムスタンプ・締切・公開証拠を一括照合し、正式合格件数を別計上する。


## 2026-11-02 4モード収集のschedule実行証拠を実ジョブログで確認
- Actions `event=schedule` に絞り調査。run `41396587415`（2026-11-02T05:53:05Z）は test/capture 両ジョブ success。capture logに `Immutable four-mode candidates pushed` と新規 `four_mode_forecasts/202611021505.json` 等の作成記録あり。main上でも原本の現存を取得確認。
- 失敗run `41377556221`（2026-11-02T02:24:27Z）では test success / capture failure。失敗ステップ `Stage only immutable new forecasts and check receipt window`、ログの具体エラーは `ValueError: source_receipt_out_of_order`。原因不明のままデータ採用基準を緩和しない。
- watchdogの別系列push失敗runはジョブ0件で、その原因をcapture失敗と混同しない。watchdogのschedule動作・Gemini手動実API実行の成功は依然未検証。
- 注意: 新規Git追加・pushのログは正式な締切前remote-first-seen監査および的中率改善の証明ではない。既存4モード・予想ロジックは不変更。


## 2026-11-02 4モード収集受信時刻JST厳格化（PR #995）
- 過去schedule run `41377556221` の `source_receipt_out_of_order` と成功run `41396587415` を調査。現行収集器は生成時刻が取得時刻より古い候補を明示的に拒否済みで、基準の緩和は不要。
- 検証器 `scripts/verify_four_mode_new_receipts.py` の元データ受信・生成・締切時刻について、時差ありであれば可としていた点をJST +09:00必須に厳格化。UTC表記の等価時刻を拒否する回帰テスト追加。
- PR #995 Four-mode prospective capture CI `41439460878` completed/success、main squash `8559c075799365f5a40544cd4697918f6a283c58`。
- これは入力時刻の検証強化。締切前の遠隔初回保存証明、監視scheduleの継続稼働、予想精度向上、Gemini実API稼働を意味しない。4モードと買い目は不変更。


## 2026-11-02 4モードGit初回追加の元データSHA256監査強化（PR #1000）
- `audit_four_mode_first_add.py` が初回Git追加を調べる際、`source_sha256.title` と `source_sha256.race_cards` の64桁16進数を必須化。既存の新規保存受信検証と歴史監査の証拠条件を統一。欠損・不正ハッシュを拒否するテストを追加。
- PR #1000 Research forecast checks run `41439837038` と Four-mode historical chronology cohort run `41439837041` はいずれも completed/success。main squash `0443d1d65fc15c616a12e187a27ee86153775f29`。
- ファイル記載のハッシュ形式の検証であり、外部ソース実体との内容一致・remote-first-seen・正式的中率の証明ではない。今後独立取得ハッシュとの照合とprospective評価が必要。Gemini実APIおよびRender本番は今回未検証。買い目・4モード変更なし。


## 2026-11-02 4モード元データSHA256と生バイト照合（PR #1002）
- 既存の予想JSONには `source_sha256.title` と `source_sha256.race_cards` があるが、元のCSV/HTTP応答の生バイトは同じJSONに保存されておらず、ハッシュ形式だけで出典真正性や締切前取得を証明できないと確認。
- `four_mode_raw_source_match.py` を追加。別途確保したタイトル/出走表の元バイトファイルを与えたときにSHA256を比較し、一致・不一致・未入手を区別。改変、欠損、シンボリックリンク、巨大ファイルをfail closed。元の予想原本と4モードは読み取り専用。
- ハッシュ一致でも `formal=false`、`remote_first_seen_verified=false`、取得時刻独立検証falseを維持。テスト `test_four_mode_raw_source_match.py` を既存研究CIに追加。
- PR #1002 Research forecast checks run `41440230086` / `41440221185` とも completed/success、main squash `34a47e7bbe3c1b69192dddd42ff1b03f59c0bc1e`。
- このPRは実際の元バイトが既に保全・照合されたという証明ではない。次は各取得方式（CSV全体hash、直接レース別HTTP hash、OpenAPI共通JSON hash）に対応した取得時の原本保存・時刻署名/受信証拠を安全に整備し、独立照合する。Gemini実API・予想精度向上・Render本番未検証。


## 2026-11-02 4モード取得元のHTTP生バイト保全（PR #1006）
- スケジュール収集時のみ `FOUR_MODE_RAW_RECEIPT_DIR=four-mode-evidence/raw-sources` を設定。公開前CSV / Boatcast直接HTTP / 代替OpenAPIの取得応答バイトを、出典URL・ローカルJST受信時刻・SHA256とともにwrite-onceのアーティファクトへ保全する処理を追加。30日保持、既存予想モデルと順位は不変更。
- `four_mode_raw_receipt.py` とテストを追加。許可HTTPSホスト、改変・衝突、保存省略時の無副作用を検査。実際の過去原本は後付け保全できず、この追加は「今後の収集」用。ローカル受信時刻は独立remote first-seen証明ではない。
- 他CIの夜間失敗を調査した結果、`tests/test_daily_research_written_mass.py` が現在時刻＋5時間を同じ日として扱う日時越えテスト不具合を修正。予想ロジックは変更しない。
- PR #1006 head `5b84c7640f24d1f92088decc7f1502c0b08ead8a` の6系統CI（Four-mode prospective capture、Research TopN batch audit、Research forecast checks、Cross-model content audit、CLEAN alternate feed、CLEAN six-boat parser）がすべてsuccess。main squash `d7860353702c81fcedfd8b9f421f4506baf44b66`。
- 生バイト保全の実運用artifact・元データとの実ハッシュ一致・取得時刻の独立証明、Gemini実API分析、予想精度改善、Render本番は未検証。次は次回実収集artifactのraw-sourcesと予想原本のSHA256比較、取得方式ごとの対応確認。


## 2026-11-02 原本取得artifactのローカル整合性監査（PR #1010）
- PR #1006後の実定期schedule runは今回調査可能なschedule履歴にまだないため、元HTTP原本の実運用保全と予想JSONとの実照合は未実証。
- `audit_four_mode_raw_receipts.py` に保存artifact内の各 `.json` / `.bin` ペアを監査する機能を追加。URL許可リスト・受信JST・byte_count・SHA256・原本IDとファイル名の一致、欠損・余分なバイトファイルを検査。検証成功でも正式的中率や独立remote-first-seen証明は許可しない。
- テスト `test_audit_four_mode_raw_receipts.py` を収集ワークフローに接続。最初のPRテストはID区切りバイトの取り違えで失敗したため修正し、再実行の Four-mode prospective capture run `41441590188` は completed/success。PR #1010 main squash `74fae3a033027f3f3bf5600d28c872321b60034c`。
- 次はPR #1006/#1010以後の実schedule runの raw-sources artifactを取得して整合性監査し、予想原本のtitle/cardsハッシュと対応確認する。Gemini実APIとRender、精度向上も未検証。


## 2026-11-02 4モード予想ハッシュとHTTP原本の対応照合（PR #1011）
- PR #1006/#1010統合後の新しいschedule収集runは今回取得できた履歴で未確認。実運用のraw-sources artifactと実ハッシュ一致は未実証。
- `link_four_mode_raw_forecast.py` を追加。既存 `audit_four_mode_raw_receipts.audit` でローカル原本ペアの整合性を合格判定した後、予想JSONに記録された `source_sha256.title/race_cards` が原本マニフェスト群に含まれるか照合する。欠損・不一致・原本未確認を分離。研究専用で `formal=false`、`remote_first_seen_verified=false` を固定。
- 保存・収集経路、予想ロジック、4モードは変更せず、収集ワークフローのPRテストに対応テストを追加。PR #1011 Four-mode prospective capture run `41442022996` completed/success。main squash `eba9d780cf1e65c9b86c99a84e641a44ca2155b9`。
- 次は実scheduleで保全された原本artifactを取得して、実予想の対応、タイトル/出走表の取得方式、受信時刻の安全性を検査する。Gemini実API、Render本番、予想精度改善も未証明。


## 2026-11-02 4モード実収集の原本照合レポート追加（PR #1016/#1019）
- 直近確認可能なschedule runは旧SHA `01d5cda7...` の #41396587415 が最新。#1006以降の新しい原本保全を使ったschedule runは未確認。手動run #41440004104 は成功・artifactありだが #1006以前のコードのため、新保全機能の証拠にならない。
- PR #1016: 各収集runの当日4モード予想について保全されたHTTP原本のハッシュ照合結果を `four-mode-evidence/source-links.json` に記録してartifactに追加。欠損・不一致を合格としない。CI #41442522181 success、main `c12b41bc0194dc6e2db7bf5813f062cb18f9c907`。
- PR #1019: source-links.jsonの末尾改行にリテラルバックスラッシュが混入する問題を修正。CI #41442668543 success、main `0876cc37bb4580826789afe7e2de19e708e7428e`。
- この時点で実運用の照合成功件数・独立締切前remote-first-seen証明・正式的中率・Gemini実API・Render本番は未検証。予想ロジックと4モード、買い目は不変更。


## 2026-11-02 実原本連動の収集時刻ゲート（PR #1021）
- PR #1016は本ターン開始時点で既にmain統合済み（squash `c12b41bc0194dc6e2db7bf5813f062cb18f9c907`）。同PRのCIは成功済み。
- 取得できた定期schedule履歴ではPR #1006以後のraw-sources実運用artifactは未確認。手動収集 run `41440004104` は成功したがPR #1006より前のコードだったため実証に利用しない。
- `link_four_mode_raw_forecast.py` が、予想生成後に取得した元データでも同ハッシュなら一致扱いにし得る点を修正。JST受信時刻 <= JST予想生成時刻を必須にし、遅い証拠を照合対象から除外。テスト追加。
- PR #1021 Four-mode prospective capture run `41443079562` completed/success、main squash `02b7387d95c76bf6152fce6e53604b96f5d5c3f0`。一度main更新競合したが再確認の上正常統合。
- 実生データの保全・ハッシュ照合、独立remote-first-seen、Gemini実API、的中率改善は未確認。予想原本・モデル・4モード不変更。


## 2026-11-02 Gemini予想研究向け4モード複数レース比較（PR #1027）
- 手動workflow_dispatch履歴を確認。`AI operations optional diagnostics` の手動Gemini実API実行成功は今回も見つからず、`AI repair proposal` の実行とは混同しない。
- `four_mode_research_batch.py` を追加。最大30件の履歴4モード固定買い目と確定結果を比較し、モード別の外れ分類、Top3/Top5/Top10、結果待ち・不正記録を分離。欠場・水面展開などの原因を結果だけから捏造しない。
- 出力は必ず `formal=false`、`model_improvement_proven=false`、`remote_first_seen_verified=false`。この履歴率は正式な前向き的中率ではない。既存モード順・買い目・予想ロジック変更なし。
- PR #1027 AI operations optional diagnostics run `41444434450` completed/success、main squash `fb87d710b0ddb9784a7f4e090903ac08b3120891`。
- 次は実レース履歴複数件で一括研究レポートを生成し、Geminiを手動実行した際の監査用入力に利用する。実API成功・予想改善・Render本番は未検証。


## 2026-11-02 Gemini予想研究AIの応答安全性（PR #1031）
- 実コード `ai_diagnostics.py` と既存回帰テストを確認。手動AIサイト修正 run `41387313853` は処理successだが実際の応答は `no_safe_patch` で変更提案なし。予想研究Gemini実API成功、正式的中率向上は引き続き未確認。
- Gemini予想研究のレスポンスが候補/partの不正型、空白テキスト、16KB超のテキストを含む際に黙認や未処理例外にならず `ValueError` で拒否する検証を追加。API権限、モデルや買い目、4モードは不変更。
- PR #1031 AI operations optional diagnostics run `41449745427` completed/success。main squash `a1cc4586e71a30afd7499de733aacc87a6770639`。モックによるCIであり、Gemini研究分析APIの実サービス成功は意味しない。


## 2026-11-02 Gemini予想研究実行可視化（PR #1033）
- AI operations optional diagnostics run のPRテスト成功は Gemini実API分析を意味しない。取得可能な最新実行履歴では当該workflowの手動API成功は確認できず、AIによるTop3/5/10的中率改善は未実証。
- `.github/workflows/ai-operations-diagnostics.yml` のGITHUB_STEP_SUMMARY出力が改行ではなく文字列 `\\n` を表示していた点を修正。API分析statusとevidence_reviewを別行で表示する。PR #1033 AI operations optional diagnostics run `41450364220` completed/success、main squash `e5215a585f9ae3ec491b110d8b1f93afd0c68fc7`。
- PR上のCIはオフライン検証。Gemini実APIは手動workflow_dispatchが必要で、この回は未実行。4モード、買い目、研究モデル、正式実績の区別を維持。


## 2026-11-02 Gemini保存済み実レースのCLI統合回帰（PR #1035）
- 取得できるworkflow_dispatch履歴には `AI operations optional diagnostics` の実API成功runがなく、Gemini実サービスによる予想分析の成功は未確認。CI上のモック成功と明確に区別。
- 保存済み桐生1R `202610280101` を対象に `ai_diagnostics.main` のCLI全経路をモックGeminiレスポンスで通し、比較ケース保存・入力SHA256・AI診断レポート生成・手動監査必須・正式的中率および本番自動変更禁止を回帰テストに追加。
- PR #1035 AI operations optional diagnostics run `41450912465` completed/success、main squash `28c00f5021312af578047ebc03414ab09fad8ebf`。予想ロジック・4モード変更なし。次は実API手動runと出力証拠の検査が必要。


## 2026-11-02 Gemini実レース診断の手動API実行待ちと表示修正（PR #1038）
- GitHub Actions `event=workflow_dispatch` の取得可能履歴に `AI operations optional diagnostics` の実行は0件。実API分析成功は依然未検証。利用可能なGitHub連携には新規workflow_dispatch起動操作がなく、この作業ではAPI実行していない。
- `.github/workflows/ai-operations-diagnostics.yml` の実行サマリーでstatus/reviewを表示するMarkdownバッククォートがバックスラッシュ付きで表示され得る点を修正。PR #1038 CI `41452441009` completed/success、main `872e6aec6fdb25e1a6a5f9465aada7e67c88216f`。
- 実APIを確認するにはGitHub Actions `AI operations optional diagnostics` のRun workflowから `race_code=202610280101` を指定して手動起動し、`ai_diagnostics_report.json` のstatus/evidence_reviewを確認する必要がある。4モードや予想ロジックは不変更、正式的中率改善の証拠にはしない。


## 2026-11-02 Gemini生成終了状態の監査強化（PR #1041）
- GitHub Actions `workflow_dispatch` 履歴では `AI operations optional diagnostics` の実API分析runは引き続き0件。既存モデル名 `gemini-3.5-flash-lite` はGoogle公式モデル資料で有効なモデル名と確認したが、当該キーでのAPIアクセス成功は未確認。
- `ai_diagnostics.extract_text` で Gemini `finishReason=STOP` を必須化。テキストがあっても MAX_TOKENS、SAFETY、finishReason欠損は分析成功扱いしない。模擬レスポンスと回帰テスト更新。
- PR #1041 AI operations optional diagnostics CI `41453095723` completed/success、main squash `04e10368827bae073a0681e4c5065ff8cabf02de`。実Gemini APIはこのCIで呼んでいない。4モード・買い目・正式的中率を不変更。


## 2026-11-02 Gemini研究AIの複数候補混同対策（PR #1044）
- Gemini応答の `finishReason` がSTOP以外の打ち切り・ブロックを拒否する仕組みは、別作業のPR #1041で既にmain統合されていることを確認し、重複変更を回避。
- 今回は `ai_diagnostics.extract_text` が複数候補の内容を連結して単一の分析案と誤認し得る点を修正。候補はちょうど1件のみ受理し、複数候補は `ambiguous_candidate_count` でfail closed。回帰テスト追加。
- PR #1044 AI operations optional diagnostics CI `41453379722` completed/success、main squash `9eb6eb926ea56fb7147ec11b70b78b453a29785c`。モックCIでありGemini実API分析の成功ではない。4モード・予想ロジック不変更。


## 2026-11-02 Gemini研究API応答の実モデル・token監査（PR #1047）
- `workflow_dispatch` 履歴では AI operations optional diagnostics の実API実行は引き続き未確認。Gemini実レース分析の成功・精度改善は主張しない。
- Google公式ドキュメントで `gemini-3.5-flash-lite` が有効なモデルコードと確認。
- `ai_diagnostics.py` にレスポンス由来の `modelVersion` と `usageMetadata`（prompt/candidates/total tokens）を任意項目として保存。異常な型・負数などを拒否。使用量は診断監査でありAI精度の実測ではない。
- PR #1047 AI operations optional diagnostics run `41454646320` completed/success、main squash `84735936f5ab551571e4e338311afd50be3597bd`。API模擬テストであり実課金APIは未実行。4モード、買い目、予想ロジックは維持。


## 2026-11-02 Gemini分析入出力の実改行修正（PR #1051）
- 最新 `workflow_dispatch` 履歴に AI operations optional diagnostics の実API成功はまだ見当たらない。今回のCIもAPIモック検証であり、Gemini実レース分析・的中率改善を意味しない。
- `ai_diagnostics.py` の分析プロンプト区切りと複数part出力の結合にリテラル `\\n` が混入していたため、実改行（LF）へ変更。実改行の回帰テスト追加。
- PR #1051 AI operations optional diagnostics CI `41455070801` completed/success、main squash `81ddc90acbd7f1724e541e76106effb4877b3de2`。4モード・買い目・予想ロジック不変更。


## 2026-11-02 Gemini手動実レース分析の初期設定修正（PR #1057）
- 当時のGitHub Actionsのworkflow_dispatch履歴で `AI operations optional diagnostics` は0件。Geminiの実APIレース分析・予想的中率改善は未実証。
- 手動Run workflow入力が空の場合、既存ワークフローはレース比較を省略して一般監査だけをGeminiに送っていたため、`race_code` を必須・保存済み `202610280101` を初期値に変更。手動実行では形式を検査して `--race-code` の実レース研究経路を必ず使う。
- PR #1057 AI operations optional diagnostics CI `41456093913` completed/success。main squash `b92cd29428f5117384309cab12e3222e306045d6`。このPRのCIはモック・オフラインであり、手動Gemini実API実行ではない。4モード・買い目・予想ロジック変更なし。


## 2026-11-02 Gemini手動分析の課金前レース証拠チェック（PR #1061）
- GitHub Actionsのworkflow_dispatch履歴に Gemini AI operations optional diagnostics の実API実行は0件であり、実Gemini研究分析・的中率改善は未検証。
- 手動Gemini分析の前に `four_mode_frozen_diagnostic.compare_race` で保存予想と確定結果を検証し、不足ならAPI要求前に停止するようワークフローを修正。`ai_frozen_race_preflight.json` を収集artifactに加え、比較可能かをread-onlyで記録。先行PR #1057の初期レースコードを維持。
- PR #1061 CI `41456856034` completed/success、main競合を再確認し統合 `b6fa9fe87d7ab08ea391d223e27e64c6af71d50d`。CIはPRオフラインテストのため、手動Gemini実API成功は意味しない。買い目・4モード・予想ロジック不変更。


## 2026-11-02 Gemini API事前検証の実行可能テスト化（PR #1065）
- `AI operations optional diagnostics` の手動workflow_dispatch実行履歴は確認時点で0件。実Gemini分析成功・予想精度向上は未実証。
- 従来workflow内に埋め込まれていた保存済みレース/確定結果の事前検査を `ai_frozen_race_preflight.py` に分離し、CIで実際に同じ判定関数をテスト。既存桐生1R `202610280101` に対する比較可能判定、正式扱い・独立証拠欠如ケースのfail-closed、入力不正拒否を検証。
- PR #1065 AI operations optional diagnostics #41457311378 completed/success、main squash `b73bc29d87d4745d2847f31e1d59f73697438f2f`。手動Gemini API呼出しは行っていない。4モード・買い目・予想ロジック変更なし。


## 2026-11-02 4モード同一レース比較 Top10 研究（PR #1068）
- `AI operations optional diagnostics` の新規 workflow_dispatch 実API実行は確認できず、Gemini実分析・改善実証は引き続き未達成。
- `four_mode_research_batch.py` に「絞り vs 本命、本命 vs バランス、バランス vs 穴」の同一研究レース Top10 被覆比較（両方・左のみ・右のみ・両方なし）を追加。確定結果なしを分母に混入しない。研究専用 `formal=false`、予想ロジックと買い目は不変更。
- PR #1068 AI operations optional diagnostics CI #41458557108 completed/success、main squash `69e0903d8e370d4095b8204fde822911bb46232a`。この比較は過去アーカイブ研究であり、独立締切前証明やAIによる的中率改善ではない。


## 2026-11-02 4モード追加買い目のTop3/5/10増分研究（PR #1073）
- 同一レースでの隣接モード（絞り→本命→バランス→穴）ペア比較をTop10だけからTop3/Top5/Top10に拡張。双方的中、左だけ、右だけ、両方不的中、右の純増的中件数と増減率（パーセントポイント）を算出。既存の `paired_top10` キーも互換保持。
- 確定結果のないレースは分母に含めず、比較対象0件の場合の増減率はnull。研究用で `formal=false`。実AI分析、Gemini API実行、正式的中率改善とは別。
- PR #1073 AI operations optional diagnostics #41459680799 completed/success、main squash `59cdce83a7836eebb6597d9cfd95dd0c3aff8d04`。予想原本、4モード構成、買い目・予想ロジック変更なし。


## 2026-11-02 4モードTopN入力検証強化（PR #1075）
- `four_mode_research_batch.summarize` に事前整合性検証を追加。研究用Top3/Top5/Top10の欠損・非boolean、Top3⇒Top5⇒Top10の包含関係違反、カバレッジとTop10矛盾、未検証の展開原因を拒否。不完全フラグを不的中として計上しない。
- 回帰テストを追加しPR #1075 AI operations optional diagnostics CI #41460287758 completed/success、main squash `4e780150536d2748d1286194efc4018c68edd0cf`。研究比較の検証強化であり、実的中率/AI精度の改善実証ではない。4モード・買い目・予想ロジック変更なし。


## 2026-11-02 保存済み実レース30件の4モードTopN研究（PR #1078）
- `four_mode_historical_cohort.py` で保存予想と確定結果が存在する先頭30件を実集計、JSON artifactを出力。
- 初回CIは買い目全体の的中がTop10外にある場合の誤制約 `covered_without_top10` で失敗。修正して再CI #41461094176 success。
- 30件の歴史研究比較：絞りTop3/5/10=5/5/5、本命5/5/9、バランス4/6/9、穴1/1/3。Top10純増は絞り→本命+4、本命→バランス0、バランス→穴-6。正式的中率やAI改善の証拠ではない。
- PR #1078 main squash `2498d7fec67b146bb8f1b3d97df8c966a1e76f0d`。4モードと予想ロジック不変更。


## 2026-11-02 保存済み120レースの日付・場コード別TopN研究（PR #1083）
- 既存30件上限を維持して小分けに集計し、同一保存レースから最大120件までTop3/5/10を日付・場コード別に算出。PR #1083 CI #41461677641 completed/success、main squash `11f574bd1d440e155421fe9293b54de5abe05834`。
- 実集計120件は全て20261028の1日。Top3/5/10: 絞り19/24/24、本命19/24/41、バランス18/25/39、穴1/2/6。穴Top10=6/120=5.0%、本命=41/120=34.17%。場別は母数5〜12件程度で評価に不足。
- この集計は歴史的アーカイブの買い目カバレッジであり独立した締切前保存証明・正式的中率やGeminiによる改善を示さない。予想ロジック、モード、買い目変更なし。次は複数日の前向きデータと場別標本数拡大。


## 2026-11-02 複数日分散の4モード120件研究（PR #1086）
- PR #1083の120件集計は全件2026-10-28だった。日別検証に不適切な偏りを解消するため、保存済み予想と確定結果の共通レースを日付ごとにラウンドロビン抽出するよう変更。
- CI #41463768144 success。対象120件は10/28・10/29・10/30・10/31・11/02各24件。Top3/5/10的中カバー件数：絞り21/26/26、本命21/26/46、バランス20/24/48、穴1/2/4。いずれも過去アーカイブ研究値、締切前独立確認のない正式的中率ではない。
- PR #1086 main squash `8dad84c652ecab5b9ec17c167ea63475ebcee86f`。予想原本、4モード、買い目、予想ロジック変更なし。


## 2026-11-02 日付×競艇場分散の実アーカイブ120件研究（PR #1091）
- PR #1086の1日24件の抽出は日付分散されていたが競艇場ごとの先頭レースに偏る余地があったため、日付内で場コードをラウンドロビンし、日付間も均等に抽出するよう研究抽出法を改善。
- CI #41464365817 successful。5日×24レース（計120件）、19場を対象。研究用Top3/Top5/Top10件数：絞り15/27/27、本命15/27/49、バランス17/27/47、穴1/2/7。抽出方法が違うので以前の120件と数字が変わるのは妥当。正式的中率・AI改善証明ではない。
- PR #1091 main squash `a26fe3ea4d41c6edbce69e723fda5822736439cf`、予想ロジック・買い目・4モード不変更。


## 2026-11-02 穴モード不的中構造・順位内訳研究（PR #1093）
- 日付×場分散の研究120件から、各モードの的中順位帯と不的中パターン、総買い目数をCIで集計する機能を追加。競走展開の原因は断定しない。
- 穴モード：Top3=1、Top5=2、Top10=7、11位以下的中=2、全買い目不的中=111。全買い目不的中の内訳：1着艇頭なし18件、1着艇頭は含むが1・2着ペアなし84件、1・2着ペアあり3着なし9件。買い目総数1440件（120レース分）。保存済み過去研究であり正式精度や改善実証ではない。
- PR #1093 CI #41464957828 success、main squash `25847d116796095b272c2d2506f231d774ae2c47`。4モード、予想コード、公開買い目不変更。


## 2026-11-02 穴モード2着候補の実アーカイブ照合（PR #1097）
- 日付・場分散120件のうち、穴モードで1着艇を買い目に含むが正しい1-2着ペアがない84件を再照合。1着固定時の2着候補数1艇64件・2艇11件・3艇8件・4艇1件。本命には正しいペアが67件、バランスには61件存在。勝ち艇の2着分布は1号艇23、2号艇21、3号艇18、4号艇12、5号艇10。
- `four_mode_historical_cohort.py` にアーカイブ再読込によるfail-closed照合、件数と限定的なレース事例を追加。CI #41465608023 success、PR #1097 main squash `f516fd07c186095fc0e6a17d0cc2a75b3302f718`。
- 過去の研究値であり、2着増設による精度改善は未実証。予想ロジックと公開買い目不変更。


## 2026-11-04 JST 継続：CSV未掲載時の公式展示補完（PR検証待ち）
- 根拠: 19:39:21 JSTに桐生11Rの公式 beforeinfo JSONを実取得。締切20:03、6艇の展示タイム/チルト/ST/進入あり。CLEAN APIは同時点でCSVの対象レース未掲載によりbeforeinfo=null。同APIと公式の登録番号6艇が完全一致。公式原文・manifestは `docs/observations/official_preview_20261104/`、テスト用同一原文は `tests/fixtures/official_preview_202611040111.json`。原文SHA256=40e7859d3841f6a9b6329b1a7426cad46dd65f98562a38e3f06cc4fa24a02d01。
- `official_preview.py` は既存公式JSON検査器を再利用し、HTTP200・最終URL・1MB上限、日付/場/R/締切、登録番号6艇、欠場なし、展示タイム5〜9・チルト−1〜3、ST/進入6艇完全性、JST受信時刻<締切を全て要求。CSVで展示が取得できない締切前レースだけ補完し、既存CSV優先・締切済み参照では公式取得しない。失敗時は出走表を保持し、CSV理由と公式失敗理由を残す。原本/モデル/予想生成/正式採点ゲート不変更。気象の補完は含めない。
- 実コードでracecard(20261104,01,11)を19:44:34 JSTに再取得し、公式6艇タイム6.66/6.68/6.59/6.81/6.63/6.67、ST F.01/F.03/F.06/.08/.03/.06の正規化とstatus=okを確認。source SHA256=f7b256e8ea4ea63da4df2321426cb42b6586e849398dfc12163d7224b59047f4。T−12より前のHTTP観測だが、独立の上流測定時刻証明・正式T−12認定ではなくformal_t12_certified=falseを維持。
- ローカル試験: 公式adapter/統合8件、出走表14件、既存展示完全性7件、出所5件、ナビ14件とNode site-regression成功。既存navigation workflowに新adapter/実原文fixtureの回帰検査を追加。PR CI・main統合・Render API/ブラウザ表示は別途確認し、未反映の段階では本番復旧と呼ばない。

- PR #1617初回CIで既存`Verify REAL beforeinfo source`が`REAL_BEFOREINFO_NO_VERIFIED_RACE`。実ログで昨日の日程へ現在の受信時刻を使うため常時締切後拒否となる検査を特定。既定対象日を当日へ修正し、CSVに未掲載なら現行production adapterから当日の締切前6艇を実取得して検証する。空/締切後/不完全は引き続きfailure、歴史日付を現在の公式取得で代用しない。追加回帰2件。cron自体は変更しない。
