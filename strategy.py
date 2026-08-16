import numpy as np
import pandas as pd


def indicators(df):
    x = df.copy().sort_values("time").reset_index(drop=True)

    x["ema20"] = x["close"].ewm(
        span=20,
        adjust=False
    ).mean()

    x["ema50"] = x["close"].ewm(
        span=50,
        adjust=False
    ).mean()

    x["ema200"] = x["close"].ewm(
        span=200,
        adjust=False
    ).mean()

    delta = x["close"].diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)

    x["rsi"] = 100 - (100 / (1 + rs))

    tr = pd.concat(
        [
            x["high"] - x["low"],
            (x["high"] - x["close"].shift()).abs(),
            (x["low"] - x["close"].shift()).abs()
        ],
        axis=1
    ).max(axis=1)

    x["atr"] = tr.rolling(14).mean()

    return x


def trend(df):

    x = indicators(df).dropna()

    if x.empty:
        return "NEUTRAL"

    r = x.iloc[-1]

    if r["ema20"] > r["ema50"] > r["ema200"]:
        return "BULLISH"

    if r["ema20"] < r["ema50"] < r["ema200"]:
        return "BEARISH"

    return "NEUTRAL"


def generate_signal(df_15m, df_1h, df_4h):

    x = indicators(df_15m).dropna()

    r = x.iloc[-1]

    price = float(r["close"])
    atr = float(r["atr"])

    if not np.isfinite(atr) or atr <= 0:
        atr = price * 0.001

    h1 = trend(df_1h)
    h4 = trend(df_4h)

    buy = 0
    sell = 0

    if r["ema20"] > r["ema50"]:
        buy += 2
    else:
        sell += 2

    if price > r["ema200"]:
        buy += 2
    else:
        sell += 2

    if 55 <= r["rsi"] <= 70:
        buy += 2

    elif 30 <= r["rsi"] <= 45:
        sell += 2

    if h1 == "BULLISH":
        buy += 2

    elif h1 == "BEARISH":
        sell += 2

    if h4 == "BULLISH":
        buy += 2

    elif h4 == "BEARISH":
        sell += 2

    if buy >= 8 and buy > sell:
        direction = "BUY"
        score = min(buy, 10)
        entry = price
        sl = entry - atr
        tp = entry + 3 * atr

    elif sell >= 8 and sell > buy:
        direction = "SELL"
        score = min(sell, 10)
        entry = price
        sl = entry + atr
        tp = entry - 3 * atr

    else:
        direction = "WAIT"
        score = max(buy, sell)
        entry = price
        sl = price
        tp = price

    return {
        "direction": direction,
        "score": int(score),
        "entry": round(entry, 2),
        "sl": round(sl, 2),
        "tp": round(tp, 2),
        "h1_trend": h1,
        "h4_trend": h4
    }


def backtest(
    df_15m,
    df_1h,
    df_4h,
    trades=50
):

    # Use the most recent 1000 candles
    # for fast research testing.
    base = df_15m.tail(1000).copy()

    h1 = trend(df_1h)
    h4 = trend(df_4h)

    x = indicators(base).dropna().reset_index(drop=True)

    journal = []

    equity = 0.0
    peak = 0.0
    max_dd = 0.0

    for i in range(
        len(x) - 20
    ):

        if len(journal) >= trades:
            break

        r = x.iloc[i]

        price = float(r["close"])
        atr = float(r["atr"])

        if not np.isfinite(atr) or atr <= 0:
            continue

        buy = 0
        sell = 0

        if r["ema20"] > r["ema50"]:
            buy += 2
        else:
            sell += 2

        if price > r["ema200"]:
            buy += 2
        else:
            sell += 2

        if 55 <= r["rsi"] <= 70:
            buy += 2

        elif 30 <= r["rsi"] <= 45:
            sell += 2

        if h1 == "BULLISH":
            buy += 2

        elif h1 == "BEARISH":
            sell += 2

        if h4 == "BULLISH":
            buy += 2

        elif h4 == "BEARISH":
            sell += 2

        if buy >= 8 and buy > sell:

            direction = "BUY"
            sl = price - atr
            tp = price + 3 * atr

        elif sell >= 8 and sell > buy:

            direction = "SELL"
            sl = price + atr
            tp = price - 3 * atr

        else:
            continue

        result_r = None
        exit_price = price

        for j in range(
            i + 1,
            min(i + 21, len(x))
        ):

            future = x.iloc[j]

            high = float(future["high"])
            low = float(future["low"])

            if direction == "BUY":

                if low <= sl:
                    result_r = -1
                    exit_price = sl
                    break

                if high >= tp:
                    result_r = 3
                    exit_price = tp
                    break

            else:

                if high >= sl:
                    result_r = -1
                    exit_price = sl
                    break

                if low <= tp:
                    result_r = 3
                    exit_price = tp
                    break

        if result_r is None:
            continue

        equity += result_r

        peak = max(
            peak,
            equity
        )

        max_dd = min(
            max_dd,
            equity - peak
        )

        journal.append(
            {
                "Time": r["time"],
                "Direction": direction,
                "Entry": round(price, 2),
                "SL": round(sl, 2),
                "TP": round(tp, 2),
                "Exit": round(exit_price, 2),
                "Result R": result_r
            }
        )

    total = len(journal)

    wins = sum(
        1 for t in journal
        if t["Result R"] > 0
    )

    win_rate = (
        wins / total * 100
        if total
        else 0
    )

    gross_profit = sum(
        t["Result R"]
        for t in journal
        if t["Result R"] > 0
    )

    gross_loss = abs(
        sum(
            t["Result R"]
            for t in journal
            if t["Result R"] < 0
        )
    )

    profit_factor = (
        gross_profit / gross_loss
        if gross_loss > 0
        else 0
    )

    expectancy = (
        equity / total
        if total
        else 0
    )

    return {
        "trades": total,
        "win_rate": win_rate,
        "net_r": equity,
        "profit_factor": profit_factor,
        "max_drawdown": max_dd,
        "expectancy": expectancy,
        "journal": pd.DataFrame(journal)
        }
