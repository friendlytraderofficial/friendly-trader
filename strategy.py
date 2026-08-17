import pandas as pd
import numpy as np
print("DEBUG: NEW STRATEGY FILE LOADED")

# =========================================================
# INDICATORS
# =========================================================

def calculate_rsi(series, period=14):
    delta = series.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1 / period,
        min_periods=period,
        adjust=False
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / period,
        min_periods=period,
        adjust=False
    ).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)

    rsi = 100 - (100 / (1 + rs))

    return rsi.fillna(50)


def calculate_atr(df, period=14):
    high = df["high"]
    low = df["low"]
    close = df["close"]

    previous_close = close.shift(1)

    tr = pd.concat(
        [
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs()
        ],
        axis=1
    ).max(axis=1)

    atr = tr.ewm(
        alpha=1 / period,
        min_periods=period,
        adjust=False
    ).mean()

    return atr


def calculate_ema(series, period):
    return series.ewm(
        span=period,
        adjust=False
    ).mean()


# =========================================================
# TREND
# =========================================================

def get_trend(df):
    if len(df) < 50:
        return "NEUTRAL"

    close = df["close"]

    ema20 = calculate_ema(close, 20)
    ema50 = calculate_ema(close, 50)

    last_close = float(close.iloc[-1])
    last_ema20 = float(ema20.iloc[-1])
    last_ema50 = float(ema50.iloc[-1])

    if (
        last_close > last_ema20
        and last_ema20 > last_ema50
    ):
        return "BULLISH"

    if (
        last_close < last_ema20
        and last_ema20 < last_ema50
    ):
        return "BEARISH"

    return "NEUTRAL"


# =========================================================
# SIGNAL ENGINE
# =========================================================

def generate_signal(
    df_15m,
    df_1h,
    df_4h
):

    df = df_15m.copy()

    if len(df) < 100:
        raise ValueError(
            "Not enough 15M candles."
        )

    close = df["close"]

    # -----------------------------------------------------
    # Indicators
    # -----------------------------------------------------

    ema9 = calculate_ema(
        close,
        9
    )

    ema21 = calculate_ema(
        close,
        21
    )

    ema50 = calculate_ema(
        close,
        50
    )

    rsi_series = calculate_rsi(
        close,
        14
    )

    atr_series = calculate_atr(
        df,
        14
    )

    latest_close = float(
        close.iloc[-1]
    )

    previous_close = float(
        close.iloc[-2]
    )

    latest_ema9 = float(
        ema9.iloc[-1]
    )

    latest_ema21 = float(
        ema21.iloc[-1]
    )

    latest_ema50 = float(
        ema50.iloc[-1]
    )

    previous_ema9 = float(
        ema9.iloc[-2]
    )

    previous_ema21 = float(
        ema21.iloc[-2]
    )

    rsi = float(
        rsi_series.iloc[-1]
    )

    atr = float(
        atr_series.iloc[-1]
    )

    if not np.isfinite(atr) or atr <= 0:
        atr = max(
            latest_close * 0.001,
            0.01
        )

    # -----------------------------------------------------
    # Momentum
    #
    # Normalised price movement over the
    # recent candles, expressed relative
    # to ATR.
    # -----------------------------------------------------

    lookback = 8

    if len(df) > lookback:

        old_close = float(
            close.iloc[-1 - lookback]
        )

        momentum = (
            (latest_close - old_close)
            / atr
        )

    else:

        momentum = 0.0

    momentum = float(
        np.clip(
            momentum,
            -3.0,
            3.0
        )
    )

    # -----------------------------------------------------
    # Higher timeframe trends
    # -----------------------------------------------------

    h1_trend = get_trend(
        df_1h
    )

    h4_trend = get_trend(
        df_4h
    )

    # =====================================================
    # SCORING
    #
    # Maximum = 10
    #
    # The important change:
    # conditions receive partial points.
    # A trade does NOT automatically get
    # 8/10 simply because the trend is bullish.
    # =====================================================

    buy_score = 0.0
    sell_score = 0.0

    # -----------------------------------------------------
    # 1. 15M EMA structure — 2 points
    # -----------------------------------------------------

    if (
        latest_ema9 > latest_ema21
        and latest_ema21 > latest_ema50
    ):
        buy_score += 2.0

    elif (
        latest_ema9 > latest_ema21
    ):
        buy_score += 1.0

    if (
        latest_ema9 < latest_ema21
        and latest_ema21 < latest_ema50
    ):
        sell_score += 2.0

    elif (
        latest_ema9 < latest_ema21
    ):
        sell_score += 1.0

    # -----------------------------------------------------
    # 2. EMA crossover / recent direction — 1 point
    # -----------------------------------------------------

    if (
        latest_ema9 > latest_ema21
        and previous_ema9 <= previous_ema21
    ):
        buy_score += 1.0

    elif (
        latest_ema9 < latest_ema21
        and previous_ema9 >= previous_ema21
    ):
        sell_score += 1.0

    # -----------------------------------------------------
    # 3. RSI — 2 points
    #
    # Avoid blindly buying every bullish RSI.
    # -----------------------------------------------------

    if 52 <= rsi <= 65:
        buy_score += 2.0

    elif 50 <= rsi < 52:
        buy_score += 1.0

    elif 65 < rsi <= 70:
        buy_score += 1.0

    if 35 <= rsi <= 48:
        sell_score += 2.0

    elif 48 < rsi <= 50:
        sell_score += 1.0

    elif 30 <= rsi < 35:
        sell_score += 1.0

    # -----------------------------------------------------
    # 4. Momentum — 1.5 points
    # -----------------------------------------------------

    if momentum >= 1.0:
        buy_score += 1.5

    elif momentum >= 0.35:
        buy_score += 0.75

    if momentum <= -1.0:
        sell_score += 1.5

    elif momentum <= -0.35:
        sell_score += 0.75

    # -----------------------------------------------------
    # 5. Higher timeframe alignment — 2 points
    # -----------------------------------------------------

    if h1_trend == "BULLISH":
        buy_score += 1.0

    elif h1_trend == "BEARISH":
        sell_score += 1.0

    if h4_trend == "BULLISH":
        buy_score += 1.0

    elif h4_trend == "BEARISH":
        sell_score += 1.0

    # -----------------------------------------------------
    # 6. Price relative to EMA50 — 1.5 points
    # -----------------------------------------------------

    if latest_close > latest_ema50:
        buy_score += 1.5

    elif latest_close < latest_ema50:
        sell_score += 1.5

    # -----------------------------------------------------
    # Clamp scores
    # -----------------------------------------------------

    buy_score = float(
        np.clip(
            buy_score,
            0,
            10
        )
    )

    sell_score = float(
        np.clip(
            sell_score,
            0,
            10
        )
    )

    # =====================================================
    # DECISION
    # =====================================================

    difference = (
        abs(
            buy_score -
            sell_score
        )
    )

    # Require a reasonably strong
    # directional edge.
    #
    # This is what prevents the system
    # from calling BUY constantly.
    # =====================================================

    minimum_score = 6.0
    minimum_edge = 1.5

    if (
        buy_score >= minimum_score
        and buy_score > sell_score
        and difference >= minimum_edge
    ):

        direction = "BUY"

        score = int(
            round(
                buy_score
            )
        )

    elif (
        sell_score >= minimum_score
        and sell_score > buy_score
        and difference >= minimum_edge
    ):

        direction = "SELL"

        score = int(
            round(
                sell_score
            )
        )

    else:

        direction = "WAIT"

        # For WAIT, show the stronger
        # side's quality rather than
        # pretending there is a trade.

        score = int(
            round(
                max(
                    buy_score,
                    sell_score
                )
            )
        )

    score = int(
        np.clip(
            score,
            0,
            10
        )
    )

    # =====================================================
    # ENTRY / SL / TP
    # =====================================================

    entry = latest_close

    # Use ATR-based risk instead of
    # an extremely tiny fixed stop.

    stop_distance = (
        atr * 1.5
    )

    target_distance = (
        stop_distance * 3.0
    )

    if direction == "BUY":

        sl = entry - stop_distance

        tp = entry + target_distance

    elif direction == "SELL":

        sl = entry + stop_distance

        tp = entry - target_distance

    else:

        sl = entry

        tp = entry

    # =====================================================
    # RETURN COMPLETE SIGNAL
    #
    # Every key expected by app.py
    # is always returned.
    # =====================================================

    return {

        "direction": direction,

        "score": score,

        "entry": float(entry),

        "sl": float(sl),

        "tp": float(tp),

        "buy_score": round(
            buy_score,
            2
        ),

        "sell_score": round(
            sell_score,
            2
        ),

        "rsi": round(
            rsi,
            2
        ),

        "atr": round(
            atr,
            2
        ),

        "momentum": round(
            momentum,
            2
        ),

        "h1_trend": h1_trend,

        "h4_trend": h4_trend
    }
