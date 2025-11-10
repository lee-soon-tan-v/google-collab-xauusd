# -------------------------------------------------
# XAUUSD PRO – All Timeframes + Candlesticks + MACD
# -------------------------------------------------
import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

st.set_page_config(page_title="XAUUSD Pro", layout="wide")
st.title("XAUUSD Pro – Candlesticks + MACD (All Timeframes)")

# --- User Inputs ---
col1, col2 = st.columns(2)
with col1:
    timeframe = st.selectbox(
        "Timeframe",
        ["1h", "2h", "3h", "4h", "6h", "8h", "12h", "1D", "2D", "3D", "1W"],
        index=7  # default: 1D
    )
with col2:
    lookback = st.slider(
        "Lookback",
        min_value=7, max_value=730, value=90, step=7,
        help="Days for D/W, hours for H"
    )

# --- Smart Data Fetching ---
@st.cache_data(ttl=300)
def get_data(tf, days_back):
    end = datetime.now()
    start = end - timedelta(days=days_back + 100)  # extra buffer

    # Map to yfinance interval
    interval_map = {
        "1h": "1h", "2h": "1h", "3h": "1h", "4h": "1h", "6h": "1h", "8h": "1h", "12h": "1h",
        "1D": "1d", "2D": "1d", "3D": "1d", "1W": "1wk"
    }
    interval = interval_map[tf]

    df_raw = yf.Ticker("GC=F").history(start=start, end=end, interval=interval)
    if df_raw.empty:
        st.error("No data. Check connection.")
        return None

    # Resample non-native timeframes
    if tf in ["2h", "3h", "6h", "8h", "12h", "2D", "3D"]:
        rule = tf.upper().replace("D", "H") if "D" in tf else tf.upper()
        df = df_raw.resample(rule).agg({
            'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
        }).dropna()
    else:
        df = df_raw

    return df

# --- Determine lookback in time ---
if timeframe.endswith(("D", "W")):
    days_back = lookback
    last_period = get_data(timeframe, days_back).last(f'{days_back}D' if timeframe != "1W" else f'{days_back//7}W')
else:
    hours_back = lookback * 24
    last_period = get_data(timeframe, hours_back // 24 + 30).last(f'{hours_back}H')

if last_period is None or last_period.empty:
    st.stop()

# --- MACD ---
def macd(series, fast=12, slow=26, signal=9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

last_period['MACD'], last_period['Signal'], last_period['Histogram'] = macd(last_period['Close'])

# --- Plot ---
fig = make_subplots(
    rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05,
    subplot_titles=(f'XAUUSD – {timeframe} Candlesticks + EMA', 'MACD (12,26,9)'),
    row_heights=[0.7, 0.3]
)

# CANDLESTICKS
fig.add_trace(go.Candlestick(
    x=last_period.index,
    open=last_period['Open'],
    high=last_period['High'],
    low=last_period['Low'],
    close=last_period['Close'],
    name="OHLC",
    increasing_line_color='gold', decreasing_line_color='red',
    increasing_fillcolor='gold', decreasing_fillcolor='red'
), row=1, col=1)

# EMA 50 & 26
fig.add_trace(go.Scatter(x=last_period.index,
                         y=last_period['Close'].ewm(span=50, adjust=False).mean(),
                         name='50 EMA', line=dict(color='red', width=2)), row=1, col=1)
fig.add_trace(go.Scatter(x=last_period.index,
                         y=last_period['Close'].ewm(span=26, adjust=False).mean(),
                         name='26 EMA', line=dict(color='orange', width=2)), row=1, col=1)

# MACD
fig.add_trace(go.Scatter(x=last_period.index, y=last_period['MACD'], name='MACD', line=dict(color='blue')), row=2, col=1)
fig.add_trace(go.Scatter(x=last_period.index, y=last_period['Signal'], name='Signal', line=dict(color='orange')), row=2, col=1)
fig.add_trace(go.Bar(x=last_period.index, y=last_period['Histogram'], name='Histogram', marker_color='gray', opacity=0.6), row=2, col=1)
fig.add_hline(y=0, line_dash="dash", line_color="black", row=2, col=1)

fig.update_layout(height=700, hovermode='x unified', xaxis_rangeslider_visible=False)
st.plotly_chart(fig, use_container_width=True)

# --- Stats ---
st.write(f"**Latest Close:** ${last_period['Close'].iloc[-1]:.2f} | "
         f"**MACD:** {last_period['MACD'].iloc[-1]:.4f} | "
         f"**Signal:** {last_period['Signal'].iloc[-1]:.4f}")
