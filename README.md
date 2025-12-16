# Stock Prices dashboard

Hosted on the Streamlit community server: [https://app-dashboard-dzcw6pagkmxzz39gzbqf2n.streamlit.app](https://app-dashboard-dzcw6pagkmxzz39gzbqf2n.streamlit.app)

A simple Streamlit app for browsing historical stock prices using the `yfinance` package.

Features:
- Select a date range using calendar pickers
- Choose one or more tickers to display (common defaults provided)
- Add custom tickers via a comma-separated input
- Overlay indicators on the chart: 52w High/Low, Moving Average (selectable MA period), RSI (14)

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://gdp-dashboard-template.streamlit.app/)

### How to run it on your own machine

1. Install the requirements

   ```bash
   pip install -r requirements.txt
   ```

2. Run the app

   ```bash
   streamlit run streamlit_app.py
   ```

### Usage

- Use the calendar pickers to select a start and end date for the data.
- Select tickers from the provided list, or add your own as a comma-separated string.
- Use the "Overlay indicators on the chart" selector to add 52w High/Low (rolling max/min over ~252 trading days), a Moving Average (pick the MA period), or RSI (14-day). RSI is shown in a separate chart beneath the main price chart.

Notes:
- `yfinance` fetches historical price data from Yahoo Finance at runtime, and the app caches results for 24 hours.
- The default MA window is 50 days; RSI follows the standard 14-day calculation.
