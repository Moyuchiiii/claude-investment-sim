---
name: learn
description: 過去データでウォークフォワード学習を行い、取引教訓を蓄積する
user_invocable: true
---

# ウォークフォワード学習

過去のマーケットデータを使って「判断→答え合わせ→教訓記録」を繰り返す。
月単位で学習を進め、前月の教訓を次月の判断に反映させる。

## 引数

- 月を指定（例: `2025-04`）: その月のスナップショットで判断し、翌月の結果で答え合わせ
- 引数なし: 利用可能な最古の未学習月から自動で開始

## 前提

事前に以下を実行してスナップショットを生成しておくこと:

```bash
cd D:\Claude\invest\claude-investment-sim
python scripts/prepare_snapshots.py --year 2025 --month 4 --range 12 --outcomes
```

## 手順

### Step 1: 既存の教訓を確認

```bash
cd D:\Claude\invest\claude-investment-sim && python scripts/get_status.py
```

出力のうち `lessons` フィールドを確認し、過去の教訓を把握する。

### Step 2: スナップショットを読み込む

指定月のスナップショットファイルを読む:

```bash
cat D:\Claude\invest\claude-investment-sim\learning\snapshots\{YYYY-MM}.json
```

### Step 3: 各銘柄について判断する

スナップショットに含まれる各銘柄・各週のデータを見て、**その時点で自分が知りうる情報だけ**をもとに判断する。

各銘柄について:
- テクニカル指標とシグナルを確認
- 出来高異常がないかチェック
- 過去の教訓（Step 1で確認済み）を考慮
- **BUY / SELL / HOLD** を判断
- 判断理由を明記

IMPORTANT: 未来の情報（翌月以降の値動き）を判断に使わないこと。その時点のデータだけで判断する。

### Step 4: 答え合わせ

答え合わせファイルを読む:

```bash
cat D:\Claude\invest\claude-investment-sim\learning\snapshots\{YYYY-MM}_outcomes.json
```

各判断について:
- 1週間後、2週間後、1ヶ月後のリターンを確認
- BUYと判断した銘柄が実際に上がったか？
- HOLDと判断した銘柄を見逃していないか？
- 損切りラインに引っかかるような下落はなかったか？

### Step 5: 教訓を記録

答え合わせの結果から得た教訓を記録する。

教訓は具体的に書く。良い例:
- 「RSI 25 + MACDゴールデンクロスの組み合わせは1ヶ月後リターンが+5%以上のケースが多い」
- 「出来高が3倍以上急増した日のBUYは、2週間後に下落していることが多い（利確売りに巻き込まれる）」
- 「日経平均が下落トレンドの中で個別株を買っても、地合いに引きずられて負けやすい」

悪い例（抽象的すぎる）:
- 「慎重に判断すべき」
- 「テクニカル指標を重視する」

教訓ごとに以下のコマンドで記録:

```bash
cd D:\Claude\invest\claude-investment-sim && python scripts/record_lesson.py --outcome <WIN|LOSS|HOLD> --lesson "<具体的な教訓>"
```

### Step 6: 地合い別の教訓タグ付け

教訓を記録する際、どういう地合い（市場環境）での教訓かを必ず含める:
- 「上昇相場で:」「下落相場で:」「横ばい相場で:」
- 「円安局面で:」「円高局面で:」

例:
```bash
python scripts/record_lesson.py --outcome WIN --lesson "上昇相場で: 電機セクターのRSI 30割れは短期反発しやすい。1週間で+3%の確率が高い"
```

### Step 7: 月次サマリー

その月の学習で得た主要な教訓を3-5個にまとめてユーザーに報告する:
- 勝ちパターン（どういう条件で買うと成功しやすいか）
- 負けパターン（どういう条件で買うと失敗しやすいか）
- セクター別の傾向
- 地合いとの関係
- 次月に活かすべきポイント

最後に「次は /learn YYYY-MM で翌月の学習に進めます」と案内する。
