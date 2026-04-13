"""決算データ・業績情報の取得"""
import yfinance as yf
from typing import Optional


class FundamentalData:
    """yfinanceからファンダメンタルズデータを取得"""

    def get_fundamentals(self, symbol: str) -> dict:
        """銘柄のファンダメンタルズ情報を取得"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info or {}

            # 基本バリュエーション
            fundamentals = {
                "per": info.get("trailingPE"),           # PER（株価収益率）
                "pbr": info.get("priceToBook"),          # PBR（株価純資産倍率）
                "eps": info.get("trailingEps"),          # EPS（1株利益）
                "dividend_yield": info.get("dividendYield"),  # 配当利回り
                "market_cap": info.get("marketCap"),     # 時価総額
                "revenue": info.get("totalRevenue"),     # 売上高
                "profit_margin": info.get("profitMargins"),  # 利益率
                "roe": info.get("returnOnEquity"),       # ROE
                "debt_to_equity": info.get("debtToEquity"),  # 負債比率
                "current_ratio": info.get("currentRatio"),   # 流動比率
                "free_cashflow": info.get("freeCashflow"),   # フリーキャッシュフロー
                "sector": info.get("sector"),            # セクター
                "industry": info.get("industry"),        # 業種
            }

            # None値を除去して返す
            return {k: v for k, v in fundamentals.items() if v is not None}

        except Exception as e:
            return {"error": f"ファンダメンタルズ取得失敗: {e}"}

    def get_earnings_history(self, symbol: str) -> list[dict]:
        """四半期決算の履歴を取得"""
        try:
            ticker = yf.Ticker(symbol)
            earnings = ticker.quarterly_earnings
            if earnings is None or earnings.empty:
                return []

            result = []
            for date_idx, row in earnings.iterrows():
                result.append({
                    "period": str(date_idx),
                    "revenue": float(row.get("Revenue", 0)) if "Revenue" in row else None,
                    "earnings": float(row.get("Earnings", 0)) if "Earnings" in row else None,
                })
            return result

        except Exception as e:
            return []

    def get_valuation_signal(self, fundamentals: dict) -> list[str]:
        """ファンダメンタルズからシグナルを生成"""
        signals = []

        per = fundamentals.get("per")
        if per is not None:
            if per < 10:
                signals.append(f"割安シグナル: PER {per:.1f}（低PER）")
            elif per > 30:
                signals.append(f"割高警告: PER {per:.1f}（高PER）")

        pbr = fundamentals.get("pbr")
        if pbr is not None:
            if pbr < 1.0:
                signals.append(f"割安シグナル: PBR {pbr:.2f}（解散価値以下）")
            elif pbr > 5.0:
                signals.append(f"割高警告: PBR {pbr:.2f}")

        roe = fundamentals.get("roe")
        if roe is not None:
            if roe > 0.15:
                signals.append(f"高収益: ROE {roe:.1%}")
            elif roe < 0.05:
                signals.append(f"低収益: ROE {roe:.1%}")

        div_yield = fundamentals.get("dividend_yield")
        if div_yield is not None:
            if div_yield > 0.03:
                signals.append(f"高配当: 利回り {div_yield:.1%}")

        profit_margin = fundamentals.get("profit_margin")
        if profit_margin is not None:
            if profit_margin > 0.15:
                signals.append(f"高利益率: {profit_margin:.1%}")
            elif profit_margin < 0.03:
                signals.append(f"低利益率: {profit_margin:.1%}")

        debt_ratio = fundamentals.get("debt_to_equity")
        if debt_ratio is not None:
            if debt_ratio > 200:
                signals.append(f"高負債警告: D/E比率 {debt_ratio:.0f}%")

        return signals
