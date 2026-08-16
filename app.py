import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests

from strategy import generate_signal, backtest


st.set_page_config(
    page_title="Friendly Trader",
    page_icon="📈",
    layout="wide"
)


st.markdown("""
<style>
.main {
    background-color: #080b14;
}

.block-container {
    padding-top: 1.2rem;
}

.metric-card {
    padding: 14px;
    border-radius: 12px;
    background: #111827;
    border: 1px solid #253047;
}
</style>
""", unsafe_allow_html=True)


st.title("Friendly Trader")
st.caption(
    "Trade Smart. Trade Friendly. — Alpha 0.2 Research Prototype"
)


# ---------------------------------------------------------
# REAL XAU/USD DATA
# ---------------------------------------------------------

    @st.cache_data(ttl=60)
def get_xauusd_data(interval, outputsize):

    api_key = st.secrets["TWELVE_DATA_API_KEY"]

    url = "https://api.twelvedata.com/time_series"

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

    data = response.json()

    if "values" not in data:
        raise RuntimeError(
            f"Twelve Data error: {data}"
        )

    df = pd.DataFrame(data["values"])

    df["datetime"] = pd.to_datetime(
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

    df = df.dropna()

    df = df.sort_values(
        "datetime"
    ).reset_index(drop=True)

    df = df.rename(
        columns={
            "datetime": "time"
        }
    )

    return df
