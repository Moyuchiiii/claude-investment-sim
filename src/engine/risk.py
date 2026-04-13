"""リスク管理"""
import yaml
from pathlib import Path
from src.db.repository import HoldingRepository
from src.data.fetcher import StockFetcher

CONFIG_PATH = Path(__file__).parent.parent.parent / "config.yaml"

def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)

class RiskManager:
    def __init__(self):
        self.config = load_config()
        self.holding_repo = HoldingRepository()
        self.fetcher = StockFetcher()

    def check_buy(self, portfolio, symbol: str, total_cost: float) -> dict:
        """買い注文のリスクチェック"""
        trading_config = self.config["trading"]

        # ポートフォリオ全体の評価額を概算
        holdings = self.holding_repo.get_all()
        total_value = portfolio.cash
        for h in holdings:
            price = self.fetcher.get_current_price(h.symbol)
            if price:
                total_value += h.quantity * price

        # 1銘柄への最大投資割合チェック
        max_position = total_value * trading_config["max_position_pct"]
        existing = self.holding_repo.get_by_symbol(1, symbol)
        existing_value = 0
        if existing:
            price = self.fetcher.get_current_price(symbol)
            if price:
                existing_value = existing.quantity * price

        if existing_value + total_cost > max_position:
            return {
                "allowed": False,
                "reason": f"ポジション上限超過（上限: {max_position:,.0f}円, 現在+注文: {existing_value + total_cost:,.0f}円）"
            }

        return {"allowed": True}

    def check_stop_loss(self, symbol: str, avg_cost: float, current_price: float) -> bool:
        """損切りラインに到達したか"""
        loss_pct = (current_price / avg_cost - 1)
        return loss_pct <= -self.config["trading"]["stop_loss_pct"]

    def check_take_profit(self, symbol: str, avg_cost: float, current_price: float) -> bool:
        """利確ラインに到達したか"""
        gain_pct = (current_price / avg_cost - 1)
        return gain_pct >= self.config["trading"]["take_profit_pct"]

    def get_risk_alerts(self) -> list[dict]:
        """リスクアラートを取得"""
        alerts = []
        holdings = self.holding_repo.get_all()

        for h in holdings:
            price = self.fetcher.get_current_price(h.symbol)
            if not price:
                continue

            if self.check_stop_loss(h.symbol, h.avg_cost, price):
                loss_pct = (price / h.avg_cost - 1) * 100
                alerts.append({
                    "type": "STOP_LOSS",
                    "symbol": h.symbol,
                    "message": f"{h.symbol}: 損切りライン到達（{loss_pct:.1f}%）",
                    "current_price": price,
                    "avg_cost": h.avg_cost
                })

            if self.check_take_profit(h.symbol, h.avg_cost, price):
                gain_pct = (price / h.avg_cost - 1) * 100
                alerts.append({
                    "type": "TAKE_PROFIT",
                    "symbol": h.symbol,
                    "message": f"{h.symbol}: 利確ライン到達（+{gain_pct:.1f}%）",
                    "current_price": price,
                    "avg_cost": h.avg_cost
                })

        return alerts
