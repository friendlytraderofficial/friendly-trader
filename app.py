import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go

from strategy import generate_signal


# =========================================================
# PAGE
# =========================================================

st.set_page_config(
    page_title="Friendly Trader",
    page_icon="📈",
    layout="wide"
)

st.title("Friendly Trader")

st.caption(
    "Trade Smart. Trade Friendly. — Alpha 0.9 Research Prototype"
)


# =========================================================
# TWELVE DATA
# =========================================================

@st.cache_data(ttl=60)
def get_market_data(interval, outputsize):

    api_key = st.secrets[
        "TWELVE_DATA_API_KEY"
    ]

    url = (
        "https://api.twelvedata.com/"
        "time_series"
    )

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
                "Twelve Data returned no data."
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
# LOAD MARKET DATA
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
        "Market data loading failed."
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
# SIGNAL
# =========================================================

try:

    result = generate_signal(
        df_15m,
        df_1h,
        df_4h
    )

except TypeError:

    st.error(
        "The generate_signal() function "
        "in strategy.py does not match "
        "the expected Alpha 0.9 format."
    )

    st.stop()

except Exception as error:

    st.error(
        "Signal generation failed."
    )

    st.exception(error)

    st.stop()


# =========================================================
# NORMALIZE SIGNAL
# =========================================================

direction = result.get(
    "direction",
    "WAIT"
)

score = int(
    result.get(
        "score",
        0
    )
)

entry = float(
    result.get(
        "entry",
        df_15m["close"].iloc[-1]
    )
)

sl = float(
    result.get(
        "sl",
        entry
    )
)

tp = float(
    result.get(
        "tp",
        entry
    )
)

h1_trend = result.get(
    "h1_trend",
    "NEUTRAL"
)

h4_trend = result.get(
    "h4_trend",
    "NEUTRAL"
)


# =========================================================
# DISPLAY SCORE
# =========================================================

# Alpha 0.9 strategy currently has
# a maximum raw score of 8.
#
# Convert it to a 10-point display
# without changing the actual decision.
#
# 8 raw -> 10 display
# 7 raw -> 8.75 display
# etc.
display_score = score

    



# =========================================================
# TOP METRICS
# =========================================================

m1, m2, m3, m4 = st.columns(4)

m1.metric(
    "XAUUSD",
    f"${df_15m['close'].iloc[-1]:,.2f}"
)

m2.metric(
    "Signal",
    direction
)

m3.metric(
    "Score",
    f"{display_score}/10"
)

m4.metric(
    "Risk / Reward",
    "1:3"
)


# =========================================================
# CHART
# =========================================================

st.subheader(
    "📊 XAUUSD 15-Minute Chart"
)

chart_df = df_15m.tail(200)

fig = go.Figure()

fig.add_trace(
    go.Candlestick(
        x=chart_df["time"],
        open=chart_df["open"],
        high=chart_df["high"],
        low=chart_df["low"],
        close=chart_df["close"],
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
# LATEST SIGNAL
# =========================================================

st.subheader(
    "🚨 Latest Signal"
)

st.markdown(
    f"## {direction}"
)


p1, p2, p3 = st.columns(3)

p1.metric(
    "Entry",
    f"{entry:.2f}"
)

p2.metric(
    "Stop Loss",
    f"{sl:.2f}"
)

p3.metric(
    "Take Profit",
    f"{tp:.2f}"
)


st.write(
    f"**Setup Score:** "
    f"{display_score}/10"
)

st.write(
    f"**1H Trend:** "
    f"{h1_trend}"
)

st.write(
    f"**4H Trend:** "
    f"{h4_trend}"
)


if direction == "WAIT":

    st.warning(
        "No high-quality setup currently. "
        "Wait for confirmation."
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
# SIMPLE RESEARCH BACKTEST
# =========================================================

st.divider()

st.subheader(
    "🧪 50-Trade Research Backtest"
)


def calculate_backtest():

    data = df_15m.copy()

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

    avg_gain = gain.rolling(
        14
    ).mean()

    avg_loss = loss.rolling(
        14
    ).mean()

    rs = (
        avg_gain /
        avg_loss.replace(
            0,
            np.nan
        )
    )

    data["rsi"] = (
        100 -
        100 / (1 + rs)
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

    data["atr"] = pd.concat(
        [
            tr1,
            tr2,
            tr3
        ],
        axis=1
    ).max(axis=1).rolling(
        14
    ).mean()

    data = data.dropna()

    trades = []

    equity = 0.0
    peak = 0.0
    max_dd = 0.0

    for i in range(
        1,
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

        buy = 0
        sell = 0

        if (
            row["ema20"] >
            row["ema50"] >
            row["ema200"]
        ):

            buy += 2

        if (
            row["ema20"] <
            row["ema50"] <
            row["ema200"]
        ):

            sell += 2

        if (
            52 <= row["rsi"] <= 65
        ):

            buy += 2

        if (
            35 <= row["rsi"] <= 48
        ):

            sell += 2

        ema_distance = (
            abs(
                price -
                row["ema20"]
            ) /
            price
        ) * 100

        if ema_distance <= 0.15:

            if price > row["ema20"]:

                buy += 2

            elif price < row["ema20"]:

                sell += 2

        if buy >= 6 and buy > sell:

            direction_bt = "BUY"

        elif sell >= 6 and sell > buy:

            direction_bt = "SELL"

        else:

            continue

        risk = atr * 1.5
        reward = risk * 3

        if direction_bt == "BUY":

            stop = price - risk
            target = price + reward

        else:

            stop = price + risk
            target = price - reward

        result_r = None

        for j in range(
            i + 1,
            min(
                i + 21,
                len(data)
            )
        ):

            candle = data.iloc[j]

            high = float(
                candle["high"]
            )

            low = float(
                candle["low"]
            )

            if direction_bt == "BUY":

                if low <= stop:

                    result_r = -1
                    break

                if high >= target:

                    result_r = 3
                    break

            else:

                if high >= stop:

                    result_r = -1
                    break

                if low <= target:

                    result_r = 3
                    break

        if result_r is None:

            continue

        equity += result_r

        peak = max(
            peak,
            equity
        )

        max_dd = min(
            max_dd,
            equity - peak
        )

        trades.append(
            result_r
        )

    if not trades:

        return {
            "trades": 0,
            "win_rate": 0,
            "net_r": 0,
            "profit_factor": 0,
            "max_dd": 0
        }

    wins = sum(
        1
        for x in trades
        if x > 0
    )

    losses = sum(
        1
        for x in trades
        if x < 0
    )

    gross_profit = sum(
        x for x in trades
        if x > 0
    )

    gross_loss = abs(
        sum(
            x for x in trades
            if x < 0
        )
    )

    if gross_loss > 0:

        pf = (
            gross_profit /
            gross_loss
        )

    else:

        pf = 0

    return {
        "trades": len(trades),
        "win_rate": (
            wins /
            len(trades)
        ) * 100,
        "net_r": sum(trades),
        "profit_factor": pf,
        "max_dd": max_dd
    }


try:

    with st.spinner(
        "Running backtest..."
    ):

        bt = calculate_backtest()

    r1, r2, r3, r4, r5 = st.columns(5)

    r1.metric(
        "Trades",
        bt["trades"]
    )

    r2.metric(
        "Win Rate",
        f"{bt['win_rate']:.1f}%"
    )

    r3.metric(
        "Net R",
        f"{bt['net_r']:.2f}R"
    )

    r4.metric(
        "Profit Factor",
        f"{bt['profit_factor']:.2f}"
    )

    r5.metric(
        "Max Drawdown",
        f"{bt['max_dd']:.2f}R"
    )

except Exception as error:

    st.error(
        "Backtest failed."
    )

    st.exception(error)


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "Alpha 0.9 is a research prototype. "
    "Market data comes from Twelve Data. "
    "Backtest results are research results only "
    "and are not proof of future performance. "
    "Real-money execution is disabled."
    )
