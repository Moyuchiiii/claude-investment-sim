from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional


@dataclass
class Portfolio:
    id: int
    cash: float
    created_at: datetime
    updated_at: datetime


@dataclass
class Holding:
    id: int
    portfolio_id: int
    symbol: str
    quantity: int
    avg_cost: float


@dataclass
class Trade:
    id: int
    symbol: str
    action: str  # BUY / SELL
    quantity: int
    price: float
    total_amount: float
    reasoning: Optional[str]
    confidence: Optional[float]
    executed_at: datetime


@dataclass
class Performance:
    id: int
    date: date
    total_value: float
    cash: float
    unrealized_pnl: Optional[float]
    realized_pnl: Optional[float]
    daily_return: Optional[float]


@dataclass
class LearningLog:
    id: int
    trade_id: Optional[int]
    outcome: str  # WIN / LOSS / HOLD
    profit_loss: Optional[float]
    lesson: Optional[str]
    strategy_adjustment: Optional[str]
    created_at: datetime
