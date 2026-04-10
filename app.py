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
    index=0
)

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
    candle_up_color = '#C0C0C0'
    candle_down_color = '#A52A2A'
    ema26_color = '#B8860B'
    ema50_color = '#8B0000'

# --- Timeframe ---
timeframe = st.selectbox(
    "Timeframe",
    ["1h", "2h", "3h", "4h", "6h", "8h", "12h",
     "1D", "2D", "3D",
     "1W", "2W", "3W"],
    index=6
)

# --- Lookback ---
lookback_value = st.slider("Lookback", 50, 2000, 500)

# --- Refresh ---
if st.button("🔄 Refresh Data"):
    st.cache_data.clear()

# --- DATA FETCH ---
@st.cache_data(ttl=300)
def get_data(ticker: str):
    end = datetime.now()
    start = end - timedelta(days=730)

    df = yf.Ticker(ticker).history(
        start=start,
        end=end,
        interval="1h"
    )

    if df.empty:
        return None

    df.index = pd.to_datetime(df.index)
    return df


df = get_data(ticker_symbol)

if df is None or df.empty:
    st.error("No data from yfinance")
    st.stop()

# --- RESAMPLE ENGINE (FIXED) ---
df = df.sort_index()

if timeframe in ["1h","2h","3h","4h","6h","8h","12h","1D","2D","3D"]:

    rule_map = {
        "1h": "1H",
        "2h": "2H",
        "3h": "3H",
        "4h": "4H",
        "6h": "6H",
        "8h": "8H",
        "12h": "12H",
        "1D": "1D",
        "2D": "2D",
        "3D": "3D"
    }

    rule = rule_map[timeframe]

    df = df.resample(rule).agg({
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
        "Volume": "sum"
    }).dropna()

elif timeframe in ["1W", "2W", "3W"]:

    # Step 1: build clean weekly candles
    weekly = df.resample("W-FRI").agg({
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
        "Volume": "sum"
    }).dropna()

    # Step 2: multi-week aggregation
    if timeframe == "1W":
        df = weekly

    elif timeframe == "2W":
        df = weekly.resample("2W").agg({
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum"
        }).dropna()

    elif timeframe == "3W":
        df = weekly.resample("3W").agg({
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum"
        }).dropna()

# --- MACD ---
def macd(series, fast=12, slow=26, signal=9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

df['MACD'], df['Signal'], df['Histogram'] = macd(df['Close'])
df['EMA26'] = df['Close'].ewm(span=26, adjust=False).mean()
df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()

# --- LOOKBACK ---
last_period = df.tail(lookback_value)

# --- PLOT ---
fig = make_subplots(
    rows=2, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.05,
    row_heights=[0.7, 0.3],
    subplot_titles=(f"{display_name} – {timeframe}", "MACD")
)

# Candles
fig.add_trace(go.Candlestick(
    x=last_period.index,
    open=last_period["Open"],
    high=last_period["High"],
    low=last_period["Low"],
    close=last_period["Close"],
    increasing_line_color=candle_up_color,
    decreasing_line_color=candle_down_color
), row=1, col=1)

# EMA
fig.add_trace(go.Scatter(
    x=last_period.index,
    y=last_period["EMA26"],
    name="EMA 26",
    line=dict(color=ema26_color)
), row=1, col=1)

fig.add_trace(go.Scatter(
    x=last_period.index,
    y=last_period["EMA50"],
    name="EMA 50",
    line=dict(color=ema50_color)
), row=1, col=1)

# MACD
fig.add_trace(go.Scatter(
    x=last_period.index,
    y=last_period["MACD"],
    name="MACD",
    line=dict(color="blue")
), row=2, col=1)

fig.add_trace(go.Scatter(
    x=last_period.index,
    y=last_period["Signal"],
    name="Signal",
    line=dict(color="orange")
), row=2, col=1)

fig.add_trace(go.Bar(
    x=last_period.index,
    y=last_period["Histogram"],
    name="Histogram",
    opacity=0.5
), row=2, col=1)

fig.add_hline(y=0, line_dash="dash", row=2, col=1)

fig.update_layout(
    height=750,
    xaxis_rangeslider_visible=False,
    hovermode="x unified"
)

st.plotly_chart(fig, use_container_width=True)

# --- STATS ---
st.write(
    f"**Latest Close:** {last_period['Close'].iloc[-1]:.2f} | "
    f"MACD: {last_period['MACD'].iloc[-1]:.4f} | "
    f"Signal: {last_period['Signal'].iloc[-1]:.4f}"
)

st.caption(f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
