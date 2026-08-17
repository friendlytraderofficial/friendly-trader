import streamlit as st
import yfinance as yf
import plotly.graph_objects as go

st.set_page_config(page_title="Friendly Trader", page_icon="📈", layout="wide")

st.title("🤝 Friendly Trader")
st.caption("Trade Smart. Trade Friendly. — Alpha 1.2 Research Prototype")

symbol = "GC=F"
df = yf.download(symbol, period="5d", interval="15m", auto_adjust=False, progress=False)

if df.empty:
    st.error("Market data unavailable. Try again later.")
    st.stop()

df.columns = df.columns.get_level_values(0)
df = df.dropna()
price = float(df["Close"].iloc[-1])

df["EMA20"] = df["Close"].ewm(span=20).mean()
df["EMA50"] = df["Close"].ewm(span=50).mean()

signal = "BUY" if df["EMA20"].iloc[-1] > df["EMA50"].iloc[-1] else "SELL"
score = 6
risk = price * 0.002
entry = price
sl = price - risk if signal == "BUY" else price + risk
tp = price + risk * 3 if signal == "BUY" else price - risk * 3

if abs(df["EMA20"].iloc[-1] - df["EMA50"].iloc[-1]) < price * 0.0005:
    signal = "WAIT"

c1, c2, c3, c4 = st.columns(4)
c1.metric("XAUUSD", f"${price:,.2f}")
c2.metric("Signal", signal)
c3.metric("Score", f"{score}/10")
c4.metric("Risk / Reward", "1:3")

st.subheader("📊 XAUUSD 15-Minute Chart")

fig = go.Figure()
fig.add_trace(go.Candlestick(
    x=df.index, open=df["Open"], high=df["High"],
    low=df["Low"], close=df["Close"], name="XAUUSD"
))
fig.update_layout(height=500, xaxis_rangeslider_visible=False)
st.plotly_chart(fig, use_container_width=True)

st.subheader("🚨 Latest Signal")
st.write(f"**{signal}**")
st.write(f"**Entry:** ${entry:,.2f}")
st.write(f"**Stop Loss:** ${sl:,.2f}")
st.write(f"**Take Profit:** ${tp:,.2f}")

st.info("⚠️ Alpha 1.2 is a research prototype. Signals are not financial advice.")
