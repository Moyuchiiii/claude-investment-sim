---
name: learn
description: 過去データとニュース文脈を組み合わせた深い学習を行い、因果関係のある教訓を蓄積する
user_invocable: true
---

# 深い文脈学習（Deep Context Learning）

過去のマーケットデータ＋実際のニュース・イベントを組み合わせて、
**「なぜその株は上がった/下がったのか」** の因果関係を学習する。

単純なテクニカル指標パターンマッチング（浅い学習）ではなく、
実世界のイベントと株価の関係を理解し、次の判断に活かす。

## 引数

- 月を指定（例: `2025-04`）: その月のデータで学習
- 引数なし: 利用可能な最古の未学習月から自動で開始

## 前提

事前に以下を実行してスナップショットを生成しておくこと:

```bash
cd D:\Claude\invest\claude-investment-sim
python scripts/prepare_snapshots.py --year 2025 --month 1 --range 12 --outcomes --skip-existing
```

## 学習フロー

### Phase 1: 市場環境の把握

**目的**: その月の日本市場全体の動きと背景を理解する

1. Web検索で月次マーケットレビューを取得する:
   - 検索クエリ: `"2025年4月 日本株 月次レビュー"` or `"2025年4月 株式市場 まとめ"`
   - 三井住友DSアセットマネジメントの月次レビュー: `https://www.smd-am.co.jp/market/lastweek/monthly/2025/month202504gl/`（URLパターン: `month{YYYYMM}gl`）
   - 日経平均・TOPIXの動き、為替、米国市場の影響、政策金利の変更等を把握

2. 把握すべき項目:
   - 日経平均/TOPIXの月間騰落率
   - ドル円の水準と方向感
   - 米国市場（S&P500/NASDAQ）の動き
   - 金融政策（日銀・FRB）の変更の有無
   - 地政学リスクや大きなイベント（選挙、災害等）
   - セクター別の強弱

3. 月次市場サマリーを短く整理する（内部メモとして保持）

### Phase 2: スナップショットデータの読み込み

指定月のスナップショットを読む:

```bash
cat D:\Claude\invest\claude-investment-sim\learning\snapshots\{YYYY-MM}.json
```

27銘柄 × 4-5週 = 約100-130件のデータポイント。全部は読まなくていい。
以下の基準で**注目銘柄を5-8個**ピックアップする:

- テクニカルシグナルが出ている（RSI極端値、MACDクロス、BBタッチ等）
- 出来高異常がある（ratio >= 2.0）
- ファンダメンタルズに特徴がある（PER < 12 or PER > 40、ROE > 20%等）
- 月間騰落率が大きい（±5%以上）

### Phase 3: 銘柄別ニュースの調査

ピックアップした各銘柄について、Web検索で当月のニュースを調べる:

検索クエリ例:
- `"2025年4月 ソニー 決算"` or `"2025年4月 ソニーグループ ニュース"`
- `"2025年4月 三菱UFJ 業績"` or `"2025年4月 三菱UFJ 株価 要因"`
- `"2025年 トヨタ 新車 発表"` or `"2025年4月 トヨタ自動車"`

調べるべきこと:
- 決算発表の有無と内容（サプライズの有無）
- 新製品・新サービスの発表
- 経営方針の変更（M&A、事業撤退、増配・自社株買い等）
- 業界全体のトレンド（半導体不足、EV需要、金利影響等）
- 不祥事・訴訟・規制強化
- アナリストの目標株価変更

IMPORTANT: 1銘柄あたり1-2回のWeb検索に留める。完璧を求めず、主要なイベントを拾えればOK。

### Phase 4: 判断（その時点の情報のみ）

各注目銘柄について、**Phase 1-3で得た情報だけ**を使って判断する。

IMPORTANT: 未来の情報（翌月以降の値動き）を判断に使わないこと。

各銘柄の判断:
- **BUY / SELL / HOLD** を決定
- 判断理由を具体的に記述（テクニカル + ファンダ + ニュース文脈）
- 例: 「ソニーG: BUY — RSI 28で売られすぎ、ただしPS5の販売台数好調のニュースあり。決算前の押し目と判断。1ヶ月目標+5%」

### Phase 5: 答え合わせ

アウトカムファイルを読む:

```bash
cat D:\Claude\invest\claude-investment-sim\learning\snapshots\{YYYY-MM}_outcomes.json
```

各判断について検証:
- 1週間後、2週間後、1ヶ月後のリターンを確認
- BUY判断 → 実際に上がったか？なぜ？
- SELL/HOLD判断 → 見逃した上昇はなかったか？
- 予想外の動き → 何が原因だったか？（追加のWeb検索で確認してもOK）

### Phase 6: 深い教訓の記録

答え合わせ結果から、**因果関係のある教訓**を記録する。

#### 良い教訓の例（深い）:
- 「ソニーG: 決算前にRSI 28まで売られた後、好決算（PS5販売台数+15%YoY）で急反発。決算前の過度な悲観は買い場になりやすい。ただし好決算が条件」
- 「三菱UFJ: 日銀利上げ観測でメガバンク全体が買われた。金融政策転換時はセクター全体で動くため、個別のテクニカルより金融政策の方向感が重要」
- 「トヨタ: EV販売の好調ニュースがあったがテクニカルは買われすぎ（RSI 75）。好材料でも高値圏では利確売りに押される。RSI 70超での新規買いは危険」

#### 悪い教訓の例（浅い — これは禁止）:
- 「RSI 28で買いシグナル → 1ヶ月後+5.2%。WIN」
- 「MACD GC発生 → トレンド継続」
- 「出来高3倍で急騰後の反落」

教訓の記録コマンド:

```bash
cd D:\Claude\invest\claude-investment-sim && python scripts/record_lesson.py \
  --outcome <WIN|LOSS|HOLD> \
  --lesson "<因果関係を含む具体的な教訓>" \
  --tags "sector:<セクター>,indicator:<指標>,catalyst:<触媒>,pattern:<パターン>" \
  --symbol "<銘柄コード>" \
  --market-context "<市場環境タグ>"
```

#### タグの付け方（拡張版）

- `--tags`: カンマ区切り。キー:値の形式
  - `sector:金融` `sector:自動車` `sector:電機・精密` `sector:医薬品`
  - `indicator:RSI` `indicator:MACD` `indicator:BB` `indicator:ADX`
  - `catalyst:決算` `catalyst:新製品` `catalyst:M&A` `catalyst:金融政策` `catalyst:為替` `catalyst:地政学`
  - `pattern:reversal` `pattern:breakout` `pattern:momentum` `pattern:mean_reversion`
  - `timeframe:1w` `timeframe:1m`
  - `confidence:high` `confidence:medium` `confidence:low`
- `--symbol`: 対象銘柄（例: `6758.T`）
- `--market-context`: その時の市場環境タグ（カンマ区切り）
  - `nikkei_up` / `nikkei_down` / `nikkei_flat`
  - `yen_weak` / `yen_strong`
  - `boj_hawkish` / `boj_dovish` / `fed_hawkish` / `fed_dovish`
  - `high_volatility` / `low_volatility`
  - `earnings_season` / `year_end` / `new_year`

### Phase 7: 月次サマリーをユーザーに報告

その月の学習で得た主要な教訓を報告する:

1. **市場環境サマリー**: その月はどんな相場だったか（1-2行）
2. **勝ちパターン**: どういう文脈で買うと成功したか（因果関係含む）
3. **負けパターン**: どういう文脈で失敗したか（因果関係含む）
4. **重要な発見**: セクター傾向、マクロ要因の影響など
5. **次月に活かすポイント**: 具体的なアクション指針

最後に「次は /learn YYYY-MM で翌月の学習に進めます」と案内する。

## バッチ学習について

複数月を連続で学習したい場合は、月ごとに `/learn YYYY-MM` を繰り返す。
前月の教訓が次月の判断に反映されるウォークフォワード形式で進める。

IMPORTANT: 旧式の `scripts/batch_learn.py`（ルールベース浅い学習）は使わない。
深い学習は1ヶ月ずつ、Web検索を交えて行うこと。

## 効率化のコツ

- 1ヶ月の学習に必要なWeb検索: 市場全体1-2回 + 銘柄別5-8回 = 合計7-10回
- 全銘柄を見る必要はない。シグナルが出ている銘柄に集中する
- 同じセクターの銘柄は同じマクロ要因で動くことが多い。まとめて調べる
- 既存の教訓と矛盾する結果が出たら、条件の違い（市場環境、セクター等）を考察する
