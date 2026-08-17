import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go

from strategy import generate_signal


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Friendly Trader",
    page_icon="📈",
    layout="wide"
)


# =========================================================
# TITLE
# =========================================================

st.title("Friendly Trader")

st.caption(
    "Trade Smart. Trade Friendly. — Alpha 0.9 Research Prototype"
)


# =========================================================
# TWELVE DATA
# =========================================================

@st.cache_data(ttl=60)
def get_market_data(
    interval,
    outputsize
):

    api_key = st.secrets[
        "TWELVE_DATA_API_KEY"
    ]

    url = (
        "https://api.twelvedata.com/"
        "time_series"
    )

    params = {
        "symbol": "XAU/USD",
        "interval": interval,
        "outputsize": outputsize,
        "apikey": api_key
    }

    response = requests.get(
        url,
        params=params,
        timeout=20
    )

    response.raise_for_status()

    result = response.json()

    if "values" not in result:

        raise RuntimeError(
            result.get(
                "message",
                "Twelve Data returned no values."
            )
        )

    df = pd.DataFrame(
        result["values"]
    )

    df["time"] = pd.to_datetime(
        df["datetime"]
    )

    for column in [
        "open",
        "high",
        "low",
        "close"
    ]:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    df = df[
        [
            "time",
            "open",
            "high",
            "low",
            "close"
        ]
    ]

    df = df.dropna()

    df = df.sort_values(
        "time"
    )

    return df.reset_index(
        drop=True
    )


# =========================================================
# LOAD DATA
# =========================================================

try:

    with st.spinner(
        "Loading XAU/USD market data..."
    ):

        df_15m = get_market_data(
            "15min",
            500
        )

        df_1h = get_market_data(
            "1h",
            500
        )

        df_4h = get_market_data(
            "4h",
            500
        )

except Exception as error:

    st.error(
        "Market data loading failed."
    )

    st.exception(error)

    st.stop()


st.success(
    f"Real data loaded: "
    f"{len(df_15m)} × 15M | "
    f"{len(df_1h)} × 1H | "
    f"{len(df_4h)} × 4H"
)


# =========================================================
# LIVE SIGNAL
# =========================================================

try:

    live_signal = generate_signal(
        df_
