# 穴モード 2026-11-09以降：候補固定の起動経路監査（研究のみ）

**状態：2026-11-08 JST、Draft PR #1685。main・Render・本番予想・収集処理・UI・Cloudflareへの変更なし。main自動統合禁止。**

## 確認した事実

- 研究PR上の `.github/workflows/hole-future-pair-precommit.yml` は `pull_request` と `workflow_dispatch` を定義するが、候補生成・候補ZIPアップロードのステップは **`github.event_name == 'workflow_dispatch'` のときだけ**動く。通常のPR CIはテストのみ。
- 2026-11-08の最新確認main `6b371040fd2fc4398bfa882e6557c333cc0800c8` の全11,247 Gitツリーエントリには、**同名ワークフローファイルが存在しない**。
- GitHub公式の `workflow_dispatch` 要件：対象ワークフローがデフォルトブランチ上に存在しない場合、手動トリガーは利用できない（https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_dispatch）。
- 従って、現在のDraftブランチに `workflow_dispatch` と書かれていても、そのことだけで **11月9日以降の研究候補固定が手動起動可能になったとは認定しない**。
- PR CI #42475509025: 成功。ただし候補固定・候補アップロードは両方スキップ。研究用 `hole-future-pair-precommit-readiness` ZIPに、本監査の `research_capture_launch_readiness.json` と従来の `research_not_eligible.json` を保存。前者は `default_branch_dispatch_prerequisite_satisfied=false`、`formal=false`、`capture_run_executed_by_this_audit=false` を返した。
- 確認したPRのバージョン：`14490a6d5d822fe3ae336fdc88f0d9785f186179`。研究用コードテスト成功は、新しいレース予想を受信・保存したことを意味しない。

## 対応ルール

1. **候補選択ロジック・既存のNov6/Nov7原本・Top5保護・固定メソッドSHAを変更しない。** 11月8日以前の確定結果を11月9日以降の予備検証・確認検証に含めない。
2. 新しい候補については、正式な `workflow_dispatch` 起動経路がレビュー・承認されるまで **`capture_not_started`** とし、未取得を的中・外れのいずれにも数えない。PRイベントの自動起動や過去データを使った再固定は代替策として認めない。
3. 起動設計は**別途手動審査**。候補は本番側とは分離し、起動権限と書込先を限定する。既存main上の別業務・別研究ワークフローの改変や本番導線の流用を、この研究PRが勝手に実施しない。
4. たとえ起動経路を用意しても、別々に **実際の候補固有の初回受領証拠、T−12以前の公式6艇beforeinfo/展示と120通りオッズの完全性、独立確定結果** を検証しない限り正式認定不可。Cloudflare Worker＋D1受領側は現時点で設計・オフラインテストのみ、実配備なし。
5. 実検証開始後は、事前登録済みの順序（最初の適格300件をpilot、次の300件をconfirmation）、同一レース重複排除、欠落・中止理由、Top1/3/5/10、現行対2候補のTop10獲得／喪失を記録。結果を見てから候補を変更・補充しない。
6. 本研究でPRを更新しても `Draft=true` のままとし、main・Render・モデル・UI・既存の正式予想・スケジューラ・Cloudflareを変更しない。自動統合しない。

## 再現可能な調査方法

- default branchの登録確認：`git ls-tree -r --name-only origin/main -- .github/workflows/hole-future-pair-precommit.yml`
- read-only判定：`python research/hole_pair_capture_launch_audit.py --default-ref origin/main`
- 回帰テスト：`python -m unittest -v research/test_hole_pair_capture_launch_audit.py`
- CI: `hole-future-pair-precommit.yml` の read-only監査ステップを参照。

**正式認定0件、当該プランの実候補初回受領認定0件、実運用開始未確認。研究参考のNov6/7の102レース的中実績とは別。**
