# 穴モード候補：Cloudflare Workers＋D1 初回受領試作（未デプロイ）

**状態：研究用Draft PR #1685の提案コードのみ。CloudflareのWorker・D1は作成せず、main、Render、予想モデル、本番買い目、定期実行設定は変更しない。**

## 対象と保証範囲

- 2026-11-09（JST）以降に実際に結果より先に固定された穴モード候補だけを受信。11月8日以前の研究済み候補は受付拒否。
- POST /v1/first-accept はBearer認証を要求し、元予想のSHA256/Git blob、選択ロジックSHA256とGit blob、3方式の候補ダイジェスト、Top5・元の1-2着ペア保護、レース日・T−12・生成完了時刻を検査する。ただし**申告された公式締切が真であることまでは証明しない**。
- DBの race_code を主キーに、候補の原文相当、候補SHA256と初回保存時刻をD1へ**原子的に1件だけ**登録する。初回保存時刻はSQLiteサーバーの strftime(..., 'now') で付与（GitHub/Worker/呼出元のローカル時計は受領時刻の根拠に使わない）。
- 同じINSERT内で **D1時刻＋2秒 < 候補が申告したT−12** と **D1時刻 > 申告した候補計算完了時刻** を確認。遅れた新規保存を拒否。同一レース同一原本の再試行は最初の保存時刻のまま応答。異なる原本は409。
- UPDATEとDELETEをSQLトリガーで拒否。ただしCloudflare D1の**管理者によるALTER/DROP等の権限は別問題**で、アプリ側のトリガーだけで管理者にも改ざん不可能な証拠にはならない。
- RECEIPT_TOKEN はWorker secretとして設定する設計。キー、トークン、データベースID、外部エンドポイントは一切PRへコミットしない。GET/一覧/変更/削除エンドポイントは用意しない。
- 受信時刻を返すだけで formal=false、independent_first_receipt_verified=false、official_t12_complete_verified=false、production_promotion_allowed=false を変えない。**D1を所有する主体と完全に独立した時刻の監査・署名付き外部証跡、正式な出走表/展示6艇/120通りオッズのT−12以前の証明、締切時刻の独立検証は未実装**。

## 2026-11-08追加：既存受領行の時刻を再送時にも検査

- 受領Workerの初期試作は、初回INSERT時にはD1サーバー時計でT−12前判定する一方、**同一レース同一候補の再送時**にはSELECTで既存のSHA・原文・締切を照合するだけで、保存済み`first_received_at_utc`自体の整合性を再検査していなかった。
- この欠落を研究用Draft内だけで修正し、最初の保存時刻が候補計算完了以前、T−12直前／以降、不正文字列、日時形式不一致ならHTTP 409 `stored_first_acceptance_clock_untrusted`を返す。既存の行を上書きしない。**DB内部の申告時刻を検証するだけであり、管理者から独立した署名や公式締切の証明にはならない。**
- テストは、保存済み時刻を故意に破損させた後の同一原文再送、締切後の一致再送でも合格ではなく内部整合のみを意味することを確認する。固定済み候補、選択ロジック、本番データの変更はない。
- [Actions #42477042688](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42477042688) で既存研究テストと追加検証が成功。候補固定・候補ZIPアップロードの各ステップはPRイベントでスキップ。**実Cloudflare/D1への配備・初回受領実証は未実施。**

## ファイルとテスト

- research/hole_pair_first_receipt_worker.mjs：受信側Workerの原型。デプロイされない。
- research/hole_pair_first_receipt_schema.sql：D1テーブル・更新削除禁止トリガー。
- research/test_hole_pair_first_receipt_worker.mjs：Node標準ライブラリでHTTP/DB模擬検証。
- research/test_hole_pair_first_receipt_sql.py：PythonのSQLiteで**実際のWorker内INSERT SQL**、ユニーク制約・DB時刻・締切境界・更新削除禁止を検証。

テストは外部通信、トークン、課金、データベース作成を行わない。

    node --test research/test_hole_pair_first_receipt_worker.mjs
    python -m unittest -v research/test_hole_pair_first_receipt_sql.py

## 手動審査後に必要な運用・監査

1. 本番系から分離したCloudflare Worker＋D1を**別途承認の上で**作成し、D1へのバインディングを設定する。Secretsへ RECEIPT_TOKEN を設定し、漏えい・トークン回転・負荷制限も設計する。
2. 未来の候補を既存の固定原本と照合し、結果が確定する前に受領し、D1の実時計、保存行、戻り値を外部監査する。自動配信や本番収集への接続は別レビュー。
3. 並列の同一レース異内容送信、同一原本再送、締切前後、通信中断、D1無料枠超過、Clock skew、悪意ある改ざんを**実Cloudflare上**でテスト。CIのSQLite/MockだけではCloudflare上の動作を実証しない。
4. D1の運用管理権限から独立した監査人または外部署名付き受領時刻の証跡を用意し、「最初の受領時刻」の独立性と耐改ざん性を確認する。
5. 公式beforeinfo/展示6艇・オッズ120通りの正確な取得時刻と初回Git保存を同一レースで確認して初めて、既存の300件pilot＋300件confirmationの**正式な適格判定**を検討する。研究済み11/6–8は混ぜない。

### Cloudflare無料枠（2026年11月時点）

D1はWorkers無料プランに対応する。無料枠は10 DB、アカウント全体5 GB・DB毎500 MB、日次5,000,000行読込と100,000行書込（超過時はクエリエラー）。**推奨は実装の検証であり、無料枠のまま運用できる保証ではない**。

公式情報：
- https://developers.cloudflare.com/d1/platform/pricing/
- https://developers.cloudflare.com/d1/platform/limits/
- https://developers.cloudflare.com/d1/reference/faq/
- https://developers.cloudflare.com/workers/configuration/secrets/

**リリース判断：保留。Draft・main自動統合禁止。**
