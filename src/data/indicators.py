import pandas as pd
import ta


class TechnicalIndicators:
    """テクニカル指標を計算"""

    def calculate_all(self, df: pd.DataFrame) -> dict:
        """主要テクニカル指標を一括計算"""
        if len(df) < 26:
            return {"error": "データ不足（最低26日分必要）"}

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"]

        return {
            "rsi_14": ta.momentum.rsi(close, window=14).iloc[-1],
            "macd": ta.trend.macd_diff(close).iloc[-1],
            "macd_signal": ta.trend.macd_signal(close).iloc[-1],
            "bb_upper": ta.volatility.bollinger_hband(close).iloc[-1],
            "bb_lower": ta.volatility.bollinger_lband(close).iloc[-1],
            "bb_middle": ta.volatility.bollinger_mavg(close).iloc[-1],
            "sma_20": ta.trend.sma_indicator(close, window=20).iloc[-1],
            "sma_50": ta.trend.sma_indicator(close, window=50).iloc[-1],
            "ema_12": ta.trend.ema_indicator(close, window=12).iloc[-1],
            "atr_14": ta.volatility.average_true_range(high, low, close, window=14).iloc[-1],
            "adx_14": ta.trend.adx(high, low, close, window=14).iloc[-1],
            "current_price": close.iloc[-1],
            "volume_avg_20": volume.rolling(window=20).mean().iloc[-1],
            "price_change_5d": (close.iloc[-1] / close.iloc[-5] - 1) * 100 if len(close) >= 5 else None,
            "price_change_20d": (close.iloc[-1] / close.iloc[-20] - 1) * 100 if len(close) >= 20 else None,
        }

    def get_signals(self, indicators: dict) -> list[str]:
        """テクニカル指標からシグナルを生成"""
        signals = []
        if "error" in indicators:
            return [indicators["error"]]

        rsi = indicators["rsi_14"]
        if rsi < 30:
            signals.append("RSI売られすぎ（買いシグナル）")
        elif rsi > 70:
            signals.append("RSI買われすぎ（売りシグナル）")

        if indicators["macd"] > 0 and indicators["macd_signal"] < 0:
            signals.append("MACDゴールデンクロス（買いシグナル）")
        elif indicators["macd"] < 0 and indicators["macd_signal"] > 0:
            signals.append("MACDデッドクロス（売りシグナル）")

        price = indicators["current_price"]
        if price < indicators["bb_lower"]:
            signals.append("ボリンジャーバンド下限割れ（買いシグナル）")
        elif price > indicators["bb_upper"]:
            signals.append("ボリンジャーバンド上限超え（売りシグナル）")

        if indicators["sma_20"] > indicators["sma_50"]:
            signals.append("短期SMA > 長期SMA（上昇トレンド）")
        else:
            signals.append("短期SMA < 長期SMA（下降トレンド）")

        return signals if signals else ["特段のシグナルなし"]
