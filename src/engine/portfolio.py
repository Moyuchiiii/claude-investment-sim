"""仮想ポートフォリオ管理"""
import yaml
from pathlib import Path
from src.db.repository import PortfolioRepository, HoldingRepository, PerformanceRepository
from src.data.fetcher import StockFetcher

CONFIG_PATH = Path(__file__).parent.parent.parent / "config.yaml"

def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)

class PortfolioManager:
    def __init__(self):
        self.portfolio_repo = PortfolioRepository()
        self.holding_repo = HoldingRepository()
        self.performance_repo = PerformanceRepository()
        self.fetcher = StockFetcher()
        self.config = load_config()

    def initialize(self) -> None:
        """ポートフォリオを初期化（初期資金でスタート）"""
        existing = self.portfolio_repo.get()
        if existing:
            return  # 既に存在する場合はスキップ
        initial_cash = self.config["portfolio"]["initial_cash"]
        self.portfolio_repo.create(initial_cash)

    def get_status(self) -> dict:
        """ポートフォリオの現在状態を取得"""
        portfolio = self.portfolio_repo.get()
        if not portfolio:
            return {"error": "ポートフォリオが初期化されていません"}

        holdings = self.holding_repo.get_all()

        # 保有銘柄の現在価格を取得
        symbols = [h.symbol for h in holdings]
        current_prices = self.fetcher.get_multiple_prices(symbols) if symbols else {}

        # 評価額を計算
        holdings_value = 0.0
        holdings_detail = []
        for h in holdings:
            current_price = current_prices.get(h.symbol)
            if current_price:
                market_value = h.quantity * current_price
                unrealized_pnl = market_value - (h.quantity * h.avg_cost)
                holdings_detail.append({
                    "symbol": h.symbol,
                    "quantity": h.quantity,
                    "avg_cost": h.avg_cost,
                    "current_price": current_price,
                    "market_value": market_value,
                    "unrealized_pnl": unrealized_pnl,
                    "return_pct": (current_price / h.avg_cost - 1) * 100
                })
                holdings_value += market_value

        total_value = portfolio.cash + holdings_value
        initial_cash = self.config["portfolio"]["initial_cash"]
        total_return = (total_value / initial_cash - 1) * 100

        return {
            "cash": portfolio.cash,
            "holdings_value": holdings_value,
            "total_value": total_value,
            "total_return_pct": total_return,
            "holdings": holdings_detail,
            "holdings_count": len(holdings)
        }

    def record_daily_performance(self) -> None:
        """日次パフォーマンスを記録"""
        status = self.get_status()
        if "error" in status:
            return

        # 前日のパフォーマンスを取得して日次リターンを計算
        history = self.performance_repo.get_history(days=2)
        daily_return = None
        if history:
            prev_value = history[0].total_value
            daily_return = (status["total_value"] / prev_value - 1) * 100

        unrealized_pnl = sum(h["unrealized_pnl"] for h in status["holdings"])

        self.performance_repo.record(
            total_value=status["total_value"],
            cash=status["cash"],
            unrealized_pnl=unrealized_pnl,
            daily_return=daily_return
        )
