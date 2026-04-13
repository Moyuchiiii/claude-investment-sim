"""仮想売買実行エンジン"""
from datetime import date
from src.db.repository import (
    PortfolioRepository, HoldingRepository, TradeRepository
)
from src.data.fetcher import StockFetcher
from src.engine.risk import RiskManager

class TradeExecutor:
    def __init__(self):
        self.portfolio_repo = PortfolioRepository()
        self.holding_repo = HoldingRepository()
        self.trade_repo = TradeRepository()
        self.fetcher = StockFetcher()
        self.risk_manager = RiskManager()

    def execute_buy(self, symbol: str, quantity: int,
                    reasoning: str = None, confidence: float = None) -> dict:
        """買い注文を実行"""
        portfolio = self.portfolio_repo.get()
        if not portfolio:
            return {"success": False, "error": "ポートフォリオが初期化されていません"}

        # 現在価格を取得
        price = self.fetcher.get_current_price(symbol)
        if not price:
            return {"success": False, "error": f"{symbol}の価格を取得できません"}

        total_cost = price * quantity

        # 残高チェック
        if total_cost > portfolio.cash:
            return {"success": False, "error": f"残高不足（必要: {total_cost:,.0f}円, 残高: {portfolio.cash:,.0f}円）"}

        # リスクチェック
        risk_check = self.risk_manager.check_buy(portfolio, symbol, total_cost)
        if not risk_check["allowed"]:
            return {"success": False, "error": risk_check["reason"]}

        # 売買を実行
        # 既存保有がある場合は平均取得単価を更新
        existing = self.holding_repo.get_by_symbol(1, symbol)
        if existing:
            new_quantity = existing.quantity + quantity
            new_avg_cost = (existing.avg_cost * existing.quantity + price * quantity) / new_quantity
            self.holding_repo.upsert(1, symbol, new_quantity, new_avg_cost)
        else:
            self.holding_repo.upsert(1, symbol, quantity, price)

        # 現金を減らす
        new_cash = portfolio.cash - total_cost
        self.portfolio_repo.update_cash(1, new_cash)

        # 取引を記録
        trade = self.trade_repo.create(
            symbol=symbol, action="BUY", quantity=quantity,
            price=price, reasoning=reasoning, confidence=confidence
        )

        return {
            "success": True,
            "trade_id": trade.id,
            "symbol": symbol,
            "action": "BUY",
            "quantity": quantity,
            "price": price,
            "total_cost": total_cost,
            "remaining_cash": new_cash
        }

    def execute_sell(self, symbol: str, quantity: int,
                     reasoning: str = None, confidence: float = None) -> dict:
        """売り注文を実行"""
        portfolio = self.portfolio_repo.get()
        if not portfolio:
            return {"success": False, "error": "ポートフォリオが初期化されていません"}

        # 保有チェック
        holding = self.holding_repo.get_by_symbol(1, symbol)
        if not holding or holding.quantity < quantity:
            available = holding.quantity if holding else 0
            return {"success": False, "error": f"{symbol}の保有数が不足（保有: {available}, 売却: {quantity}）"}

        # 現在価格を取得
        price = self.fetcher.get_current_price(symbol)
        if not price:
            return {"success": False, "error": f"{symbol}の価格を取得できません"}

        total_proceeds = price * quantity
        profit_loss = (price - holding.avg_cost) * quantity

        # 保有を更新
        new_quantity = holding.quantity - quantity
        self.holding_repo.upsert(1, symbol, new_quantity, holding.avg_cost)

        # 現金を増やす
        new_cash = portfolio.cash + total_proceeds
        self.portfolio_repo.update_cash(1, new_cash)

        # 取引を記録
        trade = self.trade_repo.create(
            symbol=symbol, action="SELL", quantity=quantity,
            price=price, reasoning=reasoning, confidence=confidence
        )

        return {
            "success": True,
            "trade_id": trade.id,
            "symbol": symbol,
            "action": "SELL",
            "quantity": quantity,
            "price": price,
            "total_proceeds": total_proceeds,
            "profit_loss": profit_loss,
            "remaining_cash": new_cash
        }

    def get_today_trade_count(self) -> int:
        """本日の取引回数を取得"""
        trades = self.trade_repo.get_recent(limit=100)
        today = date.today().isoformat()
        return sum(1 for t in trades if t.executed_at.startswith(today))
