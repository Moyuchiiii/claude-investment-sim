"""バックテストスクリプト — Claude判断なしでテクニカル指標ベースの戦略検証"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml
import pandas as pd
import numpy as np
from datetime import datetime
from src.data.fetcher import StockFetcher
from src.data.indicators import TechnicalIndicators

CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"

def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


class SimpleBacktester:
    """テクニカル指標ベースのシンプルなバックテスト"""

    def __init__(self, initial_cash: float = 1_000_000):
        self.initial_cash = initial_cash
        self.fetcher = StockFetcher()
        self.indicators = TechnicalIndicators()

    def run(self, symbol: str, period: str = "1y") -> dict:
        """1銘柄のバックテストを実行"""
        # ヒストリカルデータ取得
        df = self.fetcher.get_history(symbol, period=period)
        if df.empty or len(df) < 50:
            return {"symbol": symbol, "error": "データ不足"}

        cash = self.initial_cash
        position = 0
        avg_cost = 0.0
        trades = []
        portfolio_values = []

        for i in range(50, len(df)):
            window = df.iloc[:i+1]
            current_price = float(window["Close"].iloc[-1])
            current_date = str(window.index[-1].date())

            # テクニカル指標を計算
            tech = self.indicators.calculate_all(window)
            if "error" in tech:
                portfolio_values.append(cash + position * current_price)
                continue

            signals = self.indicators.get_signals(tech)

            # シンプルな戦略: RSI + MACD + ボリンジャーバンドの複合判断
            buy_score = 0
            sell_score = 0
            for s in signals:
                if "買いシグナル" in s:
                    buy_score += 1
                elif "売りシグナル" in s:
                    sell_score += 1
                elif "上昇トレンド" in s:
                    buy_score += 0.5
                elif "下降トレンド" in s:
                    sell_score += 0.5

            # 損切り・利確チェック
            if position > 0:
                return_pct = (current_price / avg_cost - 1)
                if return_pct <= -0.05:  # 損切り
                    proceeds = position * current_price
                    pnl = proceeds - (position * avg_cost)
                    trades.append({
                        "date": current_date, "action": "SELL(損切り)",
                        "symbol": symbol, "quantity": position,
                        "price": current_price, "pnl": pnl
                    })
                    cash += proceeds
                    position = 0
                    avg_cost = 0
                elif return_pct >= 0.15:  # 利確
                    proceeds = position * current_price
                    pnl = proceeds - (position * avg_cost)
                    trades.append({
                        "date": current_date, "action": "SELL(利確)",
                        "symbol": symbol, "quantity": position,
                        "price": current_price, "pnl": pnl
                    })
                    cash += proceeds
                    position = 0
                    avg_cost = 0

            # 売買判断
            if buy_score >= 2 and position == 0:
                # 資金の20%で購入
                invest_amount = cash * 0.2
                quantity = int(invest_amount / current_price)
                if quantity > 0:
                    cost = quantity * current_price
                    cash -= cost
                    position = quantity
                    avg_cost = current_price
                    trades.append({
                        "date": current_date, "action": "BUY",
                        "symbol": symbol, "quantity": quantity,
                        "price": current_price, "pnl": 0
                    })
            elif sell_score >= 2 and position > 0:
                proceeds = position * current_price
                pnl = proceeds - (position * avg_cost)
                trades.append({
                    "date": current_date, "action": "SELL",
                    "symbol": symbol, "quantity": position,
                    "price": current_price, "pnl": pnl
                })
                cash += proceeds
                position = 0
                avg_cost = 0

            portfolio_values.append(cash + position * current_price)

        # 最終評価
        final_value = cash + position * float(df["Close"].iloc[-1])
        total_return = (final_value / self.initial_cash - 1) * 100

        # 勝敗集計
        winning_trades = [t for t in trades if t["action"].startswith("SELL") and t["pnl"] > 0]
        losing_trades = [t for t in trades if t["action"].startswith("SELL") and t["pnl"] < 0]
        total_closed = len(winning_trades) + len(losing_trades)
        win_rate = (len(winning_trades) / total_closed * 100) if total_closed > 0 else 0

        # シャープレシオ（簡略版）
        if len(portfolio_values) > 1:
            returns = pd.Series(portfolio_values).pct_change().dropna()
            sharpe = (returns.mean() / returns.std() * np.sqrt(252)) if returns.std() > 0 else 0
        else:
            sharpe = 0

        # 最大ドローダウン
        if portfolio_values:
            peak = pd.Series(portfolio_values).expanding().max()
            drawdown = (pd.Series(portfolio_values) - peak) / peak
            max_drawdown = float(drawdown.min()) * 100
        else:
            max_drawdown = 0

        return {
            "symbol": symbol,
            "period": period,
            "initial_cash": self.initial_cash,
            "final_value": final_value,
            "total_return_pct": total_return,
            "total_trades": len(trades),
            "win_rate_pct": win_rate,
            "sharpe_ratio": sharpe,
            "max_drawdown_pct": max_drawdown,
            "trades": trades
        }


def main():
    config = load_config()
    backtester = SimpleBacktester(config["portfolio"]["initial_cash"])

    # 全銘柄でバックテスト
    all_symbols = []
    for market in config["markets"].values():
        if market.get("enabled"):
            all_symbols.extend(market["symbols"])

    print("=" * 70)
    print(f"バックテスト開始: {len(all_symbols)}銘柄")
    print("=" * 70)

    results = []
    for symbol in all_symbols:
        print(f"\n--- {symbol} ---")
        result = backtester.run(symbol, period="1y")
        results.append(result)

        if "error" in result:
            print(f"  エラー: {result['error']}")
            continue

        print(f"  リターン: {result['total_return_pct']:+.2f}%")
        print(f"  取引数: {result['total_trades']}")
        print(f"  勝率: {result['win_rate_pct']:.0f}%")
        print(f"  シャープレシオ: {result['sharpe_ratio']:.2f}")
        print(f"  最大DD: {result['max_drawdown_pct']:.1f}%")

    # サマリー
    valid_results = [r for r in results if "error" not in r]
    if valid_results:
        avg_return = np.mean([r["total_return_pct"] for r in valid_results])
        avg_sharpe = np.mean([r["sharpe_ratio"] for r in valid_results])
        avg_win_rate = np.mean([r["win_rate_pct"] for r in valid_results])

        print("\n" + "=" * 70)
        print("サマリー")
        print("=" * 70)
        print(f"銘柄数: {len(valid_results)}")
        print(f"平均リターン: {avg_return:+.2f}%")
        print(f"平均シャープレシオ: {avg_sharpe:.2f}")
        print(f"平均勝率: {avg_win_rate:.0f}%")

        # ベスト/ワースト
        best = max(valid_results, key=lambda r: r["total_return_pct"])
        worst = min(valid_results, key=lambda r: r["total_return_pct"])
        print(f"\nベスト: {best['symbol']} ({best['total_return_pct']:+.2f}%)")
        print(f"ワースト: {worst['symbol']} ({worst['total_return_pct']:+.2f}%)")


if __name__ == "__main__":
    main()
