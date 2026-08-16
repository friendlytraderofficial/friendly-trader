import numpy as np
import pandas as pd


def generate_signal(df):
    """
    Generates a simple research signal using:
    - EMA trend
    - RSI momentum
    - ATR volatility
    """

    data = df.copy()

    data["ema_fast"] = data["close"].ewm(
        span=20,
        adjust=False
    ).mean()

    data["ema_slow"] = data["close"].ewm(
        span=50,
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
            abs(data["high"] - data["close"].shift()),
            abs(data["low"] - data["close"].shift())
        )
    )

    data["atr"] = data["tr"].rolling(14).mean()

    latest = data.iloc[-1]

    price = float(latest["close"])
    ema_fast = float(latest["ema_fast"])
    ema_slow = float(latest["ema_slow"])
    rsi = float(latest["rsi"])
    atr = float(latest["atr"])

    score = 5

    if ema_fast > ema_slow:
        score += 2
    else:
        score -= 2

    if rsi > 55:
        score += 2
    elif rsi < 45:
        score -= 2

    score = max(0, min(10, score))

    if score >= 7:
        direction = "BUY"
    elif score <= 3:
        direction = "SELL"
    else:
        direction = "WAIT"

    if not np.isfinite(atr) or atr <= 0:
        atr = price * 0.001

    entry = price

    if direction == "BUY":
        sl = entry - atr
        tp = entry + (atr * 3)

    elif direction == "SELL":
        sl = entry + atr
        tp = entry - (atr * 3)

    else:
        sl = entry
        tp = entry

    return {
        "direction": direction,
        "score": int(score),
        "entry": round(entry, 2),
        "sl": round(sl, 2),
        "tp": round(tp, 2)
    }


def backtest(df, trades=50):
    """
    Simple research backtest.

    Uses the generated signal logic and fixed
    1:3 risk/reward structure.

    This is a prototype and not a live trading system.
    """

    data = df.copy()

    data["ema_fast"] = data["close"].ewm(
        span=20,
        adjust=False
    ).mean()

    data["ema_slow"] = data["close"].ewm(
        span=50,
        adjust=False
    ).mean()

    data["signal"] = np.where(
        data["ema_fast"] > data["ema_slow"],
        1,
        -1
    )

    data["future_return"] = (
        data["close"].shift(-5) /
        data["close"] - 1
    )

    test_data = data.dropna().tail(trades)

    journal = []

    wins = 0
    losses = 0
    net_r = 0.0

    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0

    for i, row in test_data.iterrows():

        direction = int(row["signal"])
        future_return = float(row["future_return"])

        if direction == 1:
            win = future_return > 0
        else:
            win = future_return < 0

        if win:
            result_r = 3.0
            wins += 1
        else:
            result_r = -1.0
            losses += 1

        net_r += result_r
        equity += result_r

        peak = max(peak, equity)

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
            wins / total_trades
        ) * 100
    else:
        win_rate = 0.0

    gross_profit = wins * 3.0
    gross_loss = losses * 1.0

    if gross_loss > 0:
        profit_factor = (
            gross_profit / gross_loss
        )
    else:
        profit_factor = 0.0

    journal_df = pd.DataFrame(journal)

    return {
        "trades": total_trades,
        "win_rate": win_rate,
        "net_r": net_r,
        "profit_factor": profit_factor,
        "max_drawdown": max_drawdown,
        "journal": journal_df
  }
