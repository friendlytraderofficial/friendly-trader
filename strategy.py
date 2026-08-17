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

    delta = data["close"].diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)

    data["rsi"] = (
        100 - (100 / (1 + rs))
    )

    previous_close = data["close"].shift(1)

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


    h1_trend = get_trend(
        df_1h
    )

    h4_trend = get_trend(
        df_4h
    )


    buy_score = 0
    sell_score = 0


    if row["ema20"] > row["ema50"]:

        buy_score += 2

    elif row["ema20"] < row["ema50"]:

        sell_score += 2


    if price > row["ema200"]:

        buy_score += 2

    elif price < row["ema200"]:

        sell_score += 2


    if 55 <= row["rsi"] <= 70:

        buy_score += 2

    elif 30 <= row["rsi"] <= 45:

        sell_score += 2


    if h1_trend == "BULLISH":

        buy_score += 2

    elif h1_trend == "BEARISH":

        sell_score += 2


    if h4_trend == "BULLISH":

        buy_score += 2

    elif h4_trend == "BEARISH":

        sell_score += 2


    # -----------------------------------------------------
    # ATR-BASED RISK MODEL
    # -----------------------------------------------------

    stop_distance = atr * 1.5

    take_profit_distance = (
        stop_distance * 3
    )


    if (
        buy_score >= 8
        and buy_score > sell_score
    ):

        direction = "BUY"

        entry = price

        sl = (
            entry -
            stop_distance
        )

        tp = (
            entry +
            take_profit_distance
        )

        score = buy_score


    elif (
        sell_score >= 8
        and sell_score > buy_score
    ):

        direction = "SELL"

        entry = price

        sl = (
            entry +
            stop_distance
        )

        tp = (
            entry -
            take_profit_distance
        )

        score = sell_score


    else:

        direction = "WAIT"

        entry = price

        sl = price

        tp = price

        score = max(
            buy_score,
            sell_score
        )


    return {
        "direction": direction,
        "score": int(score),
        "entry": round(entry, 2),
        "sl": round(sl, 2),
        "tp": round(tp, 2),
        "h1_trend": h1_trend,
        "h4_trend": h4_trend
    }
