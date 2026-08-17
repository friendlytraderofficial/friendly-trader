import numpy as np
import pandas as pd


# =========================================================
# FRIENDLY TRADER — ALPHA 1.1
# Balanced scoring engine
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

    for column in required:

        if column not in data.columns:

            raise ValueError(
                f"Missing required column: {column}"
            )

    data["time"] = pd.to_datetime(
        data["time"]
    )

    for column in [
        "open",
        "high",
        "low",
        "close",
    ]:

        data[column] = pd.to_numeric(
            data[column],
            errors="coerce"
        )

    data = (
        data
        .dropna()
        .sort_values("time")
        .reset_index(drop=True)
    )

    # =====================================================
    # EMA
    # =====================================================

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

    # =====================================================
    # RSI
    # =====================================================

    delta = data["close"].diff()

    gain = delta.clip(
        lower=0
    )

    loss = -delta.clip(
        upper=0
    )

    avg_gain = gain.ewm(
        alpha=1 / 14,
        adjust=False
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / 14,
        adjust=False
    ).mean()

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

    # =====================================================
    # ATR
    # =====================================================

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

    # =====================================================
    # MOMENTUM
    # =====================================================

    data["roc5"] = (
        data["close"]
        .pct_change(5)
        * 100
    )

    data["roc10"] = (
        data["close"]
        .pct_change(10)
        * 100
    )

    # =====================================================
    # CANDLE
    # =====================================================

    data["body"] = (
        data["close"] -
        data["open"]
    )

    data["range"] = (
        data["high"] -
        data["low"]
    )

    data["body_ratio"] = (
        data["body"].abs() /
        data["range"].replace(
            0,
            np.nan
        )
    )

    return data


# =========================================================
# TREND
# =========================================================


def get_trend(df):

    data = prepare_indicators(
        df
    ).dropna()

    if len(data) < 50:

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
# SAFE SCORE
# =========================================================


def clamp_score(value):

    return max(
        0.0,
        min(
            10.0,
            float(value)
        )
    )


# =========================================================
# SIGNAL
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

    roc10 = float(
        row["roc10"]
    )

    body_ratio = float(
        row["body_ratio"]
    )

    if not np.isfinite(rsi):

        rsi = 50.0

    if (
        not np.isfinite(atr)
        or
        atr <= 0
    ):

        atr = price * 0.001

    if not np.isfinite(roc5):

        roc5 = 0.0

    if not np.isfinite(roc10):

        roc10 = 0.0

    if not np.isfinite(body_ratio):

        body_ratio = 0.0


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
    # START SCORES
    #
    # Maximum possible score = 10
    #
    # Trend       = 3
    # RSI         = 2
    # Momentum    = 2
    # Pullback    = 2
    # Candle      = 1
    # =====================================================

    buy_score = 0.0

    sell_score = 0.0


    # =====================================================
    # 1. TREND ALIGNMENT — MAX 3
    # =====================================================

    # BUY

    if h1_trend == "BULLISH":
        buy_score += 1.0

    if h4_trend == "BULLISH":
        buy_score += 1.0

    if (
        ema20 > ema50
        and
        ema50 > ema200
    ):

        buy_score += 1.0


    # SELL

    if h1_trend == "BEARISH":
        sell_score += 1.0

    if h4_trend == "BEARISH":
        sell_score += 1.0

    if (
        ema20 < ema50
        and
        ema50 < ema200
    ):

        sell_score += 1.0


    # =====================================================
    # 2. RSI — MAX 2
    # =====================================================

    # BUY works best when RSI is strong
    # but not already extremely overbought.

    if 52 <= rsi <= 60:

        buy_score += 2.0

    elif 60 < rsi <= 65:

        buy_score += 1.5

    elif 50 <= rsi < 52:

        buy_score += 1.0

    elif 65 < rsi <= 70:

        buy_score += 0.5

    elif rsi > 70:

        buy_score -= 1.0


    # SELL

    if 40 <= rsi <= 48:

        sell_score += 2.0

    elif 35 <= rsi < 40:

        sell_score += 1.5

    elif 48 < rsi <= 50:

        sell_score += 1.0

    elif 30 <= rsi < 35:

        sell_score += 0.5

    elif rsi < 30:

        sell_score -= 1.0


    # =====================================================
    # 3. MOMENTUM — MAX 2
    # =====================================================

    if (
        roc5 > 0
        and
        roc10 > 0
    ):

        buy_score += 2.0

    elif roc5 > 0:

        buy_score += 1.0

    elif (
        roc5 < 0
        and
        roc10 < 0
    ):

        sell_score += 2.0

    elif roc5 < 0:

        sell_score += 1.0


    # =====================================================
    # 4. PULLBACK / PRICE QUALITY — MAX 2
    # =====================================================

    distance_from_ema20 = (
        abs(
            price - ema20
        )
        / atr
    )


    # BUY pullback

    if (
        price >= ema20
        and
        distance_from_ema20 <= 0.75
    ):

        buy_score += 2.0

    elif (
        price >= ema20
        and
        distance_from_ema20 <= 1.25
    ):

        buy_score += 1.0

    elif distance_from_ema20 > 2.5:

        buy_score -= 1.0


    # SELL pullback

    if (
        price <= ema20
        and
        distance_from_ema20 <= 0.75
    ):

        sell_score += 2.0

    elif (
        price <= ema20
        and
        distance_from_ema20 <= 1.25
    ):

        sell_score += 1.0

    elif distance_from_ema20 > 2.5:

        sell_score -= 1.0


    # =====================================================
    # 5. CANDLE CONFIRMATION — MAX 1
    # =====================================================

    bullish_candle = (
        row["close"] >
        row["open"]
    )

    bearish_candle = (
        row["close"] <
        row["open"]
    )


    if (
        bullish_candle
        and
        body_ratio >= 0.50
        and
        price > previous["close"]
    ):

        buy_score += 1.0


    if (
        bearish_candle
        and
        body_ratio >= 0.50
        and
        price < previous["close"]
    ):

        sell_score += 1.0


    # =====================================================
    # PENALIZE OVEREXTENSION
    # =====================================================

    if distance_from_ema20 > 2.0:

        buy_score -= 0.75

        sell_score -= 0.75


    # =====================================================
    # FINAL LIMIT
    # =====================================================

    buy_score = clamp_score(
        buy_score
    )

    sell_score = clamp_score(
        sell_score
    )


    # =====================================================
    # SIGNAL FILTER
    # =====================================================

    difference = abs(
        buy_score -
        sell_score
    )

    direction = "WAIT"


    # IMPORTANT:
    # A trade requires both:
    # 1. A high enough score
    # 2. A meaningful advantage
    #
    # This prevents BUY from being generated
    # simply because the market is generally bullish.

    if (
        buy_score >= 7.0
        and
        buy_score > sell_score
        and
        difference >= 2.0
    ):

        direction = "BUY"


    elif (
        sell_score >= 7.0
        and
        sell_score > buy_score
        and
        difference >= 2.0
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
    # RISK MANAGEMENT
    # =====================================================

    stop_distance = (
        atr * 1.5
    )

    target_distance = (
        stop_distance * 3.0
    )


    entry = price


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
    # RETURN
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
