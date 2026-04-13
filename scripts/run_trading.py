"""売買サイクルを実行するメインスクリプト"""
import sys
import yaml
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.engine.portfolio import PortfolioManager
from src.engine.executor import TradeExecutor
from src.engine.risk import RiskManager
from src.data.fetcher import StockFetcher
from src.data.indicators import TechnicalIndicators
from src.ai.claude_judge import ClaudeJudge
from src.ai.prompt_builder import PromptBuilder
from src.ai.learner import Learner
from src.db.repository import TradeRepository, LearningLogRepository

CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"

def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)

def run_trading_cycle():
    """1回の売買サイクルを実行"""
    config = load_config()

    # 初期化
    portfolio_mgr = PortfolioManager()
    portfolio_mgr.initialize()
    executor = TradeExecutor()
    risk_mgr = RiskManager()
    fetcher = StockFetcher()
    indicators = TechnicalIndicators()
    judge = ClaudeJudge()
    prompt_builder = PromptBuilder()
    learner = Learner()
    trade_repo = TradeRepository()
    learning_repo = LearningLogRepository()

    print(f"=== 売買サイクル開始: {date.today()} ===")

    # ポートフォリオ状態を取得
    portfolio_status = portfolio_mgr.get_status()
    if "error" in portfolio_status:
        print(f"エラー: {portfolio_status['error']}")
        return

    print(f"総資産: {portfolio_status['total_value']:,.0f}円 "
          f"(現金: {portfolio_status['cash']:,.0f}円)")

    # リスクアラートをチェック
    alerts = risk_mgr.get_risk_alerts()
    for alert in alerts:
        print(f"⚠️ {alert['message']}")
        # 損切り・利確の自動実行
        if alert["type"] == "STOP_LOSS":
            holding = executor.holding_repo.get_by_symbol(1, alert["symbol"])
            if holding:
                result = executor.execute_sell(
                    alert["symbol"], holding.quantity,
                    reasoning=f"損切り自動実行: {alert['message']}", confidence=0.9
                )
                print(f"  → 損切り実行: {result}")
        elif alert["type"] == "TAKE_PROFIT":
            holding = executor.holding_repo.get_by_symbol(1, alert["symbol"])
            if holding:
                result = executor.execute_sell(
                    alert["symbol"], holding.quantity,
                    reasoning=f"利確自動実行: {alert['message']}", confidence=0.9
                )
                print(f"  → 利確実行: {result}")

    # 取引回数チェック
    today_trades = executor.get_today_trade_count()
    max_trades = config["trading"]["max_daily_trades"]
    if today_trades >= max_trades:
        print(f"本日の取引上限に達しました（{today_trades}/{max_trades}）")
        portfolio_mgr.record_daily_performance()
        return

    # 全銘柄を分析
    all_symbols = []
    for market in config["markets"].values():
        if market.get("enabled"):
            all_symbols.extend(market["symbols"])

    # 学習コンテキストを取得
    lessons = learning_repo.get_lessons(limit=20)
    lessons_data = [
        {"outcome": l.outcome, "lesson": l.lesson, "profit_loss": l.profit_loss}
        for l in lessons
    ]
    recent_trades = trade_repo.get_recent(limit=10)
    recent_trades_data = [
        {
            "executed_at": t.executed_at, "action": t.action,
            "symbol": t.symbol, "quantity": t.quantity,
            "price": t.price, "confidence": t.confidence
        }
        for t in recent_trades
    ]

    # ポートフォリオ状態を再取得（損切り・利確後の最新状態）
    portfolio_status = portfolio_mgr.get_status()

    for symbol in all_symbols:
        if today_trades >= max_trades:
            print(f"取引上限到達。残りの銘柄はスキップ。")
            break

        print(f"\n--- {symbol} を分析中 ---")

        # ヒストリカルデータを取得
        history = fetcher.get_history(symbol, period="3mo")
        if history.empty:
            print(f"  {symbol}: データ取得失敗、スキップ")
            continue

        # テクニカル指標を計算
        tech_indicators = indicators.calculate_all(history)
        if "error" in tech_indicators:
            print(f"  {symbol}: {tech_indicators['error']}、スキップ")
            continue

        signals = indicators.get_signals(tech_indicators)

        # 直近の価格データ
        market_data = {
            "open": float(history["Open"].iloc[-1]),
            "high": float(history["High"].iloc[-1]),
            "low": float(history["Low"].iloc[-1]),
            "close": float(history["Close"].iloc[-1]),
            "volume": int(history["Volume"].iloc[-1]),
            "prev_close": float(history["Close"].iloc[-2]) if len(history) > 1 else None,
        }

        # Claude に判断を求める
        prompt = prompt_builder.build_trading_prompt(
            symbol=symbol,
            market_data=market_data,
            indicators=tech_indicators,
            signals=signals,
            portfolio_status=portfolio_status,
            lessons=lessons_data,
            recent_trades=recent_trades_data
        )

        decision = judge.judge(prompt)

        if not decision:
            print(f"  {symbol}: Claude判断取得失敗、スキップ")
            continue

        action = decision.get("action", "HOLD")
        quantity = decision.get("quantity", 0)
        confidence = decision.get("confidence", 0)
        reasoning = decision.get("reasoning", "")

        print(f"  判断: {action} x{quantity} (確信度: {confidence:.0%})")
        print(f"  理由: {reasoning}")

        # 確信度チェック
        min_confidence = config["trading"]["min_confidence"]
        if confidence < min_confidence:
            print(f"  → 確信度不足（{confidence:.0%} < {min_confidence:.0%}）、スキップ")
            continue

        # 売買実行
        if action == "BUY" and quantity > 0:
            result = executor.execute_buy(symbol, quantity, reasoning, confidence)
            if result["success"]:
                print(f"  ✅ 買い実行: {quantity}株 @{result['price']:,.0f}円")
                today_trades += 1
            else:
                print(f"  ❌ 買い失敗: {result['error']}")

        elif action == "SELL" and quantity > 0:
            result = executor.execute_sell(symbol, quantity, reasoning, confidence)
            if result["success"]:
                print(f"  ✅ 売り実行: {quantity}株 @{result['price']:,.0f}円 (損益: {result['profit_loss']:+,.0f}円)")
                today_trades += 1
            else:
                print(f"  ❌ 売り失敗: {result['error']}")

        else:
            print(f"  → HOLD（様子見）")

    # 日次パフォーマンスを記録
    portfolio_mgr.record_daily_performance()

    # 取引結果を評価（学習）
    learner.evaluate_trades()

    # 最終状態を表示
    final_status = portfolio_mgr.get_status()
    print(f"\n=== 売買サイクル完了 ===")
    print(f"総資産: {final_status['total_value']:,.0f}円")
    print(f"現金: {final_status['cash']:,.0f}円")
    print(f"リターン: {final_status['total_return_pct']:+.2f}%")
    print(f"本日の取引: {today_trades}件")

if __name__ == "__main__":
    run_trading_cycle()
