"""銘柄分析データをJSON出力"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.fetcher import StockFetcher
from src.data.indicators import TechnicalIndicators
from src.data.fundamentals import FundamentalData
from src.data.news import NewsCollector
from src.data.market import MarketIndicators

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
    symbol = sys.argv[1] if len(sys.argv) > 1 else None
    period = sys.argv[2] if len(sys.argv) > 2 else "3mo"

    if not symbol:
        print(json.dumps({"error": "銘柄コードを指定してください"}, ensure_ascii=False))
        return

    fetcher = StockFetcher()
    indicators = TechnicalIndicators()
    fundamentals_fetcher = FundamentalData()
    news_collector = NewsCollector()
    market_indicators = MarketIndicators()

    history = fetcher.get_history(symbol, period=period)
    if history.empty:
        print(json.dumps({"error": f"{symbol}のデータを取得できませんでした"}, ensure_ascii=False))
        return

    tech = indicators.calculate_all(history)
    signals = indicators.get_signals(tech) if "error" not in tech else []

    # ファンダメンタルズデータを取得
    fundamentals = fundamentals_fetcher.get_fundamentals(symbol)
    fundamental_signals = fundamentals_fetcher.get_valuation_signal(fundamentals)

    # ニュースを取得してセンチメント分析
    news_articles = news_collector.get_news(symbol)
    headlines = [article["title"] for article in news_articles]
    news_sentiment = news_collector.analyze_sentiment_simple(headlines)

    # 最新のローソク足データを取得
    market_data = {
        "open": float(history["Open"].iloc[-1]),
        "high": float(history["High"].iloc[-1]),
        "low": float(history["Low"].iloc[-1]),
        "close": float(history["Close"].iloc[-1]),
        "volume": int(history["Volume"].iloc[-1]),
        "prev_close": float(history["Close"].iloc[-2]) if len(history) > 1 else None,
    }

    # numpy/pandas型をネイティブのPython型に変換
    clean_tech = {}
    for k, v in tech.items():
        if v is None:
            clean_tech[k] = None
        elif isinstance(v, (int, float, str, bool)):
            clean_tech[k] = v
        else:
            try:
                clean_tech[k] = float(v)
            except (TypeError, ValueError):
                clean_tech[k] = str(v)

    # 出来高異常検知
    volume_anomaly = market_indicators.check_volume_anomaly(symbol)

    result = {
        "symbol": symbol,
        "symbol_name": SYMBOL_NAMES.get(symbol, symbol),
        "market_data": market_data,
        "indicators": clean_tech,
        "signals": signals,
        "fundamentals": fundamentals,
        "fundamental_signals": fundamental_signals,
        "news": news_articles,
        "news_sentiment": news_sentiment,
        "volume_anomaly": volume_anomaly,
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
