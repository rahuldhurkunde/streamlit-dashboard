import streamlit as st
import pandas as pd
from datetime import date, timedelta
import sys
from utils import get_price_data, set_page_config
from indicators import add_moving_average, add_52w_high_low, calculate_rsi
from news import get_news
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Check for debug flag
DEBUG = '--debug' in sys.argv

# Set the title and favicon that appear in the Browser's tab bar.
set_page_config()

# -----------------------------------------------------------------------------
# Draw the actual page (stock prices)

st.markdown("""
# :chart_with_upwards_trend: Stock Prices dashboard

Browse historical stock prices using `yfinance`.
""")

st.page_link("pages/in_depth_analysis.py", label="Go to In-depth Analysis", icon="🔬")

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
    ['NVDA', 'AMZN']
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
        ma_periods = []
        if any('Moving Average' in s for s in selected_indicators):
            ma_input = st.text_input('Moving Average periods (days, comma-separated)', value='50')
            try:
                ma_periods = [int(p.strip()) for p in ma_input.split(',') if p.strip()]
            except ValueError:
                st.error("Invalid input for Moving Average periods. Please use integers separated by commas (e.g., '50, 200').")

        st.header('Prices over time', divider='gray')

        col_ctrl1, col_ctrl2 = st.columns([1, 4])
        with col_ctrl1:
             chart_type = st.radio("Chart Type", ["Line", "Candle"], horizontal=True)
        with col_ctrl2:
             log_scale = st.checkbox('Log Scale', value=False)

        # Create a subplot figure with 2 rows if RSI is selected
        rows = 2 if 'RSI (14)' in selected_indicators else 1
        row_heights = [0.7, 0.3] if 'RSI (14)' in selected_indicators else [1]
        fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=row_heights)


        # Build a DataFrame to draw on the main price chart (price + MA + 52w)
        plot_df = pivot_df.copy()

        if 'Moving Average (MA)' in selected_indicators and ma_periods:
            plot_df = add_moving_average(plot_df, ma_periods)

        if '52w High/Low' in selected_indicators:
            plot_df = add_52w_high_low(plot_df)

        # Main Plot Logic
        if chart_type == "Line":
            for col in plot_df.columns:
                fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df[col], name=col), row=1, col=1)
        else:
            # Candlestick Plot
            # 1. Plot Candles for each ticker
            for ticker in final_tickers:
                # Filter price_df for this ticker
                ticker_data = price_df[price_df['Ticker'] == ticker]
                if not ticker_data.empty:
                    fig.add_trace(go.Candlestick(
                        x=ticker_data['Date'],
                        open=ticker_data['Open'],
                        high=ticker_data['High'],
                        low=ticker_data['Low'],
                        close=ticker_data['Price'],
                        name=ticker
                    ), row=1, col=1)
            
            # 2. Plot Indicators (MAs, etc.) - exclude the raw Ticker columns since we drew candles
            # Raw ticker columns match 'final_tickers'
            for col in plot_df.columns:
                if col not in final_tickers:
                    fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df[col], name=col), row=1, col=1)
            
            fig.update_layout(xaxis_rangeslider_visible=False)

        # If RSI is selected, show a separate chart below.
        if 'RSI (14)' in selected_indicators:
            rsi_df = calculate_rsi(pivot_df)
            if not rsi_df.empty:
                for col in rsi_df.columns:
                    fig.add_trace(go.Scatter(x=rsi_df.index, y=rsi_df[col], name=f'{col} RSI'), row=2, col=1)
                fig.update_yaxes(title_text="RSI", row=2, col=1)


        fig.update_layout(
            height=500,
            title_text="Stock Prices"
        )
        
        if log_scale:
            fig.update_yaxes(type='log', row=1, col=1)
        st.plotly_chart(fig, use_container_width=True)

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

        st.header('News Headlines', divider='gray')

        news_ticker = st.selectbox('Select ticker for news', final_tickers)
        if DEBUG:
            st.write(f"Selected ticker for news: {news_ticker}")

        if st.button('Get News'):
            if news_ticker:
                news = get_news(news_ticker)
                if DEBUG:
                    st.write("Fetched news data:", news)
                if news:
                    for article in news:
                        st.markdown(f"**{article['headline']}** ({article['publisher']})")
                        st.markdown(f"[Read more]({article['link']})")
                else:
                    st.write(f"No news found for {news_ticker}")
