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
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], name='Close', line=dict(width=1)))
        
        # Add log scale option
        log_scale = st.checkbox("Log Scale", value=True, key="log_scale_indepth")
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
        
        # Prepare data for DataFrame
        table_rows = []
        current_row_data = {}
        col_count = 0
        
        items = list(data_grid.items())
        
        for label, (val, fmt) in items:
            try:
                display_val = fmt(val) if val is not None else "-"
            except Exception:
                display_val = "-"
            
            current_row_data[f"Metric {col_count // 2 + 1}"] = label
            current_row_data[f"Value {col_count // 2 + 1}"] = display_val
            
            col_count += 2 # Each pair (Metric, Value) counts as two columns in the conceptual table
            
            if col_count >= 6: # After 3 pairs (6 columns), start a new row
                table_rows.append(current_row_data)
                current_row_data = {}
                col_count = 0
        
        # Add any remaining data as a partial row
        if current_row_data:
            # Fill remaining columns with empty strings to maintain structure for st.dataframe
            while col_count < 6:
                current_row_data[f"Metric {col_count // 2 + 1}"] = ""
                current_row_data[f"Value {col_count // 2 + 1}"] = ""
                col_count += 2
            table_rows.append(current_row_data)

        if table_rows:
            df_stats = pd.DataFrame(table_rows)
            
            def highlight_cols(s):
                styles = []
                for col_name in s.index:
                    if col_name.startswith('Value'):
                        styles.append('color: #FFD700') # Golden color for value text
                    else:
                        styles.append('') # Default (no specific styling)
                return styles

            st.dataframe(df_stats.style.apply(highlight_cols, axis=1), use_container_width=True, hide_index=True)
        else:
            st.info("No statistics available for this ticker.")

        # Show raw data expander
        with st.expander("Raw Data (JSON)"):
            st.json(info)