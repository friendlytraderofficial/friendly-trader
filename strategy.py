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

    rs = avg_gain / avg_loss.replace(0, np.nan)

    data["rsi"] = 100 - (
        100 / (1 + rs)
    )

    data["tr"] = np.maximum(
        data["high"] - data["low"],
        np.maximum(
            abs(
                data["high"] -
                data["close"].shift()
            ),
            abs(
                data["low"] -
                data["close"].shift()
            )
        )
    )

    data["atr"] = data["tr"].rolling(14).mean()

    return data


def generate_signal(df):

    data = add_indicators(df)

    latest = data.iloc[-1]

    price = float(latest["close"])
    ema20 = float(latest["ema20"])
    ema50 = float(latest["ema50"])
    ema200 = float(latest["ema200"])
    rsi = float(latest["rsi"])
    atr = float(latest["atr"])

    if not np.isfinite(atr) or atr <= 0:
        atr = price * 0.001

    score_buy = 0
    score_sell = 0

    # Trend
    if ema20 > ema50:
        score_buy += 2

    if ema20 < ema50:
        score_sell += 2

    # Major trend
    if price > ema200:
        score_buy += 2

    if price < ema200:
        score_sell += 2

    # Momentum
    if 55 <= rsi <= 70:
        score_buy += 2

    if 30 <= rsi <= 45:
        score_sell += 2

    # Short-term price position
    if price > ema20:
        score_buy += 1

    if price < ema20:
        score_sell += 1

    # Avoid extreme momentum
    if rsi > 75:
        score_buy -= 1

    if rsi < 25:
        score_sell -= 1

    score_buy = max(0, min(10, score_buy))
    score_sell = max(0, min(10, score_sell))

    if score_buy >= 7 and score_buy > score_sell:

        direction = "BUY"
        score = score_buy

        entry = price
        sl = entry - atr
        tp = entry + (atr * 3)

    elif score_sell >= 7 and score_sell > score_buy:

        direction = "SELL"
        score = score_sell

        entry = price
        sl = entry + atr
        tp = entry - (atr * 3)

    else:

        direction = "WAIT"
        score = max(
            score_buy,
            score_sell
        )

        entry = price
        sl = price
        tp = price

    return {
        "direction": direction,
        "score": int(score),
        "entry": round(entry, 2),
        "sl": round(sl, 2),
        "tp": round(tp, 2)
    }


def backtest(df, trades=50):

    data = add_indicators(df)

    data = data.dropna().copy()

    test_data = data.tail(trades)

    journal = []

    wins = 0
    losses = 0
    net_r = 0.0

    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0

    for i in range(len(test_data) - 5):

        row = test_data.iloc[i]

        price = float(row["close"])

        atr = float(row["atr"])

        if not np.isfinite(atr) or atr <= 0:
            continue

        if row["ema20"] > row["ema50"]:
            direction = 1

        elif row["ema20"] < row["ema50"]:
            direction = -1

        else:
            continue

        future = test_data.iloc[
            i + 5
        ]

        future_price = float(
            future["close"]
        )

        if direction == 1:
            win = future_price > price
        else:
            win = future_price < price

        if win:

            result_r = 3.0
            wins += 1

        else:

            result_r = -1.0
            losses += 1

        net_r += result_r
        equity += result_r

        peak = max(
            peak,
            equity
        )

        drawdown = equity - peak

        max_drawdown = min(
            max_drawdown,
            drawdown
        )

        journal.append({
            "Time": row["time"],
            "Direction": (
                "BUY"
                if direction == 1
                else "SELL"
            ),
            "Result": (
                "WIN"
                if win
                else "LOSS"
            ),
            "R": result_r
        })

    total_trades = len(journal)

    if total_trades > 0:

        win_rate = (
            wins /
            total_trades
        ) * 100

    else:

        win_rate = 0.0

    gross_profit = wins * 3

    gross_loss = losses

    if gross_loss > 0:

        profit_factor = (
            gross_profit /
            gross_loss
        )

    else:

        profit_factor = 0.0

    journal_df = pd.DataFrame(
        journal
    )

    return {
        "trades": total_trades,
        "win_rate": win_rate,
        "net_r": net_r,
        "profit_factor": profit_factor,
        "max_drawdown": max_drawdown,
        "journal": journal_df
    }
