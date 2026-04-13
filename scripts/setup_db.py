"""DB初期化スクリプト"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.migrations import migrate

if __name__ == "__main__":
    migrate()
    print("DB初期化完了: data/sim.db")
