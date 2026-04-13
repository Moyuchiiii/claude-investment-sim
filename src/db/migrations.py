import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "sim.db"


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def migrate():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS tax_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trade_id INTEGER,
        tax_type TEXT NOT NULL,
        taxable_amount REAL NOT NULL,
        tax_amount REAL NOT NULL,
        fiscal_year INTEGER NOT NULL,
        created_at TEXT DEFAULT (datetime('now', 'localtime')),
        FOREIGN KEY (trade_id) REFERENCES trades(id)
    );

    CREATE TABLE IF NOT EXISTS portfolio (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cash REAL NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS holdings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        portfolio_id INTEGER NOT NULL,
        symbol TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        avg_cost REAL NOT NULL,
        FOREIGN KEY (portfolio_id) REFERENCES portfolio(id)
    );

    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        action TEXT NOT NULL CHECK(action IN ('BUY', 'SELL')),
        quantity INTEGER NOT NULL,
        price REAL NOT NULL,
        total_amount REAL NOT NULL,
        reasoning TEXT,
        confidence REAL,
        executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS performance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date DATE NOT NULL UNIQUE,
        total_value REAL NOT NULL,
        cash REAL NOT NULL,
        unrealized_pnl REAL,
        realized_pnl REAL,
        daily_return REAL
    );

    CREATE TABLE IF NOT EXISTS learning_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trade_id INTEGER,
        outcome TEXT NOT NULL CHECK(outcome IN ('WIN', 'LOSS', 'HOLD')),
        profit_loss REAL,
        lesson TEXT,
        strategy_adjustment TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (trade_id) REFERENCES trades(id)
    );

    CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
    CREATE INDEX IF NOT EXISTS idx_trades_executed_at ON trades(executed_at);
    CREATE INDEX IF NOT EXISTS idx_holdings_portfolio ON holdings(portfolio_id);
    CREATE INDEX IF NOT EXISTS idx_performance_date ON performance(date);
    """)

    conn.commit()

    # trades テーブルにコスト追跡カラムを追加（既存DBへの追加対応）
    for column_def in [
        ("commission", "REAL DEFAULT 0"),
        ("slippage", "REAL DEFAULT 0"),
        ("tax", "REAL DEFAULT 0"),
    ]:
        col_name, col_type = column_def
        try:
            conn.execute(f"ALTER TABLE trades ADD COLUMN {col_name} {col_type}")
            conn.commit()
        except Exception:
            # カラムが既に存在する場合はスキップ
            pass

    # learning_log テーブルにタグ・銘柄・市場コンテキストカラムを追加（既存DBへの追加対応）
    for column_def in [
        ("tags", "TEXT"),
        ("symbol", "TEXT"),
        ("market_context", "TEXT"),
    ]:
        col_name, col_type = column_def
        try:
            conn.execute(f"ALTER TABLE learning_log ADD COLUMN {col_name} {col_type}")
            conn.commit()
        except Exception:
            # カラムが既に存在する場合はスキップ
            pass

    conn.close()
