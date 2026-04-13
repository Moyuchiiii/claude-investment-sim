---
name: portfolio-review
description: 現在のポートフォリオ状態をレビューし、リバランス提案を行う
---

# ポートフォリオレビュー

## トリガー条件
- ユーザーが「ポートフォリオ見せて」「状態は？」と聞いたとき
- 週次レビュー実行時

## ワークフロー

1. **状態取得**: `src/engine/portfolio.py` の PortfolioManager.get_status() を実行
2. **リスク確認**: `src/engine/risk.py` の RiskManager.get_risk_alerts() を実行
3. **学習履歴確認**: `src/ai/learner.py` の get_learning_context() で教訓を取得
4. **分析**: 集中リスク、セクター分散、パフォーマンス推移を評価
5. **提案**: リバランス、損切り、利確の具体的アクションを提示

## 出力形式
- 総資産・現金・保有評価額
- 各銘柄の損益状況
- リスクアラート
- リバランス提案
- 直近の学習からの改善点
