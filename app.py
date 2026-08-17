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

st.title(
    "Friendly Trader"
)

st.caption(
    "Trade Smart. Trade Friendly. — "
    "Alpha 1.2 Research Prototype"
)


# =========================================================
# MARKET DATA
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

    df = (
        df
        .dropna()
        .sort_values("time")
        .reset_index(drop=True)
    )

    return df


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
        "Signal engine failed."
    )

    st.exception(error)

    st.stop()


direction = signal.get(
    "direction",
    "WAIT"
)

score = int(
    signal.get(
        "score",
        0
    )
)

entry = float(
    signal.get(
        "entry",
        df_15m["close"].iloc[-1]
    )
)

sl = float(
    signal.get(
        "sl",
        entry
    )
)

tp = float(
    signal.get(
        "tp",
        entry
    )
)

buy_score = float(
    signal.get(
        "buy_score",
        0
    )
)

sell_score = float(
    signal.get(
        "sell_score",
        0
    )
)

rsi = float(
    signal.get(
        "rsi",
        50
    )
)

atr = float(
    signal.get(
        "atr",
        0
    )
)

momentum = float(
    signal.get(
        "momentum",
        0
    )
)

h1_trend = signal.get(
    "h1_trend",
    "NEUTRAL"
)

h4_trend = signal.get(
    "h4_trend",
    "NEUTRAL"
)


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
    f"{score}/10"
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
# SIGNAL DETAILS
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
    f"**Setup Score:** {score}/10"
)

st.write(
    f"**BUY Score:** {buy_score:.2f}/10"
)

st.write(
    f"**SELL Score:** {sell_score:.2f}/10"
)

st.write(
    f"**RSI:** {rsi:.2f}"
)

st.write(
    f"**ATR:** {atr:.2f}"
)

st.write(
    f"**Momentum:** {momentum:.2f}"
)

st.write(
    f"**1H Trend:** {h1_trend}"
)

st.write(
    f"**4H Trend:** {h4_trend}"
)


if direction == "WAIT":

    st.warning(
        "No sufficiently strong setup. "
        "Friendly Trader recommends waiting."
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
# BACKTEST
# =========================================================

st.divider()

st.subheader(
    "🧪 Alpha 1.2 Research Backtest"
)


def run_backtest(
    df_15m,
    df_1h,
    df_4h
):

    results = []

    minimum_candles = 220

    horizon = 20

    last_index = (
        len(df_15m) -
        horizon
    )

    for i in range(
        minimum_candles,
        last_index
    ):

        current_15m = (
            df_15m
            .iloc[:i + 1]
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

        if len(current_1h) < 50:
            continue

        if len(current_4h) < 50:
            continue

        try:

            s = generate_signal(
                current_15m,
                current_1h,
                current_4h
            )

        except Exception:

            continue

        direction_bt = s.get(
            "direction",
            "WAIT"
        )

        if direction_bt not in [
            "BUY",
            "SELL"
        ]:

            continue

        entry_bt = float(
            s["entry"]
        )

        stop_bt = float(
            s["sl"]
        )

        target_bt = float(
            s["tp"]
        )

        future = df_15m.iloc[
            i + 1:
            i + 1 + horizon
        ]

        if future.empty:
            continue

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

            if direction_bt == "BUY":

                stop_hit = (
                    low <= stop_bt
                )

                target_hit = (
                    high >= target_bt
                )

            else:

                stop_hit = (
                    high >= stop_bt
                )

                target_hit = (
                    low <= target_bt
                )

            if (
                stop_hit
                and target_hit
            ):

                result = "LOSS"

                result_r = -1.0

                exit_price = stop_bt

                exit_time = candle["time"]

                break

            if stop_hit:

                result = "LOSS"

                result_r = -1.0

                exit_price = stop_bt

                exit_time = candle["time"]

                break

            if target_hit:

                result = "WIN"

                result_r = 3.0

                exit_price = target_bt

                exit_time = candle["time"]

                break

        results.append(
            {
                "Signal Time": current_time,
                "Direction": direction_bt,
                "Score": int(
                    s.get(
                        "score",
                        0
                    )
                ),
                "BUY Score": float(
                    s.get(
                        "buy_score",
                        0
                    )
                ),
                "SELL Score": float(
                    s.get(
                        "sell_score",
                        0
                    )
                ),
                "RSI": float(
                    s.get(
                        "rsi",
                        50
                    )
                ),
                "Momentum": float(
                    s.get(
                        "momentum",
                        0
                    )
                ),
                "ATR": float(
                    s.get(
                        "atr",
                        0
                    )
                ),
                "Entry": round(
                    entry_bt,
                    2
                ),
                "SL": round(
                    stop_bt,
                    2
                ),
                "TP": round(
                    target_bt,
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
# RUN BACKTEST
# =========================================================

try:

    with st.spinner(
        "Running Alpha 1.2 research backtest..."
    ):

        results = run_backtest(
            df_15m,
            df_1h,
            df_4h
        )

    if not results:

        st.warning(
            "No qualifying trades were found "
            "in the available historical data."
        )

    else:

        journal = pd.DataFrame(
            results
        )

        # -------------------------------------------------
        # OVERALL STATISTICS
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
            wins /
            trades *
            100
        )

        net_r = (
            journal["R"].sum()
        )

        gross_profit = (
            journal.loc[
                journal["R"] > 0,
                "R"
            ].sum()
        )

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
        # MAX LOSING STREAK
        # -------------------------------------------------

        current_streak = 0

        max_streak = 0

        for r in journal["R"]:

            if r < 0:

                current_streak += 1

                max_streak = max(
                    max_streak,
                    current_streak
                )

            else:

                current_streak = 0

        # -------------------------------------------------
        # MAIN METRICS
        # -------------------------------------------------

        b1, b2, b3, b4, b5 = st.columns(5)

        b1.metric(
            "Trades",
            trades
        )

        b2.metric(
            "Win Rate",
            f"{win_rate:.1f}%"
        )

        b3.metric(
            "Net R",
            f"{net_r:.2f}R"
        )

        b4.metric(
            "Profit Factor",
            (
                "∞"
                if profit_factor == float("inf")
                else f"{profit_factor:.2f}"
            )
        )

        b5.metric(
            "Max Drawdown",
            f"{max_drawdown:.2f}R"
        )

        e1, e2, e3 = st.columns(3)

        e1.metric(
            "Expectancy",
            f"{expectancy:.3f}R"
        )

        e2.metric(
            "Timeouts",
            timeouts
        )

        e3.metric(
            "Max Losing Streak",
            max_streak
        )

        # -------------------------------------------------
        # DIRECTION ANALYSIS
        # -------------------------------------------------

        st.subheader(
            "📊 BUY vs SELL Analysis"
        )

        buy_trades = journal[
            journal["Direction"] == "BUY"
        ]

        sell_trades = journal[
            journal["Direction"] == "SELL"
        ]

        a1, a2 = st.columns(2)

        with a1:

            st.write("**BUY**")

            if len(buy_trades) > 0:

                buy_wins = (
                    buy_trades["Result"] ==
                    "WIN"
                ).sum()

                buy_win_rate = (
                    buy_wins /
                    len(buy_trades) *
                    100
                )

                buy_net_r = (
                    buy_trades["R"].sum()
                )

                st.metric(
                    "BUY Trades",
                    len(buy_trades)
                )

                st.metric(
                    "BUY Win Rate",
                    f"{buy_win_rate:.1f}%"
                )

                st.metric(
                    "BUY Net R",
                    f"{buy_net_r:.2f}R"
                )

            else:

                st.info(
                    "No BUY trades."
                )

        with a2:

            st.write("**SELL**")

            if len(sell_trades) > 0:

                sell_wins = (
                    sell_trades["Result"] ==
                    "WIN"
                ).sum()

                sell_win_rate = (
                    sell_wins /
                    len(sell_trades) *
                    100
                )

                sell_net_r = (
                    sell_trades["R"].sum()
                )

                st.metric(
                    "SELL Trades",
                    len(sell_trades)
                )

                st.metric(
                    "SELL Win Rate",
                    f"{sell_win_rate:.1f}%"
                )

                st.metric(
                    "SELL Net R",
                    f"{sell_net_r:.2f}R"
                )

            else:

                st.info(
                    "No SELL trades."
                )

        # -------------------------------------------------
        # SCORE ANALYSIS
        # -------------------------------------------------

        st.subheader(
            "🎯 Performance by Score"
        )

        score_analysis = (
            journal
            .groupby("Score")
            .agg(
                Trades=("R", "count"),
                Wins=(
                    "Result",
                    lambda x:
                    (x == "WIN").sum()
                ),
                Net_R=("R", "sum"),
                Average_R=("R", "mean")
            )
            .reset_index()
        )

        score_analysis["Win Rate %"] = (
            score_analysis["Wins"] /
            score_analysis["Trades"] *
            100
        )

        score_analysis = score_analysis[
            [
                "Score",
                "Trades",
                "Wins",
                "Win Rate %",
                "Net_R",
                "Average_R"
            ]
        ]

        st.dataframe(
            score_analysis,
            use_container_width=True,
            hide_index=True
        )

        # -------------------------------------------------
        # EQUITY CURVE
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
            yaxis_title="Cumulative R"
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
        "Backtest failed."
    )

    st.exception(error)


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "Alpha 1.2 is a research prototype. "
    "Market data comes from Twelve Data. "
    "Backtest results are historical research only "
    "and are not proof of future performance. "
    "Real-money execution is disabled."
    )
