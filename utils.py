import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import date, timedelta

def set_page_config(page_title='Stock Prices dashboard', page_icon=':chart_with_upwards_trend:'):
    # Set the title and favicon that appear in the Browser's tab bar.
    st.set_page_config(
        page_title=page_title,
        page_icon=page_icon,
    )

@st.cache_data(ttl=60 * 60 * 24)
def get_price_data(tickers, start_date, end_date):
    """Download historical Close prices for the requested tickers.

    Returns a DataFrame with columns: Date, Ticker, Price
    Cached for 24 hours by default.
    """
    frames = []
    for ticker in tickers:
        try:
            hist = yf.Ticker(ticker).history(start=start_date, end=end_date)
            if hist.empty:
                continue
            df = hist[['Close']].reset_index().rename(columns={'Close': 'Price'})
            df['Ticker'] = ticker
            frames.append(df)
        except Exception:
            # don't break the whole app if one ticker fails
            continue

    if not frames:
        return pd.DataFrame(columns=['Date', 'Ticker', 'Price'])

    result = pd.concat(frames, ignore_index=True)
    result['Date'] = pd.to_datetime(result['Date']).dt.date
    return result