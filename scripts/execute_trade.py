"""売買を実行"""
import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.engine.executor import TradeExecutor
from src.engine.portfolio import PortfolioManager


def main():
    parser = argparse.ArgumentParser(description="売買実行")
    parser.add_argument("action", choices=["BUY", "SELL"])
    parser.add_argument("symbol", help="銘柄コード (例: 7203.T)")
    parser.add_argument("quantity", type=int, help="数量")
    parser.add_argument("--reasoning", default="", help="判断理由")
    parser.add_argument("--confidence", type=float, default=0.7, help="確信度")
    args = parser.parse_args()

    executor = TradeExecutor()

    if args.action == "BUY":
        result = executor.execute_buy(args.symbol, args.quantity, args.reasoning, args.confidence)
    else:
        result = executor.execute_sell(args.symbol, args.quantity, args.reasoning, args.confidence)

    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))

    # 取引成功時に日次パフォーマンスを記録
    if result.get("success"):
        portfolio_mgr = PortfolioManager()
        portfolio_mgr.record_daily_performance()


if __name__ == "__main__":
    main()
