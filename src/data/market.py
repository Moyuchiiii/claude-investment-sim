"""マーケット全体の指標データ"""
import yfinance as yf
from src.data.cache import DataCache

# マーケットデータのキャッシュ有効期限（5分）
MARKET_CACHE_TTL = 300


class MarketIndicators:
    """日経平均・為替・米国市場など全体指標を取得"""

    def __init__(self):
        self.cache = DataCache()

    def get_market_overview(self) -> dict:
        """主要マーケット指標を一括取得"""
        cached = self.cache.get("market", "overview", MARKET_CACHE_TTL)
        if cached is not None:
            return cached

        result = {}

        # 日経平均
        result["nikkei"] = self._get_index_data("^N225", "日経平均")
        # TOPIX
        result["topix"] = self._get_index_data("^TPX", "TOPIX")
        # USD/JPY
        result["usdjpy"] = self._get_fx_data("JPY=X", "USD/JPY")
        # S&P 500
        result["sp500"] = self._get_index_data("^GSPC", "S&P 500")

        self.cache.set("market", "overview", result)
        return result

    def _get_index_data(self, symbol: str, name: str) -> dict:
        """指数データを取得"""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d")
            if hist.empty or len(hist) < 2:
                return {"name": name, "error": "データ取得失敗"}

            current = float(hist["Close"].iloc[-1])
            prev = float(hist["Close"].iloc[-2])
            change = current - prev
            change_pct = (change / prev) * 100

            return {
                "name": name,
                "value": current,
                "change": change,
                "change_pct": change_pct,
            }
        except Exception as e:
            return {"name": name, "error": str(e)}

    def _get_fx_data(self, symbol: str, name: str) -> dict:
        """為替データを取得"""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d")
            if hist.empty or len(hist) < 2:
                return {"name": name, "error": "データ取得失敗"}

            current = float(hist["Close"].iloc[-1])
            prev = float(hist["Close"].iloc[-2])
            change = current - prev
            change_pct = (change / prev) * 100

            return {
                "name": name,
                "value": current,
                "change": change,
                "change_pct": change_pct,
            }
        except Exception as e:
            return {"name": name, "error": str(e)}

    def check_volume_anomaly(self, symbol: str, threshold: float = 2.0) -> dict:
        """出来高の異常検知（20日平均比）"""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1mo")
            if hist.empty or len(hist) < 5:
                return {"symbol": symbol, "anomaly": False, "error": "データ不足"}

            current_vol = float(hist["Volume"].iloc[-1])
            avg_vol = float(hist["Volume"].iloc[:-1].tail(20).mean())

            if avg_vol == 0:
                return {"symbol": symbol, "anomaly": False, "ratio": 0}

            ratio = current_vol / avg_vol

            return {
                "symbol": symbol,
                "anomaly": ratio >= threshold,
                "ratio": round(ratio, 2),
                "current_volume": int(current_vol),
                "avg_volume": int(avg_vol),
            }
        except Exception as e:
            return {"symbol": symbol, "anomaly": False, "error": str(e)}

    def get_market_signal(self, overview: dict) -> list[str]:
        """マーケット全体のシグナルを生成"""
        signals = []

        nikkei = overview.get("nikkei", {})
        if "error" not in nikkei:
            pct = nikkei.get("change_pct", 0)
            if pct > 1.0:
                signals.append(f"日経平均 上昇中（{pct:+.1f}%）→ 地合い良好")
            elif pct < -1.0:
                signals.append(f"日経平均 下落中（{pct:+.1f}%）→ 地合い悪化、買い慎重に")
            else:
                signals.append(f"日経平均 横ばい（{pct:+.1f}%）")

        usdjpy = overview.get("usdjpy", {})
        if "error" not in usdjpy:
            val = usdjpy.get("value", 0)
            pct = usdjpy.get("change_pct", 0)
            if pct > 0.5:
                signals.append(f"円安進行（¥{val:.1f}, {pct:+.1f}%）→ 輸出株に追い風")
            elif pct < -0.5:
                signals.append(f"円高進行（¥{val:.1f}, {pct:+.1f}%）→ 内需株優位")

        sp500 = overview.get("sp500", {})
        if "error" not in sp500:
            pct = sp500.get("change_pct", 0)
            if pct > 1.0:
                signals.append(f"米国市場 上昇（S&P500 {pct:+.1f}%）→ 日本株にポジティブ")
            elif pct < -1.0:
                signals.append(f"米国市場 下落（S&P500 {pct:+.1f}%）→ 日本株に下押し圧力")

        return signals
