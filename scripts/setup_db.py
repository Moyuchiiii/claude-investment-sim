"""DB初期化スクリプト"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.migrations import migrate
from src.db.repository import PortfolioRepository
from src.engine.portfolio import load_config

if __name__ == "__main__":
    migrate()
    print("テーブル作成完了")

    # ポートフォリオが未作成なら初期資金で作成
    repo = PortfolioRepository()
    if not repo.get():
        config = load_config()
        initial_cash = config["portfolio"]["initial_cash"]
        repo.create(initial_cash)
        print(f"ポートフォリオ初期化完了: {initial_cash:,.0f}円")
    else:
        print("ポートフォリオは既に存在します")

    print("DB初期化完了: data/sim.db")
