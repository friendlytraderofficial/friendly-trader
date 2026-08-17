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
    "Trade Smart. Trade Friendly. — "
    "Alpha 1.1 Research Prototype"
)


# =========================================================
# DATA
# =========================================================

@st.cache_data(ttl=60)
def get_market_data(interval, outputsize):

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

h1_trend = signal.get(
    "h1_trend",
    "NEUTRAL"
)

h4_trend = signal.get(
    "h4_trend",
    "NEUTRAL"
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
    direction
)

c3.metric(
    "Score",
    f"{score}/10"
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
    f"**1H Trend:** {h1_trend}"
)

st.write(
    f"**4H Trend:** {h4_trend}"
)


if direction == "WAIT":

    st.warning(
        "No sufficiently strong setup. "
        "Waiting for confirmation."
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
    "🧪 Alpha 1.1 Research Backtest"
)


def run_backtest(
    df_15m,
    df_1h,
    df_4h
):

    results = []

    # -----------------------------------------------------
    # Maximum number of future candles used for a trade.
    #
    # 20 × 15 minutes = 5 hours.
    # -----------------------------------------------------

    horizon = 20

    # Need enough candles for the indicator engine.
    minimum_15m = 220

    last_index = (
        len(df_15m) -
        horizon
    )

    if last_index <= minimum_15m:

        return results


    # -----------------------------------------------------
    # Process historical signals
    # -----------------------------------------------------

    for i in range(
        minimum_15m,
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


        # -------------------------------------------------
        # IMPORTANT:
        #
        # Only use higher-timeframe candles that have
        # already CLOSED before this signal.
        #
        # This prevents using information from an
        # unfinished 1H/4H candle.
        # -------------------------------------------------

        current_1h = (
            df_1h[
                df_1h["time"] <
                current_time.floor("1h")
            ]
            .copy()
        )

        current_4h = (
            df_4h[
                df_4h["time"] <
                current_time.floor("4h")
            ]
            .copy()
        )


        # The strategy itself needs enough data.
        if len(current_1h) < 50:

            continue

        if len(current_4h) < 50:

            continue


        # -------------------------------------------------
        # Generate historical signal
        # -------------------------------------------------

        try:

            historical_signal = (
                generate_signal(
                    current_15m,
                    current_1h,
                    current_4h
                )
            )

        except Exception:

            continue


        historical_direction = (
            historical_signal.get(
                "direction",
                "WAIT"
            )
        )


        # Ignore WAIT signals.
        if historical_direction == "WAIT":

            continue


        historical_entry = float(
            historical_signal["entry"]
        )

        historical_stop = float(
            historical_signal["sl"]
        )

        historical_target = float(
            historical_signal["tp"]
        )


        # -------------------------------------------------
        # Risk per trade
        # -------------------------------------------------

        if historical_direction == "BUY":

            risk_distance = (
                historical_entry -
                historical_stop
            )

        else:

            risk_distance = (
                historical_stop -
                historical_entry
            )


        if risk_distance <= 0:

            continue


        # -------------------------------------------------
        # Future candles
        # -------------------------------------------------

        future = df_15m.iloc[
            i + 1:
            i + 1 + horizon
        ]


        if future.empty:

            continue


        # -------------------------------------------------
        # Default outcome = TIMEOUT
        #
        # But unlike the old version, timeout is NOT
        # automatically assigned 0R.
        #
        # We calculate the actual R at the final close.
        # -------------------------------------------------

        result = "TIMEOUT"

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


            if historical_direction == "BUY":

                stop_hit = (
                    low <= historical_stop
                )

                target_hit = (
                    high >= historical_target
                )

            else:

                stop_hit = (
                    high >= historical_stop
                )

                target_hit = (
                    low <= historical_target
                )


            # -------------------------------------------------
            # Conservative same-candle rule
            # -------------------------------------------------

            if (
                stop_hit
                and
                target_hit
            ):

                result = "LOSS"

                exit_price = (
                    historical_stop
                )

                exit_time = (
                    candle["time"]
                )

                break


            if stop_hit:

                result = "LOSS"

                exit_price = (
                    historical_stop
                )

                exit_time = (
                    candle["time"]
                )

                break


            if target_hit:

                result = "WIN"

                exit_price = (
                    historical_target
                )

                exit_time = (
                    candle["time"]
                )

                break


        # -------------------------------------------------
        # Calculate actual R
        # -------------------------------------------------

        if historical_direction == "BUY":

            result_r = (
                exit_price -
                historical_entry
            ) / risk_distance

        else:

            result_r = (
                historical_entry -
                exit_price
            ) / risk_distance


        # -------------------------------------------------
        # Safety clamp
        #
        # A timeout should not magically produce more
        # than the predefined target.
        # -------------------------------------------------

        if result == "TIMEOUT":

            result_r = max(
                -1.0,
                min(
                    3.0,
                    result_r
                )
            )


        # -------------------------------------------------
        # Record trade
        # -------------------------------------------------

        results.append(
            {
                "Signal Time": current_time,

                "Direction": historical_direction,

                "Score": int(
                    historical_signal.get(
                        "score",
                        0
                    )
                ),

                "BUY Score": float(
                    historical_signal.get(
                        "buy_score",
                        0
                    )
                ),

                "SELL Score": float(
                    historical_signal.get(
                        "sell_score",
                        0
                    )
                ),

                "RSI": float(
                    historical_signal.get(
                        "rsi",
                        50
                    )
                ),

                "Entry": round(
                    historical_entry,
                    2
                ),

                "SL": round(
                    historical_stop,
                    2
                ),

                "TP": round(
                    historical_target,
                    2
                ),

                "Result": result,

                "R": round(
                    result_r,
                    3
                ),

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
        "Running Alpha 1.1 research backtest..."
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
        # BASIC STATISTICS
        # -------------------------------------------------

        trades = len(
            journal
        )

        wins = (
            journal["Result"] ==
            "WIN"
        ).sum()

        losses = (
            journal["Result"] ==
            "LOSS"
        ).sum()

        timeouts = (
            journal["Result"] ==
            "TIMEOUT"
        ).sum()


        # -------------------------------------------------
        # WIN RATE
        #
        # Win rate now means actual TP winners /
        # all completed research trades.
        # -------------------------------------------------

        win_rate = (
            wins /
            trades *
            100
        )


        # -------------------------------------------------
        # NET R
        # -------------------------------------------------

        net_r = (
            journal["R"].sum()
        )


        # -------------------------------------------------
        # PROFIT FACTOR
        # -------------------------------------------------

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


        # -------------------------------------------------
        # EXPECTANCY
        # -------------------------------------------------

        expectancy = (
            net_r /
            trades
        )


        # -------------------------------------------------
        # EQUITY
        # -------------------------------------------------

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
        # AVERAGE TIMEOUT R
        # -------------------------------------------------

        timeout_r = journal.loc[
            journal["Result"] ==
            "TIMEOUT",
            "R"
        ]


        if len(timeout_r) > 0:

            average_timeout_r = (
                timeout_r.mean()
            )

        else:

            average_timeout_r = 0.0


        # -------------------------------------------------
        # DISPLAY MAIN METRICS
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


        # -------------------------------------------------
        # SECONDARY METRICS
        # -------------------------------------------------

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
        # TIMEOUT INFORMATION
        # -------------------------------------------------

        st.write(
            f"**Average Timeout Result:** "
            f"{average_timeout_r:.3f}R"
        )


        st.caption(
            "Timeout trades are now closed at the "
            "final candle close and contribute their "
            "actual gain/loss in R. They are no longer "
            "automatically counted as 0R."
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
 
