# -------------------------------------------------
# XAUUSD MACD Web App – CANDLESTICK VERSION (Full with D/W timeframes)
# -------------------------------------------------
import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# --- Page setup ---
st.set_page_config(page_title="XAUUSD Candles", layout="wide")
st.title("📈 Live XAUUSD Candlesticks with MACD & EMA")

# --- User Inputs ---
col1, col2 = st.columns(2)
with col1:
    timeframe = st.selectbox(
        "Timeframe",
        ["1h", "2h", "3h", "4h", "6h", "8h", "12h", "1D", "2D", "3D", "1W"],
        index=6
    )
with col2:
    lookback_hours = st.slider("Lookback (hours)", 24, 4000, 1000, step=24)

# Optional: Refresh button
if st.button("🔄 Refresh Data"):
    st.cache_data.clear()


# --- Fetch & Resample ---
@st.cache_data(ttl=300)
def get_data(timeframe: str):
    """Fetch and resample XAUUSD (Gold Futures) data according to timeframe."""
    end = datetime.now()
    start = end - timedelta(days=730)  # 2 years of data

    # Choose source interval based on requested timeframe
    if timeframe.endswith("h"):       # hourly
        base_interval = "1h"
    elif timeframe.endswith("D"):     # daily
        base_interval = "1d"
    elif timeframe.endswith("W"):     # weekly
        base_interval = "1wk"
    else:
        base_interval = "1h"

    df = yf.Ticker("GC=F").history(start=start, end=end, interval=base_interval)
    if df.empty:
        st.error("No data. Check connection or timeframe.")
        return None

    df.index = pd.to_datetime(df.index)

    # Handle resampling for custom timeframes
    if timeframe not in ["1h", "1D", "1W"]:
        rule = timeframe.replace("h", "H")
        df = df.resample(rule, label='right', closed='right').agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        }).dropna()

    return df


df = get_data(timeframe)
if df is None:
    st.stop()


# --- MACD Function ---
def macd(series, fast=12, slow=26, signal=9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


# --- Compute Indicators ---
df['MACD'], df['Signal'], df['Histogram'] = macd(df['Close'])
df['EMA26'] = df['Close'].ewm(span=26, adjust=False).mean()
df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()

# --- Slice Lookback ---
if timeframe.endswith("h"):
    last_period = df.last(f'{lookback_hours}H')
elif timeframe.endswith("D"):
    # Convert hours to days (since 24h = 1 day)
    lookback_days = lookback_hours / 24
    last_period = df.last(f'{lookback_days}D')
elif timeframe.endswith("W"):
    # Convert hours to weeks (168h = 1 week)
    lookback_weeks = lookback_hours / 168
    last_period = df.last(f'{lookback_weeks}W')
else:
    last_period = df

# --- Plot ---
fig = make_subplots(
    rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05,
    subplot_titles=(f'XAUUSD – {timeframe.upper()} Candlesticks + EMA', 'MACD (12,26,9)'),
    row_heights=[0.7, 0.3]
)

# Candlesticks
fig.add_trace(go.Candlestick(
    x=last_period.index,
    open=last_period['Open'],
    high=last_period['High'],
    low=last_period['Low'],
    close=last_period['Close'],
    name="OHLC",
    increasing_line_color='gold',
    decreasing_line_color='red',
    increasing_fillcolor='gold',
    decreasing_fillcolor='red',
    showlegend=False
), row=1, col=1)

# EMAs
fig.add_trace(go.Scatter(
    x=last_period.index, y=last_period['EMA26'], name='EMA 26',
    line=dict(color='orange', width=2)
), row=1, col=1)

fig.add_trace(go.Scatter(
    x=last_period.index, y=last_period['EMA50'], name='EMA 50',
    line=dict(color='red', width=2)
), row=1, col=1)

# MACD Panel
fig.add_trace(go.Scatter(
    x=last_period.index, y=last_period['MACD'], name='MACD',
    line=dict(color='blue')
), row=2, col=1)

fig.add_trace(go.Scatter(
    x=last_period.index, y=last_period['Signal'], name='Signal',
    line=dict(color='orange')
), row=2, col=1)

fig.add_trace(go.Bar(
    x=last_period.index, y=last_period['Histogram'], name='Histogram',
    marker_color='gray', opacity=0.6
), row=2, col=1)

fig.add_hline(y=0, line_dash="dash", line_color="black", row=2, col=1)

fig.update_layout(
    height=700,
    hovermode='x unified',
    xaxis_rangeslider_visible=False,
    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
)

st.plotly_chart(fig, use_container_width=True)

# --- Stats ---
st.write(f"**Latest Close:** ${last_period['Close'].iloc[-1]:.2f} | "
         f"**MACD:** {last_period['MACD'].iloc[-1]:.4f} | "
         f"**Signal:** {last_period['Signal'].iloc[-1]:.4f}")

st.caption(f"Data last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
