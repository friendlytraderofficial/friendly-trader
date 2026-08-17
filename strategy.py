import numpy as np
import pandas as pd


# =========================================================
# INDICATORS
# =========================================================

def ema(series, period):
    return series.ewm(
        span=period,
        adjust=False
    ).mean()


def rsi(series, period=14):
    delta = series.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period
    ).mean()

    rs = avg_gain / avg_loss.replace(
        0,
        np.nan
    )

    result = 100 - (
        100 / (1 + rs)
    )

    return result.fillna(50)


def atr(df, period=14):

    previous_close = df["close"].shift(1)

    tr = pd.concat(
        [
            df["high"] - df["low"],
            (
                df["high"] -
                previous_close
            ).abs(),
            (
                df["low"] -
                previous_close
            ).abs()
        ],
        axis=1
    ).max(axis=1)

    return tr.ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period
    ).mean()


# =========================================================
# DATA CLEANING
# =========================================================

def clean_data(df):

    required = [
        "time",
        "open",
        "high",
        "low",
        "close"
    ]

    data = df[
        required
    ].copy()

    data = data.dropna()

    data = data.sort_values(
        "time"
    )

    data = data.drop_duplicates(
        subset="time",
        keep="last"
    )

    return data.reset_index(
        drop=True
    )


# =========================================================
# TREND
# =========================================================

def get_trend(df):

    if len(df) < 50:
        return "NEUTRAL"

    close = df["close"]

    fast = ema(
        close,
        20
    ).iloc[-1]

    slow = ema(
        close,
        50
    ).iloc[-1]

    if fast > slow:
        return "BULLISH"

    if fast < slow:
        return "BEARISH"

    return "NEUTRAL"


# =========================================================
# MAIN SIGNAL ENGINE
# =========================================================

def generate_signal(
    df_15m,
    df_1h,
    df_4h
):

    data_15m = clean_data(
        df_15m
    )

    data_1h = clean_data(
        df_1h
    )

    data_4h = clean_data(
        df_4h
    )

    price = float(
        data_15m["close"].iloc[-1]
    )

    # -----------------------------------------------------
    # Safety check
    # -----------------------------------------------------

    if (
        len(data_15m) < 60
        or len(data_1h) < 50
        or len(data_4h) < 50
    ):

        return {
            "direction": "WAIT",
            "score": 0.0,
            "buy_score": 0.0,
            "sell_score": 0.0,
            "entry": None,
            "sl": None,
            "tp": None,
            "h1_trend": "NEUTRAL",
            "h4_trend": "NEUTRAL",
            "rsi": 50.0,
            "atr": 0.0,
            "momentum": 0.0,
            "reason": "Not enough historical data."
        }

    # -----------------------------------------------------
    # 15M indicators
    # -----------------------------------------------------

    close = data_15m["close"]

    ema20 = ema(
        close,
        20
    )

    ema50 = ema(
        close,
        50
    )

    current_ema20 = float(
        ema20.iloc[-1]
    )

    current_ema50 = float(
        ema50.iloc[-1]
    )

    current_rsi = float(
        rsi(
            close,
            14
        ).iloc[-1]
    )

    current_atr = float(
        atr(
            data_15m,
            14
        ).iloc[-1]
    )

    # -----------------------------------------------------
    # Momentum
    # -----------------------------------------------------

    lookback = 8

    old_price = float(
        close.iloc[-1 - lookback]
    )

    momentum_pct = (
        (
            price /
            old_price
        ) - 1
    ) * 100

    # -----------------------------------------------------
    # Higher timeframe trends
    # -----------------------------------------------------

    h1_trend = get_trend(
        data_1h
    )

    h4_trend = get_trend(
        data_4h
    )

    # -----------------------------------------------------
    # Recent structure
    # -----------------------------------------------------

    recent_high = float(
        data_15m[
            "high"
        ]
        .iloc[-21:-1]
        .max()
    )

    recent_low = float(
        data_15m[
            "low"
        ]
        .iloc[-21:-1]
        .min()
    )

    # =====================================================
    # SCORING
    #
    # Maximum = 10
    #
    # Trend alignment       4 points
    # 15M EMA direction     1 point
    # Momentum               2 points
    # RSI                    1 point
    # Structure              1 point
    # Volatility             1 point
    # =====================================================

    buy_score = 0.0
    sell_score = 0.0

    buy_reasons = []
    sell_reasons = []

    # -----------------------------------------------------
    # Higher timeframe trend
    # -----------------------------------------------------

    if h1_trend == "BULLISH":
        buy_score += 2.0
        buy_reasons.append(
            "1H bullish"
        )

    elif h1_trend == "BEARISH":
        sell_score += 2.0
        sell_reasons.append(
            "1H bearish"
        )

    if h4_trend == "BULLISH":
        buy_score += 2.0
        buy_reasons.append(
            "4H bullish"
        )

    elif h4_trend == "BEARISH":
        sell_score += 2.0
        sell_reasons.append(
            "4H bearish"
        )

    # -----------------------------------------------------
    # 15M EMA
    # -----------------------------------------------------

    if current_ema20 > current_ema50:

        buy_score += 1.0

        buy_reasons.append(
            "15M EMA bullish"
        )

    elif current_ema20 < current_ema50:

        sell_score += 1.0

        sell_reasons.append(
            "15M EMA bearish"
        )

    # -----------------------------------------------------
    # Momentum
    # -----------------------------------------------------

    if momentum_pct >= 0.20:

        buy_score += 2.0

        buy_reasons.append(
            "Positive momentum"
        )

    elif momentum_pct <= -0.20:

        sell_score += 2.0

        sell_reasons.append(
            "Negative momentum"
        )

    # -----------------------------------------------------
    # RSI
    #
    # Avoid buying when extremely overbought.
    # Avoid selling when extremely oversold.
    # -----------------------------------------------------

    if 52 <= current_rsi <= 68:

        buy_score += 1.0

        buy_reasons.append(
            "Healthy bullish RSI"
        )

    elif 32 <= current_rsi <= 48:

        sell_score += 1.0

        sell_reasons.append(
            "Healthy bearish RSI"
        )

    # -----------------------------------------------------
    # Structure
    # -----------------------------------------------------

    if price > recent_high:

        buy_score += 1.0

        buy_reasons.append(
            "Recent high breakout"
        )

    elif price < recent_low:

        sell_score += 1.0

        sell_reasons.append(
            "Recent low breakdown"
        )

    # -----------------------------------------------------
    # Volatility
    #
    # Only award the volatility point when ATR is
    # reasonable relative to price.
    # -----------------------------------------------------

    atr_percent = (
        current_atr /
        price
    ) * 100

    volatility_ok = (
        0.05 <= atr_percent <= 1.50
    )

    if volatility_ok:

        if buy_score > sell_score:

            buy_score += 1.0

            buy_reasons.append(
                "Usable volatility"
            )

        elif sell_score > buy_score:

            sell_score += 1.0

            sell_reasons.append(
                "Usable volatility"
            )

    # -----------------------------------------------------
    # Clamp
    # -----------------------------------------------------

    buy_score = round(
        min(
            buy_score,
            10.0
        ),
        2
    )

    sell_score = round(
        min(
            sell_score,
            10.0
        ),
        2
    )

    best_score = max(
        buy_score,
        sell_score
    )

    difference = abs(
        buy_score -
        sell_score
    )

    # =====================================================
    # SIGNAL FILTER
    #
    # We deliberately require:
    #
    # 1. Score >= 6.5
    # 2. Directional difference >= 2
    #
    # This prevents weak BUY/SELL signals.
    # =====================================================

    direction = "WAIT"

    if (
        best_score >= 6.5
        and difference >= 2.0
    ):

        if buy_score > sell_score:

            direction = "BUY"

        else:

            direction = "SELL"

    # =====================================================
    # WAIT
    #
    # IMPORTANT:
    # Do NOT fabricate SL/TP for WAIT.
    # =====================================================

    if direction == "WAIT":

        return {
            "direction": "WAIT",
            "score": best_score,
            "buy_score": buy_score,
            "sell_score": sell_score,
            "entry": None,
            "sl": None,
            "tp": None,
            "h1_trend": h1_trend,
            "h4_trend": h4_trend,
            "rsi": round(
                current_rsi,
                2
            ),
            "atr": round(
                current_atr,
                2
            ),
            "momentum": round(
                momentum_pct,
                3
            ),
            "buy_reasons": buy_reasons,
            "sell_reasons": sell_reasons,
            "reason": (
                "No sufficiently strong "
                "directional setup."
            )
        }

    # =====================================================
    # RISK MANAGEMENT
    #
    # Risk = 1.25 ATR
    # Reward = 3 ATR
    #
    # Therefore approximate R:R = 1:3
    # =====================================================

    risk_distance = max(
        current_atr * 1.25,
        price * 0.0008
    )

    if direction == "BUY":

        entry = price

        stop_loss = (
            entry -
            risk_distance
        )

        take_profit = (
            entry +
            risk_distance * 3
        )

    else:

        entry = price

        stop_loss = (
            entry +
            risk_distance
        )

        take_profit = (
            entry -
            risk_distance * 3
        )

    return {
        "direction": direction,
        "score": best_score,
        "buy_score": buy_score,
        "sell_score": sell_score,
        "entry": round(
            entry,
            2
        ),
        "sl": round(
            stop_loss,
            2
        ),
        "tp": round(
            take_profit,
            2
        ),
        "h1_trend": h1_trend,
        "h4_trend": h4_trend,
        "rsi": round(
            current_rsi,
            2
        ),
        "atr": round(
            current_atr,
            2
        ),
        "momentum": round(
            momentum_pct,
            3
        ),
        "buy_reasons": buy_reasons,
        "sell_reasons": sell_reasons,
        "reason": (
            "Directional setup passed "
            "the signal filters."
        )
    }
