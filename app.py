# -------------------------------------------------
# XAUUSD PRO – NO GAPS + GREY HISTOGRAM + All Timeframes
# -------------------------------------------------
import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

st.set_page_config(page_title="XAUUSD Pro", layout="wide")
st.title("XAUUSD Pro – Candlesticks + MACD (No Gaps)")

# --- User Inputs ---
col1, col2 = st.columns(2)
with col1:
    timeframe = st.selectbox(
        "Timeframe",
        ["1h", "2h", "3h", "4h", "6h", "8h", "12h", "1D", "2D", "3D", "1W"],
        index=7
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
    start = end - timedelta(days=days_back + 100)

    interval_map = {
        "1h": "1h", "2h": "1h", "3h": "1h", "4h": "1h", "6h": "1h", "8h": "1h", "12h": "1h",
        "1D": "1d", "2D": "1d", "3D": "1d", "1W": "1wk"
    }
    interval = interval_map[tf]

    df_raw = yf.Ticker("GC=F").history(start=start, end=end, interval=interval)
    if df_raw.empty:
        st.error("No data.")
        return None

    # Resample
    if tf in ["2h", "3h", "6h", "8h", "12h", "2D", "3D"]:
        rule = tf.upper().replace("D", "H") if "D" in tf else tf.upper()
        df = df_raw.resample(rule).agg({
            'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
        })
    else:
        df = df_raw

    # --- FILL MISSING DATES (NO GAPS) ---
    freq = tf.upper().replace("D", "H") if "D" in tf else tf.upper()
    if "W" in freq:
        freq = "W"
    full_range = pd.date_range(start=df.index.min(), end=df.index.max(), freq=freq)
    df = df.reindex(full_range)

    # Fill OHLC
    df['Open'] = df['Open'].ffill()
    df['High'] = df['High'].ffill()
    df['Low'] = df['Low'].ffill()
    df['Close'] = df['Close'].ffill()
    df['Volume'] = df['Volume'].fillna(0)

    return df.dropna(how='all')  # remove any full NaN rows at edges

# --- Lookback ---
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
fig = make_sub
