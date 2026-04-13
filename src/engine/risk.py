"""リスク管理"""
import logging
import yaml
import pandas as pd
from pathlib import Path
from src.db.repository import HoldingRepository
from src.data.fetcher import StockFetcher
from src.data.sectors import SECTOR_MAP

CONFIG_PATH = Path(__file__).parent.parent.parent / "config.yaml"

logger = logging.getLogger(__name__)


def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def check_sector_concentration(
    symbol: str,
    quantity: int,
    price: float,
    holdings: list,
    portfolio,
    config: dict,
) -> dict:
    """
    セクター集中リスクチェック。
    新規注文でセクター上限（max_sector_pct）を超える場合は拒否する。
    """
    fetcher = StockFetcher()
    target_sector = SECTOR_MAP.get(symbol, "不明")
    max_sector_pct = config.get("trading", {}).get("max_sector_pct", 0.30)

    # ポートフォリオ総評価額を計算
    total_value = portfolio.cash
    sector_values: dict[str, float] = {}

    for h in holdings:
        h_price = fetcher.get_current_price(h.symbol)
        if not h_price:
            continue
        h_value = h.quantity * h_price
        total_value += h_value

        sector = SECTOR_MAP.get(h.symbol, "不明")
        sector_values[sector] = sector_values.get(sector, 0.0) + h_value

    if total_value <= 0:
        return {"allowed": True, "reason": "", "sector": target_sector,
                "current_pct": 0.0, "after_pct": 0.0}

    # 注文金額
    order_value = quantity * price
    current_sector_value = sector_values.get(target_sector, 0.0)

    current_pct = current_sector_value / total_value
    # 注文後の合計でも total_value は変わらない（現金→株の振替なので総資産は同じ）
    after_pct = (current_sector_value + order_value) / total_value

    if after_pct > max_sector_pct:
        return {
            "allowed": False,
            "reason": (
                f"セクター集中上限超過 — {target_sector}セクター "
                f"現在: {current_pct*100:.1f}% → 注文後: {after_pct*100:.1f}% "
                f"（上限: {max_sector_pct*100:.0f}%）"
            ),
            "sector": target_sector,
            "current_pct": round(current_pct, 4),
            "after_pct": round(after_pct, 4),
        }

    return {
        "allowed": True,
        "reason": "",
        "sector": target_sector,
        "current_pct": round(current_pct, 4),
        "after_pct": round(after_pct, 4),
    }


def check_correlation_risk(symbol: str, holdings: list) -> dict:
    """
    相関リスクチェック（警告のみ、取引を止めない）。
    保有銘柄との過去3ヶ月の相関係数を計算し、0.8超の場合に警告を出す。
    """
    CORR_WARN_THRESHOLD = 0.8
    LOOKBACK_PERIOD = "3mo"

    fetcher = StockFetcher()

    held_symbols = [h.symbol for h in holdings if h.symbol != symbol]
    if not held_symbols:
        return {"warnings": [], "high_correlation_pairs": []}

    # 新規銘柄のリターン系列を取得
    try:
        new_hist = fetcher.get_history(symbol, period=LOOKBACK_PERIOD)
        if new_hist.empty or len(new_hist) < 10:
            return {"warnings": [], "high_correlation_pairs": []}
        new_returns = new_hist["Close"].pct_change().dropna()
    except Exception as e:
        logger.warning("相関チェック: %s のデータ取得失敗 — %s", symbol, e)
        return {"warnings": [], "high_correlation_pairs": []}

    warnings: list[str] = []
    high_pairs: list[dict] = []

    for held in held_symbols:
        try:
            held_hist = fetcher.get_history(held, period=LOOKBACK_PERIOD)
            if held_hist.empty or len(held_hist) < 10:
                continue
            held_returns = held_hist["Close"].pct_change().dropna()

            # 日付を揃えて相関を計算
            combined = pd.DataFrame({"new": new_returns, "held": held_returns}).dropna()
            if len(combined) < 10:
                continue

            corr = combined["new"].corr(combined["held"])
            if pd.isna(corr):
                continue

            if corr >= CORR_WARN_THRESHOLD:
                msg = f"{symbol} と {held} の相関係数が高い（r={corr:.2f}）— 分散効果が薄い可能性"
                warnings.append(msg)
                high_pairs.append({"symbol_new": symbol, "symbol_held": held, "correlation": round(corr, 4)})

        except Exception as e:
            logger.warning("相関チェック: %s との相関計算失敗 — %s", held, e)
            continue

    return {"warnings": warnings, "high_correlation_pairs": high_pairs}


def get_portfolio_risk_summary(holdings: list, prices: dict, portfolio) -> dict:
    """
    ポートフォリオ全体のリスクサマリーを返す。
    - セクター別配分
    - HHI（ハーフィンダール・ハーシュマン指数）による集中度スコア
    - 上位集中リスク銘柄
    """
    total_value = portfolio.cash
    position_values: dict[str, float] = {}
    sector_values: dict[str, float] = {}

    for h in holdings:
        price = prices.get(h.symbol)
        if not price:
            continue
        val = h.quantity * price
        total_value += val
        position_values[h.symbol] = val

        sector = SECTOR_MAP.get(h.symbol, "不明")
        sector_values[sector] = sector_values.get(sector, 0.0) + val

    if total_value <= 0 or not position_values:
        return {
            "sector_breakdown": {},
            "hhi": 0.0,
            "diversification_score": 100.0,
            "top_concentration_risks": [],
        }

    # セクター別パーセンテージ
    sector_breakdown = {
        sector: round(val / total_value * 100, 2)
        for sector, val in sorted(sector_values.items(), key=lambda x: x[1], reverse=True)
    }

    # HHI計算（0〜10000、低いほど分散）
    # 各銘柄の比率の二乗和 × 10000
    hhi = sum((val / total_value) ** 2 for val in position_values.values()) * 10000
    hhi = round(hhi, 1)

    # 分散スコア（HHI 10000=完全集中=0点、0=完全分散=100点）
    diversification_score = round(max(0.0, (1 - hhi / 10000) * 100), 1)

    # 上位集中リスク（10%超のポジション）
    top_risks = [
        {"symbol": sym, "pct": round(val / total_value * 100, 2)}
        for sym, val in sorted(position_values.items(), key=lambda x: x[1], reverse=True)
        if val / total_value >= 0.10
    ]

    return {
        "sector_breakdown": sector_breakdown,
        "hhi": hhi,
        "diversification_score": diversification_score,
        "top_concentration_risks": top_risks,
    }


class RiskManager:
    def __init__(self):
        self.config = load_config()
        self.holding_repo = HoldingRepository()
        self.fetcher = StockFetcher()

    def check_buy(self, portfolio, symbol: str, total_cost: float) -> dict:
        """買い注文のリスクチェック"""
        trading_config = self.config["trading"]

        # ポートフォリオ全体の評価額を概算
        holdings = self.holding_repo.get_all()
        total_value = portfolio.cash
        for h in holdings:
            price = self.fetcher.get_current_price(h.symbol)
            if price:
                total_value += h.quantity * price

        # 1銘柄への最大投資割合チェック
        max_position = total_value * trading_config["max_position_pct"]
        existing = self.holding_repo.get_by_symbol(1, symbol)
        existing_value = 0
        if existing:
            price = self.fetcher.get_current_price(symbol)
            if price:
                existing_value = existing.quantity * price

        if existing_value + total_cost > max_position:
            return {
                "allowed": False,
                "reason": f"ポジション上限超過（上限: {max_position:,.0f}円, 現在+注文: {existing_value + total_cost:,.0f}円）"
            }

        return {"allowed": True}

    def check_stop_loss(self, symbol: str, avg_cost: float, current_price: float) -> bool:
        """損切りラインに到達したか"""
        loss_pct = (current_price / avg_cost - 1)
        return loss_pct <= -self.config["trading"]["stop_loss_pct"]

    def check_take_profit(self, symbol: str, avg_cost: float, current_price: float) -> bool:
        """利確ラインに到達したか"""
        gain_pct = (current_price / avg_cost - 1)
        return gain_pct >= self.config["trading"]["take_profit_pct"]

    def get_risk_alerts(self) -> list[dict]:
        """リスクアラートを取得"""
        alerts = []
        holdings = self.holding_repo.get_all()

        for h in holdings:
            price = self.fetcher.get_current_price(h.symbol)
            if not price:
                continue

            if self.check_stop_loss(h.symbol, h.avg_cost, price):
                loss_pct = (price / h.avg_cost - 1) * 100
                alerts.append({
                    "type": "STOP_LOSS",
                    "symbol": h.symbol,
                    "message": f"{h.symbol}: 損切りライン到達（{loss_pct:.1f}%）",
                    "current_price": price,
                    "avg_cost": h.avg_cost
                })

            if self.check_take_profit(h.symbol, h.avg_cost, price):
                gain_pct = (price / h.avg_cost - 1) * 100
                alerts.append({
                    "type": "TAKE_PROFIT",
                    "symbol": h.symbol,
                    "message": f"{h.symbol}: 利確ライン到達（+{gain_pct:.1f}%）",
                    "current_price": price,
                    "avg_cost": h.avg_cost
                })

        return alerts
