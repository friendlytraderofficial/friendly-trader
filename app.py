import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
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
st.caption("Trade Smart. Trade Friendly. — Alpha 0.1 Research Prototype")

# Demo XAUUSD data
np.random.seed(7)

n = 1200

dates = pd.date_range(
    "2026-01-01",
    periods=n,
    freq="15min"
)

returns = np.random.normal(
    0,
    0.0008,
    n
)

price = 2350 * np.exp(
    np.cumsum(returns)
)

df = pd.DataFrame({
    "time": dates,
    "open": price,
    "high": price * (
        1 + np.random.uniform(0, 0.0015, n)
    ),
    "low": price * (
        1 - np.random.uniform(0, 0.0015, n)
    ),
    "close": price * (
        1 + np.random.normal(0, 0.00035, n)
    )
})

df["high"] = df[
    ["open", "high", "close"]
].max(axis=1)

df["low"] = df[
    ["open", "low", "close"]
].min(axis=1)

signal = generate_signal(df)

# Top metrics
c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "XAUUSD",
    f"${df.close.iloc[-1]:,.2f}"
)

c2.metric(
    "Signal",
    signal["direction"]
)

c3.metric(
    "Score",
    f'{signal["score"]}/10'
)

c4.metric(
    "Risk / Reward",
    "1:3"
)

# Main layout
left, right = st.columns([2.2, 1])

with left:

    st.subheader("📊 XAUUSD Market Chart")

    fig = go.Figure(
        data=[
            go.Candlestick(
                x=df.time.tail(250),
                open=df.open.tail(250),
                high=df.high.tail(250),
                low=df.low.tail(250),
                close=df.close.tail(250)
            )
        ]
    )

    fig.update_layout(
        template="plotly_dark",
        height=520,
        xaxis_rangeslider_visible=False
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

with right:

    st.subheader("🚨 Latest Signal")

    st.markdown(
        f"## {signal['direction']}"
    )

    st.write(
        f"**Entry:** {signal['entry']}"
    )

    st.write(
        f"**Stop Loss:** {signal['sl']}"
    )

    st.write(
        f"**Take Profit:** {signal['tp']}"
    )

    st.progress(
        signal["score"] / 10
    )

    st.write(
        f"**Setup Score:** "
        f"{signal['score']}/10"
    )

    st.info(
        "Prototype only. "
        "Real-money execution is disabled."
    )

st.divider()

st.subheader("🧪 50-Trade Backtest")

results = backtest(
    df,
    trades=50
)

m1, m2, m3, m4, m5 = st.columns(5)

m1.metric(
    "Trades",
    results["trades"]
)

m2.metric(
    "Win Rate",
    f'{results["win_rate"]:.1f}%'
)

m3.metric(
    "Net R",
    f'{results["net_r"]:.2f}R'
)

m4.metric(
    "Profit Factor",
    f'{results["profit_factor"]:.2f}'
)

m5.metric(
    "Max Drawdown",
    f'{results["max_drawdown"]:.2f}R'
)

st.subheader("📒 Trade Journal")

st.dataframe(
    results["journal"],
    use_container_width=True,
    hide_index=True
)

st.caption(
    "Alpha 0.1 uses synthetic data. "
    "Do not use these results for real trading."
)
