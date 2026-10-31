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
