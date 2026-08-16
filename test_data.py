import streamlit as st
import requests

st.title("Friendly Trader — Data Connection Test")

api_key = st.secrets["TWELVE_DATA_API_KEY"]

url = "https://api.twelvedata.com/price"

params = {
    "symbol": "XAU/USD",
    "apikey": api_key
}

response = requests.get(
    url,
    params=params,
    timeout=15
)

st.write("HTTP status:", response.status_code)
st.json(response.json())
