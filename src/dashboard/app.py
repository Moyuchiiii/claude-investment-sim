"""投資シミュレーター ダッシュボード"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import yaml
from datetime import datetime

from src.db.repository import (
    PortfolioRepository, HoldingRepository, TradeRepository,
    PerformanceRepository, LearningLogRepository
)
from src.data.fetcher import StockFetcher

CONFIG_PATH = Path(__file__).parent.parent.parent / "config.yaml"

def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)

# ページ設定
st.set_page_config(
    page_title="投資シミュレーター",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Claude 投資シミュレーター")
st.caption("Claude Code による自律投資シミュレーション")

# リポジトリ初期化
portfolio_repo = PortfolioRepository()
holding_repo = HoldingRepository()
trade_repo = TradeRepository()
performance_repo = PerformanceRepository()
learning_repo = LearningLogRepository()
fetcher = StockFetcher()
config = load_config()

# サイドバー
st.sidebar.header("設定")
days_range = st.sidebar.slider("表示期間（日）", 7, 90, 30)

# メインコンテンツ
portfolio = portfolio_repo.get()

if not portfolio:
    st.warning("ポートフォリオが初期化されていません。`python scripts/setup_db.py` を実行してください。")
    st.stop()

# === 概要セクション ===
holdings = holding_repo.get_all()
symbols = [h.symbol for h in holdings]
prices = fetcher.get_multiple_prices(symbols) if symbols else {}

holdings_value = sum(
    h.quantity * (prices.get(h.symbol) or h.avg_cost)
    for h in holdings
)
total_value = portfolio.cash + holdings_value
initial_cash = config["portfolio"]["initial_cash"]
total_return = (total_value / initial_cash - 1) * 100

col1, col2, col3, col4 = st.columns(4)
col1.metric("総資産", f"¥{total_value:,.0f}", f"{total_return:+.2f}%")
col2.metric("現金", f"¥{portfolio.cash:,.0f}")
col3.metric("保有評価額", f"¥{holdings_value:,.0f}")
col4.metric("保有銘柄数", f"{len(holdings)}銘柄")

st.divider()

# === タブ構成 ===
tab1, tab2, tab3, tab4 = st.tabs(["📊 パフォーマンス", "💼 ポートフォリオ", "📝 取引履歴", "🧠 学習ログ"])

# --- パフォーマンスタブ ---
with tab1:
    performance = performance_repo.get_history(days=days_range)

    if performance:
        perf_df = pd.DataFrame([
            {
                "日付": p.date,
                "総資産": p.total_value,
                "現金": p.cash,
                "含み損益": p.unrealized_pnl or 0,
                "日次リターン": p.daily_return or 0
            }
            for p in reversed(performance)
        ])

        # 資産推移グラフ
        fig_value = go.Figure()
        fig_value.add_trace(go.Scatter(
            x=perf_df["日付"], y=perf_df["総資産"],
            mode="lines+markers", name="総資産",
            line=dict(color="#2196F3", width=2)
        ))
        fig_value.add_hline(
            y=initial_cash, line_dash="dash",
            line_color="gray", annotation_text="初期資金"
        )
        fig_value.update_layout(
            title="資産推移",
            xaxis_title="日付", yaxis_title="金額（円）",
            template="plotly_dark"
        )
        st.plotly_chart(fig_value, use_container_width=True)

        # 日次リターングラフ
        if "日次リターン" in perf_df.columns:
            colors = ["#4CAF50" if r >= 0 else "#F44336" for r in perf_df["日次リターン"]]
            fig_return = go.Figure()
            fig_return.add_trace(go.Bar(
                x=perf_df["日付"], y=perf_df["日次リターン"],
                marker_color=colors, name="日次リターン"
            ))
            fig_return.update_layout(
                title="日次リターン（%）",
                xaxis_title="日付", yaxis_title="リターン（%）",
                template="plotly_dark"
            )
            st.plotly_chart(fig_return, use_container_width=True)
    else:
        st.info("パフォーマンスデータがまだありません。売買サイクルを実行してください。")

# --- ポートフォリオタブ ---
with tab2:
    if holdings:
        holdings_data = []
        for h in holdings:
            current_price = prices.get(h.symbol) or h.avg_cost
            market_value = h.quantity * current_price
            unrealized_pnl = market_value - (h.quantity * h.avg_cost)
            return_pct = (current_price / h.avg_cost - 1) * 100
            holdings_data.append({
                "銘柄": h.symbol,
                "数量": h.quantity,
                "平均取得単価": f"¥{h.avg_cost:,.0f}",
                "現在価格": f"¥{current_price:,.0f}",
                "評価額": f"¥{market_value:,.0f}",
                "含み損益": f"¥{unrealized_pnl:+,.0f}",
                "リターン": f"{return_pct:+.1f}%"
            })

        st.dataframe(pd.DataFrame(holdings_data), use_container_width=True, hide_index=True)

        # ポートフォリオ構成円グラフ
        pie_data = [{"銘柄": "現金", "金額": portfolio.cash}]
        for h in holdings:
            current_price = prices.get(h.symbol) or h.avg_cost
            pie_data.append({"銘柄": h.symbol, "金額": h.quantity * current_price})

        fig_pie = px.pie(
            pd.DataFrame(pie_data), values="金額", names="銘柄",
            title="ポートフォリオ構成"
        )
        fig_pie.update_layout(template="plotly_dark")
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("保有銘柄はありません。")

# --- 取引履歴タブ ---
with tab3:
    trades = trade_repo.get_recent(limit=50)
    if trades:
        trades_data = []
        for t in trades:
            trades_data.append({
                "日時": t.executed_at[:16] if t.executed_at else "",
                "銘柄": t.symbol,
                "売買": t.action,
                "数量": t.quantity,
                "価格": f"¥{t.price:,.0f}",
                "金額": f"¥{t.total_amount:,.0f}",
                "確信度": f"{t.confidence:.0%}" if t.confidence else "-",
                "理由": (t.reasoning or "")[:50]
            })
        st.dataframe(pd.DataFrame(trades_data), use_container_width=True, hide_index=True)

        # 売買統計
        buy_count = sum(1 for t in trades if t.action == "BUY")
        sell_count = sum(1 for t in trades if t.action == "SELL")
        col1, col2, col3 = st.columns(3)
        col1.metric("総取引数", len(trades))
        col2.metric("買い", buy_count)
        col3.metric("売り", sell_count)
    else:
        st.info("取引履歴はありません。")

# --- 学習ログタブ ---
with tab4:
    lessons = learning_repo.get_lessons(limit=30)
    if lessons:
        for l in lessons:
            icon = "✅" if l.outcome == "WIN" else "❌" if l.outcome == "LOSS" else "⏸️"
            with st.expander(f"{icon} [{l.outcome}] {l.lesson or '教訓なし'} — {l.created_at[:10] if l.created_at else ''}"):
                if l.profit_loss is not None:
                    st.write(f"損益: ¥{l.profit_loss:+,.0f}")
                if l.strategy_adjustment:
                    st.write(f"戦略調整: {l.strategy_adjustment}")
                if l.trade_id:
                    st.write(f"取引ID: {l.trade_id}")

        # 勝敗統計
        wins = sum(1 for l in lessons if l.outcome == "WIN")
        losses = sum(1 for l in lessons if l.outcome == "LOSS")
        total = wins + losses
        win_rate = (wins / total * 100) if total > 0 else 0

        st.divider()
        col1, col2, col3 = st.columns(3)
        col1.metric("勝率", f"{win_rate:.0f}%")
        col2.metric("勝ち", wins)
        col3.metric("負け", losses)
    else:
        st.info("学習ログはまだありません。売買サイクルを実行してデータを蓄積してください。")

# フッター
st.divider()
st.caption(f"最終更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Claude Code 投資シミュレーター v1.0")
