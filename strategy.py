import numpy as np
import pandas as pd


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

    data = data.dropna().copy()

    data = data.sort_values(
        "time"
    ).reset_index(
        drop=True
    )

    # EMA
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

    # RSI
    delta = data["close"].diff()

    gain = delta.clip(
        lower=0
    )

    loss = -delta.clip(
        upper=0
    )

    average_gain = gain.ewm(
        alpha=1 / 14,
        adjust=False
    ).mean()

    average_loss = loss.ewm(
        alpha=1 / 14,
        adjust=False
    ).mean()

    rs = (
        average_gain /
        average_loss.replace(
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

    # ATR
    previous_close = (
        data["close"].shift(1)
    )

    range_1 = (
        data["high"] -
        data["low"]
    )

    range_2 = (
        data["high"] -
        previous_close
    ).abs()

    range_3 = (
        data["low"] -
        previous_close
    ).abs()

    true_range = pd.concat(
        [
            range_1,
            range_2,
            range_3,
        ],
        axis=1
    ).max(axis=1)

    data["atr"] = true_range.ewm(
        alpha=1 / 14,
        adjust=False
    ).mean()

    # Momentum
    data["roc5"] = (
        data["close"]
        .pct_change(5)
        * 100
    )

    return data


def get_trend(df):

    data = prepare_indicators(
        df
    ).dropna()

    if len(data) < 20:
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


def limit_score(value):

    return max(
        0.0,
        min(
            10.0,
            float(value)
        )
    )


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
            "Not enough 15M candles."
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

    if not np.isfinite(rsi):
        rsi = 50.0

    if not np.isfinite(roc5):
        roc5 = 0.0

    # Higher timeframe trend
    h1_trend = get_trend(
        df_1h
    )

    h4_trend = get_trend(
        df_4h
    )

    # =====================================================
    # BUY SCORE
    # =====================================================

    buy_score = 0.0

    if ema20 > ema50:
        buy_score += 1.5

    if ema50 > ema200:
        buy_score += 1.5

    if h1_trend == "BULLISH":
        buy_score += 2.0

    elif h1_trend == "NEUTRAL":
        buy_score += 0.5

    if h4_trend == "BULLISH":
        buy_score += 2.0

    elif h4_trend == "NEUTRAL":
        buy_score += 0.5

    if 52 <= rsi <= 65:
        buy_score += 1.5

    elif 50 <= rsi < 52:
        buy_score += 0.5

    elif rsi > 70:
        buy_score -= 1.5

    if roc5 > 0:
        buy_score += 0.75

    if price > ema20:
        buy_score += 0.5

    if row["close"] > row["open"]:
        buy_score += 0.25

    # =====================================================
    # SELL SCORE
    # =====================================================

    sell_score = 0.0

    if ema20 < ema50:
        sell_score += 1.5

    if ema50 < ema200:
        sell_score += 1.5

    if h1_trend == "BEARISH":
        sell_score += 2.0

    elif h1_trend == "NEUTRAL":
        sell_score += 0.5

    if h4_trend == "BEARISH":
        sell_score += 2.0

    elif h4_trend == "NEUTRAL":
        sell_score += 0.5

    if 35 <= rsi <= 48:
        sell_score += 1.5

    elif 48 < rsi <= 50:
        sell_score += 0.5

    elif rsi < 30:
        sell_score -= 1.5

    if roc5 < 0:
        sell_score += 0.75

    if price < ema20:
        sell_score += 0.5

    if row["close"] < row["open"]:
        sell_score += 0.25

    buy_score = limit_score(
        buy_score
    )

    sell_score = limit_score(
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

    if (
        buy_score >= 7.0
        and
        buy_score > sell_score
        and
        difference >= 1.5
    ):
        direction = "BUY"

    elif (
        sell_score >= 7.0
        and
        sell_score > buy_score
        and
        difference >= 1.5
    ):
        direction = "SELL"

    # Display score
    if direction == "BUY":
        score = round(
            buy_score
        )

    elif direction == "SELL":
        score = round(
            sell_score
        )

    else:
        score = round(
            max(
                buy_score,
                sell_score
            )
        )

    score = max(
        0,
        min(
            10,
            int(score)
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
