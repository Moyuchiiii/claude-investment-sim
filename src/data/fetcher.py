import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import os


class StockFetcher:
    """株価データ取得（yfinanceメイン）"""

    def get_current_price(self, symbol: str) -> Optional[float]:
        """現在の株価を取得"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.fast_info
            return info.get("lastPrice") or info.get("previousClose")
        except Exception:
            return None

    def get_history(self, symbol: str, period: str = "3mo", interval: str = "1d") -> pd.DataFrame:
        """ヒストリカルデータを取得"""
        ticker = yf.Ticker(symbol)
        return ticker.history(period=period, interval=interval)

    def get_multiple_prices(self, symbols: list[str]) -> dict[str, Optional[float]]:
        """複数銘柄の現在価格を一括取得"""
        prices = {}
        for symbol in symbols:
            prices[symbol] = self.get_current_price(symbol)
        return prices

    def get_company_info(self, symbol: str) -> dict:
        """企業情報を取得"""
        ticker = yf.Ticker(symbol)
        try:
            return ticker.info
        except Exception:
            return {}
