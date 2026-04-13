"""学習ログに教訓を記録"""
import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.repository import LearningLogRepository


def main():
    parser = argparse.ArgumentParser(description="教訓記録")
    parser.add_argument("--trade-id", type=int, default=None)
    parser.add_argument("--outcome", choices=["WIN", "LOSS", "HOLD"], required=True)
    parser.add_argument("--lesson", required=True, help="教訓テキスト")
    parser.add_argument("--profit-loss", type=float, default=None)
    parser.add_argument("--adjustment", default=None, help="戦略調整")
    args = parser.parse_args()

    repo = LearningLogRepository()
    log = repo.create(
        trade_id=args.trade_id,
        outcome=args.outcome,
        profit_loss=args.profit_loss,
        lesson=args.lesson,
        strategy_adjustment=args.adjustment,
    )

    print(json.dumps({"success": True, "id": log.id, "lesson": args.lesson}, ensure_ascii=False))


if __name__ == "__main__":
    main()
