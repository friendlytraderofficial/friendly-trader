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

        atr = price *
