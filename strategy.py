import numpy as np
import pandas as pd


def add_indicators(df):

    data = df.copy()

    data = data.sort_values("time").reset_index(drop=True)

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

    rs = avg_gain / avg_loss.replace(0, np.nan)

    data["rsi"] = 100 - (
        100 / (1 + rs)
    )

    previous_close = data["close"].shift(1)

    tr1 = data["high"] - data["low"]

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

    data["atr"] = data["tr"].rolling(14).mean()

    return data


def get_trend(df):

    data = add_indicators(df)

    data = data.dropna().copy()

    if len(data) == 0:
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
    df_1h=None,
    df_4h=None
):

    data = add_indicators(
        df_15m
    ).dropna().copy()

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
    # 15M
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
    # Higher timeframes
    # -------------------------

    h1_trend = "NEUTRAL"
    h4_trend = "NEUTRAL"

    if df_1h is not None:
        h1_trend = get_trend(df_1h)

    if df_4h is not None:
        h4_trend = get_trend(df_4h)

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
    # Final signal
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
        tp = entry + (3 * atr)

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
        tp = entry - (3 * atr)

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
        "entry": round(entry, 2),
        "sl": round(sl, 2),
        "tp": round(tp, 2),
        "h1_trend": h1_trend,
        "h4_trend": h4_trend
    }


def prepare_multi_timeframe_data(
    df_15m,
    df_1h,
    df_4h
):

    base = add_indicators(
        df_15m
    ).dropna().copy()

    h1 = add_indicators(
        df_1h
    ).dropna().copy()

    h4 = add_indicators(
        df_4h
    ).dropna().copy()

    h1["h1_trend"] = np.where(
        (
            (h1["ema20"] > h1["ema50"]) &
            (h1["ema50"] > h1["ema200"])
        ),
        "BULLISH",
        np.where(
            (
                (h1["ema20"] < h1["ema50"]) &
                (h1["ema50"] < h1["ema200"])
            ),
            "BEARISH",
            "NEUTRAL"
        )
    )

    h4["h4_trend"] = np.where(
        (
            (h4["ema20"] > h4["ema50"]) &
            (h4["ema50"] > h4["ema200"])
        ),
        "BULLISH",
        np.where(
            (
                (h4["ema20"] < h4["ema50"]) &
                (h4["ema50"] < h4["ema200"])
            ),
            "BEARISH",
            "NEUTRAL"
        )
    )

    h1_small = h1[
        ["time", "h1_trend"]
    ].sort_values("time")

    h4_small = h4[
        ["time", "h4_trend"]
    ].sort_values("time")

    base = base.sort_values(
        "time"
    )

    # Attach latest completed/available 1H trend
    base = pd.merge_asof(
        base,
        h1_small,
        on="time",
        direction="backward"
    )

    # Attach latest completed/available 4H trend
    base = pd.merge_asof(
        base,
        h4_small,
        on="time",
        direction="backward"
    )

    base["h1_trend"] = base[
        "h1_trend"
    ].fillna("NEUTRAL")

    base["h4_trend"] = base[
        "h4_trend"
    ].fillna("NEUTRAL")

    return base


def backtest(
    df_15m,
    df_1h=None,
    df_4h=None,
    trades=50,
    max_holding_bars=20,
    cost_r=0.10
):

    if df_1h is None or df_4h is None:

        return {
            "trades": 0,
            "win_rate": 0,
            "net_r": 0,
            "profit_factor": 0,
            "max_drawdown": 0,
            "expectancy": 0,
            "journal": pd.DataFrame()
        }

    data = prepare_multi_timeframe_data(
        df_15m,
        df_1h,
        df_4h
    )

    if len(data) == 0:

        return {
            "trades": 0,
            "win_rate": 0,
            "net_r": 0,
            "profit_factor": 0,
            "max_drawdown": 0,
            "expectancy": 0,
            "journal": pd.DataFrame()
        }

    journal = []

    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0

    wins = 0

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

        buy_score = 0
        sell_score = 0

        # -------------------------
        # 15M conditions
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
        # Higher timeframe
        # -------------------------

        h1_trend = row["h1_trend"]
        h4_trend = row["h4_trend"]

        if h1_trend == "BULLISH":
            buy_score += 2

        elif h1_trend == "BEARISH":
            sell_score += 2

        if h4_trend == "BULLISH":
            buy_score += 2

        elif h4_trend == "BEARISH":
            sell_score += 2

        # -------------------------
        # Entry
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
            tp = entry + (3 * atr)

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
            tp = entry - (3 * atr)

        else:

            i += 1
            continue

        result = "TIMEOUT"
        result_r = 0.0
        exit_price = entry
        exit_time = row["time"]
        bars_held = 0

        end = min(
            i + 1 + max_holding_bars,
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

            # Conservative assumption:
            # if SL and TP occur in same candle,
            # count it as a loss.

            if hit_sl and hit_tp:

                result = "LOSS"
                result_r = -1.0
                exit_price = sl
                exit_time = future["time"]
                break

            if hit_sl:

                result = "LOSS"
                result_r = -1.0
                exit_price = sl
                exit_time = future["time"]
                break

            if hit_tp:

                result = "WIN"
                result_r = 3.0
                exit_price = tp
                exit_time = future["time"]
                break

        else:

            future = data.iloc[
                end - 1
            ]

            exit_price = float(
                future["close"]
            )

            exit_time = future["time"]

            if direction == "BUY":

                raw_r = (
                    exit_price - entry
                ) / atr

            else:

                raw_r = (
                    entry - exit_price
                ) / atr

            raw_r = max(
                -1.0,
                min(3.0, raw_r)
            )

            result_r = raw_r

            if result_r > 0:
                result = "PARTIAL WIN"

            elif result_r < 0:
                result = "PARTIAL LOSS"

            else:
                result = "BREAKEVEN"

        net_r = result_r - cost_r

        equity += net_r

        if net_r > 0:
            wins += 1

        peak = max(
            peak,
            equity
        )

        drawdown = (
            equity - peak
        )

        max_drawdown = min(
            max_drawdown,
            drawdown
        )

        journal.append(
            {
                "Entry Time": row["time"],
                "Exit Time": exit_time,
                "Direction": direction,
                "Score": int(score),
                "H1 Trend": h1_trend,
                "H4 Trend": h4_trend,
                "Entry": round(entry, 2),
                "SL": round(sl, 2),
                "TP": round(tp, 2),
                "Exit": round(exit_price, 2),
                "Bars Held": bars_held,
                "Result": result,
                "Net R": round(net_r, 2)
            }
        )

        i = max(
            i + 1,
            i + bars_held
        )

    total_trades = len(
        journal
    )

    win_rate = (
        wins / total_trades * 100
        if total_trades > 0
        else 0
    )

    gross_profit = sum(
        max(0, x["Net R"])
        for x in journal
    )

    gross_loss = abs(
        sum(
            min(0, x["Net R"])
            for x in journal
        )
    )

    if gross_loss > 0:

        profit_factor = (
            gross_profit /
            gross_loss
        )

    else:

        profit_factor = 0

    expectancy = (
        equity / total_trades
        if total_trades > 0
        else 0
    )

    return {
        "trades": total_trades,
        "win_rate": win_rate,
        "net_r": equity,
        "profit_factor": profit_factor,
        "max_drawdown": max_drawdown,
        "expectancy": expectancy,
        "journal": pd.DataFrame(journal)
    }
