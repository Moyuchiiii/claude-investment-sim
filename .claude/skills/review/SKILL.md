---
name: review
description: ポートフォリオの状況を確認し、戦略の振り返り・改善提案を行う
user_invocable: true
---

# ポートフォリオレビュー

ポートフォリオの現在状況を確認し、過去の取引を振り返って改善提案を行う。

## 手順

### Step 1: 現在状況を取得

```bash
cd D:\Claude\invest\claude-investment-sim && python scripts/get_status.py
```

### Step 2: 分析

以下を評価する:
- 全体のリターン推移
- 各保有銘柄の損益状況
- 集中リスク（1銘柄に偏りすぎていないか）
- リスクアラートの有無
- 直近の取引の勝敗パターン
- 過去の教訓が活かされているか

### Step 3: 保有銘柄の最新テクニカル分析

保有中の銘柄があれば、それぞれの現在のテクニカル状況を確認:

```bash
cd D:\Claude\invest\claude-investment-sim && python scripts/analyze_symbol.py <symbol>
```

### Step 4: レポート

以下をユーザーに報告:
- ポートフォリオサマリー（総資産・現金・含み損益）
- 各銘柄の状況と今後の見通し
- リスク評価
- 戦略の改善提案
- 次回の取引で意識すべきポイント

### Step 5: 教訓記録

新たな気づきがあれば記録:

```bash
cd D:\Claude\invest\claude-investment-sim && python scripts/record_lesson.py --outcome HOLD --lesson "<教訓>"
```
