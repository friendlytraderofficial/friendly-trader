import numpy as np
import pandas as pd


# =========================================================
# ALPHA 1.0 — INDICATORS
# =========================================================

def prepare_indicators(df):
    data = df.copy()

    data["time"] = pd.to_datetime(data["time"])

    data = data.sort_values("time").reset_index(drop=True)

    for col in ["open", "high", "low", "close"]:
        data[col] = pd.to_numeric(
            data[col],
            errors="coerce"
        )

    # EMA
    data["ema20"] = data["close"].ewm(
        span=20,
        adjust=False
    ).mean()

    data["ema50"] = data["close"].ewm(
        span=50,
        adjust=False
    ).mean()

    data["ema200"] = data["close"].ewm(
        span=200,
        adjust=False
    ).mean()

    # RSI
    delta = data["close"].diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1 / 14,
        adjust=False
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / 14,
        adjust=False
    ).mean()

    rs = avg_gain / avg_loss.replace(
        0,
        np.nan
    )

    data["rsi"] = (
        100 -
        (100 / (1 + rs))
    )

    # ATR
    previous_close = data["close"].shift(1)

    tr = pd.concat(
        [
            data["high"] - data["low"],
            (
                data["high"] -
                previous_close
            ).abs(),
            (
                data["low"] -
                previous_close
            ).abs()
        ],
        axis=1
    ).max(axis=1)

    data["atr"] = tr.ewm(
        alpha=1 / 14,
        adjust=False
    ).mean()

    # Candle body
    data["body"] = (
        data["close"] -
        data["open"]
    )

    data["body_size"] = (
        data["body"].abs()
    )

    # Recent momentum
    data["roc_5"] = (
        data["close"].pct_change(5) * 100
    )

    return data


# =========================================================
# TREND
# =========================================================

def get_trend(df):

    data = prepare_indicators(df).dropna()

    if len(data) < 5:
        return "NEUTRAL"

    row = data.iloc[-1]

    if (
        row["ema20"] > row["ema50"]
        and
        row["ema50"] > row["ema200"]
    ):
        return "BULLISH"

    if (
        row["ema20"] < row["ema50"]
        and
        row["ema50"] < row["ema200"]
    ):
        return "BEARISH"

    return "NEUTRAL"


# =========================================================
# SCORE COMPONENT
# =========================================================

def clamp(value, low=0.0, high=100.0):

    return max(
        low,
        min(high, value)
    )


# =========================================================
# ALPHA 1.0 SIGNAL
# =========================================================

def generate_signal(
    df_15m,
    df_1h,
    df_4h
):

    data = prepare_indicators(
        df_15m
    ).dropna()

    if len(data) < 200:

        raise ValueError(
            "Not enough 15M data for Alpha 1.0."
        )

    row = data.iloc[-1]
    previous = data.iloc[-2]

    price = float(
        row["close"]
    )

    atr = float(
        row["atr"]
    )

    rsi = float(
        row["rsi"]
    )

    roc = float(
        row["roc_5"]
    )

    ema20 = float(
        row["ema20"]
    )

    ema50 = float(
        row["ema50"]
    )

    ema200 = float(
        row["ema200"]
    )

    if not np.isfinite(atr) or atr <= 0:

        atr = price * 0.001


    # =====================================================
    # HIGHER TIMEFRAME TREND
    # =====================================================

    h1_trend = get_trend(
        df_1h
    )

    h4_trend = get_trend(
        df_4h
    )


    # =====================================================
    # 15M TREND STRENGTH
    # =====================================================

    bullish_trend = (
        ema20 > ema50 > ema200
    )

    bearish_trend = (
        ema20 < ema50 < ema200
    )


    # =====================================================
    # TREND SCORE
    # =====================================================

    buy_trend = 0.0
    sell_trend = 0.0

    if bullish_trend:
        buy_trend += 25

    elif price > ema50:
        buy_trend += 12

    if h1_trend == "BULLISH":
        buy_trend += 15

    elif h1_trend == "NEUTRAL":
        buy_trend += 7


    if h4_trend == "BULLISH":
        buy_trend += 15

    elif h4_trend == "NEUTRAL":
        buy_trend += 7


    if bearish_trend:
        sell_trend += 25

    elif price < ema50:
        sell_trend += 12

    if h1_trend == "BEARISH":
        sell_trend += 15

    elif h1_trend == "NEUTRAL":
        sell_trend += 7


    if h4_trend == "BEARISH":
        sell_trend += 15

    elif h4_trend == "NEUTRAL":
        sell_trend += 7


    # =====================================================
    # MOMENTUM
    # =====================================================

    buy_momentum = 0.0
    sell_momentum = 0.0

    if 52 <= rsi <= 62:
        buy_momentum += 20

    elif 50 <= rsi < 52:
        buy_momentum += 10

    elif 62 < rsi <= 68:
        buy_momentum += 8


    if 38 <= rsi <= 48:
        sell_momentum += 20

    elif 48 < rsi <= 50:
        sell_momentum += 10

    elif 32 <= rsi < 38:
        sell_momentum += 8


    if roc > 0:
        buy_momentum += 10

    if roc < 0:
        sell_momentum += 10


    # =====================================================
    # CANDLE CONFIRMATION
    # =====================================================

    buy_candle = 0.0
    sell_candle = 0.0

    if row["close"] > row["open"]:
        buy_candle += 8

    if row["close"] < row["open"]:
        sell_candle += 8


    if row["close"] > previous["close"]:
        buy_candle += 7

    if row["close"] < previous["close"]:
        sell_candle += 7


    # =====================================================
    # ENTRY QUALITY
    # =====================================================

    distance_atr = abs(
        price - ema20
    ) / atr

    buy_entry = 0.0
    sell_entry = 0.0

    # Ideal entry is reasonably close
    # to the short-term trend.

    if distance_atr <= 0.75:

        if price >= ema20:
            buy_entry += 10

        if price <= ema20:
            sell_entry += 10

    elif distance_atr <= 1.25:

        buy_entry += 5
        sell_entry += 5

    # Strong extension is penalized.
    elif distance_atr > 2.0:

        buy_entry -= 15
        sell_entry -= 15


    # =====================================================
    # FINAL RAW SCORES
    # =====================================================

    buy_raw = (
        buy_trend +
        buy_momentum +
        buy_candle +
        buy_entry
    )

    sell_raw = (
        sell_trend +
        sell_momentum +
        sell_candle +
        sell_entry
    )


    # Normalize to 0-10.
    buy_score = clamp(
        buy_raw / 10
    )

    sell_score = clamp(
        sell_raw / 10
    )


    # =====================================================
    # CONFIDENCE GAP
    # =====================================================

    strongest = max(
        buy_score,
        sell_score
    )

    weakest = min(
        buy_score,
        sell_score
    )

    gap = (
        strongest -
        weakest
    )


    # =====================================================
    # SIGNAL DECISION
    # =====================================================

    direction = "WAIT"

    if (
        buy_score >= 7.5
        and
        buy_score > sell_score
        and
        gap >= 1.5
    ):

        direction = "BUY"

    elif (
        sell_score >= 7.5
        and
        sell_score > buy_score
        and
        gap >= 1.5
    ):

        direction = "SELL"


    # =====================================================
    # DISPLAY SCORE
    # =====================================================

    if direction == "BUY":

        score = int(
            round(buy_score)
        )

    elif direction == "SELL":

        score = int(
            round(sell_score)
        )

    else:

        score = int(
            round(
                max(
                    buy_score,
                    sell_score
                )
            )
        )


    score = int(
        clamp(
            score,
            0,
            10
        )
    )


    # =====================================================
    # RISK MODEL
    # =====================================================

    stop_distance = atr * 1.5

    target_distance = (
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
            target_distance
        )

    elif direction == "SELL":

        entry = price

        sl = (
            entry +
            stop_distance
        )

        tp = (
            entry -
            target_distance
        )

    else:

        entry = price
        sl = price
        tp = price


    return {
        "direction": direction,
        "score": score,
        "buy_score": round(
            buy_score,
            2
        ),
        "sell_score": round(
            sell_score,
            2
        ),
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
        "h4_trend": h4_trend,
        "rsi": round(
            rsi,
            2
        ),
        "atr": round(
            atr,
            2
        )
    }
