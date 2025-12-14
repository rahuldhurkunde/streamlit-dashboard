import streamlit as st
import pandas as pd
from datetime import date, timedelta
from utils import get_price_data, set_page_config
from indicators import add_moving_average, add_52w_high_low, calculate_rsi
from news import get_news

# Set the title and favicon that appear in the Browser's tab bar.
set_page_config()

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
            plot_df = add_moving_average(plot_df, ma_period)

        if '52w High/Low' in selected_indicators:
            plot_df = add_52w_high_low(plot_df)

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

        # If RSI is selected, show a separate chart below.
        if 'RSI (14)' in selected_indicators:
            rsi_df = calculate_rsi(pivot_df)
            if not rsi_df.empty:
                st.header('RSI (14) over time', divider='gray')
                st.line_chart(rsi_df)

        st.header('News Headlines', divider='gray')
        
        news_ticker = st.selectbox('Select ticker for news', final_tickers)

        if st.button('Get News'):
            if news_ticker:
                news = get_news(news_ticker)
                if news:
                    for article in news:
                        st.markdown(f"**{article['headline']}** ({article['publisher']})")
                        st.markdown(f"[Read more]({article['link']})")
                else:
                    st.write(f"No news found for {news_ticker}")
