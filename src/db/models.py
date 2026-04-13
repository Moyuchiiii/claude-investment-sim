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
    commission: float = 0.0    # 売買手数料
    slippage: float = 0.0      # スリッページ額
    tax: float = 0.0           # 譲渡益税
    executed_at: Optional[str] = None


@dataclass
class TaxRecord:
    id: int
    trade_id: Optional[int]
    tax_type: str              # 'capital_gains' or 'dividend'
    taxable_amount: float      # 課税対象額
    tax_amount: float          # 税額
    fiscal_year: int           # 課税年度
    created_at: Optional[str] = None


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
