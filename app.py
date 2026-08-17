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
    "Trade Smart. Trade Friendly. — Alpha 1.1 Research Prototype"
)


# =========================================================
# MARKET DATA
# =========================================================

@st.cache_data(ttl=60)
def get_market_data(interval, outputsize):

    api_key = st.secrets["TWELVE_DATA_API_KEY"]

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
# SIGNAL
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


direction = signal["direction"]
score = signal["score"]
entry = signal["entry"]
sl = signal["sl"]
tp = signal["tp"]

buy_score = signal["buy_score"]
sell_score = signal["sell_score"]

h1_trend = signal["h1_trend"]
h4_trend = signal["h4_trend"]

rsi = signal["rsi"]
atr = signal["atr"]
momentum = signal["momentum"]


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
    f"**Momentum:** {momentum}%"
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
    "🧪 Alpha 1.1 Research Backtest"
)


 def run_backtest(
    df_15m,
    df_1h,
    df_4h
):

    results = []

    minimum_candles = 220
    horizon = 20

    last_index = len(df_15m) - horizon

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

            signal = generate_signal(
                current_15m,
                current_1h,
                current_4h
            )

        except Exception:
            continue

        direction = signal.get(
            "direction",
            "WAIT"
        )

        # -------------------------------------------------
        # WAIT IS NOT A TRADE
        # -------------------------------------------------

        if direction not in [
            "BUY",
            "SELL"
        ]:
            continue

        entry = float(
            signal["entry"]
        )

        stop = float(
            signal["sl"]
        )

        target = float(
            signal["tp"]
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

        # -------------------------------------------------
        # CHECK FUTURE PRICE ACTION
        # -------------------------------------------------

        for _, candle in future.iterrows():

            high = float(
                candle["high"]
            )

            low = float(
                candle["low"]
            )

            if direction == "BUY":

                stop_hit = (
                    low <= stop
                )

                target_hit = (
                    high >= target
                )

            else:

                stop_hit = (
                    high >= stop
                )

                target_hit = (
                    low <= target
                )

            # Conservative assumption:
            # if SL and TP are both touched
            # in one candle, SL happens first.

            if (
                stop_hit
                and target_hit
            ):

                result = "LOSS"

                result_r = -1.0

                exit_price = stop

                exit_time = candle["time"]

                break

            if stop_hit:

                result = "LOSS"

                result_r = -1.0

                exit_price = stop

                exit_time = candle["time"]

                break

            if target_hit:

                result = "WIN"

                result_r = 3.0

                exit_price = target

                exit_time = candle["time"]

                break

        # -------------------------------------------------
        # SAVE TRADE
        # -------------------------------------------------

        results.append(
            {
                "Signal Time": current_time,

                "Direction": direction,

                "Score": int(
                    signal.get(
                        "score",
                        0
                    )
                ),

                "BUY Score": float(
                    signal.get(
                        "buy_score",
                        0
                    )
                ),

                "SELL Score": float(
                    signal.get(
                        "sell_score",
                        0
                    )
                ),

                "RSI": float(
                    signal.get(
                        "rsi",
                        50
                    )
                ),

                "Momentum": float(
                    signal.get(
                        "momentum",
                        0
                    )
                ),

                "ATR": float(
                    signal.get(
                        "atr",
                        0
                    )
                ),

                "Entry": round(
                    entry,
                    2
                ),

                "SL": round(
                    stop,
                    2
                ),

                "TP": round(
                    target,
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

    
            
        
            

            
                
                
        

        
        

            
        

        
        
        
        
        

        
        


    "and are not proof of future performance. "
    "Real-money execution is disabled."
    )
