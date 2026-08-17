import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go

from strategy import generate_signal


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Friendly Trader",
    page_icon="📈",
    layout="wide"
)

st.title("Friendly Trader")

st.caption(
    "Trade Smart. Trade Friendly. — Alpha 0.8 Research Prototype"
)


# =========================================================
# MARKET DATA
# =========================================================

@st.cache_data(ttl=60)
def get_market_data(interval, outputsize):

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
            result.get(
                "message",
                "Twelve Data returned no values."
            )
        )

    df = pd.DataFrame(
        result["values"]
    )

    df["time"] = pd.to_datetime(
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

    df = df[
        [
            "time",
            "open",
            "high",
            "low",
            "close"
        ]
    ]

    df = df.dropna()

    df = df.sort_values(
        "time"
    )

    return df.reset_index(
        drop=True
    )


# =========================================================
# LOAD DATA
# =========================================================

try:

    with st.spinner(
        "Loading XAU/USD market data..."
    ):

        df_15m = get_market_data(
            "15min",
            500
        )

        df_1h = get_market_data(
            "1h",
            500
        )

        df_4h = get_market_data(
            "4h",
            500
        )

except Exception as error:

    st.error(
        "Unable to load market data."
    )

    st.exception(error)

    st.stop()


st.success(
    f"Real data loaded: "
    f"{len(df_15m)} × 15M | "
    f"{len(df_1h)} × 1H | "
    f"{len(df_4h)} × 4H"
)


# =========================================================
# CURRENT SIGNAL
# =========================================================

try:

    signal = generate_signal(
        df_15m,
        df_1h,
        df_4h
    )

except Exception as error:

    st.error(
        "Signal generation failed."
    )

    st.exception(error)

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
# CHART
# =========================================================

st.subheader(
    "📊 XAUUSD 15-Minute Chart"
)

chart_data = df_15m.tail(200)

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
    height=500,
    xaxis_rangeslider_visible=False
)

st.plotly_chart(
    fig,
    use_container_width=True
)


# =========================================================
# SIGNAL
# =========================================================

st.subheader(
    "🚨 Latest Signal"
)

st.markdown(
    f"## {signal['direction']}"
)

s1, s2, s3 = st.columns(3)

s1.metric(
    "Entry",
    f"{signal['entry']:.2f}"
)

s2.metric(
    "Stop Loss",
    f"{signal['sl']:.2f}"
)

s3.metric(
    "Take Profit",
    f"{signal['tp']:.2f}"
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
    "Source",
    "Twelve Data"
)


# =========================================================
# FAST BACKTEST
# =========================================================

st.divider()

st.subheader(
    "🧪 50-Trade Research Backtest"
)


def add_backtest_indicators(df):

    data = df.copy()

    data = data.sort_values(
        "time"
    )

    data = data.reset_index(
        drop=True
    )

    data["ema20"] = (
        data["close"]
        .ewm(
            span=20,
            adjust=False
        )
        .mean()
    )

    data["ema50"] = (
        data["close"]
        .ewm(
            span=50,
            adjust=False
        )
        .mean()
    )

    data["ema200"] = (
        data["close"]
        .ewm(
            span=200,
            adjust=False
        )
        .mean()
    )

    delta = data["close"].diff()

    gain = delta.clip(
        lower=0
    )

    loss = -delta.clip(
        upper=0
    )

    avg_gain = (
        gain.rolling(14)
        .mean()
    )

    avg_loss = (
        loss.rolling(14)
        .mean()
    )

    rs = (
        avg_gain /
        avg_loss.replace(
            0,
            np.nan
        )
    )

    data["rsi"] = (
        100 -
        (100 / (1 + rs))
    )

    previous_close = (
        data["close"].shift(1)
    )

    tr1 = (
        data["high"] -
        data["low"]
    )

    tr2 = (
        data["high"] -
        previous_close
    ).abs()

    tr3 = (
        data["low"] -
        previous_close
    ).abs()

    data["tr"] = pd.concat(
        [
            tr1,
            tr2,
            tr3
        ],
        axis=1
    ).max(axis=1)

    data["atr"] = (
        data["tr"]
        .rolling(14)
        .mean()
    )

    return data


def get_trend_at_time(
    trend_df,
    current_time
):

    available = trend_df[
        trend_df["time"] <= current_time
    ]

    if available.empty:

        return "NEUTRAL"

    row = available.iloc[-1]

    if (
        row["ema20"] >
        row["ema50"] >
        row["ema200"]
    ):

        return "BULLISH"

    if (
        row["ema20"] <
        row["ema50"] <
        row["ema200"]
    ):

        return "BEARISH"

    return "NEUTRAL"


def run_fast_backtest(
    df_15m,
    df_1h,
    df_4h
):

    data = add_backtest_indicators(
        df_15m
    ).dropna()

    h1 = add_backtest_indicators(
        df_1h
    ).dropna()

    h4 = add_backtest_indicators(
        df_4h
    ).dropna()

    trades = []

    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0

    start_index = max(
        200,
        0
    )

    for i in range(
        start_index,
        len(data) - 20
    ):

        if len(trades) >= 50:
            break

        row = data.iloc[i]

        price = float(
            row["close"]
        )

        atr = float(
            row["atr"]
        )

        if not np.isfinite(atr):
            continue

        if atr <= 0:
            continue

        current_time = row["time"]

        h1_trend = get_trend_at_time(
            h1,
            current_time
        )

        h4_trend = get_trend_at_time(
            h4,
            current_time
        )

        buy_score = 0
        sell_score = 0

        # EMA 20 / 50
        if row["ema20"] > row["ema50"]:

            buy_score += 2

        elif row["ema20"] < row["ema50"]:

            sell_score += 2

        # EMA 200
        if price > row["ema200"]:

            buy_score += 2

        elif price < row["ema200"]:

            sell_score += 2

        # RSI
        if (
            55 <= row["rsi"] <= 70
        ):

            buy_score += 2

        elif (
            30 <= row["rsi"] <= 45
        ):

            sell_score += 2

        # 1H
        if h1_trend == "BULLISH":

            buy_score += 2

        elif h1_trend == "BEARISH":

            sell_score += 2

        # 4H
        if h4_trend == "BULLISH":

            buy_score += 2

        elif h4_trend == "BEARISH":

            sell_score += 2

        # Signal
        if (
            buy_score >= 8
            and buy_score > sell_score
        ):

            direction = "BUY"

        elif (
            sell_score >= 8
            and sell_score > buy_score
        ):

            direction = "SELL"

        else:

            continue

        # ATR risk model
        stop_distance = (
            atr * 1.5
        )

        target_distance = (
            stop_distance * 3
        )

        if direction == "BUY":

            stop_loss = (
                price -
                stop_distance
            )

            take_profit = (
                price +
                target_distance
            )

        else:

            stop_loss = (
                price +
                stop_distance
            )

            take_profit = (
                price -
                target_distance
            )

        result_r = None
        exit_price = None

        for j in range(
            i + 1,
            min(
                i + 21,
                len(data)
            )
        ):

            future = data.iloc[j]

            high = float(
                future["high"]
            )

            low = float(
                future["low"]
            )

            if direction == "BUY":

                if low <= stop_loss:

                    result_r = -1.0
                    exit_price = stop_loss

                    break

                if high >= take_profit:

                    result_r = 3.0
                    exit_price = take_profit

                    break

            else:

                if high >= stop_loss:

                    result_r = -1.0
                   
