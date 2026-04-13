"""投資シミュレーター ダッシュボード — Trading Terminal Edition"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import pandas as pd
import yaml
import ta as ta_lib
from datetime import datetime

from src.db.repository import (
    PortfolioRepository, HoldingRepository, TradeRepository,
    PerformanceRepository, LearningLogRepository
)
from src.data.fetcher import StockFetcher
from src.data.indicators import TechnicalIndicators

CONFIG_PATH = Path(__file__).parent.parent.parent / "config.yaml"

def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)

# 銘柄名マッピング
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
}

# ページ設定
st.set_page_config(
    page_title="Claude Trading Terminal",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# カスタムCSS — トレーディングターミナル風
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700&family=Noto+Sans+JP:wght@300;400;500;700&display=swap');

    /* ベーステーマ */
    .stApp {
        background: #0a0e17;
        color: #c8d6e5;
    }

    /* ヘッダー */
    .terminal-header {
        background: linear-gradient(135deg, #0d1321 0%, #1a1f35 100%);
        border: 1px solid rgba(0, 212, 170, 0.15);
        border-radius: 8px;
        padding: 20px 28px;
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .terminal-title {
        font-family: 'JetBrains Mono', monospace;
        font-size: 22px;
        font-weight: 700;
        color: #00d4aa;
        letter-spacing: 2px;
    }
    .terminal-subtitle {
        font-family: 'Noto Sans JP', sans-serif;
        font-size: 12px;
        color: #5a6a7a;
        margin-top: 4px;
    }
    .terminal-status {
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px;
        color: #00d4aa;
        background: rgba(0, 212, 170, 0.08);
        padding: 4px 12px;
        border-radius: 4px;
        border: 1px solid rgba(0, 212, 170, 0.2);
    }

    /* メトリクスカード */
    .metric-card {
        background: linear-gradient(180deg, #111827 0%, #0d1117 100%);
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 16px 20px;
        text-align: center;
    }
    .metric-label {
        font-family: 'Noto Sans JP', sans-serif;
        font-size: 11px;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-bottom: 6px;
    }
    .metric-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 24px;
        font-weight: 700;
        color: #e2e8f0;
    }
    .metric-delta-up {
        font-family: 'JetBrains Mono', monospace;
        font-size: 13px;
        color: #00d4aa;
        margin-top: 4px;
    }
    .metric-delta-down {
        font-family: 'JetBrains Mono', monospace;
        font-size: 13px;
        color: #ef4444;
        margin-top: 4px;
    }

    /* サイドバー */
    section[data-testid="stSidebar"] {
        background: #0d1117 !important;
        border-right: 1px solid #1e293b !important;
    }
    section[data-testid="stSidebar"] .stMarkdown h1,
    section[data-testid="stSidebar"] .stMarkdown h2,
    section[data-testid="stSidebar"] .stMarkdown h3 {
        font-family: 'JetBrains Mono', monospace !important;
        color: #00d4aa !important;
        font-size: 14px !important;
        letter-spacing: 2px !important;
    }

    /* 銘柄リストカード */
    .watchlist-item {
        background: #111827;
        border: 1px solid #1e293b;
        border-radius: 6px;
        padding: 10px 14px;
        margin-bottom: 6px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        cursor: pointer;
        transition: border-color 0.2s;
    }
    .watchlist-item:hover {
        border-color: #00d4aa;
    }
    .watchlist-symbol {
        font-family: 'JetBrains Mono', monospace;
        font-size: 13px;
        font-weight: 600;
        color: #e2e8f0;
    }
    .watchlist-name {
        font-family: 'Noto Sans JP', sans-serif;
        font-size: 10px;
        color: #64748b;
    }
    .watchlist-price {
        font-family: 'JetBrains Mono', monospace;
        font-size: 13px;
        font-weight: 500;
        text-align: right;
    }
    .price-up { color: #00d4aa; }
    .price-down { color: #ef4444; }
    .price-flat { color: #64748b; }

    /* シグナルバッジ */
    .signal-buy {
        background: rgba(0, 212, 170, 0.12);
        color: #00d4aa;
        border: 1px solid rgba(0, 212, 170, 0.3);
        padding: 6px 14px;
        border-radius: 4px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 12px;
        margin: 4px 0;
    }
    .signal-sell {
        background: rgba(239, 68, 68, 0.12);
        color: #ef4444;
        border: 1px solid rgba(239, 68, 68, 0.3);
        padding: 6px 14px;
        border-radius: 4px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 12px;
        margin: 4px 0;
    }
    .signal-neutral {
        background: rgba(100, 116, 139, 0.12);
        color: #94a3b8;
        border: 1px solid rgba(100, 116, 139, 0.3);
        padding: 6px 14px;
        border-radius: 4px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 12px;
        margin: 4px 0;
    }

    /* Streamlitデフォルト上書き */
    .stTabs [data-baseweb="tab-list"] {
        background: #111827;
        border-radius: 8px;
        padding: 4px;
        gap: 0;
        border: 1px solid #1e293b;
    }
    .stTabs [data-baseweb="tab"] {
        font-family: 'JetBrains Mono', monospace;
        font-size: 12px;
        letter-spacing: 0.5px;
        color: #64748b;
        border-radius: 6px;
        padding: 8px 16px;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(0, 212, 170, 0.1) !important;
        color: #00d4aa !important;
        border: 1px solid rgba(0, 212, 170, 0.3) !important;
    }
    .stDataFrame {
        border: 1px solid #1e293b;
        border-radius: 8px;
    }

    /* メトリクスウィジェット上書き */
    [data-testid="stMetric"] {
        background: linear-gradient(180deg, #111827 0%, #0d1117 100%);
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 16px;
    }
    [data-testid="stMetricLabel"] {
        font-family: 'Noto Sans JP', sans-serif !important;
        color: #64748b !important;
        font-size: 12px !important;
    }
    [data-testid="stMetricValue"] {
        font-family: 'JetBrains Mono', monospace !important;
        color: #e2e8f0 !important;
    }
    [data-testid="stMetricDelta"] {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* セクション区切り */
    .section-divider {
        border: none;
        border-top: 1px solid #1e293b;
        margin: 24px 0;
    }

    /* フッター */
    .terminal-footer {
        font-family: 'JetBrains Mono', monospace;
        font-size: 10px;
        color: #334155;
        text-align: center;
        padding: 16px;
        border-top: 1px solid #1e293b;
        margin-top: 32px;
    }

    /* セレクトボックス・スライダー */
    .stSelectbox label, .stSlider label {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 11px !important;
        color: #64748b !important;
        letter-spacing: 1px;
        text-transform: uppercase;
    }
</style>
""", unsafe_allow_html=True)

# Plotlyチャートの共通テーマ
CHART_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="#0a0e17",
    font=dict(family="JetBrains Mono, monospace", color="#94a3b8", size=11),
    xaxis=dict(
        gridcolor="#1e293b", zerolinecolor="#1e293b",
        showgrid=True, gridwidth=1
    ),
    yaxis=dict(
        gridcolor="#1e293b", zerolinecolor="#1e293b",
        showgrid=True, gridwidth=1
    ),
    margin=dict(l=0, r=0, t=40, b=0),
    legend=dict(
        bgcolor="rgba(0,0,0,0)", bordercolor="#1e293b",
        font=dict(size=10)
    ),
)

# リポジトリ初期化
portfolio_repo = PortfolioRepository()
holding_repo = HoldingRepository()
trade_repo = TradeRepository()
performance_repo = PerformanceRepository()
learning_repo = LearningLogRepository()
fetcher = StockFetcher()
indicators_calc = TechnicalIndicators()
config = load_config()

# ポートフォリオ取得
portfolio = portfolio_repo.get()

if not portfolio:
    st.markdown("""
    <div style="text-align:center; padding:60px; color:#64748b;">
        <div style="font-family:'JetBrains Mono'; font-size:48px; color:#1e293b;">[ ]</div>
        <div style="margin-top:16px; font-family:'Noto Sans JP'; font-size:14px;">
            ポートフォリオが初期化されていません
        </div>
        <div style="margin-top:8px; font-family:'JetBrains Mono'; font-size:12px; color:#334155;">
            python scripts/setup_db.py
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# 全銘柄リスト（日本株のみ）
all_symbols = []
for market in config["markets"].values():
    if market.get("enabled"):
        all_symbols.extend(market["symbols"])

# セッション状態の初期化
if "selected_symbol" not in st.session_state:
    st.session_state.selected_symbol = all_symbols[0] if all_symbols else None

# === サイドバー ===
with st.sidebar:
    st.markdown("### TERMINAL")
    st.markdown('<div style="font-family:Noto Sans JP; font-size:11px; color:#334155; margin-bottom:16px;">Claude Investment Simulator</div>', unsafe_allow_html=True)

    # session_state と同期したセレクトボックス
    current_index = all_symbols.index(st.session_state.selected_symbol) if st.session_state.selected_symbol in all_symbols else 0
    selected_symbol = st.selectbox(
        "SYMBOL",
        all_symbols,
        index=current_index,
        format_func=lambda s: f"{s}  {SYMBOL_NAMES.get(s, '')}"
    )
    # セレクトボックスの変更を session_state に反映
    if selected_symbol != st.session_state.selected_symbol:
        st.session_state.selected_symbol = selected_symbol
        st.rerun()

    chart_period = st.select_slider(
        "PERIOD",
        options=["1mo", "3mo", "6mo", "1y", "2y"],
        value="3mo"
    )

    st.markdown("---")
    st.markdown("### WATCHLIST")

    # 監視銘柄リスト（クリックで銘柄切り替え）
    st.markdown("""
    <style>
        /* ウォッチリストボタンをカード風に */
        div[data-testid="stSidebar"] .stButton button {
            background: #111827;
            border: 1px solid #1e293b;
            border-radius: 6px;
            padding: 8px 14px;
            width: 100%;
            text-align: left;
            color: #e2e8f0;
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
            margin-bottom: 4px;
            transition: border-color 0.2s;
        }
        div[data-testid="stSidebar"] .stButton button:hover {
            border-color: #00d4aa;
        }
    </style>
    """, unsafe_allow_html=True)

    for sym in all_symbols:
        name = SYMBOL_NAMES.get(sym, "")
        price = fetcher.get_current_price(sym)
        price_str = f"¥{price:,.0f}" if price else "---"
        # 選択中の銘柄はハイライト
        is_selected = sym == st.session_state.selected_symbol
        label = f"{'▶ ' if is_selected else '  '}{sym}  {name}\n{price_str}"
        if st.button(label, key=f"watchlist_{sym}"):
            st.session_state.selected_symbol = sym
            st.rerun()

# session_state から選択銘柄を参照
selected_symbol = st.session_state.selected_symbol

# === ヘッダー ===
st.markdown(f"""
<div class="terminal-header">
    <div>
        <div class="terminal-title">CLAUDE TRADING TERMINAL</div>
        <div class="terminal-subtitle">自律投資シミュレーション v1.0</div>
    </div>
    <div class="terminal-status">LIVE {datetime.now().strftime('%H:%M:%S')}</div>
</div>
""", unsafe_allow_html=True)

# === メトリクスカード ===
holdings = holding_repo.get_all()
holding_symbols = [h.symbol for h in holdings]
prices = fetcher.get_multiple_prices(holding_symbols) if holding_symbols else {}

holdings_value = sum(
    h.quantity * (prices.get(h.symbol) or h.avg_cost)
    for h in holdings
)
total_value = portfolio.cash + holdings_value
initial_cash = config["portfolio"]["initial_cash"]
total_return = (total_value / initial_cash - 1) * 100

col1, col2, col3, col4 = st.columns(4)
with col1:
    delta_class = "metric-delta-up" if total_return >= 0 else "metric-delta-down"
    delta_sign = "+" if total_return >= 0 else ""
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">総資産</div>
        <div class="metric-value">¥{total_value:,.0f}</div>
        <div class="{delta_class}">{delta_sign}{total_return:.2f}%</div>
    </div>
    """, unsafe_allow_html=True)
with col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">現金</div>
        <div class="metric-value">¥{portfolio.cash:,.0f}</div>
        <div class="metric-delta-up">{portfolio.cash / total_value * 100:.0f}%</div>
    </div>
    """, unsafe_allow_html=True)
with col3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">保有評価額</div>
        <div class="metric-value">¥{holdings_value:,.0f}</div>
        <div class="metric-delta-up">{len(holdings)} 銘柄</div>
    </div>
    """, unsafe_allow_html=True)
with col4:
    trades_today = trade_repo.get_recent(limit=100)
    today_str = datetime.now().strftime("%Y-%m-%d")
    today_count = sum(1 for t in trades_today if t.executed_at and t.executed_at.startswith(today_str))
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">本日の取引</div>
        <div class="metric-value">{today_count}</div>
        <div class="metric-delta-up">/ {config['trading']['max_daily_trades']} MAX</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

# === メインチャート（常時表示） ===
if selected_symbol:
    history = fetcher.get_history(selected_symbol, period=chart_period)

    if not history.empty and len(history) > 5:
        symbol_name = SYMBOL_NAMES.get(selected_symbol, selected_symbol)
        current_price = float(history["Close"].iloc[-1])
        prev_price = float(history["Close"].iloc[-2]) if len(history) > 1 else current_price
        price_change = current_price - prev_price
        price_change_pct = (price_change / prev_price) * 100

        # チャートヘッダー
        change_color = "#00d4aa" if price_change >= 0 else "#ef4444"
        change_sign = "+" if price_change >= 0 else ""
        st.markdown(f"""
        <div style="display:flex; align-items:baseline; gap:16px; margin-bottom:8px;">
            <span style="font-family:'JetBrains Mono'; font-size:18px; font-weight:700; color:#e2e8f0;">
                {selected_symbol}
            </span>
            <span style="font-family:'Noto Sans JP'; font-size:13px; color:#64748b;">
                {symbol_name}
            </span>
            <span style="font-family:'JetBrains Mono'; font-size:24px; font-weight:700; color:#e2e8f0;">
                ¥{current_price:,.0f}
            </span>
            <span style="font-family:'JetBrains Mono'; font-size:14px; color:{change_color};">
                {change_sign}{price_change:,.0f} ({change_sign}{price_change_pct:.2f}%)
            </span>
        </div>
        """, unsafe_allow_html=True)

        # ローソク足チャート + 出来高（サブプロット）
        fig = make_subplots(
            rows=2, cols=1, shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.8, 0.2]
        )

        # ローソク足
        fig.add_trace(go.Candlestick(
            x=history.index, open=history["Open"], high=history["High"],
            low=history["Low"], close=history["Close"], name="",
            increasing_line_color="#00d4aa", increasing_fillcolor="#00d4aa",
            decreasing_line_color="#ef4444", decreasing_fillcolor="#ef4444",
            showlegend=False
        ), row=1, col=1)

        # ボリンジャーバンド
        bb_upper = ta_lib.volatility.bollinger_hband(history["Close"])
        bb_lower = ta_lib.volatility.bollinger_lband(history["Close"])
        bb_mid = ta_lib.volatility.bollinger_mavg(history["Close"])

        fig.add_trace(go.Scatter(
            x=history.index, y=bb_upper, name="BB",
            line=dict(color="rgba(0,212,170,0.15)", width=1),
            showlegend=False
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=history.index, y=bb_lower, name="",
            line=dict(color="rgba(0,212,170,0.15)", width=1),
            fill="tonexty", fillcolor="rgba(0,212,170,0.03)",
            showlegend=False
        ), row=1, col=1)

        # SMA
        sma20 = ta_lib.trend.sma_indicator(history["Close"], window=20)
        sma50 = ta_lib.trend.sma_indicator(history["Close"], window=50)
        fig.add_trace(go.Scatter(
            x=history.index, y=sma20, name="SMA20",
            line=dict(color="#f59e0b", width=1, dash="dot")
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=history.index, y=sma50, name="SMA50",
            line=dict(color="#3b82f6", width=1, dash="dot")
        ), row=1, col=1)

        # 出来高
        vol_colors = [
            "#00d4aa" if c >= o else "#ef4444"
            for c, o in zip(history["Close"], history["Open"])
        ]
        fig.add_trace(go.Bar(
            x=history.index, y=history["Volume"],
            marker_color=vol_colors, name="Volume",
            opacity=0.6, showlegend=False
        ), row=2, col=1)

        fig.update_layout(
            **CHART_LAYOUT,
            height=520,
            xaxis_rangeslider_visible=False,
            xaxis2=dict(gridcolor="#1e293b"),
            yaxis2=dict(gridcolor="#1e293b"),
        )
        fig.update_yaxes(title_text="", row=1, col=1)
        fig.update_yaxes(title_text="", row=2, col=1)

        st.plotly_chart(fig, use_container_width=True)

        # RSI + MACD 横並び
        col_rsi, col_macd = st.columns(2)

        with col_rsi:
            rsi = ta_lib.momentum.rsi(history["Close"], window=14)
            fig_rsi = go.Figure()
            fig_rsi.add_trace(go.Scatter(
                x=history.index, y=rsi, name="RSI",
                line=dict(color="#a855f7", width=2),
                fill="tozeroy", fillcolor="rgba(168,85,247,0.05)"
            ))
            fig_rsi.add_hline(y=70, line_dash="dot", line_color="rgba(239,68,68,0.4)")
            fig_rsi.add_hline(y=30, line_dash="dot", line_color="rgba(0,212,170,0.4)")
            fig_rsi.add_hrect(y0=30, y1=70, fillcolor="rgba(255,255,255,0.02)", line_width=0)
            fig_rsi.update_layout(
                **CHART_LAYOUT, height=220,
                title=dict(text="RSI (14)", font=dict(size=12, color="#64748b")),
            )
            fig_rsi.update_yaxes(range=[0, 100], gridcolor="#1e293b")
            st.plotly_chart(fig_rsi, use_container_width=True)

        with col_macd:
            macd_line = ta_lib.trend.macd(history["Close"])
            macd_signal = ta_lib.trend.macd_signal(history["Close"])
            macd_hist = ta_lib.trend.macd_diff(history["Close"])
            macd_colors = ["#00d4aa" if v >= 0 else "#ef4444" for v in macd_hist]

            fig_macd = go.Figure()
            fig_macd.add_trace(go.Bar(
                x=history.index, y=macd_hist, name="Hist",
                marker_color=macd_colors, opacity=0.4, showlegend=False
            ))
            fig_macd.add_trace(go.Scatter(
                x=history.index, y=macd_line, name="MACD",
                line=dict(color="#3b82f6", width=2)
            ))
            fig_macd.add_trace(go.Scatter(
                x=history.index, y=macd_signal, name="Signal",
                line=dict(color="#f59e0b", width=1.5)
            ))
            fig_macd.update_layout(
                **CHART_LAYOUT, height=220,
                title=dict(text="MACD", font=dict(size=12, color="#64748b")),
            )
            st.plotly_chart(fig_macd, use_container_width=True)

        # テクニカル指標 + シグナル
        tech = indicators_calc.calculate_all(history)
        if "error" not in tech:
            signals = indicators_calc.get_signals(tech)

            col_ind, col_sig = st.columns([3, 2])
            with col_ind:
                ic1, ic2, ic3, ic4, ic5 = st.columns(5)
                rsi_val = tech["rsi_14"]
                rsi_color = "#ef4444" if rsi_val > 70 else "#00d4aa" if rsi_val < 30 else "#94a3b8"
                ic1.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">RSI</div>
                    <div class="metric-value" style="color:{rsi_color}; font-size:20px;">{rsi_val:.1f}</div>
                </div>""", unsafe_allow_html=True)
                ic2.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">MACD</div>
                    <div class="metric-value" style="font-size:20px;">{tech['macd']:.1f}</div>
                </div>""", unsafe_allow_html=True)
                ic3.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">ADX</div>
                    <div class="metric-value" style="font-size:20px;">{tech['adx_14']:.1f}</div>
                </div>""", unsafe_allow_html=True)
                ic4.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">ATR</div>
                    <div class="metric-value" style="font-size:20px;">{tech['atr_14']:.0f}</div>
                </div>""", unsafe_allow_html=True)
                change_5d = tech.get("price_change_5d")
                c5_color = "#00d4aa" if change_5d and change_5d >= 0 else "#ef4444"
                ic5.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">5D CHG</div>
                    <div class="metric-value" style="color:{c5_color}; font-size:20px;">{change_5d:+.1f}%</div>
                </div>""", unsafe_allow_html=True)

            with col_sig:
                for s in signals:
                    if "買い" in s or "上昇" in s:
                        st.markdown(f'<div class="signal-buy">{s}</div>', unsafe_allow_html=True)
                    elif "売り" in s or "下降" in s:
                        st.markdown(f'<div class="signal-sell">{s}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="signal-neutral">{s}</div>', unsafe_allow_html=True)

    else:
        st.warning(f"{selected_symbol} のデータを取得できませんでした。")

st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

# === 下部タブ ===
tab1, tab2, tab3, tab4 = st.tabs(["PORTFOLIO", "TRADES", "PERFORMANCE", "LEARNING"])

with tab1:
    if holdings:
        holdings_data = []
        for h in holdings:
            current_price = prices.get(h.symbol) or h.avg_cost
            market_value = h.quantity * current_price
            unrealized_pnl = market_value - (h.quantity * h.avg_cost)
            return_pct = (current_price / h.avg_cost - 1) * 100
            holdings_data.append({
                "銘柄": f"{h.symbol} {SYMBOL_NAMES.get(h.symbol, '')}",
                "数量": h.quantity,
                "取得単価": f"¥{h.avg_cost:,.0f}",
                "現在価格": f"¥{current_price:,.0f}",
                "評価額": f"¥{market_value:,.0f}",
                "損益": f"¥{unrealized_pnl:+,.0f}",
                "収益率": f"{return_pct:+.1f}%"
            })
        st.dataframe(pd.DataFrame(holdings_data), use_container_width=True, hide_index=True)

        # 構成比
        pie_data = [{"name": "Cash", "value": portfolio.cash}]
        for h in holdings:
            cp = prices.get(h.symbol) or h.avg_cost
            pie_data.append({"name": h.symbol, "value": h.quantity * cp})
        fig_pie = go.Figure(go.Pie(
            labels=[d["name"] for d in pie_data],
            values=[d["value"] for d in pie_data],
            hole=0.55,
            marker=dict(colors=["#1e293b", "#00d4aa", "#3b82f6", "#f59e0b", "#a855f7",
                                "#ef4444", "#06b6d4", "#84cc16", "#ec4899", "#f97316", "#6366f1"]),
            textfont=dict(family="JetBrains Mono", size=11),
        ))
        fig_pie.update_layout(**CHART_LAYOUT, height=300, showlegend=True)
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.markdown('<div style="text-align:center; padding:40px; color:#334155; font-family:JetBrains Mono;">NO POSITIONS</div>', unsafe_allow_html=True)

with tab2:
    trades = trade_repo.get_recent(limit=50)
    if trades:
        trades_data = []
        for t in trades:
            action_color = "#00d4aa" if t.action == "BUY" else "#ef4444"
            trades_data.append({
                "日時": t.executed_at[:16] if t.executed_at else "",
                "銘柄": f"{t.symbol} {SYMBOL_NAMES.get(t.symbol, '')}",
                "売買": t.action,
                "数量": t.quantity,
                "価格": f"¥{t.price:,.0f}",
                "金額": f"¥{t.total_amount:,.0f}",
                "確信度": f"{t.confidence:.0%}" if t.confidence else "-",
                "理由": (t.reasoning or "")[:60]
            })
        st.dataframe(pd.DataFrame(trades_data), use_container_width=True, hide_index=True)

        buy_count = sum(1 for t in trades if t.action == "BUY")
        sell_count = sum(1 for t in trades if t.action == "SELL")
        tc1, tc2, tc3 = st.columns(3)
        tc1.metric("総取引", len(trades))
        tc2.metric("BUY", buy_count)
        tc3.metric("SELL", sell_count)
    else:
        st.markdown('<div style="text-align:center; padding:40px; color:#334155; font-family:JetBrains Mono;">NO TRADES YET</div>', unsafe_allow_html=True)

with tab3:
    days_range = 30
    performance = performance_repo.get_history(days=days_range)
    if performance:
        perf_df = pd.DataFrame([
            {"date": p.date, "value": p.total_value, "cash": p.cash, "return": p.daily_return or 0}
            for p in reversed(performance)
        ])

        fig_perf = go.Figure()
        fig_perf.add_trace(go.Scatter(
            x=perf_df["date"], y=perf_df["value"], name="NAV",
            line=dict(color="#00d4aa", width=2),
            fill="tozeroy", fillcolor="rgba(0,212,170,0.05)"
        ))
        fig_perf.add_hline(y=initial_cash, line_dash="dot", line_color="#334155",
                           annotation_text="Initial", annotation_font_color="#334155")
        fig_perf.update_layout(**CHART_LAYOUT, height=300,
                               title=dict(text="NAV HISTORY", font=dict(size=12, color="#64748b")))
        st.plotly_chart(fig_perf, use_container_width=True)

        # 日次リターン
        ret_colors = ["#00d4aa" if r >= 0 else "#ef4444" for r in perf_df["return"]]
        fig_ret = go.Figure(go.Bar(
            x=perf_df["date"], y=perf_df["return"], marker_color=ret_colors
        ))
        fig_ret.update_layout(**CHART_LAYOUT, height=200,
                              title=dict(text="DAILY RETURNS %", font=dict(size=12, color="#64748b")))
        st.plotly_chart(fig_ret, use_container_width=True)
    else:
        st.markdown('<div style="text-align:center; padding:40px; color:#334155; font-family:JetBrains Mono;">NO PERFORMANCE DATA</div>', unsafe_allow_html=True)

with tab4:
    lessons = learning_repo.get_lessons(limit=30)
    if lessons:
        wins = sum(1 for l in lessons if l.outcome == "WIN")
        losses = sum(1 for l in lessons if l.outcome == "LOSS")
        total = wins + losses
        win_rate = (wins / total * 100) if total > 0 else 0

        lc1, lc2, lc3 = st.columns(3)
        lc1.metric("Win Rate", f"{win_rate:.0f}%")
        lc2.metric("Wins", wins)
        lc3.metric("Losses", losses)

        for l in lessons:
            icon = "+" if l.outcome == "WIN" else "-" if l.outcome == "LOSS" else "="
            icon_color = "#00d4aa" if l.outcome == "WIN" else "#ef4444" if l.outcome == "LOSS" else "#64748b"
            with st.expander(f"[{l.outcome}] {l.lesson or 'No lesson'} — {l.created_at[:10] if l.created_at else ''}"):
                if l.profit_loss is not None:
                    st.code(f"P&L: ¥{l.profit_loss:+,.0f}")
                if l.strategy_adjustment:
                    st.code(f"Adjustment: {l.strategy_adjustment}")
    else:
        st.markdown('<div style="text-align:center; padding:40px; color:#334155; font-family:JetBrains Mono;">NO LEARNING DATA YET</div>', unsafe_allow_html=True)

# フッター
st.markdown(f"""
<div class="terminal-footer">
    CLAUDE TRADING TERMINAL v1.0 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | SIMULATION ONLY
</div>
""", unsafe_allow_html=True)
