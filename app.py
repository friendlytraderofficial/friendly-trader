import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests

from strategy import generate_signal, backtest


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Friendly Trader",
    page_icon="📈",
    layout="wide"
)


# =========================================================
# HEADER
# =========================================================

st.title("Friendly Trader")

st.caption(
    "Trade Smart. Trade Friendly. — Alpha 0.6 Research Prototype"
)


# =========================================================
# TWELVE DATA
# =========================================================

@st.cache_data(ttl=60)
def get_xauusd_data(interval, outputsize):

    api_key = st.secrets["TWELVE_DATA_API_KEY"]

    url = "https://api.twelvedata.com/time_series"

    params = {
        "symbol": "XAU/USD",
        "interval": interval,
        "outputsize": outputsize,
        "apikey": api_key
    }

    response = requests.get(
        url,
        params=params,
        timeout=20
    )

    response.raise_for_status()

    result = response.json()

    if "values" not in result:
        raise RuntimeError(
            f"Twelve Data error: {result}"
        )

    df = pd.DataFrame(result["values"])

    df["time"] = pd.to_datetime(
        df["datetime"]
    )

    for column in ["open", "high", "low", "close"]:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    df = df[
        ["time", "open", "high", "low", "close"]
    ]

    df = df.dropna()

    df = df.sort_values("time")

    df = df.reset_index(drop=True)

    return df


# =========================================================
# LOAD DATA
# =========================================================

try:

    df_15m = get_xauusd_data(
        "15min",
        5000
    )

    df_1h = get_xauusd_data(
        "1h",
        2000
    )

    df_4h = get_xauusd_data(
        "4h",
        1000
    )

except Exception as e:

    st.error("Market data loading failed.")

    st.code(str(e))

    st.stop()


# =========================================================
# DATA STATUS
# =========================================================

st.success(
    f"Real data loaded: "
    f"{len(df_15m)} × 15M | "
    f"{len(df_1h)} × 1H | "
    f"{len(df_4h)} × 4H"
)


# =========================================================
# SIGNAL
# =========================================================

try:

    signal = generate_signal(
        df_15m,
        df_1h,
        df_4h
    )

except Exception as e:

    st.error("Signal generation failed.")

    st.code(str(e))

    st.stop()


# =========================================================
# TOP METRICS
# =========================================================

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "XAUUSD",
    f"${df_15m['close'].iloc[-1]:,.2f}"
)

c2.metric(
    "Signal",
    signal["direction"]
)

c3.metric(
    "Score",
    f"{signal['score']}/10"
)

c4.metric(
    "Risk / Reward",
    "1:3"
)


# =========================================================
# MAIN SECTION
# =========================================================

left, right = st.columns([2.2, 1])


# =========================================================
# CHART
# =========================================================

with left:

    st.subheader(
        "📊 XAUUSD 15-Minute Market Chart"
    )

    chart_data = df_15m.tail(250)

    fig = go.Figure()

    fig.add_trace(
        go.Candlestick(
            x=chart_data["time"],
            open=chart_data["open"],
            high=chart_data["high"],
            low=chart_data["low"],
            close=chart_data["close"],
            name="XAUUSD"
        )
    )

    fig.update_layout(
        template="plotly_dark",
        height=520,
        xaxis_rangeslider_visible=False
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


# =========================================================
# SIGNAL PANEL
# =========================================================

with right:

    st.subheader(
        "🚨 Latest Signal"
    )

    st.markdown(
        f"## {signal['direction']}"
    )

    st.write(
        f"**Entry:** {signal['entry']}"
    )

    st.write(
        f"**Stop Loss:** {signal['sl']}"
    )

    st.write(
        f"**Take Profit:** {signal['tp']}"
    )

    score = max(
        0,
        min(10, signal["score"])
    )

    st.progress(
        score / 10
    )

    st.write(
        f"**Setup Score:** {score}/10"
    )

    st.write(
        f"**1H Trend:** "
        f"{signal.get('h1_trend', 'N/A')}"
    )

    st.write(
        f"**4H Trend:** "
        f"{signal.get('h4_trend', 'N/A')}"
    )

    if signal["direction"] == "WAIT":

        st.warning(
            "Weak setup — wait for confirmation."
        )

    else:

        st.info(
            "Research signal only. "
            "Real-money execution is disabled."
        )


# =========================================================
# MARKET DATA
# =========================================================

st.divider()

st.subheader(
    "📡 Market Data"
)

d1, d2, d3, d4 = st.columns(4)

d1.metric(
    "15M Candles",
    len(df_15m)
)

d2.metric(
    "1H Candles",
    len(df_1h)
)

d3.metric(
    "4H Candles",
    len(df_4h)
)

d4.metric(
    "Data Source",
    "Twelve Data"
)


# =========================================================
# BACKTEST
# =========================================================

st.divider()

st.subheader(
    "🧪 50-Trade Research Backtest"
)

st.info(
    "Running the multi-timeframe research backtest..."
)

try:

    results = backtest(
        df_15m,
        df_1h,
        df_4h,
        trades=50
    )

except Exception as e:

    st.error(
        "Backtest failed."
    )

    st.code(
        str(e)
    )

    st.stop()


# =========================================================
# BACKTEST METRICS
# =========================================================

st.subheader(
    "📈 Backtest Results"
)

m1, m2, m3, m4, m5 = st.columns(5)

m1.metric(
    "Trades",
    results.get("trades", 0)
)

m2.metric(
    "Win Rate",
    f"{results.get('win_rate', 0):.1f}%"
)

m3.metric(
    "Net R",
    f"{results.get('net_r', 0):.2f}R"
)

m4.metric(
    "Profit Factor",
    f"{results.get('profit_factor', 0):.2f}"
)

m5.metric(
    "Max Drawdown",
    f"{results.get('max_drawdown', 0):.2f}R"
)


# =========================================================
# EXPECTANCY
# =========================================================

if "expectancy" in results:

    st.metric(
        "Expectancy / Trade",
        f"{results['expectancy']:.3f}R"
    )


# =========================================================
# TRADE JOURNAL
# =========================================================

st.subheader(
    "📒 Trade Journal"
)

journal = results.get(
    "journal",
    pd.DataFrame()
)

if isinstance(journal, pd.DataFrame) and not journal.empty:

    st.dataframe(
        journal,
        use_container_width=True,
        hide_index=True
    )

else:

    st.info(
        "No qualifying trades were found."
    )


# =========================================================
# FOOTER
# =========================================================

st.caption(
    "Alpha 0.6 uses real XAU/USD market data "
    "with 15M + 1H + 4H confirmation. "
    "Backtest results are research results only "
    "and should not be treated as proof of future performance."
    )
