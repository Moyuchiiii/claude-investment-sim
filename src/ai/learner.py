"""過去の取引結果から学習し、戦略を改善する"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from src.db.repository import (
    TradeRepository, LearningLogRepository, PerformanceRepository, HoldingRepository
)
from src.data.fetcher import StockFetcher
from src.ai.claude_judge import ClaudeJudge
from src.ai.prompt_builder import PromptBuilder

LEARNING_DIR = Path(__file__).parent.parent.parent / "learning"

class Learner:
    """取引結果を評価し、教訓を蓄積する"""

    def __init__(self):
        self.trade_repo = TradeRepository()
        self.learning_repo = LearningLogRepository()
        self.performance_repo = PerformanceRepository()
        self.holding_repo = HoldingRepository()
        self.fetcher = StockFetcher()
        self.judge = ClaudeJudge()
        self.prompt_builder = PromptBuilder()
        LEARNING_DIR.mkdir(parents=True, exist_ok=True)

    def evaluate_trades(self) -> list[dict]:
        """直近の取引を評価し、learning_logに記録"""
        recent_trades = self.trade_repo.get_recent(limit=50)
        results = []

        for trade in recent_trades:
            # 既にこの取引の評価がある場合はスキップ
            existing_lessons = self.learning_repo.get_lessons(limit=200)
            if any(l.trade_id == trade.id for l in existing_lessons):
                continue

            # 売りの場合: 利益/損失が確定している
            if trade.action == "SELL":
                # 直前のBUYを探して損益を計算（簡略化: trade.priceとreasoning参照）
                outcome = "WIN" if trade.total_amount > 0 else "LOSS"

                # Claudeに教訓を生成させる
                lesson_prompt = f"""以下の取引結果を分析し、教訓を1文で述べてください。

取引: {trade.action} {trade.symbol} x{trade.quantity} @{trade.price:,.0f}円
理由: {trade.reasoning or '不明'}
結果: {outcome}

教訓を1文で簡潔に述べてください（JSON不要、テキストのみ）。"""

                lesson_response = self.judge.judge(lesson_prompt)
                lesson_text = None
                if isinstance(lesson_response, dict):
                    lesson_text = lesson_response.get("lesson", str(lesson_response))
                elif isinstance(lesson_response, str):
                    lesson_text = lesson_response

                log = self.learning_repo.create(
                    trade_id=trade.id,
                    outcome=outcome,
                    profit_loss=0,  # 簡略化
                    lesson=lesson_text,
                    strategy_adjustment=None
                )
                results.append({"trade_id": trade.id, "outcome": outcome, "lesson": lesson_text})

        return results

    def weekly_review(self) -> dict:
        """週次レビューを実行"""
        trades = self.trade_repo.get_recent(limit=50)
        performance = self.performance_repo.get_history(days=7)

        trades_data = [
            {
                "executed_at": t.executed_at,
                "action": t.action,
                "symbol": t.symbol,
                "quantity": t.quantity,
                "price": t.price,
                "reasoning": t.reasoning
            }
            for t in trades
        ]

        perf_data = [
            {
                "date": str(p.date),
                "total_value": p.total_value,
                "daily_return": p.daily_return or 0
            }
            for p in performance
        ]

        review_prompt = self.prompt_builder.build_review_prompt(trades_data, perf_data)
        review_result = self.judge.judge(review_prompt)

        if review_result:
            # 教訓を保存
            lessons = review_result.get("lessons", [])
            adjustments = review_result.get("strategy_adjustments", [])

            for lesson in lessons:
                self.learning_repo.create(
                    trade_id=None,
                    outcome="HOLD",
                    lesson=lesson,
                    strategy_adjustment="; ".join(adjustments) if adjustments else None
                )

            # 戦略進化記録をファイルに追記
            self._record_evolution(review_result)

        return review_result or {"error": "レビュー結果を取得できませんでした"}

    def get_learning_context(self) -> str:
        """学習コンテキスト（教訓一覧）をテキストで返す"""
        lessons = self.learning_repo.get_lessons(limit=20)
        if not lessons:
            return "まだ教訓は蓄積されていません。"

        lines = []
        for l in lessons:
            outcome_icon = "✅" if l.outcome == "WIN" else "❌" if l.outcome == "LOSS" else "⏸"
            lines.append(
                f"{outcome_icon} [{l.outcome}] {l.lesson or '教訓なし'}"
                f"{f' → 調整: {l.strategy_adjustment}' if l.strategy_adjustment else ''}"
            )
        return "\n".join(lines)

    def _record_evolution(self, review: dict) -> None:
        """戦略進化記録をファイルに追記"""
        filepath = LEARNING_DIR / "strategy_evolution.md"

        entry = f"""
## レビュー: {datetime.now().strftime('%Y-%m-%d')}

- 評価: {review.get('overall_grade', '?')}
- 勝率: {review.get('win_rate', '?')}
- リスク評価: {review.get('risk_assessment', '?')}

### 教訓
{chr(10).join(f'- {l}' for l in review.get('lessons', []))}

### 戦略調整
{chr(10).join(f'- {a}' for a in review.get('strategy_adjustments', []))}

---
"""
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(entry)
