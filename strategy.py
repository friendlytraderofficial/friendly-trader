import numpy as np
import pandas as pd


# =========================================================
# FRIENDLY TRADER — ALPHA 1.0
# Strategy engine
# =========================================================


def prepare_indicators(df):
    data = df.copy()

    required = [
        "time",
        "open",
        "high",
        "low",
        "close",
    ]

    missing = [
        c for c in required
        if c not in data.columns
    ]

    if missing:
        raise ValueError(
            f"Missing columns: {missing}"
        )

    data["time"] = pd.to_datetime(
        data["time"]
    )

    for col in [
        "open",
        "high",
        "low",
        "close",
    ]:
        data[col] = pd.to_numeric(
            data[col],
            errors="coerce"
        )

    data = (
        data
        .dropna()
        .sort_values("time")
        .reset_index(drop=True)
    )

    # -----------------------------------------------------
    # EMA
    # -----------------------------------------------------

    data["ema20"] = (
        data["close"]
        .ewm(
            span=20,
            adjust=False
        )
        .mean()
    )

    data["ema50"] = (
        data["close"]
        .ewm(
            span=50,
            adjust=False
        )
        .mean()
    )

    data["ema200"] = (
        data["close"]
        .ewm(
            span=200,
            adjust=False
        )
        .mean()
    )

    # -----------------------------------------------------
    # RSI
    # -----------------------------------------------------

    delta = data["close"].diff()

    gain = delta.clip(
        lower=0
    )

    loss = -delta.clip(
        upper=0
    )

    avg_gain = (
        gain
        .ewm(
            alpha=1 / 14,
            adjust=False
        )
        .mean()
    )

    avg_loss = (
        loss
        .ewm(
            alpha=1 / 14,
            adjust=False
        )
        .mean()
    )

    rs = (
        avg_gain /
        avg_loss.replace(
            0,
            np.nan
        )
    )

    data["rsi"] = (
        100 -
        (
            100 /
            (1 + rs)
        )
    )

    # -----------------------------------------------------
    # ATR
    # -----------------------------------------------------

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

    true_range = pd.concat(
        [
            tr1,
            tr2,
            tr3,
        ],
        axis=1
    ).max(axis=1)

    data["atr"] = (
        true_range
        .ewm(
            alpha=1 / 14,
            adjust=False
        )
        .mean()
    )

    # -----------------------------------------------------
    # Momentum
    # -----------------------------------------------------

    data["roc5"] = (
        data["close"]
        .pct_change(5)
        * 100
    )

    # -----------------------------------------------------
    # Candle information
    # -----------------------------------------------------

    data["body"] = (
        data["close"] -
        data["open"]
    )

    data["range"] = (
        data["high"] -
        data["low"]
    )

    return data


# =========================================================
# TREND
# =========================================================


def get_trend(df):

    data = prepare_indicators(
        df
    ).dropna()

    if len(data) < 10:
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


# =========================================================
# CLAMP
# =========================================================


def clamp(
    value,
    minimum=0.0,
    maximum=10.0
):

    return max(
        minimum,
        min(
            maximum,
            float(value)
        )
    )


# =========================================================
# SIGNAL ENGINE
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
            "At least 200 valid 15M candles "
            "are required."
        )

    row = data.iloc[-1]

    previous = data.iloc[-2]

    price = float(
        row["close"]
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

    rsi = float(
        row["rsi"]
    )

    atr = float(
        row["atr"]
    )

    roc5 = float(
        row["roc5"]
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
    # 15M TREND
    # =====================================================

    bullish_15m = (
        ema20 > ema50 > ema200
    )

    bearish_15m = (
        ema20 < ema50 < ema200
    )


    # =====================================================
    # BUY SCORE
    # =====================================================

    buy_score = 0.0

    # 15M trend
    if bullish_15m:
        buy_score += 2.0

    elif price > ema50:
        buy_score += 1.0


    # 1H trend
    if h1_trend == "BULLISH":
        buy_score += 1.5

    elif h1_trend == "NEUTRAL":
        buy_score += 0.5


    # 4H trend
    if h4_trend == "BULLISH":
        buy_score += 1.5

    elif h4_trend == "NEUTRAL":
        buy_score += 0.5


    # RSI
    if 52 <= rsi <= 60:
        buy_score += 1.5

    elif 60 < rsi <= 65:
        buy_score += 1.0

    elif 50 <= rsi < 52:
        buy_score += 0.5

    elif rsi > 70:
        buy_score -= 1.0


    # Momentum
    if roc5 > 0:
        buy_score += 0.75

    elif roc5 < -0.20:
        buy_score -= 0.5


    # Candle
    if row["close"] > row["open"]:
        buy_score += 0.5

    if row["close"] > previous["close"]:
        buy_score += 0.5


    # =====================================================
    # SELL SCORE
    # =====================================================

    sell_score = 0.0

    # 15M trend
    if bearish_15m:
        sell_score += 2.0

    elif price < ema50:
        sell_score += 1.0


    # 1H trend
    if h1_trend == "BEARISH":
        sell_score += 1.5

    elif h1_trend == "NEUTRAL":
        sell_score += 0.5


    # 4H trend
    if h4_trend == "BEARISH":
        sell_score += 1.5

    elif h4_trend == "NEUTRAL":
        sell_score += 0.5


    # RSI
    if 40 <= rsi <= 48:
        sell_score += 1.5

    elif 35 <= rsi < 40:
        sell_score += 1.0

    elif 48 < rsi <= 50:
        sell_score += 0.5

    elif rsi < 30:
        sell_score -= 1.0


    # Momentum
    if roc5 < 0:
        sell_score += 0.75

    elif roc5 > 0.20:
        sell_score -= 0.5


    # Candle
    if row["close"] < row["open"]:
        sell_score += 0.5

    if row["close"] < previous["close"]:
        sell_score += 0.5


    # =====================================================
    # ENTRY QUALITY
    # =====================================================

    distance_from_ema20 = (
        abs(price - ema20)
        / atr
    )

    # Too far from EMA = bad chase entry
    if distance_from_ema20 > 2.0:

        buy_score -= 1.5
        sell_score -= 1.5

    elif distance_from_ema20 <= 0.75:

        buy_score += 0.75
        sell_score += 0.75


    # =====================================================
    # LIMIT SCORES
    # =====================================================

    buy_score = clamp(
        buy_score
    )

    sell_score = clamp(
        sell_score
    )


    # =====================================================
    # SIGNAL
    # =====================================================

    score_difference = (
        abs(
            buy_score -
            sell_score
        )
    )

    direction = "WAIT"

    # We deliberately require a meaningful
    # advantage before issuing a trade.

    if (
        buy_score >= 7.0
        and
        buy_score > sell_score
        and
        score_difference >= 1.5
    ):

        direction = "BUY"

    elif (
        sell_score >= 7.0
        and
        sell_score > buy_score
        and
        score_difference >= 1.5
    ):

        direction = "SELL"


    # =====================================================
    # DISPLAY SCORE
    # =====================================================

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


    score = max(
        0,
        min(
            10,
            score
        )
    )


    # =====================================================
    # RISK
    # =====================================================

    stop_distance = (
        atr * 1.5
    )

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


    # =====================================================
    # IMPORTANT:
    # RETURN EVERY FIELD USED BY APP.PY
    # =====================================================

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

        "sl
