"""セクター分析・ローテーション戦略"""
from src.data.fetcher import StockFetcher

# 銘柄→セクター分類
SECTOR_MAP = {
    "7203.T": "自動車",
    "6902.T": "自動車",
    "6758.T": "電機・精密",
    "6501.T": "電機・精密",
    "6861.T": "電機・精密",
    "9984.T": "情報通信",
    "9432.T": "情報通信",
    "8306.T": "金融",
    "4063.T": "素材・化学",
    "7974.T": "エンタメ",
    # 医薬品
    "4502.T": "医薬品",
    "4568.T": "医薬品",
    # 不動産
    "8801.T": "不動産",
    "8802.T": "不動産",
    # 小売
    "9983.T": "小売",
    "3382.T": "小売",
    # 食品・飲料
    "2502.T": "食品・飲料",
    "2503.T": "食品・飲料",
    # 陸運
    "9020.T": "陸運",
    "9022.T": "陸運",
    # 建設
    "1812.T": "建設",
    # 保険
    "8766.T": "保険",
    # 商社
    "8058.T": "商社",
    "8001.T": "商社",
    # 半導体
    "8035.T": "半導体",
    # 電機・空調（既存の電機・精密とは別セクター）
    "6367.T": "電機・精密",
    # 金融
    "8316.T": "金融",
}

# セクターの色（ダッシュボード用）
SECTOR_COLORS = {
    "自動車": "#3b82f6",
    "電機・精密": "#00d4aa",
    "情報通信": "#a855f7",
    "金融": "#f59e0b",
    "素材・化学": "#06b6d4",
    "エンタメ": "#ec4899",
    "医薬品": "#10b981",
    "不動産": "#8b5cf6",
    "小売": "#f43f5e",
    "食品・飲料": "#84cc16",
    "陸運": "#0ea5e9",
    "建設": "#d97706",
    "保険": "#14b8a6",
    "商社": "#e879f9",
    "半導体": "#facc15",
}


class SectorAnalyzer:
    """セクター分析を行う"""

    def __init__(self):
        self.fetcher = StockFetcher()

    def get_sector(self, symbol: str) -> str:
        """銘柄のセクターを返す"""
        return SECTOR_MAP.get(symbol, "不明")

    def get_sector_symbols(self, sector: str) -> list[str]:
        """セクター内の全銘柄を返す"""
        return [s for s, sec in SECTOR_MAP.items() if sec == sector]

    def get_all_sectors(self) -> list[str]:
        """全セクター一覧を返す"""
        return list(set(SECTOR_MAP.values()))

    def analyze_sector_performance(self, period: str = "1mo") -> dict:
        """セクター別パフォーマンスを計算"""
        sector_returns = {}

        for symbol, sector in SECTOR_MAP.items():
            history = self.fetcher.get_history(symbol, period=period)
            if history.empty or len(history) < 2:
                continue

            # 期間リターンを計算
            start_price = float(history["Close"].iloc[0])
            end_price = float(history["Close"].iloc[-1])
            ret = (end_price / start_price - 1) * 100

            if sector not in sector_returns:
                sector_returns[sector] = {"returns": [], "symbols": []}
            sector_returns[sector]["returns"].append(ret)
            sector_returns[sector]["symbols"].append(symbol)

        # セクター平均リターンを計算
        result = {}
        for sector, data in sector_returns.items():
            avg_return = sum(data["returns"]) / len(data["returns"])
            result[sector] = {
                "avg_return_pct": round(avg_return, 2),
                "symbols": data["symbols"],
                "individual_returns": {
                    s: round(r, 2) for s, r in zip(data["symbols"], data["returns"])
                },
            }

        return result

    def get_rotation_signals(self, period: str = "1mo") -> list[str]:
        """セクターローテーションシグナルを生成"""
        performance = self.analyze_sector_performance(period)
        if not performance:
            return ["セクターデータ不足"]

        # リターン順にソート
        sorted_sectors = sorted(
            performance.items(),
            key=lambda x: x[1]["avg_return_pct"],
            reverse=True
        )

        signals = []

        # トップセクター
        best_sector, best_data = sorted_sectors[0]
        signals.append(
            f"強セクター: {best_sector}（{period}リターン: {best_data['avg_return_pct']:+.1f}%）→ 資金流入の可能性"
        )

        # ワーストセクター
        worst_sector, worst_data = sorted_sectors[-1]
        signals.append(
            f"弱セクター: {worst_sector}（{period}リターン: {worst_data['avg_return_pct']:+.1f}%）→ 資金流出の可能性"
        )

        # セクター間の乖離
        spread = best_data["avg_return_pct"] - worst_data["avg_return_pct"]
        if spread > 10:
            signals.append(f"セクター間乖離: {spread:.1f}% — ローテーション発生の兆候")
        elif spread < 3:
            signals.append(f"セクター間乖離: {spread:.1f}% — 全体相場連動（セクター選好なし）")

        # 各セクターの状況
        for sector, data in sorted_sectors:
            ret = data["avg_return_pct"]
            if ret > 5:
                signals.append(f"{sector}: 上昇トレンド（{ret:+.1f}%）")
            elif ret < -5:
                signals.append(f"{sector}: 下降トレンド（{ret:+.1f}%）")

        return signals

    def get_sector_summary(self) -> dict:
        """全セクターのサマリーを返す（JSON出力用）"""
        perf_1m = self.analyze_sector_performance("1mo")
        perf_3m = self.analyze_sector_performance("3mo")
        signals = self.get_rotation_signals("1mo")

        summary = {
            "performance_1m": perf_1m,
            "performance_3m": perf_3m,
            "rotation_signals": signals,
        }
        return summary
