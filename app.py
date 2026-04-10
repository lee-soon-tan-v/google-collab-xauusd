import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# --- Page setup ---
st.set_page_config(page_title="Precious Metals Candles", layout="wide")
st.title("📈 Live Precious Metals – Candlesticks + EMA + MACD")

# --- Asset Selection ---
asset = st.selectbox(
    "Select Metal",
    options=["Gold (XAUUSD)", "Silver"],
    index=0,
    help="Gold uses GC=F (futures), Silver uses SI=F (futures) from Yahoo Finance"
)

# Map selection to ticker and friendly name
if asset == "Gold (XAUUSD)":
    ticker_symbol = "GC=F"
    display_name = "Gold (XAUUSD)"
    candle_up_color = 'gold'
    candle_down_color = 'red'
    ema26_color = 'orange'
    ema50_color = 'red'
else:
    ticker_symbol = "SI=F"
    display_name = "Silver"
    candle_up_color = '#C0C0C0'     # silver-ish
    candle_down_color = '#A52A2A'   # darker red for contrast
    ema26_color = '#B8860B'         # darker goldenrod
    ema50_color = '#8B0000'         # dark red

# --- User Inputs ---
col1, col2 = st.columns(2)
with col1:
    timeframe = st.selectbox(
        "Timeframe",
        ["1h", "2h", "3h", "4h", "6h", "8h", "12h", "1D", "2D", "3D", "1W"],
        index=6
    )

# Dynamically adjust slider range/label
if timeframe.endswith("h"):
    label = "Lookback (hours)"
    min_lookback, max_lookback, default = 24, 4000, 1000
elif timeframe.endswith("D"):
    label = "Lookback (days)"
    min_lookback, max_lookback, default = 7, 1500, 365
elif timeframe.endswith("W"):
    label = "Lookback (weeks)"
    min_lookback, max_lookback, default = 4, 520, 104
else:
    label = "Lookback (hours)"
    min_lookback, max_lookback, default = 24, 4000, 1000

with col2:
    lookback_value = st.slider(label, min_lookback, max_lookback, default, step=min_lookback)

# Refresh
if st.button("🔄 Refresh Data"):
    st.cache_data.clear()

# --- Fetch & Resample ---
@st.cache_data(ttl=300)
def get_data(ticker: str, timeframe: str):
    """Fetch and resample data for the selected ticker."""
    end = datetime.now()
    start = end - timedelta(days=730)  # 2 years default fetch

    # Base interval
    if timeframe.endswith("h"):
        base_interval = "1h"
    elif timeframe.endswith("D"):
        base_interval = "1d"
    elif timeframe.endswith("W"):
        base_interval = "1wk"
    else:
        base_interval = "1h"

    df = yf.Ticker(ticker).history(start=start, end=end, interval=base_interval)

    if df.empty:
        st.error(f"No data returned for {ticker}. Check connection or try a different timeframe.")
        return None

    df.index = pd.to_datetime(df.index)

    # Custom resampling for non-standard intervals
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

df = get_data(ticker_symbol, timeframe)
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
    last_period = df.last(f'{lookback_value}H')
elif timeframe.endswith("D"):
    last_period = df.last(f'{lookback_value}D')
elif timeframe.endswith("W"):
    last_period = df.last(f'{lookback_value}W')
else:
    last_period = df

# --- Plot ---
fig = make_subplots(
    rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05,
    subplot_titles=(f'{display_name} – {timeframe.upper()} Candlesticks + EMA', 'MACD (12,26,9)'),
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
    increasing_line_color=candle_up_color,
    decreasing_line_color=candle_down_color,
    increasing_fillcolor=candle_up_color,
    decreasing_fillcolor=candle_down_color,
    showlegend=False
), row=1, col=1)

# EMAs
fig.add_trace(go.Scatter(
    x=last_period.index, y=last_period['EMA26'], name='EMA 26',
    line=dict(color=ema26_color, width=2)
), row=1, col=1)
fig.add_trace(go.Scatter(
    x=last_period.index, y=last_period['EMA50'], name='EMA 50',
    line=dict(color=ema50_color, width=2)
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
latest_close = last_period['Close'].iloc[-1]
st.write(f"**Latest Close:** ${latest_close:.2f} | "
         f"**MACD:** {last_period['MACD'].iloc[-1]:.4f} | "
         f"**Signal:** {last_period['Signal'].iloc[-1]:.4f}")

st.caption(f"Data last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} • Source: Yahoo Finance ({ticker_symbol})")
