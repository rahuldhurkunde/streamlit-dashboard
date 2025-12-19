import pytest
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from simulation_lib import Wallet, LinearRegressionPredictor

def test_wallet_monthly_contribution():
    # Setup data: 3 months of daily data
    dates = pd.date_range(start='2023-01-01', periods=90, freq='D')
    # Price constant at $100
    prices = [100.0] * 90
    df = pd.DataFrame({'Date': dates, 'Price': prices})
    
    # Wallet: $1000 initial, $100 monthly
    wallet = Wallet(initial_capital=1000.0, contribution_amount=100.0, contribution_freq='Monthly')
    
    res = wallet.simulate_portfolio(df)
    
    # Check initial
    # Day 0: Invest $1000 -> 10 shares. Value $1000.
    assert res['Invested Capital'].iloc[0] == 1000.0
    assert res['Portfolio Value'].iloc[0] == 1000.0
    
    # Check after 1 month (approx 30 days)
    # 2023-02-01 is index 31 (Jan has 31 days).
    # On Feb 1st, we contribute $100. Total invested $1100.
    # Total shares 11. Value $1100.
    
    # Find row for Feb 1
    feb_1_idx = res[res['Date'] == datetime(2023, 2, 1)].index[0]
    assert res['Invested Capital'].iloc[feb_1_idx] == 1100.0
    assert res['Portfolio Value'].iloc[feb_1_idx] == 1100.0
    
    # Check end
    # We should have contributions on Jan 1 (Initial), Feb 1, Mar 1.
    # Total invested: 1000 + 100 + 100 = 1200.
    mar_1_idx = res[res['Date'] == datetime(2023, 3, 1)].index[0]
    assert res['Invested Capital'].iloc[mar_1_idx] == 1200.0

def test_linear_regression_predictor():
    # Perfect line y = x
    dates = [datetime(2023, 1, 1) + timedelta(days=i) for i in range(10)]
    prices = [float(i) for i in range(10)] # Price 0, 1, 2...
    
    model = LinearRegressionPredictor()
    model.train(dates, prices)
    
    # Predict next 5 days
    future_dates = [datetime(2023, 1, 1) + timedelta(days=i) for i in range(10, 15)]
    preds, low, high = model.predict(future_dates)
    
    # Expected: 10, 11, 12, 13, 14
    expected = np.array([10.0, 11.0, 12.0, 13.0, 14.0])
    np.testing.assert_almost_equal(preds, expected, decimal=5)
    
    # Std dev should be 0 for perfect line
    assert model.std_dev < 1e-5

