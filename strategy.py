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

    previous_close = data["close"].shift(1)

    tr1 = data["high"] - data["low"]
    tr2 = abs(data["high"] - previous_close)
    tr3 = abs(data["low"] - previous_close)

    data["tr"] = pd.concat(
        [tr1, tr2, tr3],
        axis=1
    ).max(axis=1)

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

    buy_score = 0
    sell_score = 0

    # Short-term trend
    if ema20 > ema50:
        buy_score += 2
    elif ema20 < ema50:
        sell_score += 2

    # Major trend
    if price > ema200:
        buy_score += 2
    elif price < ema200:
        sell_score += 2

    # RSI momentum
    if 55 <= rsi <= 70:
        buy_score += 2
    elif 30 <= rsi <= 45:
        sell_score += 2

    # Price vs EMA20
    if price > ema20:
        buy_score += 1
    elif price < ema20:
        sell_score += 1

    # Avoid extreme momentum
    if rsi > 75:
        buy_score -= 1

    if rsi < 25:
        sell_score -= 1

    buy_score = max(0, min(10, buy_score))
    sell_score = max(0, min(10, sell_score))

    if buy_score >= 7 and buy_score > sell_score:

        direction = "BUY"
        score = buy_score

        entry = price
        sl = entry - atr
        tp = entry + (3 * atr)

    elif sell_score >= 7 and sell_score > buy_score:

        direction = "SELL"
        score = sell_score

        entry = price
        sl = entry + atr
        tp = entry - (3 * atr)

    else:

        direction = "WAIT"
        score = max(buy_score, sell_score)

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


def backtest(
    df,
    trades=50,
    max_holding_bars=20,
    cost_r=0.10
):
    """
    Candle-by-candle 1:3 R:R research backtest.

    Entry:
        Close of signal candle.

    BUY:
        SL = 1 ATR below entry
        TP = 3 ATR above entry

    SELL:
        SL = 1 ATR above entry
        TP = 3 ATR below entry

    If both TP and SL occur in the same candle,
    the result is treated conservatively as a loss.

    cost_r:
        Research allowance for trading costs expressed in R.
        This is a placeholder and should later be calibrated
        to the actual broker's spread/slippage.
    """

    data = add_indicators(df)
    data = data.dropna().reset_index(drop=True)

    journal = []

    equity = 0.0
    peak_equity = 0.0
    max_drawdown = 0.0

    wins = 0
    losses = 0
    total_cost = 0.0

    i = 0

    while (
        i < len(data) - 1
        and len(journal) < trades
    ):

        row = data.iloc[i]

        price = float(row["close"])
        ema20 = float(row["ema20"])
        ema50 = float(row["ema50"])
        ema200 = float(row["ema200"])
        rsi = float(row["rsi"])
        atr = float(row["atr"])

        if not np.isfinite(atr) or atr <= 0:
            i += 1
            continue

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

        buy_score = max(0, min(10, buy_score))
        sell_score = max(0, min(10, sell_score))

        if buy_score >= 7 and buy_score > sell_score:

            direction = "BUY"
            score = buy_score

            entry = price
            sl = entry - atr
            tp = entry + (3 * atr)

        elif sell_score >= 7 and sell_score > buy_score:

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

        for j in range(i + 1, end):

            future = data.iloc[j]

            high = float(future["high"])
            low = float(future["low"])

            bars_held += 1

            if direction == "BUY":

                hit_sl = low <= sl
                hit_tp = high >= tp

            else:

                hit_sl = high >= sl
                hit_tp = low <= tp

            # Conservative rule:
            # if both are touched in the same candle,
            # assume SL happened first.
            if hit_sl and hit_tp:

                result = "LOSS"
                result_r = -1.0
                exit_price = sl
                exit_time = future["time"]
                losses += 1
                break

            if hit_sl:

                result = "LOSS"
                result_r = -1.0
                exit_price = sl
                exit_time = future["time"]
                losses += 1
                break

            if hit_tp:

                result = "WIN"
                result_r = 3.0
                exit_price = tp
                exit_time = future["time"]
                wins += 1
                break

        else:

            # Position expired without TP/SL.
            future = data.iloc[end - 1]

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
                wins += 1
            elif result_r < 0:
                result = "PARTIAL LOSS"
                losses += 1
            else:
                result = "BREAKEVEN"

        net_before_cost = result_r

        result_r_after_cost = (
            result_r - cost_r
        )

        total_cost += cost_r

        equity += result_r_after_cost

        peak_equity = max(
            peak_equity,
            equity
        )

        drawdown = (
            equity - peak_equity
        )

        max_drawdown = min(
            max_drawdown,
            drawdown
        )

        journal.append({
            "Entry Time": row["time"],
            "Exit Time": exit_time,
            "Direction": direction,
            "Score": int(score),
            "Entry": round(entry, 2),
            "SL": round(sl, 2),
            "TP": round(tp, 2),
            "Exit": round(exit_price, 2),
            "Bars Held": bars_held,
            "Result": result,
            "Gross R": round(
                net_before_cost,
                2
            ),
            "Cost R": round(
                cost_r,
                2
            ),
            "Net R": round(
                result_r_after_cost,
                2
            )
        })

        # Prevent overlapping trades.
        i = max(
            i + 1,
            i + bars_held
        )

    total_trades = len(journal)

    if total_trades:

        win_rate = (
            wins /
            total_trades
        ) * 100

    else:

        win_rate = 0.0

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

        profit_factor = 0.0

    if total_trades:

        expectancy = (
            sum(
                x["Net R"]
                for x in journal
            ) /
            total_trades
        )

    else:

        expectancy = 0.0

    journal_df = pd.DataFrame(
        journal
    )

    return {
        "trades": total_trades,
        "win_rate": win_rate,
        "net_r": equity,
        "profit_factor": profit_factor,
        "max_drawdown": max_drawdown,
        "expectancy": expectancy,
        "total_cost": total_cost,
        "journal": journal_df
    }
