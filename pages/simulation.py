import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
import simulation_lib
import utils

st.set_page_config(page_title="Stock Simulation", page_icon="📈")

st.title("Stock Price Simulation & Backtesting")

st.markdown("""
This tool allows you to simulate a stock's performance and test prediction models.
1. Select a Ticker and a Time Period (Start -> End).
2. The model trains on data from **Start to End**.
3. It predicts prices for the **3 months following End**.
4. We also simulate a Wallet's growth over the entire period.
""")

# --- Sidebar Inputs ---
st.sidebar.header("Configuration")

# Ticker Input
ticker = st.sidebar.text_input("Ticker Symbol", value="NVDA").upper()

# Date Inputs
today = date.today()
default_start = today - relativedelta(years=2)
default_end = today - relativedelta(months=3) # Default to 3 months ago to show comparison

start_date = st.sidebar.date_input("Start Date", value=default_start)
end_date = st.sidebar.date_input("End Date (Simulation Cut-off)", value=default_end)

if start_date >= end_date:
    st.sidebar.error("Start Date must be before End Date.")

# Wallet Inputs
st.sidebar.subheader("Wallet Settings")
initial_investment = st.sidebar.number_input("Initial Investment ($)", value=10000.0, step=1000.0)
contribution_amount = st.sidebar.number_input("Regular Contribution ($)", value=0.0, step=100.0)
contribution_freq = st.sidebar.selectbox("Contribution Frequency", ["None", "Monthly", "Quarterly", "Annually"])

# Model Selection
backend = simulation_lib.SimulationBackend()
model_name = st.sidebar.selectbox("Prediction Model", list(backend.models.keys()))

# Run Button
if st.sidebar.button("Run Simulation"):
    with st.spinner("Fetching data and running simulation..."):
        # 1. Determine Date Ranges
        # Comparison period: End -> End + 3 months
        # We need data up to End + 3 months (or today, whichever is earlier/later)
        # If End + 3 months is in the future, we just get up to Today for actuals.
        
        prediction_end_date = end_date + relativedelta(months=3)
        fetch_end_date = max(prediction_end_date, today) 
        # Actually yfinance fetch end is exclusive, and we want to ensure we get enough data.
        # Let's fetch a bit more to be safe.
        
        # We need to handle the case where prediction_end_date is in the future relative to Today.
        # yfinance will just return up to Today.
        
        df_all = utils.get_price_data([ticker], start_date, fetch_end_date + timedelta(days=5))
        
        if df_all.empty:
            st.error(f"No data found for {ticker} in the given range.")
        else:
            # Ensure Date is datetime for pandas ops (utils returns date objects usually, let's standardize)
            df_all['Date'] = pd.to_datetime(df_all['Date'])
            
            # 2. Split Data
            # Training: <= End Date
            # Actuals (Ground Truth): > End Date AND <= Prediction End Date
            
            mask_train = df_all['Date'].dt.date <= end_date
            df_train = df_all.loc[mask_train].copy()
            
            # For validation, we look at the period we want to predict
            mask_test = (df_all['Date'].dt.date > end_date) & (df_all['Date'].dt.date <= prediction_end_date)
            df_test = df_all.loc[mask_test].copy()
            
            if df_train.empty:
                st.error("Not enough training data before the End Date.")
            else:
                # 3. Train Model
                model = backend.get_model(model_name)
                model.train(df_train['Date'].tolist(), df_train['Price'].values)
                
                # 4. Predict
                # Generate dates for the next 3 months (daily)
                # If we have df_test, we can use those dates to align exactly. 
                # If df_test is empty (future), we need to generate business days.
                
                if not df_test.empty:
                    future_dates = df_test['Date'].tolist()
                    # Also, if df_test doesn't cover the full 3 months (e.g. gaps), we might want to fill?
                    # For comparison, using exact dates is best.
                else:
                    # Generate dates
                    future_dates = pd.date_range(start=end_date + timedelta(days=1), end=prediction_end_date, freq='B').to_pydatetime().tolist()
                
                # If df_test is partial (e.g. End is yesterday), we still want to predict 3 months out.
                # So let's always generate the full 3-month range for prediction
                full_future_dates = pd.date_range(start=end_date + timedelta(days=1), end=prediction_end_date, freq='B').to_pydatetime().tolist()
                
                pred_prices, lower, upper = model.predict(full_future_dates)
                
                df_pred = pd.DataFrame({
                    'Date': full_future_dates,
                    'Predicted': pred_prices,
                    'Lower': lower,
                    'Upper': upper
                })

                # 5. Wallet Simulation
                # Run on the whole available history (Train + Test) to show user their journey
                df_history_combined = pd.concat([df_train, df_test]).sort_values('Date').drop_duplicates('Date')
                
                wallet = simulation_lib.Wallet(initial_investment, contribution_amount, contribution_freq)
                wallet_res = wallet.simulate_portfolio(df_history_combined)
                
                # --- Visualization ---
                
                # Chart 1: Price vs Prediction
                fig_price = go.Figure()
                
                # Historical
                fig_price.add_trace(go.Scatter(
                    x=df_train['Date'], y=df_train['Price'],
                    mode='lines', name='Historical Price',
                    line=dict(color='blue')
                ))
                
                # Actual Future (if exists)
                if not df_test.empty:
                    fig_price.add_trace(go.Scatter(
                        x=df_test['Date'], y=df_test['Price'],
                        mode='lines', name='Actual Future Price',
                        line=dict(color='green')
                    ))
                
                # Prediction
                fig_price.add_trace(go.Scatter(
                    x=df_pred['Date'], y=df_pred['Predicted'],
                    mode='lines', name='Predicted Price',
                    line=dict(color='orange', dash='dash')
                ))
                
                # Uncertainty Bands
                fig_price.add_trace(go.Scatter(
                    x=df_pred['Date'].tolist() + df_pred['Date'].tolist()[::-1],
                    y=df_pred['Upper'].tolist() + df_pred['Lower'].tolist()[::-1],
                    fill='toself',
                    fillcolor='rgba(255, 165, 0, 0.2)',
                    line=dict(color='rgba(255,255,255,0)'),
                    name='Uncertainty (95%)'
                ))
                
                fig_price.update_layout(title=f"{ticker} Price Simulation", xaxis_title="Date", yaxis_title="Price ($)")
                st.plotly_chart(fig_price, use_container_width=True)
                
                # Chart 2: Wallet Value
                st.subheader("Portfolio Performance")
                
                # Metrics
                final_val = wallet_res['Portfolio Value'].iloc[-1]
                total_inv = wallet_res['Invested Capital'].iloc[-1]
                profit = final_val - total_inv
                roi = (profit / total_inv * 100) if total_inv > 0 else 0
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Final Portfolio Value", f"${final_val:,.2f}")
                col2.metric("Total Invested", f"${total_inv:,.2f}")
                col3.metric("Total Profit/Loss", f"${profit:,.2f}", f"{roi:.2f}%")
                
                fig_wallet = go.Figure()
                
                fig_wallet.add_trace(go.Scatter(
                    x=wallet_res['Date'], y=wallet_res['Portfolio Value'],
                    mode='lines', name='Portfolio Value',
                    fill='tozeroy',
                    line=dict(color='purple')
                ))
                
                fig_wallet.add_trace(go.Scatter(
                    x=wallet_res['Date'], y=wallet_res['Invested Capital'],
                    mode='lines', name='Invested Capital',
                    line=dict(color='gray', dash='dot')
                ))
                
                fig_wallet.update_layout(title="Wallet Growth Over Time", xaxis_title="Date", yaxis_title="Value ($)")
                st.plotly_chart(fig_wallet, use_container_width=True)
