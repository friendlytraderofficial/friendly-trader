import streamlit as st
import pandas as pd
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

    data = response.json()

    if "values" not in data:

        raise RuntimeError(
            f"Twelve Data error: {data}"
        )

    df = pd.DataFrame(
        data["values"]
    )

    df["datetime"] = pd.to_datetime(
        df["datetime"]
    )

    for column in [
        "open",
        "high",
        "low",
        "close"
    ]:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    df = df.dropna()

    df = df.sort_values(
        "datetime"
    )

    df = df.reset_index(
        drop=True
    )

    df = df.rename(
        columns={
            "datetime": "time"
        }
    )

    return df


# =========================================================
# LOAD MARKET DATA
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

    st.error(
        "Unable to load real XAU/USD data."
    )

    st.code(
        str(e)
    )

    st.stop()


if len(df_15m) < 200:

    st.error(
        "Not enough 15-minute market data."
    )

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
# ALPHA 0.6 SIGNAL
# =========================================================

signal = generate_signal(
    df_15m,
    df_1h,
    df_4h
)


# =========================================================
# TOP METRICS
# =========================================================

c1, c2, c3, c4 = st.columns(4)


c1.metric(
    "XAUUSD",
    f"${df_15m.close.iloc[-1]:,.2f}"
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


# =========================================================
# MAIN LAYOUT
# =========================================================

left, right = st.columns(
    [2.2, 1]
)


# =========================================================
# CHART
# =========================================================

with left:

    st.subheader(
        "📊 XAUUSD 15-Minute Market Chart"
    )

    chart_data = df_15m.tail(
        250
    )

    fig = go.Figure(
        data=[
            go.Candlestick(

                x=chart_data["time"],

                open=chart_data["open"],

                high=chart_data["high"],

                low=chart_data["low"],

                close=chart_data["close"]
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


# =========================================================
# LATEST SIGNAL
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

    st.progress(
        min(
            signal["score"] / 10,
            1.0
        )
    )

    st.write(
        f"**Setup Score:** "
        f"{signal['score']}/10"
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
#
