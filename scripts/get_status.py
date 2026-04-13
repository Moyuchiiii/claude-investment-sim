"""ポートフォリオ状況をJSON出力"""
import sys
import json
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.engine.portfolio import PortfolioManager
from src.engine.risk import RiskManager
from src.db.repository import TradeRepository, LearningLogRepository, TaxRepository

SYMBOL_NAMES = {
    "7203.T": "トヨタ自動車",
    "6758.T": "ソニーG",
    "9984.T": "ソフトバンクG",
    "6861.T": "キーエンス",
    "8306.T": "三菱UFJ",
    "6501.T": "日立製作所",
    "7974.T": "任天堂",
    "4063.T": "信越化学",
    "9432.T": "NTT",
    "6902.T": "デンソー",
}


def main():
    portfolio_mgr = PortfolioManager()
    risk_mgr = RiskManager()
    trade_repo = TradeRepository()
    learning_repo = LearningLogRepository()
    tax_repo = TaxRepository()

    status = portfolio_mgr.get_status()
    if "error" in status:
        print(json.dumps({"error": status["error"]}, ensure_ascii=False))
        return

    alerts = risk_mgr.get_risk_alerts()

    # 直近10件の取引履歴を取得
    recent_trades = trade_repo.get_recent(limit=10)
    trades_data = [
        {
            "executed_at": t.executed_at,
            "action": t.action,
            "symbol": t.symbol,
            "symbol_name": SYMBOL_NAMES.get(t.symbol, t.symbol),
            "quantity": t.quantity,
            "price": t.price,
            "confidence": t.confidence,
            "reasoning": t.reasoning,
        }
        for t in recent_trades
    ]

    # 過去の教訓を最大20件取得
    lessons = learning_repo.get_lessons(limit=20)
    lessons_data = [
        {
            "outcome": l.outcome,
            "lesson": l.lesson,
            "profit_loss": l.profit_loss,
            "strategy_adjustment": l.strategy_adjustment,
        }
        for l in lessons
    ]

    # 今年の税金サマリーを取得
    current_year = datetime.now().year
    tax_summary = tax_repo.get_yearly_summary(current_year)
    loss_carryforward = tax_repo.get_loss_carryforward(current_year)

    result = {
        "portfolio": status,
        "risk_alerts": alerts,
        "recent_trades": trades_data,
        "lessons": lessons_data,
        "tax_summary": {
            "year": current_year,
            "ytd_realized_gains": tax_summary["total_taxable"],
            "ytd_tax_paid": tax_summary["total_tax"],
            "loss_carryforward": loss_carryforward,
        },
    }

    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
