---
name: learn
description: 過去データで判断→答え合わせ→教訓を繰り返し、正解率の向上を追跡する
user_invocable: true
---

# ウォークフォワード学習（正解率追跡型）

全27銘柄に対してBUY/SELL/HOLDの判断を下し、1ヶ月後の結果で答え合わせ。
月ごとの正解率を記録し、学習による改善を数値で追跡する。

## 正解の定義

| 判断 | 正解条件（1ヶ月後リターン） |
|------|---------------------------|
| BUY  | +3%以上                    |
| SELL | -3%以下                    |
| HOLD | ±3%以内                    |

## 引数

- 月を指定（例: `2025-01`）: その月で学習
- `--progress`: 正解率の推移を表示
- 引数なし: 最も古い未学習月から開始

## 手順

### Step 1: 前月までの教訓を確認

```bash
cd D:\Claude\invest\claude-investment-sim
python scripts/score_judgments.py --progress
python scripts/get_status.py
```

過去の正解率推移と、前月で得た教訓を確認する。
初月（教訓ゼロ）の場合はスキップ。

### Step 2: 市場環境を調査（Web検索）

その月の日本株市場全体の状況をWeb検索で調べる:
- 検索: "YYYY年M月 日本株 月次レビュー"
- 日経平均/TOPIX、為替、金融政策、主要イベントを把握

### Step 3: スナップショットを読み込む

```bash
cat D:\Claude\invest\claude-investment-sim\learning\snapshots\{YYYY-MM}.json
```

全27銘柄のデータを確認する。各銘柄について:
- テクニカル指標（RSI, MACD, BB, ADX等）
- ファンダメンタルズ（PER, PBR, ROE等）
- 出来高異常
- シグナル

### Step 4: 全27銘柄に判断をつける

IMPORTANT: この時点でアウトカムファイルを絶対に見ない。

各銘柄について BUY / SELL / HOLD を決定し、理由を1行で書く。
スナップショットには複数週のデータがあるが、**月初の週（最初のデータポイント）** で判断する。

判断は以下のJSON形式でファイルに書き出す:

ファイルパス: `D:\Claude\invest\claude-investment-sim\learning\judgments\{YYYY-MM}.json`

```json
{
  "month": "YYYY-MM",
  "context": "その月の市場環境メモ（1-2行）",
  "lessons_used": ["前月から持ち越した教訓があれば記載"],
  "judgments": [
    {
      "symbol": "7203.T",
      "symbol_name": "トヨタ自動車",
      "date": "2025-01-10",
      "judgment": "BUY",
      "reason": "RSI 54 + SMA上昇トレンド + PER 11.7の割安感"
    },
    ...全27銘柄分
  ]
}
```

IMPORTANT: 判断をファイルに書き出してから次のステップに進む。書き出し前にアウトカムを見たらカンニング。

### Step 5: スコアリング（答え合わせ）

```bash
cd D:\Claude\invest\claude-investment-sim
python scripts/score_judgments.py {YYYY-MM}
```

スクリプトが自動で:
- 各判断の正誤を判定（BUY→+3%以上で正解、等）
- 正解率を計算
- BUY判断の平均リターン（期待値）を計算
- 不正解リストを表示
- 結果を `learning/scores/{YYYY-MM}.json` に保存

### Step 6: 不正解の分析

スコアリング結果の不正解リストを見て、**なぜ間違えたか**を分析する。

ここで必要ならWeb検索で銘柄ニュースを調べてもOK。
ただし教訓は**次月の判断に使える一般化されたルール**にする。

良い教訓: 「利上げ局面では銀行株のRSI過熱は無視してBUY継続」
悪い教訓: 「三菱UFJは1月に上がった」（一般化されてない）

教訓を記録:
```bash
python scripts/record_lesson.py \
  --outcome <WIN|LOSS|HOLD> \
  --lesson "<一般化された教訓>" \
  --tags "sector:XX,indicator:XX,catalyst:XX" \
  --symbol "XXXX.T" \
  --market-context "XX,XX"
```

教訓は3-5個に絞る。多すぎると次月の判断で混乱する。

### Step 7: 正解率の推移を確認

```bash
python scripts/score_judgments.py --progress
```

月ごとの正解率が上がっているか確認する。

### Step 8: ユーザーに報告

以下を報告:
1. 今月の正解率（例: 18/27 = 66.7%）
2. BUY/SELL/HOLD別の正解率
3. BUY判断の平均リターン（期待値）
4. 主な不正解とその原因
5. 次月に活かす教訓（3-5個）
6. 正解率の推移グラフ（テキスト）

「次は /learn YYYY-MM で翌月に進めます」と案内。

## 重要ルール

- **必ず順番にやる**: 1月→2月→3月...の順。並列禁止
- **判断ファイル書き出し後にアウトカムを見る**: カンニング防止
- **全27銘柄に判断**: 得意な銘柄だけ選ばない
- **前月の教訓を参照してから判断**: ウォークフォワードの肝
- **正解率と期待値の両方を追う**: 正解率が高くても期待値がマイナスなら意味がない
