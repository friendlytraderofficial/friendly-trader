import numpy as np
import pandas as pd


def add_indicators(df):

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

    # RSI
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

    # ATR
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

    # ATR percentage
    data["atr_pct"] = (
        data["atr"] /
        data["close"]
    ) * 100

    return data


def get_trend(df):

    data = add_indicators(df)

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


def generate_signal(
    df_15m,
    df_1h,
    df_4h
):

    data = add_indicators(
        df_15m
    ).dropna()

    if data.empty:

        raise ValueError(
            "Not enough 15M data."
        )

    row = data.iloc[-1]

    price = float(
        row["close"]
    )

    atr = float(
        row["atr"]
    )

    if not np.isfinite(atr) or atr <= 0:

        atr = price * 0.001


    # =====================================================
    # HIGHER TIMEFRAME TRENDS
    # =====================================================

    h1_trend = get_trend(
        df_1h
    )

    h4_trend = get_trend(
        df_4h
    )

# =====================================================
# SCORE — SELECTIVE ALPHA 0.9
# =====================================================

buy_score = 0
sell_score = 0


# -----------------------------------------------------
# 1. 15M TREND ALIGNMENT
# -----------------------------------------------------

bullish_15m = (
    row["ema20"] >
    row["ema50"] >
    row["ema200"]
)

bearish_15m = (
    row["ema20"] <
    row["ema50"] <
    row["ema200"]
)


# -----------------------------------------------------
# 2. HIGHER TIMEFRAME CONFIRMATION
# -----------------------------------------------------

bullish_higher_tf = (
    h1_trend == "BULLISH"
    and
    h4_trend == "BULLISH"
)

bearish_higher_tf = (
    h1_trend == "BEARISH"
    and
    h4_trend == "BEARISH"
)


# -----------------------------------------------------
# 3. RSI
# -----------------------------------------------------

bullish_rsi = (
    52 <= rsi <= 65
)

bearish_rsi = (
    35 <= rsi <= 48
)


# -----------------------------------------------------
# 4. EMA20 ENTRY LOCATION
# -----------------------------------------------------

distance_from_ema20 = (
    abs(
        price -
        row["ema20"]
    ) /
    price
) * 100


near_ema20 = (
    distance_from_ema20 <= 0.15
)


price_above_ema20 = (
    price > row["ema20"]
)

price_below_ema20 = (
    price < row["ema20"]
)


# =====================================================
# BUY SCORE
# =====================================================

if bullish_15m:

    buy_score += 2


if h1_trend == "BULLISH":

    buy_score += 1


if h4_trend == "BULLISH":

    buy_score += 1


if bullish_rsi:

    buy_score += 2


if (
    near_ema20
    and
    price_above_ema20
):

    buy_score += 2


# =====================================================
# SELL SCORE
# =====================================================

if bearish_15m:

    sell_score += 2


if h1_trend == "BEARISH":

    sell_score += 1


if h4_trend == "BEARISH":

    sell_score += 1


if bearish_rsi:

    sell_score += 2


if (
    near_ema20
    and
    price_below_ema20
):

    sell_score += 2


# =====================================================
# MAXIMUM SCORE = 8
# =====================================================

score = max(
    buy_score,
    sell_score
)
    

    

    


    # =====================================================
    # MAXIMUM SCORE = 10
    # =====================================================

    score = max(
        buy_score,
        sell_score
    )


    # =====================================================
# SIGNAL THRESHOLD
# =====================================================

if (
    buy_score >= 7
    and
    buy_score > sell_score
    and
    bullish_15m
    and
    bullish_higher_tf
):

    direction = "BUY"

elif (
    sell_score >= 7
    and
    sell_score > buy_score
    and
    bearish_15m
    and
    bearish_higher_tf
):

    direction = "SELL"

else:

    direction = "WAIT"

    
        


    # =====================================================
    # ATR RISK MODEL
    # =====================================================

    stop_distance = (
        atr * 1.5
    )

    take_profit_distance = (
        stop_distance * 3
    )


    if direction == "BUY":

        entry = price

        sl = (
            entry -
            stop_distance
        )

        tp = (
            entry +
            take_profit_distance
        )


    elif direction == "SELL":

        entry = price

        sl = (
            entry +
            stop_distance
        )

        tp = (
            entry -
            take_profit_distance
        )


    else:

        entry = price

        sl = price

        tp = price


    return {
        "direction": direction,
        "score": int(score),
        "entry": round(
            entry,
            2
        ),
        "sl": round(
            sl,
            2
        ),
        "tp": round(
            tp,
            2
        ),
        "h1_trend": h1_trend,
        "h4_trend": h4_trend
        }
