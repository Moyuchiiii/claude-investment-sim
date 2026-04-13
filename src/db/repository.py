import sqlite3
from datetime import datetime, date
from typing import Optional
from .migrations import get_connection
from .models import Portfolio, Holding, Trade, Performance, LearningLog


class PortfolioRepository:
    def get(self, portfolio_id: int = 1) -> Optional[Portfolio]:
        conn = get_connection()
        row = conn.execute("SELECT * FROM portfolio WHERE id = ?", (portfolio_id,)).fetchone()
        conn.close()
        if not row:
            return None
        return Portfolio(**dict(row))

    def create(self, cash: float) -> Portfolio:
        conn = get_connection()
        now = datetime.now().isoformat()
        cursor = conn.execute(
            "INSERT INTO portfolio (cash, created_at, updated_at) VALUES (?, ?, ?)",
            (cash, now, now)
        )
        portfolio_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return Portfolio(id=portfolio_id, cash=cash, created_at=now, updated_at=now)

    def update_cash(self, portfolio_id: int, cash: float):
        conn = get_connection()
        conn.execute(
            "UPDATE portfolio SET cash = ?, updated_at = ? WHERE id = ?",
            (cash, datetime.now().isoformat(), portfolio_id)
        )
        conn.commit()
        conn.close()


class HoldingRepository:
    def get_all(self, portfolio_id: int = 1) -> list[Holding]:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM holdings WHERE portfolio_id = ?", (portfolio_id,)
        ).fetchall()
        conn.close()
        return [Holding(**dict(r)) for r in rows]

    def get_by_symbol(self, portfolio_id: int, symbol: str) -> Optional[Holding]:
        conn = get_connection()
        row = conn.execute(
            "SELECT * FROM holdings WHERE portfolio_id = ? AND symbol = ?",
            (portfolio_id, symbol)
        ).fetchone()
        conn.close()
        if not row:
            return None
        return Holding(**dict(row))

    def upsert(self, portfolio_id: int, symbol: str, quantity: int, avg_cost: float):
        conn = get_connection()
        existing = conn.execute(
            "SELECT id FROM holdings WHERE portfolio_id = ? AND symbol = ?",
            (portfolio_id, symbol)
        ).fetchone()
        if existing:
            if quantity <= 0:
                conn.execute("DELETE FROM holdings WHERE id = ?", (existing["id"],))
            else:
                conn.execute(
                    "UPDATE holdings SET quantity = ?, avg_cost = ? WHERE id = ?",
                    (quantity, avg_cost, existing["id"])
                )
        else:
            if quantity > 0:
                conn.execute(
                    "INSERT INTO holdings (portfolio_id, symbol, quantity, avg_cost) VALUES (?, ?, ?, ?)",
                    (portfolio_id, symbol, quantity, avg_cost)
                )
        conn.commit()
        conn.close()


class TradeRepository:
    def create(self, symbol: str, action: str, quantity: int, price: float,
               reasoning: str = None, confidence: float = None) -> Trade:
        conn = get_connection()
        total_amount = quantity * price
        now = datetime.now().isoformat()
        cursor = conn.execute(
            """INSERT INTO trades (symbol, action, quantity, price, total_amount, reasoning, confidence, executed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (symbol, action, quantity, price, total_amount, reasoning, confidence, now)
        )
        trade_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return Trade(
            id=trade_id, symbol=symbol, action=action, quantity=quantity,
            price=price, total_amount=total_amount, reasoning=reasoning,
            confidence=confidence, executed_at=now
        )

    def get_recent(self, limit: int = 50) -> list[Trade]:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM trades ORDER BY executed_at DESC LIMIT ?", (limit,)
        ).fetchall()
        conn.close()
        return [Trade(**dict(r)) for r in rows]

    def get_by_symbol(self, symbol: str) -> list[Trade]:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM trades WHERE symbol = ? ORDER BY executed_at DESC", (symbol,)
        ).fetchall()
        conn.close()
        return [Trade(**dict(r)) for r in rows]


class PerformanceRepository:
    def record(self, total_value: float, cash: float,
               unrealized_pnl: float = None, realized_pnl: float = None,
               daily_return: float = None):
        conn = get_connection()
        today = date.today().isoformat()
        conn.execute(
            """INSERT OR REPLACE INTO performance (date, total_value, cash, unrealized_pnl, realized_pnl, daily_return)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (today, total_value, cash, unrealized_pnl, realized_pnl, daily_return)
        )
        conn.commit()
        conn.close()

    def get_history(self, days: int = 30) -> list[Performance]:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM performance ORDER BY date DESC LIMIT ?", (days,)
        ).fetchall()
        conn.close()
        return [Performance(**dict(r)) for r in rows]


class LearningLogRepository:
    def create(self, trade_id: int, outcome: str, profit_loss: float = None,
               lesson: str = None, strategy_adjustment: str = None) -> LearningLog:
        conn = get_connection()
        now = datetime.now().isoformat()
        cursor = conn.execute(
            """INSERT INTO learning_log (trade_id, outcome, profit_loss, lesson, strategy_adjustment, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (trade_id, outcome, profit_loss, lesson, strategy_adjustment, now)
        )
        log_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return LearningLog(
            id=log_id, trade_id=trade_id, outcome=outcome,
            profit_loss=profit_loss, lesson=lesson,
            strategy_adjustment=strategy_adjustment, created_at=now
        )

    def get_lessons(self, limit: int = 20) -> list[LearningLog]:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM learning_log ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        conn.close()
        return [LearningLog(**dict(r)) for r in rows]
