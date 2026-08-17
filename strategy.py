import numpy as np
import pandas as pd


def indicators(df):
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

    # RSI
    delta = data["close"].diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)

    data["rsi"] = 100 - (
        100 / (1 + rs)
    )

    # ATR
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

    data["atr"] = pd.concat(
        [tr1, tr2, tr3],
        axis=1
    ).max(axis=1).rolling(14).mean()

    return data


def trend(df):

    data = indicators(df).dropna()

    if data.empty:
        return "NEUTRAL"

    row = data.iloc[-1]

    if (
        row["ema20"] > row["ema50"]
        and
        row["ema50"] > row["ema200"]
    ):
        return "BULLISH"

    if (
        row["ema20"] < row["ema50"]
        and
        row["ema50"] < row["ema200"]
    ):
        return "BEARISH"

    return "NEUTRAL"


def generate_signal(     
      print(
        "DEBUG SIGNAL:",
        direction,
        score,
        buy_score,
        sell_score
)  df_15m,
    df_1h,
    df_4h
):
    print("ALPHA 0.9 SIGNAL ENGINE RUNNING")
    data = indicators(
        df_15m
    ).dropna()

    if len(data) < 50:
        raise ValueError(
            "Not enough 15M data."
        )

    row = data.iloc[-1]
    previous = data.iloc[-2]

    price = float(row["close"])
    atr = float(row["atr"])
    rsi = float(row["rsi"])

    if not np.isfinite(atr) or atr <= 0:
        atr = price * 0.001


    # =====================================================
    # HIGHER TIMEFRAME TRENDS
    # =====================================================

    h1 = trend(df_1h)
    h4 = trend(df_4h)


    # =====================================================
    # 15M TREND
    # =====================================================

    bullish_15m = (
        row["ema20"] >
        row["ema50"] >
        row["ema200"]
    )

    bearish_15m = (
        row["ema20"] <
        row["ema50"] <
        row["ema200"]
    )


    # =====================================================
    # CANDLE CONFIRMATION
    # =====================================================

    bullish_candle = (
        row["close"] >
        row["open"]
    )

    bearish_candle = (
        row["close"] <
        row["open"]
    )


    # =====================================================
    # MOMENTUM CONFIRMATION
    # =====================================================

    rsi_rising = (
        row["rsi"] >
        previous["rsi"]
    )

    rsi_falling = (
        row["rsi"] <
        previous["rsi"]
    )


    bullish_momentum = (
        52 <= rsi <= 65
        and
        rsi_rising
    )

    bearish_momentum = (
        35 <= rsi <= 48
        and
        rsi_falling
    )


    # =====================================================
    # EMA20 DISTANCE
    # =====================================================

    ema_distance_pct = (
        abs(
            price -
            row["ema20"]
        )
        /
        price
    ) * 100


    # Gold can move quickly, so don't enter
    # when price is already heavily extended.

    not_extended = (
        ema_distance_pct <= 0.30
    )


    # =====================================================
    # BUY SCORE
    # =====================================================

    buy_score = 0

    if bullish_15m:
        buy_score += 2

    if h1 == "BULLISH":
        buy_score += 1

    if h4 == "BULLISH":
        buy_score += 1

    if bullish_momentum:
        buy_score += 2

    if not_extended:
        buy_score += 1

    if bullish_candle:
        buy_score += 1

    if price > row["ema20"]:
        buy_score += 1

    if price > previous["close"]:
        buy_score += 1


    # =====================================================
    # SELL SCORE
    # =====================================================

    sell_score = 0

    if bearish_15m:
        sell_score += 2

    if h1 == "BEARISH":
        sell_score += 1

    if h4 == "BEARISH":
        sell_score += 1

    if bearish_momentum:
        sell_score += 2

    if not_extended:
        sell_score += 1

    if bearish_candle:
        sell_score += 1

    if price < row["ema20"]:
        sell_score += 1

    if price < previous["close"]:
        sell_score += 1


    # =====================================================
    # FINAL SCORE
    # =====================================================

    raw_score = max(
        buy_score,
        sell_score
    )

    # Already a genuine 0-10 score.
   
