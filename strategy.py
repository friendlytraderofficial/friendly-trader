import numpy as np
import pandas as pd


def add_indicators(df):
    data = df.copy()

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

    delta = data["close"].diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()

    rs = avg_gain / avg_loss.replace(
        0,
        np.nan
    )

    data["rsi"] = 100 - (
        100 / (1 + rs)
    )

    previous_close = data["close"].shift(1)

    tr1 = data["high"] - data["low"]
    tr2 = abs(
        data["high"] -
        previous_close
    )
    tr3 = abs(
        data["low"] -
        previous_close
    )

    data["tr"] = pd.concat(
        [tr1, tr2, tr3],
        axis=1
    ).max(axis=1)

    data["atr"] = data["tr"].rolling(
        14
    ).mean()

    return data


def trend_direction(df):

    data = add_indicators(df)

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
    df_1h=None,
    df_4h=None
):

    data = add_indicators(
        df_15m
    )

    latest = data.iloc[-1]

    price = float(
        latest["close"]
    )

    ema20 = float(
        latest["ema20"]
    )

    ema50 = float(
        latest["ema50"]
    )

    ema200 = float(
        latest["ema200"]
    )

    rsi = float(
        latest["rsi"]
    )

    atr = float(
        latest["atr"]
    )

    if not np.isfinite(atr) or atr <= 0:

        atr = price * 0.001

    buy_score = 0
    sell_score = 0

    # -------------------------
    # 15M SETUP
    # -------------------------

    if ema20 > ema50:
        buy_score += 2

    elif ema20 < ema50:
        sell_score += 2

    if price > ema200:
        buy_score += 2

    elif price < ema200:
        sell_score += 2

    if 55 <= rsi <= 70:
        buy_score += 2

    elif 30 <= rsi <= 45:
        sell_score += 2

    if price > ema20:
        buy_score += 1

    elif price < ema20:
        sell_score += 1

    if rsi > 75:
        buy_score -= 1

    if rsi < 25:
        sell_score -= 1

    # -------------------------
    # HIGHER TIMEFRAME FILTER
    # -------------------------

    h1_trend = "NEUTRAL"
    h4_trend = "NEUTRAL"

    if df_1h is not None:
        h1_trend = trend_direction(
            df_1h
        )

    if df_4h is not None:
        h4_trend = trend_direction(
            df_4h
        )

    # Strong confirmation
    if h1_trend == "BULLISH":
        buy_score += 2

    elif h1_trend == "BEARISH":
        sell_score += 2

    if h4_trend == "BULLISH":
        buy_score += 2

    elif h4_trend == "BEARISH":
        sell_score += 2

    buy_score = max(
        0,
        min(10, buy_score)
    )

    sell_score = max(
        0,
        min(10, sell_score)
    )

    # -------------------------
    # FINAL DECISION
    # -------------------------

    if (
        buy_score >= 8
        and h1_trend == "BULLISH"
        and h4_trend == "BULLISH"
        and buy_score > sell_score
    ):

        direction = "BUY"
        score = buy_score

        entry = price
        sl = entry - atr
        tp = entry + (
            3 * atr
        )

    elif (
        sell_score >= 8
        and h1_trend == "BEARISH"
        and h4_trend == "BEARISH"
        and sell_score > buy_score
    ):

        direction = "SELL"
        score = sell_score

        entry = price
        sl = entry + atr
        tp = entry - (
            3 * atr
        )

    else:

        direction = "WAIT"
        score = max(
            buy_score,
            sell_score
        )

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


def backtest(
    df_15m,
    df_1h=None,
    df_4h=None,
    trades=50,
    max_holding_bars=20,
    cost_r=0.10
):

    data = add_indicators(
        df_15m
    )

    data = data.dropna().copy()

    h1 = None
    h4 = None

    if df_1h is not None:

        h1 = add_indicators(
            df_1h
        ).dropna().copy()

    if df_4h is not None:

        h4 = add_indicators(
            df_4h
        ).dropna().copy()

    journal = []

    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0

    wins = 0
    losses = 0

    i = 0

    while (
        i < len(data) - 1
        and len(journal) < trades
    ):

        row = data.iloc[i]

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

        if (
            not np.isfinite(atr)
            or atr <= 0
        ):
            i += 1
            continue

        # -------------------------
        # 15M SCORE
        # -------------------------

        buy_score = 0
        sell_score = 0

        if ema20 > ema50:
            buy_score += 2

        elif ema20 < ema50:
            sell_score += 2

        if price > ema200:
            buy_score += 2

        elif price < ema200:
            sell_score += 2

        if 55 <= rsi <= 70:
            buy_score += 2

        elif 30 <= rsi <= 45:
            sell_score += 2

        if price > ema20:
            buy_score += 1

        elif price < ema20:
            sell_score += 1

        if rsi > 75:
            buy_score -= 1

        if rsi < 25:
            sell_score -= 1

        # -------------------------
        # HISTORICAL 1H / 4H
        # -------------------------

        current_time = row["time"]

        h1_trend = "NEUTRAL"
        h4_trend = "NEUTRAL"

        if h1 is not None:

            h1_available = h1[
                h1["time"] <= current_time
            ]

            if len(h1_available) > 0:

                h1_row = h1_available.iloc[-1]

                if (
                    h1_row["ema20"] >
                    h1_row["ema50"] >
                    h1_row["ema200"]
                ):
                    h1_trend = "BULLISH"

                elif (
                    h1_row["ema20"] <
                    h1_row["ema50"] <
                    h1_row["ema200"]
                ):
                    h1_trend = "BEARISH"

        if h4 is not None:

            h4_available = h4[
                h4["time"] <= current_time
            ]

            if len(h4_available) > 0:

                h4_row = h4_available.iloc[-1]

                if (
                    h4_row["ema20"] >
                    h4_row["ema50"] >
                    h4_row["ema200"]
                ):
                    h4_trend = "BULLISH"

                elif (
                    h4_row["ema20"] <
                    h4_row["ema50"] <
                    h4_row["ema200"]
                ):
                    h4_trend = "BEARISH"

        if h1_trend == "BULLISH":
            buy_score += 2

        elif h1_trend == "BEARISH":
            sell_score += 2

        if h4_trend == "BULLISH":
            buy_score += 2

        elif h4_trend == "BEARISH":
            sell_score += 2

        # -------------------------
        # ENTRY
        # -------------------------

        if (
            buy_score >= 8
            and h1_trend == "BULLISH"
            and h4_trend == "BULLISH"
            and buy_score > sell_score
        ):

            direction = "BUY"
            score = buy_score

            entry = price
            sl = entry - atr
            tp = entry + (
                3 * atr
            )

        elif (
            sell_score >= 8
            and h1_trend == "BEARISH"
            and h4_trend == "BEARISH"
            and sell_score > buy_score
        ):

            direction = "SELL"
            score = sell_score

            entry = price
            sl = entry + atr
            tp = entry - (
                3 * atr
            )

        else:

            i += 1
            continue

        result = "TIMEOUT"
        result_r = 0.0
        exit_price = entry
        exit_time = row["time"]
        bars_held = 0

        end = min(
            i + 1 +
            max_holding_bars,
            len(data)
        )

        for j in range(
            i + 1,
            end
        ):

            future = data.iloc[j]

            high = float(
                future["high"]
            )

            low = float(
                future["low"]
            )

            bars_held += 1

            if direction == "BUY":

                hit_sl = low <= sl
                hit_tp = high >= tp

            else:

                hit_sl = high >= sl
                hit_tp = low <= tp

            # Conservative same-candle rule
            if hit_sl and hit_tp:

                result
