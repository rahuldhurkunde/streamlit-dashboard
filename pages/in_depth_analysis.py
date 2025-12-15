import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import sys
import os
from datetime import datetime

# Add the parent directory to sys.path so we can import utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils import set_page_config
from indicators import calculate_rsi

# Set the page config
set_page_config(page_title="In-depth Analysis", page_icon=":chart_with_downwards_trend:")

def format_number(num):
    if num is None:
        return "-"
    if isinstance(num, (int, float)):
        if num >= 1e12:
            return f"{num / 1e12:.2f}T"
        if num >= 1e9:
            return f"{num / 1e9:.2f}B"
        if num >= 1e6:
            return f"{num / 1e6:.2f}M"
        return f"{num:.2f}"
    return str(num)

def format_percent(num):
    if num is None:
        return "-"
    return f"{num * 100:.2f}%"

def get_change(current, old):
    if old == 0 or pd.isna(old):
        return None
    return (current - old) / old

st.markdown("# :microscope: In-depth Analysis")

# 1. Ticker Input
ticker = st.text_input("Enter Ticker Symbol", value="NVDA").strip().upper()

if ticker:
    stock = yf.Ticker(ticker)
    
    # 2. Fetch History
    with st.spinner(f"Loading data for {ticker}..."):
        # Fetch max history for the chart and calculations
        hist = stock.history(period="max")
        
        # Fetch info for fundamental data
        info = stock.info

    if hist.empty:
        st.error(f"No data found for {ticker}")
    else:
        # 3. Plot Price Chart (Entirety)
        st.subheader(f"{ticker} - All Time Price History")
        
        col1, col2 = st.columns([1, 4])
        with col1:
            chart_type = st.radio("Chart Type", ["Line", "Candle"], key="chart_type_indepth")
        with col2:
            # Add log scale option
            log_scale = st.checkbox("Log Scale", value=True, key="log_scale_indepth")

        fig = go.Figure()
        
        if chart_type == "Line":
            fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], name='Close', line=dict(width=1)))
        else:
            fig.add_trace(go.Candlestick(
                x=hist.index,
                open=hist['Open'],
                high=hist['High'],
                low=hist['Low'],
                close=hist['Close'],
                name=ticker
            ))
            fig.update_layout(xaxis_rangeslider_visible=False)
        
        fig.update_layout(
            height=500,
            yaxis_type="log" if log_scale else "linear",
            xaxis_title="Date",
            yaxis_title="Price",
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)

        # 4. Summary Statistics Table
        st.subheader("Fundamental & Technical Statistics")

        # Prepare data for calculations
        current_price = info.get('currentPrice', hist['Close'].iloc[-1])
        
        # Calculate performance metrics manually to ensure coverage
        # Ensure index is datetime
        hist.index = pd.to_datetime(hist.index)
        last_date = hist.index[-1]
        
        def get_perf(days):
            target_date = last_date - pd.Timedelta(days=days)
            # Find nearest date
            idx = hist.index.get_indexer([target_date], method='nearest')[0]
            if idx < 0 or idx >= len(hist):
                return None
            old_price = hist['Close'].iloc[idx]
            return get_change(current_price, old_price)

        # Basic keys from info
        # We try to mimic the user's requested grid layout by creating a list of dicts or a dataframe
        
        # Map of Label -> (Value, Formatter)
        data_grid = {
            "Index": ("-", str), # API doesn't provide easily
            "P/E": (info.get('trailingPE'), "{:.2f}".format),
            "EPS (ttm)": (info.get('trailingEps'), "{:.2f}".format),
            "Insider Own": (info.get('heldPercentInsiders'), format_percent),
            "Shs Outstand": (info.get('sharesOutstanding'), format_number),
            "Perf Week": (get_perf(7), format_percent),
            
            "Market Cap": (info.get('marketCap'), format_number),
            "Forward P/E": (info.get('forwardPE'), "{:.2f}".format),
            "EPS next Y": (info.get('forwardEps'), "{:.2f}".format),
            "Insider Trans": ("-", str),
            "Shs Float": (info.get('floatShares'), format_number),
            "Perf Month": (get_perf(30), format_percent),
            
            "Enterprise Value": (info.get('enterpriseValue'), format_number),
            "PEG": (info.get('trailingPegRatio'), "{:.2f}".format),
            "EPS next Q": ("-", str), # Not reliably in info
            "Inst Own": (info.get('heldPercentInstitutions'), format_percent),
            "Short Float": (info.get('shortPercentOfFloat'), format_percent),
            "Perf Quarter": (get_perf(91), format_percent),
            
            "Income": (info.get('netIncomeToCommon'), format_number),
            "P/S": (info.get('priceToSalesTrailing12Months'), "{:.2f}".format),
            "EPS this Y": (info.get('epsCurrentYear'), "{:.2f}".format), # Approximate
            "Inst Trans": ("-", str),
            "Short Ratio": (info.get('shortRatio'), "{:.2f}".format),
            "Perf Half Y": (get_perf(182), format_percent),
            
            "Sales": (info.get('totalRevenue'), format_number),
            "P/B": (info.get('priceToBook'), "{:.2f}".format),
            "ROA": (info.get('returnOnAssets'), format_percent),
            "Short Interest": (info.get('sharesShort'), format_number),
            "Perf YTD": (get_change(current_price, hist[hist.index.year == last_date.year].iloc[0]['Close']) if not hist.empty else None, format_percent),
            
            "Book/sh": (info.get('bookValue'), "{:.2f}".format),
            "P/C": (current_price / info.get('totalCashPerShare') if info.get('totalCashPerShare') else None, "{:.2f}".format),
            "ROE": (info.get('returnOnEquity'), format_percent),
            "52W High": (info.get('fiftyTwoWeekHigh'), "{:.2f}".format),
            "Perf Year": (info.get('52WeekChange'), format_percent),
            
            "Cash/sh": (info.get('totalCashPerShare'), "{:.2f}".format),
            "P/FCF": ("-", str), # Complex calc
            "ROIC": ("-", str),
            "52W Low": (info.get('fiftyTwoWeekLow'), "{:.2f}".format),
            "Perf 3Y": (get_perf(365*3), format_percent),
            
            "Dividend Est.": (info.get('dividendRate'), "{:.2f}".format),
            "EV/EBITDA": (info.get('enterpriseToEbitda'), "{:.2f}".format),
            "Gross Margin": (info.get('grossMargins'), format_percent),
            "Perf 5Y": (get_perf(365*5), format_percent),
            
            "Dividend TTM": (info.get('trailingAnnualDividendRate'), "{:.2f}".format),
            "EV/Sales": (info.get('enterpriseToRevenue'), "{:.2f}".format),
            "Oper. Margin": (info.get('operatingMargins'), format_percent),
            "ATR (14)": ("-", str), # Need calc
            "Perf 10Y": (get_perf(365*10), format_percent),
            
            "Quick Ratio": (info.get('quickRatio'), "{:.2f}".format),
            "Profit Margin": (info.get('profitMargins'), format_percent),
            "RSI (14)": (calculate_rsi(pd.DataFrame({ticker: hist['Close']})).iloc[-1].item() if not hist.empty else None, "{:.2f}".format),
            "Recom": (info.get('recommendationMean'), "{:.2f}".format),
            
            "Current Ratio": (info.get('currentRatio'), "{:.2f}".format),
            "SMA20": (get_change(current_price, hist['Close'].rolling(20).mean().iloc[-1]), format_percent),
            "Beta": (info.get('beta'), "{:.2f}".format),
            "Target Price": (info.get('targetMeanPrice'), "{:.2f}".format),
            
            "Debt/Eq": (info.get('debtToEquity'), "{:.2f}".format),
            "SMA50": (get_change(current_price, info.get('fiftyDayAverage')), format_percent),
            "Rel Volume": ("-", str),
            "Prev Close": (info.get('previousClose'), "{:.2f}".format),
            
            "Employees": (info.get('fullTimeEmployees'), format_number),
            "SMA200": (get_change(current_price, info.get('twoHundredDayAverage')), format_percent),
            "Avg Volume": (info.get('averageVolume'), format_number),
            "Price": (info.get('currentPrice'), "{:.2f}".format),
            
            "Volume": (info.get('volume'), format_number),
            "Change": (info.get('regularMarketChangePercent'), lambda x: f"{x:.2f}%" if x else "-"),
        }
        
        # Definitions for tooltips
        metric_definitions = {
            "P/E": "Price-to-Earnings Ratio: Share price divided by earnings per share.",
            "EPS (ttm)": "Earnings Per Share (Trailing 12 Months).",
            "Insider Own": "Percentage of shares held by company insiders.",
            "Shs Outstand": "Shares Outstanding: Total shares held by all shareholders.",
            "Perf Week": "Performance over the last week.",
            "Market Cap": "Total value of all outstanding shares.",
            "Forward P/E": "Projected P/E ratio for the next 12 months.",
            "EPS next Y": "Estimated Earnings Per Share for the next year.",
            "Insider Trans": "Recent insider buying/selling activity.",
            "Shs Float": "Shares available for trading by the public.",
            "Perf Month": "Performance over the last month.",
            "Enterprise Value": "Measure of a company's total value (Market Cap + Debt - Cash).",
            "PEG": "Price/Earnings to Growth Ratio.",
            "EPS next Q": "Estimated Earnings Per Share for the next quarter.",
            "Inst Own": "Percentage of shares held by institutional investors.",
            "Short Float": "Percentage of float that is shorted.",
            "Perf Quarter": "Performance over the last quarter.",
            "Income": "Net Income: The company's total profit.",
            "P/S": "Price-to-Sales Ratio.",
            "EPS this Y": "Earnings Per Share estimate for the current year.",
            "Inst Trans": "Recent institutional buying/selling activity.",
            "Short Ratio": "Days to Cover: Number of days to close out short positions.",
            "Perf Half Y": "Performance over the last 6 months.",
            "Sales": "Total Revenue.",
            "P/B": "Price-to-Book Ratio.",
            "ROA": "Return on Assets.",
            "Short Interest": "Total number of shares sold short.",
            "Perf YTD": "Performance Year-to-Date.",
            "Book/sh": "Book Value per Share.",
            "P/C": "Price-to-Cash Ratio.",
            "ROE": "Return on Equity.",
            "52W High": "Highest price in the last 52 weeks.",
            "Perf Year": "Performance over the last year.",
            "Cash/sh": "Total Cash per Share.",
            "P/FCF": "Price-to-Free-Cash-Flow.",
            "ROIC": "Return on Invested Capital.",
            "52W Low": "Lowest price in the last 52 weeks.",
            "Perf 3Y": "Performance over the last 3 years.",
            "Dividend Est.": "Estimated Annual Dividend.",
            "EV/EBITDA": "Enterprise Value to EBITDA.",
            "Gross Margin": "Gross Profit as a percentage of Revenue.",
            "Perf 5Y": "Performance over the last 5 years.",
            "Dividend TTM": "Trailing 12 Months Dividend.",
            "EV/Sales": "Enterprise Value to Sales.",
            "Oper. Margin": "Operating Margin: Operating income divided by revenue.",
            "ATR (14)": "Average True Range (volatility measure).",
            "Perf 10Y": "Performance over the last 10 years.",
            "Quick Ratio": "Measure of company's ability to meet short-term obligations.",
            "Profit Margin": "Net Income divided by Revenue.",
            "RSI (14)": "Relative Strength Index (momentum oscillator).",
            "Recom": "Analyst Recommendation Rating (1=Strong Buy, 5=Sell).",
            "Current Ratio": "Current Assets divided by Current Liabilities.",
            "SMA20": "Distance from 20-Day Simple Moving Average.",
            "Beta": "Measure of volatility relative to the market.",
            "Target Price": "Average Analyst Target Price.",
            "Debt/Eq": "Debt-to-Equity Ratio.",
            "SMA50": "Distance from 50-Day Simple Moving Average.",
            "Rel Volume": "Relative Volume: Current volume compared to average.",
            "Prev Close": "Previous trading session's closing price.",
            "Employees": "Number of full-time employees.",
            "SMA200": "Distance from 200-Day Simple Moving Average.",
            "Avg Volume": "Average Daily Trading Volume.",
            "Price": "Current Stock Price.",
            "Volume": "Current Trading Volume.",
            "Change": "Percentage change from previous close.",
            "Index": "Market index membership."
        }

        # Generate HTML Table
        html_table = """
        <style>
            table.stats-table {
                width: 100%;
                border-collapse: collapse;
                font-family: sans-serif;
                font-size: 0.65em;
            }
            table.stats-table td {
                border: 1px solid #555;
                padding: 8px;
            }
            .metric-label {
                cursor: help;
                font-weight: 500;
                position: relative; /* Anchor for tooltip */
            }
            /* Custom CSS Tooltip */
            .metric-label:hover::after {
                content: attr(data-tooltip);
                position: absolute;
                bottom: 100%;
                left: 50%;
                transform: translateX(-50%);
                background-color: #333;
                color: #fff;
                padding: 6px 10px;
                border-radius: 5px;
                font-size: 0.85rem;
                white-space: normal;
                max-width: 250px;
                width: max-content;
                z-index: 9999;
                box-shadow: 0 4px 6px rgba(0,0,0,0.3);
                text-align: center;
                border: 1px solid #666;
            }
            .metric-value {
                color: #FFD700;
                font-weight: bold;
            }
        </style>
        <table class="stats-table">
        """

        items = list(data_grid.items())
        total_items = len(items)
        cols_per_row = 4 # Pairs of (Metric, Value)
        
        for i in range(0, total_items, cols_per_row):
            html_table += "<tr>"
            chunk = items[i : i + cols_per_row]
            
            # Ensure we always have 3 pairs per row for alignment, filling with empty if needed
            while len(chunk) < cols_per_row:
                chunk.append(("", (None, str)))

            for label, (val, fmt) in chunk:
                if label:
                    try:
                        display_val = fmt(val) if val is not None else "-"
                    except:
                        display_val = "-"
                    
                    definition = metric_definitions.get(label, "")
                    # Escape quotes in definition to prevent HTML breaking
                    definition = definition.replace('"', '&quot;')
                    tooltip_attr = f'data-tooltip="{definition}"' if definition else ""
                    
                    html_table += f'<td class="metric-label" {tooltip_attr}>{label}</td>'
                    html_table += f'<td class="metric-value">{display_val}</td>'
                else:
                    # Empty filler cells
                    html_table += "<td></td><td></td>"
            
            html_table += "</tr>"
        
        html_table += "</table>"
        
        st.markdown(html_table, unsafe_allow_html=True)


        # Show raw data expander
        with st.expander("Raw Data (JSON)"):
            st.json(info)
