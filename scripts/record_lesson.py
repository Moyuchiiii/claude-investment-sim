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
    parser.add_argument("--tags", default=None,
                        help="カンマ区切りタグ（例: 'sector:金融,indicator:RSI,market:bearish'）")
    parser.add_argument("--symbol", default=None,
                        help="関連銘柄コード（例: '8306.T'）")
    parser.add_argument("--market-context", default=None,
                        help="市場環境（例: 'nikkei_down,yen_weak'）")
    args = parser.parse_args()

    repo = LearningLogRepository()
    log = repo.create(
        trade_id=args.trade_id,
        outcome=args.outcome,
        profit_loss=args.profit_loss,
        lesson=args.lesson,
        strategy_adjustment=args.adjustment,
        tags=args.tags,
        symbol=args.symbol,
        market_context=args.market_context,
    )

    print(json.dumps({
        "success": True,
        "id": log.id,
        "lesson": args.lesson,
        "tags": log.tags,
        "symbol": log.symbol,
        "market_context": log.market_context,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
