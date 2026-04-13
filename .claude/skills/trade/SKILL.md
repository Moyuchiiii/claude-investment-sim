---
name: trade
description: 銘柄を分析し、売買判断を行い実行する自律トレーディングスキル
user_invocable: true
---

# 自律トレーディング

仮想ポートフォリオ（初期100万円）で日本株の売買を行う。
あなた自身がトレーダーとして、データを分析し、売買を判断・実行する。

## 引数

- 引数なし: 全銘柄を分析して売買判断
- 銘柄コード指定（例: `7203.T`）: その銘柄のみ分析

## 手順

### Step 1: ポートフォリオ状況を確認

```bash
cd D:\Claude\invest\claude-investment-sim && python scripts/get_status.py
```

出力されたJSONから以下を把握する:
- 現金残高、総資産、保有銘柄
- リスクアラート（損切り・利確ライン到達）
- 直近の取引履歴
- 過去の教訓（学習ログ）

### Step 2: リスクアラート対応

損切り（STOP_LOSS）・利確（TAKE_PROFIT）アラートがある場合、即座に実行:

```bash
cd D:\Claude\invest\claude-investment-sim && python scripts/execute_trade.py SELL <symbol> <全数量> --reasoning "損切り/利確: <理由>" --confidence 0.9
```

### Step 3: 銘柄分析

引数で銘柄が指定されていればその銘柄のみ、なければ全銘柄を分析する。
全銘柄: 7203.T, 6758.T, 9984.T, 6861.T, 8306.T, 6501.T, 7974.T, 4063.T, 9432.T, 6902.T

各銘柄について:

```bash
cd D:\Claude\invest\claude-investment-sim && python scripts/analyze_symbol.py <symbol>
```

### Step 4: 売買判断

分析データをもとに、あなた自身の判断で以下を決定する:

- **BUY / SELL / HOLD** のいずれか
- **数量**: 1銘柄への投資は総資産の20%まで
- **確信度**: 0.0〜1.0（0.6未満ならHOLD）
- **理由**: なぜその判断に至ったか

#### 判断基準
- RSI 30以下: 売られすぎ → 買い検討
- RSI 70以上: 買われすぎ → 売り検討
- MACDがシグナル線を上抜け: 買いシグナル
- MACDがシグナル線を下抜け: 売りシグナル
- ボリンジャーバンド下限近く: 反発期待で買い検討
- ボリンジャーバンド上限近く: 反落リスクで売り検討
- ADX 25以上: トレンドが強い
- 複数のシグナルが一致する場合に確信度を上げる
- 過去の教訓を必ず考慮する（同じ失敗を繰り返さない）

#### リスクルール
- 1日の取引上限: 5件
- 損切りライン: -5%
- 利確ライン: +15%
- 確信度 0.6 未満は見送り

### Step 5: 売買実行

BUY または SELL と判断した場合:

```bash
cd D:\Claude\invest\claude-investment-sim && python scripts/execute_trade.py <BUY|SELL> <symbol> <quantity> --reasoning "<理由>" --confidence <確信度>
```

### Step 6: 学習記録

取引を実行した場合、過去の取引結果を振り返り教訓を記録:

```bash
cd D:\Claude\invest\claude-investment-sim && python scripts/record_lesson.py --outcome <WIN|LOSS|HOLD> --lesson "<教訓>" --profit-loss <損益額>
```

### Step 7: レポート

最後にユーザーに以下をレポートする:
- 分析した銘柄と結果
- 実行した取引（あれば）
- ポートフォリオの現在状況
- 注目すべきシグナルや教訓
