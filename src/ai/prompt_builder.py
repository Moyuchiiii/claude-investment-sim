"""売買判断用プロンプトを構築"""
import json
from datetime import datetime

class PromptBuilder:
    """Claude CLIに渡すプロンプトを組み立てる"""

    def build_trading_prompt(self, symbol: str, market_data: dict,
                              indicators: dict, signals: list[str],
                              portfolio_status: dict, lessons: list[dict],
                              recent_trades: list[dict]) -> str:
        """売買判断プロンプトを生成"""

        lessons_text = "まだ教訓はありません（取引開始直後）"
        if lessons:
            lessons_text = "\n".join([
                f"- [{l.get('outcome', '?')}] {l.get('lesson', '記録なし')} "
                f"(損益: {l.get('profit_loss', 0):+,.0f}円)"
                for l in lessons[:10]
            ])

        recent_trades_text = "過去の取引はありません"
        if recent_trades:
            recent_trades_text = "\n".join([
                f"- {t.get('executed_at', '?')[:10]} {t.get('action', '?')} {t.get('symbol', '?')} "
                f"x{t.get('quantity', 0)} @{t.get('price', 0):,.0f}円 "
                f"(確信度: {t.get('confidence', 0):.0%})"
                for t in recent_trades[:10]
            ])

        prompt = f"""あなたは投資判断AIです。以下の情報をもとに、この銘柄の売買判断を行ってください。

## 対象銘柄: {symbol}
## 現在日時: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## 市場データ
{json.dumps(market_data, indent=2, ensure_ascii=False, default=str)}

## テクニカル指標
{json.dumps(indicators, indent=2, ensure_ascii=False, default=str)}

## テクニカルシグナル
{chr(10).join(f'- {s}' for s in signals)}

## 現在のポートフォリオ
- 現金: {portfolio_status.get('cash', 0):,.0f}円
- 総資産: {portfolio_status.get('total_value', 0):,.0f}円
- 保有銘柄数: {portfolio_status.get('holdings_count', 0)}
- 総リターン: {portfolio_status.get('total_return_pct', 0):+.2f}%

## この銘柄の保有状況
{self._format_holding(symbol, portfolio_status)}

## 過去の教訓（学習済み）
{lessons_text}

## 直近の取引履歴
{recent_trades_text}

## 判断ルール
- 確信度が0.6未満の場合はHOLDにする
- 1銘柄への投資は総資産の20%まで
- 損切りライン: -5%、利確ライン: +15%
- 短期的なノイズに惑わされず、トレンドとファンダメンタルズを重視する

## 出力形式
必ず以下のJSON形式のみで回答してください。説明文は不要です。
```json
{{
  "action": "BUY または SELL または HOLD",
  "quantity": 数量（HOLDの場合は0）,
  "confidence": 0.0から1.0の確信度,
  "reasoning": "判断理由を日本語で簡潔に"
}}
```"""
        return prompt

    def _format_holding(self, symbol: str, portfolio_status: dict) -> str:
        """保有状況をフォーマット"""
        holdings = portfolio_status.get("holdings", [])
        for h in holdings:
            if h["symbol"] == symbol:
                return (
                    f"- 保有数: {h['quantity']}株\n"
                    f"- 平均取得単価: {h['avg_cost']:,.0f}円\n"
                    f"- 現在価格: {h['current_price']:,.0f}円\n"
                    f"- 含み損益: {h['unrealized_pnl']:+,.0f}円 ({h['return_pct']:+.1f}%)"
                )
        return "未保有"

    def build_review_prompt(self, trades: list[dict], performance: list[dict]) -> str:
        """週次レビュー用プロンプトを生成"""
        trades_text = "\n".join([
            f"- {t.get('executed_at', '?')[:10]} {t.get('action', '?')} {t.get('symbol', '?')} "
            f"x{t.get('quantity', 0)} @{t.get('price', 0):,.0f}円 "
            f"理由: {t.get('reasoning', '不明')}"
            for t in trades
        ]) or "取引なし"

        perf_text = "\n".join([
            f"- {p.get('date', '?')}: 総資産 {p.get('total_value', 0):,.0f}円 "
            f"(日次: {p.get('daily_return', 0):+.2f}%)"
            for p in performance
        ]) or "記録なし"

        return f"""あなたは投資パフォーマンスのレビューアーです。
以下の取引履歴とパフォーマンスを分析し、改善点を提案してください。

## 期間の取引
{trades_text}

## パフォーマンス推移
{perf_text}

## 出力形式
必ず以下のJSON形式のみで回答してください。
```json
{{
  "win_rate": 勝率（0-1）,
  "lessons": ["教訓1", "教訓2", ...],
  "strategy_adjustments": ["調整1", "調整2", ...],
  "risk_assessment": "リスク評価コメント",
  "overall_grade": "A/B/C/D/Fの評価"
}}
```"""
