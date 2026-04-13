"""仮想売買実行エンジン"""
from datetime import date, datetime
from pathlib import Path
import yaml
from src.db.repository import (
    PortfolioRepository, HoldingRepository, TradeRepository, TaxRepository
)
from src.data.fetcher import StockFetcher
from src.engine.risk import RiskManager

CONFIG_PATH = Path(__file__).parent.parent.parent / "config.yaml"


def _load_costs_config() -> dict:
    """config.yaml から costs セクションを読み込む"""
    with open(CONFIG_PATH, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config.get("costs", {
        "commission_rate": 0.0,
        "commission_min": 0,
        "slippage_rate": 0.0005,
        "tax_rate": 0.20315,
        "enable_tax": True,
        "enable_slippage": True,
    })


class TradeExecutor:
    def __init__(self):
        self.portfolio_repo = PortfolioRepository()
        self.holding_repo = HoldingRepository()
        self.trade_repo = TradeRepository()
        self.tax_repo = TaxRepository()
        self.fetcher = StockFetcher()
        self.risk_manager = RiskManager()

    def execute_buy(self, symbol: str, quantity: int,
                    reasoning: str = None, confidence: float = None) -> dict:
        """買い注文を実行（スリッページ・手数料を適用）"""
        portfolio = self.portfolio_repo.get()
        if not portfolio:
            return {"success": False, "error": "ポートフォリオが初期化されていません"}

        # 現在価格を取得
        market_price = self.fetcher.get_current_price(symbol)
        if not market_price:
            return {"success": False, "error": f"{symbol}の価格を取得できません"}

        costs = _load_costs_config()

        # スリッページ適用（買いは高くなる）
        slippage_rate = costs["slippage_rate"] if costs["enable_slippage"] else 0.0
        execution_price = market_price * (1 + slippage_rate)
        slippage_amount = (execution_price - market_price) * quantity

        # 手数料計算
        subtotal = execution_price * quantity
        commission = max(subtotal * costs["commission_rate"], costs["commission_min"])

        # 総コスト
        total_cost = subtotal + commission

        # 残高チェック
        if total_cost > portfolio.cash:
            return {"success": False, "error": f"残高不足（必要: {total_cost:,.0f}円, 残高: {portfolio.cash:,.0f}円）"}

        # リスクチェック
        risk_check = self.risk_manager.check_buy(portfolio, symbol, total_cost)
        if not risk_check["allowed"]:
            return {"success": False, "error": risk_check["reason"]}

        # 売買を実行
        # 既存保有がある場合は平均取得単価を更新（実行価格ベースで計算）
        existing = self.holding_repo.get_by_symbol(1, symbol)
        if existing:
            new_quantity = existing.quantity + quantity
            new_avg_cost = (existing.avg_cost * existing.quantity + execution_price * quantity) / new_quantity
            self.holding_repo.upsert(1, symbol, new_quantity, new_avg_cost)
        else:
            self.holding_repo.upsert(1, symbol, quantity, execution_price)

        # 現金を減らす
        new_cash = portfolio.cash - total_cost
        self.portfolio_repo.update_cash(1, new_cash)

        # 取引を記録（実行価格・コストをDBに保存）
        trade = self.trade_repo.create(
            symbol=symbol, action="BUY", quantity=quantity,
            price=execution_price, reasoning=reasoning, confidence=confidence,
            commission=commission, slippage=slippage_amount, tax=0.0
        )

        print(f"[BUY] {symbol} x{quantity} | 市場価格: ¥{market_price:,.0f} -> 実行価格: ¥{execution_price:,.2f} | "
              f"スリッページ: ¥{slippage_amount:,.0f} | 手数料: ¥{commission:,.0f} | 合計: ¥{total_cost:,.0f}")

        return {
            "success": True,
            "trade_id": trade.id,
            "symbol": symbol,
            "action": "BUY",
            "market_price": market_price,
            "execution_price": round(execution_price, 2),
            "slippage": round(slippage_amount, 2),
            "quantity": quantity,
            "subtotal": round(subtotal, 0),
            "commission": round(commission, 0),
            "tax": 0,
            "total_cost": round(total_cost, 0),
            "remaining_cash": round(new_cash, 0),
        }

    def execute_sell(self, symbol: str, quantity: int,
                     reasoning: str = None, confidence: float = None) -> dict:
        """売り注文を実行（スリッページ・手数料・譲渡益税を適用）"""
        portfolio = self.portfolio_repo.get()
        if not portfolio:
            return {"success": False, "error": "ポートフォリオが初期化されていません"}

        # 保有チェック
        holding = self.holding_repo.get_by_symbol(1, symbol)
        if not holding or holding.quantity < quantity:
            available = holding.quantity if holding else 0
            return {"success": False, "error": f"{symbol}の保有数が不足（保有: {available}, 売却: {quantity}）"}

        # 現在価格を取得
        market_price = self.fetcher.get_current_price(symbol)
        if not market_price:
            return {"success": False, "error": f"{symbol}の価格を取得できません"}

        costs = _load_costs_config()

        # スリッページ適用（売りは安くなる）
        slippage_rate = costs["slippage_rate"] if costs["enable_slippage"] else 0.0
        execution_price = market_price * (1 - slippage_rate)
        slippage_amount = (market_price - execution_price) * quantity

        # 手数料計算
        gross_proceeds = execution_price * quantity
        commission = max(gross_proceeds * costs["commission_rate"], costs["commission_min"])

        # 譲渡益税の計算
        profit_loss = (execution_price - holding.avg_cost) * quantity
        tax = 0.0
        if profit_loss > 0 and costs["enable_tax"]:
            tax = profit_loss * costs["tax_rate"]

        # 純受取額
        net_proceeds = gross_proceeds - commission - tax

        # 保有を更新
        new_quantity = holding.quantity - quantity
        self.holding_repo.upsert(1, symbol, new_quantity, holding.avg_cost)

        # 現金を増やす
        new_cash = portfolio.cash + net_proceeds
        self.portfolio_repo.update_cash(1, new_cash)

        # 取引を記録
        trade = self.trade_repo.create(
            symbol=symbol, action="SELL", quantity=quantity,
            price=execution_price, reasoning=reasoning, confidence=confidence,
            commission=commission, slippage=slippage_amount, tax=tax
        )

        # 税金記録（利益が出た場合）
        if tax > 0:
            fiscal_year = datetime.now().year
            self.tax_repo.create(
                trade_id=trade.id,
                tax_type="capital_gains",
                taxable_amount=profit_loss,
                tax_amount=tax,
                fiscal_year=fiscal_year,
            )

        # 損失の場合も繰越用に記録
        elif profit_loss < 0 and costs["enable_tax"]:
            fiscal_year = datetime.now().year
            self.tax_repo.create(
                trade_id=trade.id,
                tax_type="capital_gains",
                taxable_amount=profit_loss,
                tax_amount=0.0,
                fiscal_year=fiscal_year,
            )

        print(f"[SELL] {symbol} x{quantity} | 市場価格: ¥{market_price:,.0f} -> 実行価格: ¥{execution_price:,.2f} | "
              f"スリッページ: ¥{slippage_amount:,.0f} | 手数料: ¥{commission:,.0f} | 税: ¥{tax:,.0f} | "
              f"純受取: ¥{net_proceeds:,.0f}")

        return {
            "success": True,
            "trade_id": trade.id,
            "symbol": symbol,
            "action": "SELL",
            "market_price": market_price,
            "execution_price": round(execution_price, 2),
            "slippage": round(slippage_amount, 2),
            "quantity": quantity,
            "gross_proceeds": round(gross_proceeds, 0),
            "commission": round(commission, 0),
            "profit_loss": round(profit_loss, 0),
            "tax": round(tax, 0),
            "net_proceeds": round(net_proceeds, 0),
            "remaining_cash": round(new_cash, 0),
        }

    def get_today_trade_count(self) -> int:
        """本日の取引回数を取得"""
        trades = self.trade_repo.get_recent(limit=100)
        today = date.today().isoformat()
        return sum(1 for t in trades if t.executed_at and t.executed_at.startswith(today))
