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


# =========================================================
# TITLE
# =========================================================

st.title("Friendly Trader")

st.caption(
    "Trade Smart. Trade Friendly. — Alpha 0.9 Research Prototype"
)


# =========================================================
# TWELVE DATA
# =========================================================

@st.cache_data(ttl=60)
def get_market_data(
    interval,
    outputsize
):

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

    live_signal = generate_signal(
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


direction = live_signal.get(
    "direction",
    "WAIT"
)

score = int(
    live_signal.get(
        "score",
        0
    )
)

entry = float(
    live_signal.get(
        "entry",
        df_15m["close"].iloc[-1]
    )
)

sl = float(
    live_signal.get(
        "sl",
        entry
    )
)

tp = float(
    live_signal.get(
        "tp",
        entry
    )
)

h1_trend = live_signal.get(
    "h1_trend",
    "NEUTRAL"
)

h4_trend = live_signal.get(
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
    f"**1H Trend:** {h1_trend}"
)

st.write(
    f"**4H Trend:** {h4_trend}"
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
# BACKTEST
# =========================================================

st.divider()

st.subheader(
    "🧪 50-Trade Research Backtest"
)


def run_same_strategy_backtest(
    df_15m,
    df_1h,
    df_4h
):

    results = []

    total_candles = len(
        df_15m
    )

    # We need enough future candles
    # to determine whether SL or TP
    # was hit.

    max_index = (
        total_candles - 21
    )

    if max_index <= 0:

        return results


    for i in range(
        max_index
    ):

        if len(results) >= 50:

            break


        current_15m = (
            df_15m.iloc[
                : i + 1
            ].copy()
        )


        if len(current_15m) < 50:

            continue


        current_time = (
            current_15m["time"].iloc[-1]
        )


        # Only use higher-timeframe
        # candles that already existed
        # at the moment of the signal.

        current_1h = (
            df_1h[
                df_1h["time"] <= current_time
            ].copy()
        )

        current_4h = (
            df_4h[
                df_4h["time"] <= current_time
            ].copy()
        )


        if len(current_1h) < 50:

            continue

        if len(current_4h) < 50:

            continue


        try:

            signal = generate_signal(
                current_15m,
                current_1h,
                current_4h
            )

        except Exception:

            continue


        direction_bt = signal.get(
            "direction",
            "WAIT"
        )


        if direction_bt not in [
            "BUY",
            "SELL"
        ]:

            continue


        entry_bt = float(
            signal["entry"]
        )

        sl_bt = float(
            signal["sl"]
        )

        tp_bt = float(
            signal["tp"]
        )


        # -------------------------------------------------
        # Future candles
        # -------------------------------------------------

        future = df_15m.iloc[
            i + 1 :
            i + 21
        ]


        result_r = None

        exit_price = None

        exit_time = None


        for _, candle in future.iterrows():

            high = float(
                candle["high"]
            )

            low = float(
                candle["low"]
            )


            if direction_bt == "BUY":

                stop_hit = (
                    low <= sl_bt
                )

                target_hit = (
                    high >= tp_bt
                )


                # Conservative rule:
                # if both are touched inside
                # the same candle, assume SL
                # happened first.

                if stop_hit:

                    result_r = -1.0

                    exit_price = sl_bt

                    exit_time = candle["time"]

                    break


                if target_hit:

                    result_r = 3.0

                    exit_price = tp_bt

                    exit_time = candle["time"]

                    break


            else:

                stop_hit = (
                    high >= sl_bt
                )

                target_hit = (
                    low <= tp_bt
                )


                if stop_hit:

                    result_r = -1.0

                    exit_price = sl_bt

                    exit_time = candle["time"]

                    break


                if target_hit:

                    result_r = 3.0

                    exit_price = tp_bt

                    exit_time = candle["time"]

                    break


        if result_r is None:

            continue


        results.append(
            {
                "Signal Time": current_time,
                "Direction": direction_bt,
                "Score": int(
                    signal.get(
                        "score",
                        0
                    )
                ),
                "Entry": round(
                    entry_bt,
                    2
                ),
                "Stop Loss": round(
                    sl_bt,
                    2
                ),
                "Take Profit": round(
                    tp_bt,
                    2
                ),
                "Result R": result_r,
                "Exit Time": exit_time,
                "Exit Price": round(
                    exit_price,
                    2
                )
            }
        )


    return results


# =========================================================
# RUN
# =========================================================

try:

    with st.spinner(
        "Running the same Alpha 0.9 strategy "
        "through historical candles..."
    ):

        backtest_results = (
            run_same_strategy_backtest(
                df_15m,
                df_1h,
                df_4h
            )
        )


    if not backtest_results:

        st.warning(
            "No completed qualifying trades "
            "were found in the available data."
        )

    else:

        journal = pd.DataFrame(
            backtest_results
        )


        # -------------------------------------------------
        # PERFORMANCE
        # -------------------------------------------------

        trades = len(
            journal
        )

        wins = (
            journal["Result R"] > 0
        ).sum()

        losses = (
            journal["Result R"] < 0
        ).sum()

        win_rate = (
            wins /
            trades
        ) * 100


        net_r = (
            journal["Result R"]
            .sum()
        )


        gross_profit = (
            journal.loc[
                journal["Result R"] > 0,
                "Result R"
            ]
            .sum()
        )


        gross_loss = abs(
            journal.loc[
                journal["Result R"] < 0,
                "Result R"
            ]
            .sum()
        )


        if gross_loss > 0:

            profit_factor = (
                gross_profit /
                gross_loss
            )

        else:

            profit_factor = 0.0


        # -------------------------------------------------
        # EQUITY / DRAWDOWN
        # -------------------------------------------------

        equity = (
            journal["Result R"]
            .cumsum()
        )

        running_peak = (
            equity.cummax()
        )

        drawdown = (
            equity -
            running_peak
        )

        max_drawdown = (
            drawdown.min()
        )


        # -------------------------------------------------
        # DISPLAY
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
            f"{profit_factor:.2f}"
        )

        b5.metric(
            "Max Drawdown",
            f"{max_drawdown:.2f}R"
        )


        # -------------------------------------------------
        # EQUITY CURVE
        # -------------------------------------------------

        st.subheader(
            "📈 Research Equity Curve"
        )

        equity_chart = go.Figure()

        equity_chart.add_trace(
            go.Scatter(
                x=list(
                    range(
                        1,
                        len(equity) + 1
                    )
                ),
                y=equity,
                mode="lines+markers",
                name="Net R"
            )
        )

        equity_chart.update_layout(
            height=350,
            xaxis_title="Trade",
            yaxis_title="Cumulative R"
        )

        st.plotly_chart(
            equity_chart,
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
    "Alpha 0.9 is a research prototype. "
    "The backtest uses the same signal engine "
    "as the live dashboard. "
    "Results are research results only and "
    "are not proof of future performance. "
    "Real-money execution is disabled."
    )
