import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests

from strategy import generate_signal, backtest


st.set_page_config(
    page_title="Friendly Trader",
    page_icon="📈",
    layout="wide"
)


st.markdown("""
<style>
.main {
    background-color: #080b14;
}

.block-container {
    padding-top: 1.2rem;
}

.metric-card {
    padding: 14px;
    border-radius: 12px;
    background: #111827;
    border: 1px solid #253047;
}
</style>
""", unsafe_allow_html=True)


st.title("Friendly Trader")
st.caption(
    "Trade Smart. Trade Friendly. — Alpha 0.2 Research Prototype"
)


# ---------------------------------------------------------
# REAL XAU/USD DATA
# ---------------------------------------------------------

@st.cache_data(ttl=60)
def get_xauusd_data():

    api_key = st.secrets["TWELVE_DATA_API_KEY"]

    url = "https://api.twelvedata.com/time_series"

    params = {
        "symbol": "XAU/USD",
        "interval": "15min",
        "outputsize": 5000,
        "apikey": api_key
    }

    response = requests.get(
        url,
        params=params,
        timeout=20
    )

    response.raise_for_status()

    data = response.json()

    if "values" not in data:
        raise RuntimeError(
            f"Twelve Data error: {data}"
        )

    df = pd.DataFrame(data["values"])

    df["datetime"] = pd.to_datetime(
        df["datetime"]
    )

    numeric_columns = [
        "open",
        "high",
        "low",
        "close"
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    df = df.dropna()

    df = df.sort_values(
        "datetime"
    ).reset_index(drop=True)

    df = df.rename(
        columns={
            "datetime": "time"
        }
    )

    return df


# ---------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------

try:

    df = get_xauusd_data()

except Exception as e:

    st.error(
        "Unable to load real XAU/USD data."
    )

    st.code(str(e))

    st.stop()


if len(df) < 100:

    st.error(
        "Not enough market data received."
    )

    st.stop()


# ---------------------------------------------------------
# SIGNAL
# ---------------------------------------------------------

signal = generate_signal(df)


# ---------------------------------------------------------
# TOP METRICS
# ---------------------------------------------------------

c1, c2, c3, c4 = st.columns(4)


c1.metric(
    "XAUUSD",
    f"${df.close.iloc[-1]:,.2f}"
)


c2.metric(
    "Signal",
    signal["direction"]
)


c3.metric(
    "Score",
    f'{signal["score"]}/10'
)


c4.metric(
    "Risk / Reward",
    "1:3"
)


# ---------------------------------------------------------
# MARKET CHART
# ---------------------------------------------------------

left, right = st.columns([2.2, 1])


with left:

    st.subheader(
        "📊 XAUUSD 15-Minute Market Chart"
    )

    chart_data = df.tail(250)

    fig = go.Figure(
        data=[
            go.Candlestick(
                x=chart_data.time,
                open=chart_data.open,
                high=chart_data.high,
                low=chart_data.low,
                close=chart_data.close
            )
        ]
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


# ---------------------------------------------------------
# SIGNAL PANEL
# ---------------------------------------------------------

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

    st.progress(
        signal["score"] / 10
    )

    st.write(
        f"**Setup Score:** "
        f"{signal['score']}/10"
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


# ---------------------------------------------------------
# MARKET INFORMATION
# ---------------------------------------------------------

st.divider()

st.subheader(
    "📡 Market Data"
)

d1, d2, d3 = st.columns(3)


d1.metric(
    "Candles Loaded",
    len(df)
)


d2.metric(
    "Timeframe",
    "15 Minutes"
)


d3.metric(
    "Data Source",
    "Twelve Data"
)


# ---------------------------------------------------------
# BACKTEST
# ---------------------------------------------------------

st.divider()

st.subheader(
    "🧪 50-Trade Research Backtest"
)


results = backtest(
    df,
    trades=50
)


m1, m2, m3, m4, m5 = st.columns(5)


m1.metric(
    "Trades",
    results["trades"]
)


m2.metric(
    "Win Rate",
    f'{results["win_rate"]:.1f}%'
)


m3.metric(
    "Net R",
    f'{results["net_r"]:.2f}R'
)


m4.metric(
    "Profit Factor",
    f'{results["profit_factor"]:.2f}'
)


m5.metric(
    "Max Drawdown",
    f'{results["max_drawdown"]:.2f}R'
)


# ---------------------------------------------------------
# TRADE JOURNAL
# ---------------------------------------------------------

st.subheader(
    "📒 Trade Journal"
)


st.dataframe(
    results["journal"],
    use_container_width=True,
    hide_index=True
)


st.caption(
    "Alpha 0.2 uses real XAU/USD market data. "
    "Backtest results are research results only "
    "and should not be treated as proof of future performance."
    )        
