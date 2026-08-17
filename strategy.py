import pandas as pd
import numpy as np


def add_indicators(df):
    df = df.copy()

    close = df["close"]

    # EMAs
    df["ema20"] = close.ewm(span=20, adjust=False).mean()
    df["ema50"] = close.ewm(span=50, adjust=False).mean()
    df["ema100"] = close.ewm(span=100, adjust=False).mean()

    # RSI
    delta = close.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / 14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / 14, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)

    df["rsi"] = 100 - (100 / (1 + rs))
    df["rsi"] = df["rsi"].fillna(50)

    # ATR
    previous_close = close.shift(1)

    tr1 = df["high"] - df["low"]
    tr2 = (df["high"] - previous_close).abs()
    tr3 = (df["low"] - previous_close).abs()

    true_range = pd.concat(
        [tr1, tr2, tr3],
        axis=1
    ).max(axis=1)

    df["atr"] = (
        true_range
        .ewm(alpha=1 / 14, adjust=False)
        .mean()
    )

    # Recent momentum
    df["momentum"] = close.pct_change(5) * 100

    return df


def get_trend(df):
    data = add_indicators(df)

    last = data.iloc[-1]

    if (
        last["ema20"] > last["ema50"]
        and last["ema50"] > last["ema100"]
    ):
        return "BULLISH"

    if (
        last["ema20"] < last["ema50"]
        and last["ema50"] < last["ema100"]
    ):
        return "BEARISH"

    return "NEUTRAL"


def generate_signal(df_15m, df_1h, df_4h):

    data = add_indicators(df_15m)

    last = data.iloc[-1]

    close = float(last["close"])
    ema20 = float(last["ema20"])
    ema50 = float(last["ema50"])
    rsi = float(last["rsi"])
    atr = float(last["atr"])
    momentum = float(last["momentum"])

    h1_trend = get_trend(df_1h)
    h4_trend = get_trend(df_4h)

    # -------------------------------------------------
    # BUY SCORE
    # -------------------------------------------------

    buy_score = 0.0

    if h1_trend == "BULLISH":
        buy_score += 2.0

    if h4_trend == "BULLISH":
        buy_score += 2.0

    if ema20 > ema50:
        buy_score += 1.5

    if 50 <= rsi <= 68:
        buy_score += 1.5

    if momentum > 0:
        buy_score += 1.0

    if close > ema20:
        buy_score += 1.0

    # -------------------------------------------------
    # SELL SCORE
    # -------------------------------------------------

    sell_score = 0.0

    if h1_trend == "BEARISH":
        sell_score += 2.0

    if h4_trend == "BEARISH":
        sell_score += 2.0

    if ema20 < ema50:
        sell_score += 1.5

    if 32 <= rsi <= 50:
        sell_score += 1.5

    if momentum < 0:
        sell_score += 1.0

    if close < ema20:
        sell_score += 1.0

    # -------------------------------------------------
    # NORMALIZE
    # -------------------------------------------------

    buy_score = round(min(buy_score, 10), 1)
    sell_score = round(min(sell_score, 10), 1)

    # -------------------------------------------------
    # REQUIRE REAL CONFIRMATION
    # -------------------------------------------------

    difference = abs(
        buy_score - sell_score
    )

    if (
        buy_score < 6
        and sell_score < 6
    ):
        direction = "WAIT"

    elif difference < 1.5:
        direction = "WAIT"

    elif buy_score > sell_score:
        direction = "BUY"

    else:
        direction = "SELL"

    # -------------------------------------------------
    # ENTRY / SL / TP
    # -------------------------------------------------

    entry = close

    # ATR-based stop.
    # This prevents ridiculously tiny stops.
    stop_distance = max(
        atr * 1.5,
        close * 0.0015
    )

    target_distance = (
        stop_distance * 3
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

    # -------------------------------------------------
    # DISPLAY SCORE
    # -------------------------------------------------

    if direction == "BUY":
        score = round(buy_score)

    elif direction == "SELL":
        score = round(sell_score)

    else:
        score = round(
            max(
                buy_score,
                sell_score
            )
        )

    return {
        "direction": direction,
        "score": score,
        "buy_score": buy_score,
        "sell_score": sell_score,
        "entry": round(entry, 2),
        "sl": round(sl, 2),
        "tp": round(tp, 2),
        "h1_trend": h1_trend,
        "h4_trend": h4_trend,
        "rsi": round(rsi, 2),
        "atr": round(atr, 2),
        "momentum": round(momentum, 3),
    }
