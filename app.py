"""
app.py  —  Kite Trader Dashboard
Run: streamlit run app.py
"""

import os
import time
import sys
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from datetime import datetime, timedelta
from dotenv import load_dotenv, set_key

# ── path setup ────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
load_dotenv()

from core.kite_manager import get_kite, generate_login_url, complete_login, get_profile
from core.data import fetch_historical, search_instruments, get_ltp, INTERVAL_MAP
from strategies.drop_rise import run_backtest, LiveStrategy

ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")

# ── page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Kite Trader",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Sora:wght@300;600;800&display=swap');

  html, body, [class*="css"] { font-family: 'Sora', sans-serif; }
  code, .stCode { font-family: 'JetBrains Mono', monospace; }

  .main { background: #0d1117; }
  .stApp { background: #0d1117; color: #e6edf3; }

  /* sidebar */
  section[data-testid="stSidebar"] {
    background: #161b22 !important;
    border-right: 1px solid #21262d;
  }

  /* metric cards */
  [data-testid="stMetric"] {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 12px;
    padding: 16px 20px;
  }
  [data-testid="stMetricValue"] { font-size: 1.6rem !important; font-weight: 800; }

  /* buttons */
  .stButton > button {
    background: #238636 !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    transition: all .2s;
  }
  .stButton > button:hover { background: #2ea043 !important; transform: translateY(-1px); }

  /* tabs */
  .stTabs [data-baseweb="tab"] {
    font-weight: 600;
    font-size: 0.9rem;
    letter-spacing: 0.03em;
  }

  /* trade log */
  .trade-log {
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 8px;
    padding: 12px 16px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    max-height: 250px;
    overflow-y: auto;
    color: #8b949e;
  }
  .trade-log .buy  { color: #3fb950; }
  .trade-log .sell { color: #f85149; }

  .badge-paper { background:#1f6feb22; color:#58a6ff; border:1px solid #1f6feb; border-radius:20px; padding:2px 10px; font-size:0.75rem; font-weight:700; }
  .badge-live  { background:#da363322; color:#f85149; border:1px solid #da3633; border-radius:20px; padding:2px 10px; font-size:0.75rem; font-weight:700; }
  .badge-back  { background:#38841422; color:#3fb950; border:1px solid #388414; border-radius:20px; padding:2px 10px; font-size:0.75rem; font-weight:700; }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ═══════════════════════════════════════════════════════════════════════════════
if "live_strategy" not in st.session_state:
    st.session_state.live_strategy = None
if "live_running" not in st.session_state:
    st.session_state.live_running = False
if "paper_strategy" not in st.session_state:
    st.session_state.paper_strategy = None


# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 📈 Kite Trader")
    st.markdown("---")

    kite = get_kite()
    if kite:
        profile = get_profile(kite)
        if "error" not in profile:
            st.success(f"✅ {profile.get('user_name', 'Connected')}")
            st.caption(f"{profile.get('email','')}")
            if st.button("Logout", use_container_width=True):
                set_key(ENV_PATH, "KITE_ACCESS_TOKEN", "")
                os.environ["KITE_ACCESS_TOKEN"] = ""
                st.rerun()
        else:
            st.warning("Token expired — please re-login")
            kite = None
    else:
        st.warning("⚠️ Not connected to Kite")

    st.markdown("---")
    page = st.radio(
        "Navigate",
        ["🔐 Connect", "📊 Backtest", "🤖 Paper Trade", "⚡ Live Trade", "📋 Settings"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.caption("Strategy: **Drop & Rise**")
    st.caption("10% drop → BUY · 5% rise → SELL")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: CONNECT
# ═══════════════════════════════════════════════════════════════════════════════
if page == "🔐 Connect":
    st.title("🔐 Connect to Zerodha Kite")
    st.markdown("---")

    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.subheader("Step 1 — API Credentials")
        api_key = st.text_input("API Key", value=os.getenv("KITE_API_KEY", ""), type="password")
        api_secret = st.text_input("API Secret", value=os.getenv("KITE_API_SECRET", ""), type="password")

        if st.button("Save Credentials", use_container_width=True):
            set_key(ENV_PATH, "KITE_API_KEY", api_key)
            set_key(ENV_PATH, "KITE_API_SECRET", api_secret)
            os.environ["KITE_API_KEY"] = api_key
            os.environ["KITE_API_SECRET"] = api_secret
            st.success("Saved!")

    with col2:
        st.subheader("Step 2 — Login")
        login_url = generate_login_url()
        if login_url:
            st.markdown(f"[👉 Click here to login to Kite]({login_url})")
            st.caption("After login, Kite redirects you to a URL like:\n`http://127.0.0.1/?request_token=XXXXXXXX&action=login&status=success`")

            request_token = st.text_input("Paste request_token here")
            if st.button("Complete Login", use_container_width=True):
                if request_token:
                    try:
                        data = complete_login(request_token.strip())
                        st.success(f"✅ Logged in as {data.get('user_name', '')}")
                        st.balloons()
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Login failed: {e}")
        else:
            st.info("Save your API credentials first.")

    if kite:
        st.markdown("---")
        st.success("✅ Already connected! Navigate to Backtest or Paper Trade.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: BACKTEST
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📊 Backtest":
    st.title("📊 Backtest — Drop & Rise Strategy")
    st.markdown('<span class="badge-back">BACKTEST</span>', unsafe_allow_html=True)
    st.markdown("---")

    if not kite:
        st.warning("Connect to Kite first (sidebar → Connect page)")
        st.stop()

    # ── Controls ──────────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    with col1:
        symbol_query = st.text_input("Symbol", value="INFY", placeholder="e.g. RELIANCE, INFY")
        exchange = st.selectbox("Exchange", ["NSE", "BSE", "NFO"])

    with col2:
        drop_pct = st.slider("Buy trigger — Drop %", 1.0, 30.0, 10.0, 0.5)
        rise_pct = st.slider("Sell trigger — Rise %", 1.0, 30.0, 5.0, 0.5)

    with col3:
        interval_label = st.selectbox("Candle interval", list(INTERVAL_MAP.keys()), index=6)
        date_from = st.date_input("From", datetime.today() - timedelta(days=365))
        date_to = st.date_input("To", datetime.today())
        qty = st.number_input("Quantity per trade", 1, 10000, 1)
        capital = st.number_input("Starting capital (₹)", 10000, 10_000_000, 100000, step=10000)

    run_btn = st.button("▶ Run Backtest", use_container_width=True)

    if run_btn:
        with st.spinner("Fetching data and running backtest..."):
            try:
                # Find instrument token
                instruments = search_instruments(kite, symbol_query, exchange)
                exact = [i for i in instruments if i["tradingsymbol"].upper() == symbol_query.upper()]
                if not exact:
                    st.error(f"Symbol '{symbol_query}' not found on {exchange}")
                    st.stop()

                instrument = exact[0]
                token = instrument["instrument_token"]

                df = fetch_historical(
                    kite,
                    token,
                    from_date=datetime.combine(date_from, datetime.min.time()),
                    to_date=datetime.combine(date_to, datetime.max.time()),
                    interval=INTERVAL_MAP[interval_label],
                )

                if df.empty:
                    st.error("No data returned. Check date range / symbol.")
                    st.stop()

                result = run_backtest(
                    df,
                    symbol=symbol_query.upper(),
                    drop_pct=drop_pct,
                    rise_pct=rise_pct,
                    qty=qty,
                    capital=capital,
                )
                st.session_state["bt_result"] = result
                st.session_state["bt_df"] = df
                st.session_state["bt_symbol"] = symbol_query.upper()

            except Exception as e:
                st.error(f"Error: {e}")

    # ── Results ───────────────────────────────────────────────────────────────
    if "bt_result" in st.session_state:
        result = st.session_state["bt_result"]
        df = st.session_state["bt_df"]
        sym = st.session_state["bt_symbol"]

        st.markdown("---")
        st.subheader(f"Results — {sym}")

        # KPIs
        c1, c2, c3, c4, c5 = st.columns(5)
        pnl_color = "normal" if result.total_pnl >= 0 else "inverse"
        c1.metric("Total P&L", f"₹{result.total_pnl:,.0f}", delta=f"{result.total_pnl/capital*100:.1f}%")
        c2.metric("Win Rate", f"{result.win_rate:.1f}%")
        c3.metric("Total Trades", len(result.closed_trades))
        c4.metric("Max Drawdown", f"{result.max_drawdown:.1f}%")
        c5.metric("Sharpe Ratio", f"{result.sharpe:.2f}")

        tab1, tab2, tab3 = st.tabs(["📈 Equity Curve", "🕯 Price + Trades", "📋 Trade Log"])

        with tab1:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=result.equity_curve["datetime"],
                y=result.equity_curve["equity"],
                mode="lines",
                name="Portfolio Value",
                line=dict(color="#3fb950", width=2),
                fill="tozeroy",
                fillcolor="rgba(63,185,80,0.08)",
            ))
            fig.add_hline(y=capital, line_dash="dot", line_color="#8b949e", annotation_text="Initial Capital")
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="#0d1117",
                plot_bgcolor="#0d1117",
                height=400,
                showlegend=False,
                xaxis_title="Date",
                yaxis_title="Portfolio Value (₹)",
            )
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=df["datetime"], y=df["close"],
                mode="lines", name="Close",
                line=dict(color="#58a6ff", width=1.5),
            ))
            # Buy markers
            buys = [(t.buy_time, t.buy_price) for t in result.closed_trades]
            sells = [(t.sell_time, t.sell_price) for t in result.closed_trades if t.sell_price]
            if buys:
                bx, by = zip(*buys)
                fig2.add_trace(go.Scatter(
                    x=list(bx), y=list(by), mode="markers", name="BUY",
                    marker=dict(symbol="triangle-up", size=12, color="#3fb950"),
                ))
            if sells:
                sx, sy = zip(*sells)
                fig2.add_trace(go.Scatter(
                    x=list(sx), y=list(sy), mode="markers", name="SELL",
                    marker=dict(symbol="triangle-down", size=12, color="#f85149"),
                ))
            fig2.update_layout(
                template="plotly_dark",
                paper_bgcolor="#0d1117",
                plot_bgcolor="#0d1117",
                height=400,
                xaxis_title="Date",
                yaxis_title="Price (₹)",
            )
            st.plotly_chart(fig2, use_container_width=True)

        with tab3:
            if result.closed_trades:
                trade_data = [{
                    "Symbol": t.symbol,
                    "Buy Time": t.buy_time.strftime("%Y-%m-%d %H:%M") if t.buy_time else "",
                    "Buy Price": f"₹{t.buy_price:.2f}",
                    "Sell Time": t.sell_time.strftime("%Y-%m-%d %H:%M") if t.sell_time else "",
                    "Sell Price": f"₹{t.sell_price:.2f}" if t.sell_price else "-",
                    "P&L": f"₹{t.pnl:.2f}",
                    "P&L %": f"{t.pnl_pct:.2f}%",
                    "Duration": t.duration,
                } for t in result.closed_trades]
                st.dataframe(pd.DataFrame(trade_data), use_container_width=True, hide_index=True)
            else:
                st.info("No completed trades in this period.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: PAPER TRADE
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🤖 Paper Trade":
    st.title("🤖 Paper Trading — Drop & Rise")
    st.markdown('<span class="badge-paper">PAPER</span> &nbsp; Simulated trades, no real money', unsafe_allow_html=True)
    st.markdown("---")

    if not kite:
        st.warning("Connect to Kite first")
        st.stop()

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Strategy Settings")
        p_symbol = st.text_input("Symbol", "INFY", key="p_sym")
        p_exchange = st.selectbox("Exchange", ["NSE", "BSE"], key="p_exc")
        p_drop = st.slider("Drop % to BUY", 1.0, 30.0, 10.0, 0.5, key="p_drop")
        p_rise = st.slider("Rise % to SELL", 1.0, 30.0, 5.0, 0.5, key="p_rise")
        p_qty = st.number_input("Quantity", 1, 10000, 1, key="p_qty")

        if st.button("🚀 Start Paper Trading", use_container_width=True):
            st.session_state.paper_strategy = LiveStrategy(
                symbol=p_symbol.upper(),
                exchange=p_exchange,
                drop_pct=p_drop,
                rise_pct=p_rise,
                qty=p_qty,
                mode="paper",
                kite=None,
            )
            st.session_state.live_running = True
            st.success("Paper trading started!")

        if st.button("⏹ Stop", use_container_width=True):
            st.session_state.live_running = False

        if st.button("🔄 Reset", use_container_width=True):
            st.session_state.paper_strategy = None
            st.session_state.live_running = False

    with col2:
        if st.session_state.paper_strategy:
            strat = st.session_state.paper_strategy

            # Fetch current LTP
            instrument_str = f"{p_exchange}:{p_symbol.upper()}"
            ltp_data = get_ltp(kite, [instrument_str])
            current_price = ltp_data.get(instrument_str, {}).get("last_price")

            if current_price and st.session_state.live_running:
                action = strat.tick(current_price)

            # Metrics
            m1, m2, m3 = st.columns(3)
            m1.metric("LTP", f"₹{current_price:.2f}" if current_price else "—")
            m2.metric("Total P&L", f"₹{strat.total_pnl:.2f}")
            m3.metric("Day High (tracked)", f"₹{strat.day_high:.2f}" if strat.day_high else "—")

            if strat.open_trade:
                unr = (current_price - strat.open_trade.buy_price) * strat.open_trade.qty if current_price else 0
                st.info(f"📌 Open position: Bought @ ₹{strat.open_trade.buy_price:.2f} | Unrealised: ₹{unr:.2f}")
                target_price = strat.open_trade.buy_price * (1 + strat.rise_pct / 100)
                st.caption(f"Sell target: ₹{target_price:.2f}")

            st.subheader("Trade Log")
            if strat.log:
                log_html = "<div class='trade-log'>"
                for line in reversed(strat.log[-50:]):
                    css = "buy" if "BUY" in line else "sell"
                    log_html += f"<div class='{css}'>{line}</div>"
                log_html += "</div>"
                st.markdown(log_html, unsafe_allow_html=True)
            else:
                st.caption("No activity yet. Waiting for trigger...")

            if strat.trades:
                st.subheader("Closed Trades")
                td = [{
                    "Buy": f"₹{t.buy_price:.2f}",
                    "Sell": f"₹{t.sell_price:.2f}" if t.sell_price else "-",
                    "P&L": f"₹{t.pnl:.2f}",
                    "P&L%": f"{t.pnl_pct:.2f}%",
                    "Duration": t.duration,
                } for t in strat.trades]
                st.dataframe(pd.DataFrame(td), use_container_width=True, hide_index=True)

            if st.session_state.live_running:
                time.sleep(5)
                st.rerun()
        else:
            st.info("Configure your settings and click **Start Paper Trading**.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: LIVE TRADE
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "⚡ Live Trade":
    st.title("⚡ Live Trading — Drop & Rise")
    st.markdown('<span class="badge-live">LIVE</span> &nbsp; ⚠️ Real orders will be placed on your Zerodha account', unsafe_allow_html=True)
    st.markdown("---")

    if not kite:
        st.warning("Connect to Kite first")
        st.stop()

    st.error("⚠️ **LIVE MODE**: Orders are real. Start with smallest quantity possible.")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Strategy Settings")
        l_symbol = st.text_input("Symbol", "INFY", key="l_sym")
        l_exchange = st.selectbox("Exchange", ["NSE", "BSE"], key="l_exc")
        l_drop = st.slider("Drop % to BUY", 1.0, 30.0, 10.0, 0.5, key="l_drop")
        l_rise = st.slider("Rise % to SELL", 1.0, 30.0, 5.0, 0.5, key="l_rise")
        l_qty = st.number_input("Quantity", 1, 10000, 1, key="l_qty")

        confirm = st.checkbox("I understand this places REAL orders")

        if confirm and st.button("🔴 Start Live Trading", use_container_width=True):
            st.session_state.live_strategy = LiveStrategy(
                symbol=l_symbol.upper(),
                exchange=l_exchange,
                drop_pct=l_drop,
                rise_pct=l_rise,
                qty=l_qty,
                mode="live",
                kite=kite,
            )
            st.session_state.live_running = True
            st.success("Live trading started!")

        if st.button("⏹ Stop Live Trading", use_container_width=True):
            st.session_state.live_running = False
            st.warning("Live trading stopped.")

    with col2:
        if st.session_state.live_strategy:
            strat = st.session_state.live_strategy

            instrument_str = f"{l_exchange}:{l_symbol.upper()}"
            ltp_data = get_ltp(kite, [instrument_str])
            current_price = ltp_data.get(instrument_str, {}).get("last_price")

            if current_price and st.session_state.live_running:
                strat.tick(current_price)

            m1, m2, m3 = st.columns(3)
            m1.metric("LTP", f"₹{current_price:.2f}" if current_price else "—")
            m2.metric("Realised P&L", f"₹{strat.total_pnl:.2f}")
            m3.metric("Trades Today", len(strat.trades))

            if strat.open_trade:
                unr = (current_price - strat.open_trade.buy_price) * strat.open_trade.qty if current_price else 0
                st.warning(f"📌 Open position: Bought @ ₹{strat.open_trade.buy_price:.2f} | Unrealised: ₹{unr:.2f}")

            st.subheader("Order Log")
            if strat.log:
                log_html = "<div class='trade-log'>"
                for line in reversed(strat.log[-50:]):
                    css = "buy" if "BUY" in line else "sell"
                    log_html += f"<div class='{css}'>{line}</div>"
                log_html += "</div>"
                st.markdown(log_html, unsafe_allow_html=True)

            if st.session_state.live_running:
                time.sleep(5)
                st.rerun()
        else:
            st.info("Configure strategy and click **Start Live Trading**.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📋 Settings":
    st.title("📋 Settings")
    st.markdown("---")

    st.subheader("API Credentials")
    api_key = st.text_input("API Key", value=os.getenv("KITE_API_KEY", ""), type="password")
    api_secret = st.text_input("API Secret", value=os.getenv("KITE_API_SECRET", ""), type="password")

    if st.button("Update Credentials"):
        set_key(ENV_PATH, "KITE_API_KEY", api_key)
        set_key(ENV_PATH, "KITE_API_SECRET", api_secret)
        os.environ["KITE_API_KEY"] = api_key
        os.environ["KITE_API_SECRET"] = api_secret
        st.success("Saved!")

    st.markdown("---")
    st.subheader("Clear Session")
    if st.button("Clear access token (force re-login)"):
        set_key(ENV_PATH, "KITE_ACCESS_TOKEN", "")
        os.environ["KITE_ACCESS_TOKEN"] = ""
        st.success("Access token cleared.")

    st.markdown("---")
    st.subheader("About")
    st.markdown("""
    **Kite Trader** — Local algo trading dashboard  
    Strategy: **Drop & Rise** (configurable %)  
    Built with: `streamlit` · `kiteconnect` · `plotly` · `pandas`
    """)
