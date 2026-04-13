"""ニュースデータの取得"""
import feedparser
import urllib.parse
from datetime import datetime
from typing import Optional
from src.data.cache import DataCache

# キャッシュ有効期限
NEWS_CACHE_TTL = 3600  # 1時間

# 銘柄コードから企業名へのマッピング（検索用）
SEARCH_NAMES = {
    "7203.T": "トヨタ自動車",
    "6758.T": "ソニー",
    "9984.T": "ソフトバンクグループ",
    "6861.T": "キーエンス",
    "8306.T": "三菱UFJ",
    "6501.T": "日立製作所",
    "7974.T": "任天堂",
    "4063.T": "信越化学工業",
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
    "3382.T": "セブン＆アイホールディングス",
    # 食品・飲料
    "2502.T": "アサヒグループホールディングス",
    "2503.T": "キリンホールディングス",
    # 陸運
    "9020.T": "JR東日本",
    "9022.T": "JR東海",
    # 建設
    "1812.T": "鹿島建設",
    # 保険
    "8766.T": "東京海上ホールディングス",
    # 商社
    "8058.T": "三菱商事",
    "8001.T": "伊藤忠商事",
    # 半導体
    "8035.T": "東京エレクトロン",
    # 電機・空調
    "6367.T": "ダイキン工業",
    # 金融
    "8316.T": "三井住友フィナンシャルグループ",
}


class NewsCollector:
    """Google News RSSからニュースヘッドラインを取得"""

    def __init__(self):
        self.cache = DataCache()

    def get_news(self, symbol: str, max_results: int = 5) -> list[dict]:
        """銘柄に関連するニュースを取得"""
        # キャッシュチェック
        cached = self.cache.get("news", symbol, NEWS_CACHE_TTL)
        if cached is not None:
            return cached

        company_name = SEARCH_NAMES.get(symbol)
        if not company_name:
            # .Tを除去して検索
            company_name = symbol.replace(".T", "")

        query = urllib.parse.quote(f"{company_name} 株価")
        url = f"https://news.google.com/rss/search?q={query}&hl=ja&gl=JP&ceid=JP:ja"

        try:
            feed = feedparser.parse(url)
            articles = []

            for entry in feed.entries[:max_results]:
                published = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6]).strftime("%Y-%m-%d %H:%M")

                articles.append({
                    "title": entry.title,
                    "source": entry.get("source", {}).get("title", "不明"),
                    "published": published,
                    "link": entry.link,
                })

            self.cache.set("news", symbol, articles)
            return articles

        except Exception:
            return []

    def get_market_news(self, max_results: int = 5) -> list[dict]:
        """日本株市場全体のニュースを取得"""
        # キャッシュチェック（市場ニュースはキー固定）
        cached = self.cache.get("news", "market", NEWS_CACHE_TTL)
        if cached is not None:
            return cached

        query = urllib.parse.quote("日経平均 株式市場")
        url = f"https://news.google.com/rss/search?q={query}&hl=ja&gl=JP&ceid=JP:ja"

        try:
            feed = feedparser.parse(url)
            articles = []

            for entry in feed.entries[:max_results]:
                published = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6]).strftime("%Y-%m-%d %H:%M")

                articles.append({
                    "title": entry.title,
                    "source": entry.get("source", {}).get("title", "不明"),
                    "published": published,
                    "link": entry.link,
                })

            self.cache.set("news", "market", articles)
            return articles

        except Exception:
            return []

    def analyze_sentiment_simple(self, headlines: list[str]) -> dict:
        """ヘッドラインからシンプルなセンチメントスコアを算出（ルールベース）

        ※これは簡易版。/trade スキルではClaude自身がヘッドラインを見て判断する。
        """
        positive_words = [
            "上昇", "高値", "最高", "好調", "増益", "増収", "上方修正",
            "買い", "急騰", "回復", "成長", "過去最高", "黒字", "上回",
            "好決算", "増配", "自社株買い", "提携", "受注",
        ]
        negative_words = [
            "下落", "安値", "最安", "不調", "減益", "減収", "下方修正",
            "売り", "急落", "悪化", "縮小", "赤字", "下回", "懸念",
            "悪決算", "減配", "リストラ", "訴訟", "不正",
        ]

        pos_count = 0
        neg_count = 0
        for headline in headlines:
            for w in positive_words:
                if w in headline:
                    pos_count += 1
            for w in negative_words:
                if w in headline:
                    neg_count += 1

        total = pos_count + neg_count
        if total == 0:
            return {"score": 0.0, "label": "中立", "positive": 0, "negative": 0}

        score = (pos_count - neg_count) / total  # -1.0 ~ 1.0
        if score > 0.2:
            label = "ポジティブ"
        elif score < -0.2:
            label = "ネガティブ"
        else:
            label = "中立"

        return {
            "score": round(score, 2),
            "label": label,
            "positive": pos_count,
            "negative": neg_count,
        }
