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
# ALPHA 0.8 BACKTEST V2
# =========================================================

st.divider()

st.subheader(
    "🧪 50-Trade Research Backtest"
)


def prepare_backtest_data(df):

    data = df.copy()

    data = data.sort_values("time")
    data = data.reset_index(drop=True)

    data["ema20"] = (
        data["close"]
        .ewm(span=20, adjust=False)
        .mean()
    )

    data["ema50"] = (
        data["close"]
        .ewm(span=50, adjust=False)
        .mean()
    )

    data["ema200"] = (
        data["close"]
        .ewm(span=200, adjust=False)
        .mean()
    )

    delta = data["close"].diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()

    rs = (
        avg_gain /
        avg_loss.replace(0, np.nan)
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
        [tr1, tr2, tr3],
        axis=1
    ).max(axis=1)

    data["atr"] = (
        data["tr"]
        .rolling(14)
        .mean()
    )

    return data


def calculate_trend(df):

    data = prepare_backtest_data(df)

    data = data.dropna()

    if data.empty:
        return "NEUTRAL"

    row = data.iloc[-1]

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


@st.cache_data
def run_alpha08_backtest(
    df_15m,
    df_1h,
    df_4h
):

    data = prepare_backtest_data(
        df_15m
    )

    h1 = prepare_backtest_data(
        df_1h
    )

    h4 = prepare_backtest_data(
        df_4h
    )

    data = data.dropna()
    h1 = h1.dropna()
    h4 = h4.dropna()

    trades = []

    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0

    for i in range(
        200,
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


        # ---------------------------------------------
        # FIND THE MOST RECENT 1H TREND
        # ---------------------------------------------

        current_time = row["time"]

        h1_rows = h1[
            h1["time"] <= current_time
        ]

        h4_rows = h4[
            h4["time"] <= current_time
        ]

        if h1_rows.empty:
            continue

        if h4_rows.empty:
            continue

        h1_row = h1_rows.iloc[-1]
        h4_row = h4_rows.iloc[-1]


        # ---------------------------------------------
        # HIGHER TIMEFRAME TRENDS
        # ---------------------------------------------

        if (
            h1_row["ema20"] >
            h1_row["ema50"] >
            h1_row["ema200"]
        ):

            h1_trend = "BULLISH"

        elif (
            h1_row["ema20"] <
            h1_row["ema50"] <
            h1_row["ema200"]
        ):

            h1_trend = "BEARISH"

        else:

            h1_trend = "NEUTRAL"


        if (
            h4_row["ema20"] >
            h4_row["ema50"] >
            h4_row["ema200"]
        ):

            h4_trend = "BULLISH"

        elif (
            h4_row["ema20"] <
            h4_row["ema50"] <
            h4_row["ema200"]
        ):

            h4_trend = "BEARISH"

        else:

            h4_trend = "NEUTRAL"


        # ---------------------------------------------
        # SCORE
        # ---------------------------------------------

        buy_score = 0
        sell_score = 0


        if row["ema20"] > row["ema50"]:

            buy_score += 2

        elif row["ema20"] < row["ema50"]:

            sell_score += 2


        if price > row["ema200"]:

            buy_score += 2

        elif price < row["ema200"]:

            sell_score += 2


        if (
            55 <= row["rsi"] <= 70
        ):

            buy_score += 2

        elif (
            30 <= row["rsi"] <= 45
        ):

            sell_score += 2


        if h1_trend == "BULLISH":

            buy_score += 2

        elif h1_trend == "BEARISH":

            sell_score += 2


        if h4_trend == "BULLISH":

            buy_score += 2

        elif h4_trend == "BEARISH":

            sell_score += 2


        # ---------------------------------------------
        # SIGNAL
        # ---------------------------------------------

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


        # ---------------------------------------------
        # ATR RISK MODEL
        # ---------------------------------------------

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


        # ---------------------------------------------
        # LOOK FOR EXIT
        # ---------------------------------------------

        result_r = None
        exit_price = None
        exit_time = None


        for j in range(
            i + 1,
            min(i + 21, len(data))
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
                    exit_time = future["time"]

                    break


                if high >= take_profit:

                    result_r = 3.0
                    exit_price = take_profit
                    exit_time = future["time"]

                    break


            else:

                if high >= stop_loss:

                    result_r = -1.0
                    exit_price = stop_loss
                    exit_time = future["time"]

                    break


                if low <= take_profit:

                    result_r = 3.0
                    exit_price = take_profit
                    exit_time = future["time"]

                    break


        if result_r is None:

            continue


        # ---------------------------------------------
        # EQUITY
        # ---------------------------------------------

        equity += result_r

        peak = max(
            peak,
            equity
        )

        drawdown = (
            equity -
            peak
        )

        max_drawdown = min(
            max_drawdown,
            drawdown
        )


        trades.append(
            {
                "Entry Time": row["time"],
                "Exit Time": exit_time,
                "Direction": direction,
                "Score": max(
                    buy_score,
                    sell_score
                ),
                "Entry": round(
                    price,
                    2
                ),
                "Stop Loss": round(
                    stop_loss,
                    2
                ),
                "Take Profit": round(
                    take_profit,
                    2
                ),
                "Result R": result_r
            }
        )


    journal = pd.DataFrame(
        trades
    )


    if journal.empty:

        return {
            "trades": 0,
            "win_rate": 0.0,
            "net_r": 0.0,
            "profit_factor": 0.0,
            "max_drawdown": 0.0,
            "journal": journal
        }


    wins = (
        journal["Result R"] > 0
    ).sum()


    win_rate = (
        wins /
        len(journal)
    ) * 100


    net_r = (
        journal["Result R"]
        .sum()
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

        profit_factor = 0.0


    return {
        "trades": len(journal),
        "win_rate": win_rate,
        "net_r": net_r,
        "profit_factor": profit_factor,
        "max_drawdown": max_drawdown,
        "journal": journal
    }


# =========================================================
# RUN
# =========================================================
with st.spinner("Running Alpha 0.8 backtest..."):
    backtest = run_alpha08_backtest(
        df_15m,
        df_1h,
        df_4h
    )


