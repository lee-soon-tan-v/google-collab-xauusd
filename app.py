# -------------------------------------------------
# XAUUSD MACD Web App – Streamlit Version
# -------------------------------------------------
import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

st.set_page_config(page_title="XAUUSD MACD", layout="wide")
st.title("Live XAUUSD Chart with MACD & EMA")

# --- User Inputs ---
col1, col2 = st.columns(2)
with col1:
    hours = st.selectbox("Timeframe", ["1h", "2h", "3h", "4h", "6h", "8h", "12h"], index=5)
with col2:
    lookback_hours = st.slider("Lookback (hours)", 24, 2000, 1000, step=24)

# --- Fetch & Resample ---
@st.cache_data(ttl=300)  # Cache 5 mins
def get_data():
    end = datetime.now()
    start = end - timedelta(days=365)
    df_1h = yf.Ticker("GC=F").history(start=start, end=end, interval="1h")
    if df_1h.empty:
        st.error("No data. Check connection.")
        return None
    # Resample
    df = df_1h.resample(hours.upper()).agg({
        'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
    }).dropna()
    return df

df = get_data()
if df is None:
    st.stop()

# --- MACD ---
def macd(series, fast=12, slow=26, signal=9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

df['MACD'], df['Signal'], df['Histogram'] = macd(df['Close'])

# --- Slice ---
last_period = df.last(f'{lookback_hours}H')

# --- Plot ---
fig = make_subplots(
    rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05,
    subplot_titles=(f'XAUUSD – {hours.upper()} (Close + 50 & 26 EMA)', 'MACD (12,26,9)'),
    row_heights=[0.7, 0.3]
)

fig.add_trace(go.Scatter(x=last_period.index, y=last_period['Close'],
                         name='Close', line=dict(color='black')), row=1, col=1)
fig.add_trace(go.Scatter(x=last_period.index,
                         y=last_period['Close'].ewm(span=50, adjust=False).mean(),
                         name='50 EMA', line=dict(color='red', width=2)), row=1, col=1)
fig.add_trace(go.Scatter(x=last_period.index,
                         y=last_period['Close'].ewm(span=26, adjust=False).mean(),
                         name='26 EMA', line=dict(color='orange', width=2)), row=1, col=1)

fig.add_trace(go.Scatter(x=last_period.index, y=last_period['MACD'], name='MACD', line=dict(color='blue')), row=2, col=1)
fig.add_trace(go.Scatter(x=last_period.index, y=last_period['Signal'], name='Signal', line=dict(color='orange')), row=2, col=1)
fig.add_trace(go.Bar(x=last_period.index, y=last_period['Histogram'], name='Histogram', marker_color='gray', opacity=0.6), row=2, col=1)
fig.add_hline(y=0, line_dash="dash", line_color="black", row=2, col=1)

fig.update_layout(height=700, hovermode='x unified')
st.plotly_chart(fig, use_container_width=True)

# --- Stats ---
st.write(f"**Latest Close:** ${last_period['Close'].iloc[-1]:.2f} | "
         f"**MACD:** {last_period['MACD'].iloc[-1]:.4f} | "
         f"**Signal:** {last_period['Signal'].iloc[-1]:.4f}")
