import streamlit as st
import pandas as pd
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
    "Trade Smart. Trade Friendly. — Alpha 1.0 Research Prototype"
)


# =========================================================
# DATA
# =========================================================

@st.cache_data(ttl=60)
def get_market_data(
    interval,
    outputsize
):

    api_key = st.secrets[
        "TWELVE_DATA_API_KEY"
    ]

    response = requests.get(
        "https://api.twelvedata.com/time_series",
        params={
            "symbol": "XAU/USD",
            "interval": interval,
            "outputsize": outputsize,
            "apikey": api_key
        },
        timeout=20
    )

    response.raise_for_status()

    result = response.json()

    if "values" not in result:

        raise RuntimeError(
            result.get(
                "message",
                "No market data returned."
            )
        )

    df = pd.DataFrame(
        result["values"]
    )

    df["time"] = pd.to_datetime(
        df["datetime"]
    )

    for col in [
        "open",
        "high",
        "low",
        "close"
    ]:

        df[col] = pd.to_numeric(
            df[col],
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
    ].dropna()

    return (
        df
        .sort_values("time")
        .reset_index(drop=True)
    )


# =========================================================
# LOAD
# =========================================================

try:

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
# LIVE SIGNAL
# =========================================================

try:

    signal = generate_signal(
        df_15m,
        df_1h,
        df_4h
    )

except Exception as error:

    st.error(
        "Signal engine error."
    )

    st.exception(error)

    st.stop()


direction = signal["direction"]

score = signal["score"]

entry = signal["entry"]

sl = signal["sl"]

tp = signal["tp"]

h1 = signal["h1_trend"]

h4 = signal["h4_trend"]

rsi = signal["rsi"]

atr = signal["atr"]

buy_score = signal["buy_score"]

sell_score = signal["sell_score"]


# =========================================================
# METRICS
# =========================================================

a, b, c, d = st.columns(4)

a.metric(
    "XAUUSD",
    f"${df_15m['close'].iloc[-1]:,.2f}"
)

b.metric(
    "Signal",
    direction
)

c.metric(
    "Score",
    f"{score}/10"
)

d.metric(
    "Risk / Reward",
    "1:3"
)


# =========================================================
# CHART
# =========================================================

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
    f"## {direction}"
)

x, y, z = st.columns(3)

x.metric(
    "Entry",
    f"{entry:.2f}"
)

y.metric(
    "Stop Loss",
    f"{sl:.2f}"
)

z.metric(
    "Take Profit",
    f"{tp:.2f}"
)

st.write(
    f"**Setup Score:** {score}/10"
)

st.write(
    f"**BUY Score:** {buy_score}/10"
)

st.write(
    f"**SELL Score:** {sell_score}/10"
)

st.write(
    f"**RSI:** {rsi}"
)

st.write(
    f"**ATR:** {atr}"
)

st.write(
    f"**1H Trend:** {h1}"
)

st.write(
    f"**4H Trend:** {h4}"
)

if direction == "WAIT":

    st.warning(
        "No sufficiently strong setup. "
        "Waiting for better confirmation."
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

m1, m2, m3, m4 = st.columns(4)

m1.metric(
    "15M Candles",
    len(df_15m)
)

m2.metric(
    "1H Candles",
    len(df_1h)
)

m3.metric(
    "4H Candles",
    len(df_4h)
)

m4.metric(
    "Source",
    "Twelve Data"
)


# =========================================================
# BACKTEST
# =========================================================

st.divider()

st.subheader(
    "🧪 Alpha 1.0 Research Backtest"
)


def run_backtest(
    df_15m,
    df_1h,
    df_4h
):

    results = []

    minimum_15m = 220

    horizon = 20

    for i in range(
        minimum_15m,
        len(df_15m) - horizon
    ):

        current_15m = (
            df_15m.iloc[
                :i + 1
            ]
            .copy()
        )

        current_time = (
            current_15m["time"].iloc[-1]
        )


        current_1h = (
            df_1h[
                df_1h["time"] <= current_time
            ]
            .copy()
        )

        current_4h = (
            df_4h[
                df_4h["time"] <= current_time
            ]
            .copy()
        )


        if len(current_1h) < 220:
            continue

        if len(current_4h) < 220:
            continue


        try:

            s = generate_signal(
                current_15m,
                current_1h,
                current_4h
            )

        except Exception:

            continue


        direction = s["direction"]


        if direction == "WAIT":
            continue


        entry = float(
            s["entry"]
        )

        sl = float(
            s["sl"]
        )

        tp = float(
            s["tp"]
        )


        future = df_15m.iloc[
            i + 1 :
            i + 1 + horizon
        ]


        result = "TIMEOUT"

        result_r = 0.0

        exit_price = float(
            future["close"].iloc[-1]
        )

        exit_time = (
            future["time"].iloc[-1]
        )


        for _, candle in future.iterrows():

            high = float(
                candle["high"]
            )

            low = float(
                candle["low"]
            )


            if direction == "BUY":

                hit_sl = (
                    low <= sl
                )

                hit_tp = (
                    high >= tp
                )

            else:

                hit_sl = (
                    high >= sl
                )

                hit_tp = (
                    low <= tp
                )


            if hit_sl and hit_tp:

                result = "LOSS"

                result_r = -1.0

                exit_price = sl

                exit_time = candle["time"]

                break


            if hit_sl:

                result = "LOSS"

                result_r = -1.0

                exit_price = sl

                exit_time = candle["time"]

                break


            if hit_tp:

                result = "WIN"

                result_r = 3.0

                exit_price = tp

                exit_time = candle["time"]

                break


        results.append(
            {
                "Signal Time": current_time,
                "Direction": direction,
                "Score": s["score"],
                "BUY Score": s["buy_score"],
                "SELL Score": s["sell_score"],
                "Entry": round(
                    entry,
                    2
                ),
                "SL": round(
                    sl,
                    2
                ),
                "TP": round(
                    tp,
                    2
                ),
                "Result": result,
                "R": result_r,
                "Exit Time": exit_time,
                "Exit Price": round(
                    exit_price,
                    2
                )
            }
        )


    return results


# =========================================================
# EXECUTE
# =========================================================

try:

    with st.spinner(
        "Running Alpha 1.0 research backtest..."
    ):

        results = run_backtest(
            df_15m,
            df_1h,
            df_4h
        )


    if not results:

        st.warning(
            "No qualifying signals were found "
            "in the available historical sample."
        )

    else:

        journal = pd.DataFrame(
            results
        )


        # -------------------------------------------------
        # STATS
        # -------------------------------------------------

        trades = len(
            journal
        )

        wins = (
            journal["Result"] == "WIN"
        ).sum()

        losses = (
            journal["Result"] == "LOSS"
        ).sum()

        timeouts = (
            journal["Result"] == "TIMEOUT"
        ).sum()


        win_rate = (
            wins / trades * 100
        )


        net_r = (
            journal["R"].sum()
        )


        gross_profit = journal.loc[
            journal["R"] > 0,
            "R"
        ].sum()


        gross_loss = abs(
            journal.loc[
                journal["R"] < 0,
                "R"
            ].sum()
        )


        if gross_loss > 0:

            profit_factor = (
                gross_profit /
                gross_loss
            )

        else:

            profit_factor = float(
                "inf"
            )


        expectancy = (
            net_r /
            trades
        )


        equity = (
            journal["R"]
            .cumsum()
        )

        peak = (
            equity.cummax()
        )

        drawdown = (
            equity -
            peak
        )

        max_drawdown = (
            drawdown.min()
        )


        # -------------------------------------------------
        # LOSING STREAK
        # -------------------------------------------------

        max_losing_streak = 0

        current_losing_streak = 0

        for r in journal["R"]:

            if r < 0:

                current_losing_streak += 1

                max_losing_streak = max(
                    max_losing_streak,
                    current_losing_streak
                )

            else:

                current_losing_streak = 0


        # -------------------------------------------------
        # DISPLAY
        # -------------------------------------------------

        q1, q2, q3, q4, q5 = st.columns(5)

        q1.metric(
            "Trades",
            trades
        )

        q2.metric(
            "Win Rate",
            f"{win_rate:.1f}%"
        )

        q3.metric(
            "Net R",
            f"{net_r:.2f}R"
        )

        q4.metric(
            "Profit Factor",
            (
                "∞"
                if profit_factor == float("inf")
                else f"{profit_factor:.2f}"
            )
        )

        q5.metric(
            "Max Drawdown",
            f"{max_drawdown:.2f}R"
        )


        r1, r2, r3 = st.columns(3)

        r1.metric(
            "Expectancy",
            f"{expectancy:.3f}R/trade"
        )

        r2.metric(
            "Timeouts",
            timeouts
        )

        r3.metric(
            "Max Losing Streak",
            max_losing_streak
        )


        # -------------------------------------------------
        # EQUITY
        # -------------------------------------------------

        st.subheader(
            "📈 Research Equity Curve"
        )

        equity_fig = go.Figure()

        equity_fig.add_trace(
            go.Scatter(
                x=list(
                    range(
                        1,
                        len(equity) + 1
                    )
                ),
                y=equity,
                mode="lines+markers",
                name="Cumulative R"
            )
        )

        equity_fig.update_layout(
            height=350,
            xaxis_title="Trade",
            yaxis_title="R"
        )

        st.plotly_chart(
            equity_fig,
            use_container_width=True
        )


        # -------------------------------------------------
        # JOURNAL
        # -------------------------------------------------

        st.subheader(
            "📒 Trade Journal"
        )

        st.dataframe(
            journal,
            use_container_width=True,
            hide_index=True
        )


except Exception as error:

    st.error(
        "Backtest error."
    )

    st.exception(error)


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "Alpha 1.0 is a research prototype. "
    "This system does not execute real trades. "
    "Backtest results are historical research only "
    "and are not proof of future performance."
    )
