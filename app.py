import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests

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
    "Trade Smart. Trade Friendly. — Alpha 0.8 Research Prototype"
)


# =========================================================
# DATA
# =========================================================

@st.cache_data(ttl=60)
def get_data(interval, outputsize):

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
        raise RuntimeError(result)

    df = pd.DataFrame(result["values"])

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

with st.spinner(
    "Loading XAU/USD market data..."
):

    try:

        df_15m = get_data(
            "15min",
            500
        )

        df_1h = get_data(
            "1h",
            500
        )

        df_4h = get_data(
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

left, right = st.columns(
    [2.2, 1]
)

with left:

    st.subheader(
        "📊 XAUUSD 15-Minute Chart"
    )

    chart = df_15m.tail(200)

    fig = go.Figure()

    fig.add_trace(
        go.Candlestick(
            x=chart["time"],
            open=chart["open"],
            high=chart["high"],
            low=chart["low"],
            close=chart["close"],
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

    st.progress(
        signal["score"] / 10
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

d1.metric("15M Candles", len(df_15m))
d2.metric("1H Candles", len(df_1h))
d3.metric("4H Candles", len(df_4h))
d4.metric("Source", "Twelve Data")
# =========================================================
# RESEARCH BACKTEST
# =========================================================

st.divider()

st.subheader(
    "🧪 50-Trade Research Backtest"
)


@st.cache_data
def run_backtest(df):

    data = df.copy()

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

    previous_close = data["close"].shift(1)

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
        [tr1, tr2, tr3],
        axis=1
    ).max(axis=1)

    data["atr"] = (
        data["tr"]
        .rolling(14)
        .mean()
    )

    trades = []

    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0

    for i in range(
        60,
        len(data) - 20
    ):

        if len(trades) >= 50:
            break

        row = data.iloc[i]

        atr = float(row["atr"])

        if not np.isfinite(atr):
            continue

        if atr <= 0:
            continue

        entry = float(row["close"])

        if row["ema20"] > row["ema50"]:

            direction = "BUY"

        elif row["ema20"] < row["ema50"]:

            direction = "SELL"

        else:

            continue

        stop_distance = atr * 1.5
        target_distance = stop_distance * 3

        if direction == "BUY":

            stop_loss = entry - stop_distance
            take_profit = entry + target_distance

        else:

            stop_loss = entry + stop_distance
            take_profit = entry - target_distance

        result_r = None
        exit_price = None

        for j in range(
            i + 1,
            min(i + 21, len(data))
        ):

            future = data.iloc[j]

            high = float(future["high"])
            low = float(future["low"])

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
                    exit_price = stop_loss
                    break

                if low <= take_profit:

                    result_r = 3.0
                    exit_price = take_profit
                    break

        if result_r is None:
            continue

        equity += result_r

        peak = max(
            peak,
            equity
        )

        drawdown = equity - peak

        max_drawdown = min(
            max_drawdown,
            drawdown
        )

        trades.append(
            {
                "Time": row["time"],
                "Direction": direction,
                "Entry": round(entry, 2),
                "Stop Loss": round(stop_loss, 2),
                "Take Profit": round(take_profit, 2),
                "Result R": result_r
            }
        )

    journal = pd.DataFrame(trades)

    if journal.empty:

        return {
            "trades": 0,
            "win_rate": 0,
            "net_r": 0,
            "profit_factor": 0,
            "max_drawdown": 0,
            "journal": journal
        }

    wins = (
        journal["Result R"] > 0
    ).sum()

    win_rate = (
        wins / len(journal)
    ) * 100

    net_r = (
        journal["Result R"].sum()
    )

    gross_profit = journal.loc[
        journal["Result R"] > 0,
        "Result R"
    ].sum()

    gross_loss = abs(
        journal.loc[
            journal["Result R"] < 0,
            "Result R"
        ].sum()
    )

    if gross_loss > 0:

        profit_factor = (
            gross_profit /
            gross_loss
        )

    else:

        profit_factor = 0

    return {
        "trades": len(journal),
        "win_rate": win_rate,
        "net_r": net_r,
        "profit_factor": profit_factor,
        "max_drawdown": max_drawdown,
        "journal": journal
    }


with st.spinner(
    "Running research backtest..."
):

    backtest = run_backtest(
        df_15m
    )


b1, b2, b3, b4, b5 = st.columns(5)

b1.metric(
    "Trades",
    backtest["trades"]
)

b2.metric(
    "Win Rate",
    f"{backtest['win_rate']:.1f}%"
)

b3.metric(
    "Net R",
    f"{backtest['net_r']:.2f}R"
)

b4.metric(
    "Profit Factor",
    f"{backtest['profit_factor']:.2f}"
)

b5.metric(
    "Max Drawdown",
    f"{backtest['max_drawdown']:.2f}R"
)


st.subheader(
    "📒 Trade Journal"
)

if not backtest["journal"].empty:

    st.dataframe(
        backtest["journal"],
        use_container_width=True,
        hide_index=True
    )

else:

    st.info(
        "No completed trades found."
    )


st.caption(
    "Backtest results are research results only "
    "and should not be treated as proof of future performance. "
    "Real-money execution is disabled."
)
