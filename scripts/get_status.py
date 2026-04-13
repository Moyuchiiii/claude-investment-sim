"""ポートフォリオ状況をJSON出力"""
import sys
import json
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.engine.portfolio import PortfolioManager
from src.engine.risk import RiskManager
from src.db.repository import TradeRepository, LearningLogRepository, TaxRepository
from src.data.sectors import SectorAnalyzer, SECTOR_MAP

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
    # 医薬品
    "4502.T": "武田薬品工業",
    "4568.T": "第一三共",
    # 不動産
    "8801.T": "三井不動産",
    "8802.T": "三菱地所",
    # 小売
    "9983.T": "ファーストリテイリング",
    "3382.T": "セブン＆アイHD",
    # 食品・飲料
    "2502.T": "アサヒグループHD",
    "2503.T": "キリンHD",
    # 陸運
    "9020.T": "JR東日本",
    "9022.T": "JR東海",
    # 建設
    "1812.T": "鹿島建設",
    # 保険
    "8766.T": "東京海上HD",
    # 商社
    "8058.T": "三菱商事",
    "8001.T": "伊藤忠商事",
    # 半導体
    "8035.T": "東京エレクトロン",
    # 電機・空調
    "6367.T": "ダイキン工業",
    # 金融
    "8316.T": "三井住友FG",
}


def main():
    portfolio_mgr = PortfolioManager()
    risk_mgr = RiskManager()
    trade_repo = TradeRepository()
    learning_repo = LearningLogRepository()
    tax_repo = TaxRepository()
    sector_analyzer = SectorAnalyzer()

    status = portfolio_mgr.get_status()
    if "error" in status:
        print(json.dumps({"error": status["error"]}, ensure_ascii=False))
        return

    # 保有銘柄にセクター情報を付与
    for holding in status.get("holdings", []):
        holding["sector"] = sector_analyzer.get_sector(holding["symbol"])

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

    # セクター分析を取得
    sector_analysis = sector_analyzer.get_sector_summary()

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
        "sector_analysis": sector_analysis,
    }

    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
