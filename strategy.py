import pandas as pd
import numpy as np


# =========================================================
# INDICATORS
# =========================================================

def calculate_ema(series, period):
    return series.ewm(
        span=period,
        adjust=False
    ).mean()


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

    rs = avg_gain / avg_loss.replace(
        0,
        np.nan
    )

    rsi = 100 - (
        100 / (1 + rs)
    )

    return rsi.fillna(50)


def calculate_atr(df, period=14):

    previous_close = df["close"].shift(1)

    tr = pd.concat(
        [
            df["high"] - df["low"],
            (
                df["high"] -
                previous_close
            ).abs(),
            (
                df["low"] -
                previous_close
            ).abs()
        ],
        axis=1
    ).max(axis=1)

    return tr.ewm(
        alpha=1 / period,
        min_periods=period,
        adjust=False
    ).mean()


# =========================================================
# TREND
# =========================================================

def get_trend(df):

    if len(df) < 50:
        return "NEUTRAL"

    close = df["close"]

    ema20 = calculate_ema(
        close,
        20
    )

    ema50 = calculate_ema(
        close,
        50
    )

    price = float(
        close.iloc[-1]
    )

    e20 = float(
        ema20.iloc[-1]
    )

    e50 = float(
        ema50.iloc[-1]
    )

    if (
        price > e20
        and e20 > e50
    ):
        return "BULLISH"

    if (
        price < e20
        and e20 < e50
    ):
        return "BEARISH"

    return "NEUTRAL"


# =========================================================
# MAIN SIGNAL ENGINE
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

    price = float(
        close.iloc[-1]
    )

    e9 = float(
        ema9.iloc[-1]
    )

    e21 = float(
        ema21.iloc[-1]
    )

    e50 = float(
        ema50.iloc[-1]
    )

    previous_e9 = float(
        ema9.iloc[-2]
    )

    previous_e21 = float(
        ema21.iloc[-2]
    )

    rsi = float(
        rsi_series.iloc[-1]
    )

    atr = float(
        atr_series.iloc[-1]
    )

    if (
        not np.isfinite(atr)
        or atr <= 0
    ):
        atr = max(
            price * 0.001,
            0.01
        )

    # -----------------------------------------------------
    # Momentum
    # -----------------------------------------------------

    lookback = 8

    old_price = float(
        close.iloc[-1 - lookback]
    )

    momentum = (
        price - old_price
    ) / atr

    momentum = float(
        np.clip(
            momentum,
            -3.0,
            3.0
        )
    )

    # -----------------------------------------------------
    # Higher timeframe trend
    # -----------------------------------------------------

    h1_trend = get_trend(
        df_1h
    )

    h4_trend = get_trend(
        df_4h
    )

    # -----------------------------------------------------
    # Scores
    # -----------------------------------------------------

    buy_score = 0.0
    sell_score = 0.0

    # EMA structure

    if (
        e9 > e21
        and e21 > e50
    ):
        buy_score += 2.0

    elif e9 > e21:
        buy_score += 1.0

    if (
        e9 < e21
        and e21 < e50
    ):
        sell_score += 2.0

    elif e9 < e21:
        sell_score += 1.0

    # EMA crossover

    if (
        e9 > e21
        and previous_e9 <= previous_e21
    ):
        buy_score += 1.0

    if (
        e9 < e21
        and previous_e9 >= previous_e21
    ):
        sell_score += 1.0

    # RSI

    if 52 <= rsi <= 65:
        buy_score += 2.0

    elif 50 <= rsi < 52:
        buy_score += 0.75

    elif 65 < rsi <= 70:
        buy_score += 0.75

    if 35 <= rsi <= 48:
        sell_score += 2.0

    elif 48 < rsi <= 50:
        sell_score += 0.75

    elif 30 <= rsi < 35:
        sell_score += 0.75

    # Momentum

    if momentum >= 1.0:
        buy_score += 2.0

    elif momentum >= 0.35:
        buy_score += 1.0

    elif momentum < 0:
        buy_score -= 1.0

    if momentum <= -1.0:
        sell_score += 2.0

    elif momentum <= -0.35:
        sell_score += 1.0

    elif momentum > 0:
        sell_score -= 1.0

    # Higher timeframe

    if h1_trend == "BULLISH":
        buy_score += 1.0

    elif h1_trend == "BEARISH":
        sell_score += 1.0

    if h4_trend == "BULLISH":
        buy_score += 1.0

    elif h4_trend == "BEARISH":
        sell_score += 1.0

    # Price vs EMA50

    if price > e50:
        buy_score += 1.0

    elif price < e50:
        sell_score += 1.0

    # Clamp

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
    # HARD CONFIRMATION
    # =====================================================

    bullish_confirmation = (
        h1_trend == "BULLISH"
        and h4_trend == "BULLISH"
        and e9 > e21
        and price > e21
        and momentum > 0
        and rsi >= 50
    )

    bearish_confirmation = (
        h1_trend == "BEARISH"
        and h4_trend == "BEARISH"
        and e9 < e21
        and price < e21
        and momentum < 0
        and rsi <= 50
    )

    minimum_score = 6.0
    minimum_edge = 1.5

    direction = "WAIT"

    if (
        bullish_confirmation
        and buy_score >= minimum_score
        and buy_score > sell_score
        and (
            buy_score -
            sell_score
        ) >= minimum_edge
    ):

        direction = "BUY"

    elif (
        bearish_confirmation
        and sell_score >= minimum_score
        and sell_score > buy_score
        and (
            sell_score -
            buy_score
        ) >= minimum_edge
    ):

        direction = "SELL"

    if direction == "BUY":

        score = int(
            round(
                buy_score
            )
        )

    elif direction == "SELL":

        score = int(
            round(
                sell_score
            )
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
        np.clip(
            score,
            0,
            10
        )
    )

    # =====================================================
    # ATR RISK MODEL
    # =====================================================

    entry = price

    stop_distance = (
        atr * 1.5
    )

    target_distance = (
        stop_distance * 3.0
    )

    if direction == "BUY":

        sl = (
            entry -
            stop_distance
        )

        tp = (
            entry +
            target_distance
        )

    elif direction == "SELL":

        sl = (
            entry +
            stop_distance
        )

        tp = (
            entry -
            target_distance
        )

    else:

        sl = entry
        tp = entry

    # =====================================================
    # RETURN EVERYTHING
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
