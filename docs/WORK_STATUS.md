# BOAT EDGE CLEAN — 作業引き継ぎ / WORK STATUS

更新日: 2026-11-01 (JST)
この文書は会話をまたぐ運用上の引き継ぎ。下記の「過去会話による報告」は今この文書を作成した時点での本番再検証を意味しない。実際のGitHub/CI/Render/公開URLの状態を調べ、確認できた証拠で更新する。

## BOATERSモデルを全担当の固定方針とする（2026-11-01 ユーザー指示）
- 正本は AGENTS.md の「UI・情報設計の最優先固定方針」。メイン開発／予想研究／データ収集の全トークに適用。
- BOATERSをモデルにした1レース1ページ：確定結果を予想より上へ、AI展開予想、先頭艇別条件付き2着/3着率、6艇別イン逃げ/3連対/決まり手率、展示・進入・気象、最終3連単予想とオッズ。
- 既存ドラフトPR #725 はUI土台。未取得が多く、数値連携・CI・実機・本番確認は未完了。**完成扱い禁止**。メイン開発が重複PRを作らず内容を整理・統合する。
- 収集担当：選手・コース別/先頭艇条件付き成績の期間・分母・出典を検証して保存。研究担当：実測率とAI予測確率を分離して予想寄与を検証。メイン担当：表示・1ページ統合・回帰試験・本番確認。無関係な変更でUI方針を覆さない。

## 現在の最優先作業
| 優先 | 作業 | 状態 | 完了条件 |
| --- | --- | --- | --- |
| P0 | 旧サイト・不要コード・旧導線の参照/依存を調査し安全に撤去 | 未完了・要調査 | 現行本番への参照とデプロイ依存を確認し、不要物の削除後も回帰テスト成功。旧リポジトリは無断削除しない |
| P0 | 当日/昨日/過去日の出走表・予想の非表示不具合 | 未完了・要再現 | 実レースで該当データが公開画面に表示されるか、データ欠落理由が明確 |
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

## 2026-11-01 12場の404原因確定（非開催）
- Renderログ `2026-10-31 20:30–20:36 UTC` で翌11/1の `jcd=12`、1R/5Rの404を観測。12場は住之江。BOAT RACE公式の開催予定は住之江11/5–11/10（高松宮記念特別競走）で、11/1は非開催。独立した11/1の開催場一覧も住之江を非開催としている。**この404は非開催日への問い合わせであり、開催中出走表の不具合ではない**。以前の疑義を訂正。根拠: https://www.boatrace.jp/ と https://boatrace-techo.com/?date=2026-11-01 。
- これは旧サイト撤去ゲートの締切前6艇展示・進入・時刻証拠の成立を示さない。実際の開催場で定期E2E実測成功を得る必要がある。旧repo/Pages停止・削除なし。

## 2026-11-01 T-12ゲート#734 の実行可否を確認
- 既存PR #734はmain commit `d7ebf6711a8dd5aa4a33b4b5c50a7c5590396c74` へ統合。独立 `tkz` / `stt` ソースの時刻がいずれも締切12分前以前なら `T12_COMPLETE_PAIR_PASS`、未証明なら `NO_T12_SIX_BOAT_PAIR_VERIFIED` で不合格とする検査が追加された。
- PR headのActions run `41240118410` では履歴出走表、結果、120オッズ、構文の4ジョブsuccess。一方 `e2e-live-race` はPR時の仕様でskipped。**T-12成功の証拠はまだない**。
- 本日最初の定期サンプルは09:30 JSTの設定で、05:43 JST時点ではこの時間に達していない。今回の調査で過去の実レースE2E成功の新証拠は得られなかった。実測に基づく停止判定は保留し、旧サイトは変更しない。
