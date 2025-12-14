import streamlit as st
import pandas as pd
import math
import yfinance as yf
from datetime import date, timedelta

# Set the title and favicon that appear in the Browser's tab bar.
st.set_page_config(
    page_title='Stock Prices dashboard',
    page_icon=':chart_with_upwards_trend:',
)

# -----------------------------------------------------------------------------
# Declare some useful functions.

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

# -----------------------------------------------------------------------------
# Draw the actual page (stock prices)

st.markdown("""
# :chart_with_upwards_trend: Stock Prices dashboard

Browse historical stock prices using `yfinance`.
""")

# date range selectors
today = date.today()
one_year_ago = today - timedelta(days=365)

start_date, end_date = st.date_input(
    'Which date range are you interested in?',
    value=(one_year_ago, today),
)

# Offer a set of common tickers by default
available_tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA']

selected_tickers = st.multiselect(
    'Which tickers would you like to view?',
    available_tickers,
    ['AAPL', 'MSFT', 'GOOGL', 'AMZN']
)

# Allow the user to add custom tickers as a comma-separated list
custom_input = st.text_input('Add custom tickers (comma-separated)', '', help='Enter tickers like AAPL, TSLA, BABA')
custom_list = [t.strip().upper() for t in custom_input.split(',') if t.strip()]

# Merge selected tickers with custom tickers, preserving order and removing duplicates
final_tickers = []
for t in (selected_tickers or []) + custom_list:
    if t and t not in final_tickers:
        final_tickers.append(t)

if not final_tickers:
    st.warning("Select or enter at least one ticker to fetch prices")
else:
    # Fetch price data (cached)
    price_df = get_price_data(final_tickers, start_date.isoformat(), (end_date + timedelta(days=1)).isoformat())

    if price_df.empty:
        st.warning('No price data found for the selected tickers / dates.')
    else:
        # Pivot for plotting: index=Date, columns=Ticker
        pivot_df = price_df.pivot(index='Date', columns='Ticker', values='Price')
        pivot_df = pivot_df.sort_index()

        # Add selector for technical indicators
        indicator_options = [
            '52w High/Low',
            'Moving Average (MA)',
            'RSI (14)'
        ]

        selected_indicators = st.multiselect(
            'Overlay indicators on the chart',
            indicator_options,
            []
        )

        # If MA is selected, allow the user to pick a window
        ma_period = None
        if any('Moving Average' in s for s in selected_indicators):
            ma_period = st.number_input('Moving Average period (days)', min_value=2, max_value=500, value=50)

        st.header('Prices over time', divider='gray')

        # Build a DataFrame to draw on the main price chart (price + MA + 52w)
        plot_df = pivot_df.copy()

        if 'Moving Average (MA)' in selected_indicators and ma_period:
            for ticker in pivot_df.columns:
                plot_df[f'{ticker}_MA{ma_period}'] = plot_df[ticker].rolling(window=ma_period, min_periods=1).mean()

        if '52w High/Low' in selected_indicators:
            # 52 weeks ~ 252 trading days
            win = 252
            for ticker in pivot_df.columns:
                plot_df[f'{ticker}_52w_high'] = plot_df[ticker].rolling(window=win, min_periods=1).max()
                plot_df[f'{ticker}_52w_low'] = plot_df[ticker].rolling(window=win, min_periods=1).min()

        st.line_chart(plot_df)

        st.header(f'Prices at end of range ({end_date.isoformat()})', divider='gray')

        cols = st.columns(4)

        for i, ticker in enumerate(final_tickers):
            col = cols[i % len(cols)]

            with col:
                if ticker not in pivot_df.columns or pivot_df[ticker].dropna().empty:
                    st.metric(label=f'{ticker} Price', value='n/a', delta='n/a', delta_color='off')
                    continue

                series = pivot_df[ticker].dropna()
                first_price = series.iloc[0]
                last_price = series.iloc[-1]

                if pd.isna(first_price) or first_price == 0:
                    growth = 'n/a'
                    delta_color = 'off'
                else:
                    pct_change = (last_price - first_price) / first_price * 100
                    growth = f'{pct_change:+.2f}%'
                    delta_color = 'normal'

                st.metric(
                    label=f'{ticker} Price',
                    value=f'${last_price:,.2f}',
                    delta=growth,
                    delta_color=delta_color,
                )

        # If RSI is selected, show a separate chart below. Use 14-day RSI.
        if 'RSI (14)' in selected_indicators:
            rsi_period = 14
            rsi_frames = {}
            for ticker in pivot_df.columns:
                series = pivot_df[ticker].dropna()
                if series.empty:
                    continue

                delta = series.diff()
                up = delta.clip(lower=0)
                down = -1 * delta.clip(upper=0)
                # Wilder's smoothing (EMA with alpha = 1/n)
                ma_up = up.ewm(alpha=1/rsi_period, adjust=False).mean()
                ma_down = down.ewm(alpha=1/rsi_period, adjust=False).mean()
                rs = ma_up / ma_down
                rsi = 100 - (100 / (1 + rs))
                rsi.index = series.index
                rsi_frames[ticker] = rsi

            if rsi_frames:
                rsi_df = pd.DataFrame(rsi_frames)
                st.header('RSI (14) over time', divider='gray')
                st.line_chart(rsi_df)
