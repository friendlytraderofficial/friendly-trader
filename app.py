import streamlit as st
import pandas as pd
import requests

st.set_page_config(
    page_title="Friendly Trader Test",
    page_icon="📈"
)

st.title("Friendly Trader")

st.success("App is running successfully.")

api_key = st.secrets["TWELVE_DATA_API_KEY"]

st.write("Testing Twelve Data...")

url = "https://api.twelvedata.com/time_series"

params = {
    "symbol": "XAU/USD",
    "interval": "15min",
    "outputsize": 100,
    "apikey": api_key
}

try:

    response = requests.get(
        url,
        params=params,
        timeout=20
    )

    st.write(
        "HTTP Status:",
        response.status_code
    )

    data = response.json()

    if "values" not in data:

        st.error("Twelve Data did not return candles.")

        st.json(data)

        st.stop()

    df = pd.DataFrame(
        data["values"]
    )

    st.success(
        f"Successfully loaded {len(df)} candles."
    )

    st.subheader(
        "Latest XAU/USD Data"
    )

    st.dataframe(
        df.head(10),
        use_container_width=True
    )

except Exception as e:

    st.error(
        "Data test failed."
    )

    st.exception(e)


st.divider()

st.subheader(
    "Backtest Diagnostic"
)

st.info(
    "If you can see this message, "
    "the problem is specifically inside "
    "the strategy/backtest code."
)

st.success(
    "Diagnostic page loaded completely."
)
