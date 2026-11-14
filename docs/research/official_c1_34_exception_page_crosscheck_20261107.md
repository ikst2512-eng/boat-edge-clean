# 4場の1コース例外34件：公式結果ページの事故表示突合（2026-11-07）

**研究Draft #1692専用 / 競走後の公式表示を使用 / T−12・予想モデル・本番補正へ投入不可。**

## 検査範囲・証拠の区別

BoatraceCSVの2026-08-01〜10-31の92日、13,970有効レースから実際に抽出・Git SHA凍結した、実1コース艇がFであるか、F表示なしで着順1〜6に存在しない4場34レース。GitHub Actions https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42357445746 で日別92/92 Git blob SHA一致・候補34件抽出済み。候補JSONのSHA-256は b834b6db01b75062918309d27c97d065702359b2fae0a88d57e8705b3323cc32。

これら34件について、BOAT RACE公式の**個別レース結果ウェブページ**に掲載された**実1コース艇の事故・着順記号**を確認した。34件のうち、二次CSVで1コースFとされた16件は公式ページでもＦ表示、Fではなく1〜6着未記録だった18件は公式ページに別の事故記号が表示された。観測対象の状況に矛盾は見つからなかった。**公式日別K原票と当該34レースの行単位照合はまだ0件。** 公式場別3か月統計の分母にどれを含めるかも未確定。

| 公式結果の1コース艇表示 | 件数 |
|---|---:|
| Ｆ（フライング） | 16 |
| 転（転覆） | 11 |
| エ（エンスト） | 4 |
| 沈（沈没） | 1 |
| 妨（妨害失格） | 1 |
| 落（落水） | 1 |
| **合計** | **34** |

**これは公式結果の事故分類であり、公式場別コース統計から除外する34レースを証明したものではない。** エンスト・転覆・沈没・妨害失格・落水も「着順欄空欄だから分母から除外」とは扱えない。

## 全34レースの一次表示参照

| 場コード | レースコード | 実1コース艇の公式表示 | 公式レース結果 |
|---|---|---|---|
| 17 | 202608041701 | Ｆ | [公式結果ページ](https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20260804&jcd=17&rno=1) |
| 17 | 202609041708 | Ｆ | [公式結果ページ](https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20260904&jcd=17&rno=8) |
| 17 | 202608181704 | 妨 | [公式結果ページ](https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20260818&jcd=17&rno=4) |
| 17 | 202608261704 | 転 | [公式結果ページ](https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20260826&jcd=17&rno=4) |
| 23 | 202610012307 | Ｆ | [公式結果ページ](https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20261001&jcd=23&rno=7) |
| 23 | 202610102308 | Ｆ | [公式結果ページ](https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20261010&jcd=23&rno=8) |
| 23 | 202608212302 | 転 | [公式結果ページ](https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20260821&jcd=23&rno=2) |
| 23 | 202608232312 | 転 | [公式結果ページ](https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20260823&jcd=23&rno=12) |
| 23 | 202608302307 | 転 | [公式結果ページ](https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20260830&jcd=23&rno=7) |
| 23 | 202610022308 | 転 | [公式結果ページ](https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20261002&jcd=23&rno=8) |
| 23 | 202610182311 | 転 | [公式結果ページ](https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20261018&jcd=23&rno=11) |
| 23 | 202610312309 | 転 | [公式結果ページ](https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20261031&jcd=23&rno=9) |
| 23 | 202609172311 | 落 | [公式結果ページ](https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20260917&jcd=23&rno=11) |
| 03 | 202608120306 | Ｆ | [公式結果ページ](https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20260812&jcd=03&rno=6) |
| 03 | 202608260307 | Ｆ | [公式結果ページ](https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20260826&jcd=03&rno=7) |
| 03 | 202609050305 | Ｆ | [公式結果ページ](https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20260905&jcd=03&rno=5) |
| 03 | 202609050308 | Ｆ | [公式結果ページ](https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20260905&jcd=03&rno=8) |
| 03 | 202609230310 | Ｆ | [公式結果ページ](https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20260923&jcd=03&rno=10) |
| 03 | 202610290303 | Ｆ | [公式結果ページ](https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20261029&jcd=03&rno=3) |
| 03 | 202609060306 | エ | [公式結果ページ](https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20260906&jcd=03&rno=6) |
| 03 | 202609230308 | エ | [公式結果ページ](https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20260923&jcd=03&rno=8) |
| 03 | 202609230307 | 転 | [公式結果ページ](https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20260923&jcd=03&rno=7) |
| 03 | 202610270312 | 転 | [公式結果ページ](https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20261027&jcd=03&rno=12) |
| 03 | 202610120310 | 沈 | [公式結果ページ](https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20261012&jcd=03&rno=10) |
| 06 | 202608110610 | Ｆ | [公式結果ページ](https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20260811&jcd=06&rno=10) |
| 06 | 202609110604 | Ｆ | [公式結果ページ](https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20260911&jcd=06&rno=4) |
| 06 | 202610020601 | Ｆ | [公式結果ページ](https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20261002&jcd=06&rno=1) |
| 06 | 202610040610 | Ｆ | [公式結果ページ](https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20261004&jcd=06&rno=10) |
| 06 | 202610230607 | Ｆ | [公式結果ページ](https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20261023&jcd=06&rno=7) |
| 06 | 202610310602 | Ｆ | [公式結果ページ](https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20261031&jcd=06&rno=2) |
| 06 | 202608220610 | エ | [公式結果ページ](https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20260822&jcd=06&rno=10) |
| 06 | 202608250609 | エ | [公式結果ページ](https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20260825&jcd=06&rno=9) |
| 06 | 202608020609 | 転 | [公式結果ページ](https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20260802&jcd=06&rno=9) |
| 06 | 202609300610 | 転 | [公式結果ページ](https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20260930&jcd=06&rno=10) |

## 8月1日の公式Kファイル取得について（別作業）

GitHub Actions https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42357619036 で、公式競走成績LZH 2026-08-01のHTTP実ファイル37KB弱を取得し、原本SHA-256 8e95b7ddce0fe7849179c1a6cf69e4ad938fada13da527410d29f610709ff8ba を記録。研究環境で実バイト照合と内部K260801.TXTの展開に成功し、同日13場・156レース、6艇×156レースの成績行を抽出した。ただし、この1日は**34例外候補と対応する日付の一覧ではなく**、LZH取得・パーサー検証の試行日である。

公式Kが1日取得できた事実を92日すべての独立照合済みと扱わない。2026-08-01のK原票と同日の二次CSV156件を比較する別研究コードをDraft内で検証中であり、この時点で公式3か月分母差の原因は未確定。

## 次の厳格な評価基準

1. 公式Kを対象日ごとに受信しSHA-256を記録、内部の成績行・進入・着順・F/L/S/K・気象をレース単位で検証。公式の集計母数の定義は一次ソースで別に確認。
2. 公式表示の34例外と二次CSV34例外の各レースコードを逐一突合する。結果ページ表示の分類だけをもって公式統計の除外ルールを宣言しない。
3. 公式結果後の値と、T−12以前の独立したbeforeinfo受信・観測時刻を混同しない。
4. 風向軸は一次資料で検証し、将来別期間で4モードとの前向き比較ができるまでは風補正採用なし。

**改変範囲**: この研究用Markdownのみ。Draft、未統合維持。main、Render、本番予想4モード、T−12認定、予想原本、cron、UI、AI自動統合は変更しない。
