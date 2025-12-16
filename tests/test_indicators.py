import pandas as pd
import numpy as np
import pytest
from indicators import add_moving_average, add_52w_high_low, calculate_rsi

@pytest.fixture
def sample_price_df():
    # Create a simple DataFrame for testing
    dates = pd.date_range(start='2023-01-01', periods=100)
    data = {
        'AAPL': np.arange(100, 200),  # Linear increase
        'GOOG': np.random.rand(100) * 100
    }
    return pd.DataFrame(data, index=dates)

def test_add_moving_average(sample_price_df):
    df = sample_price_df.copy()
    df = add_moving_average(df, ma_periods=[10, 20])
    
    assert 'AAPL_MA10' in df.columns
    assert 'AAPL_MA20' in df.columns
    assert 'GOOG_MA10' in df.columns
    
    # Check simple calculation for linear increase (avg of last 10 of 100..109 is roughly 104.5)
    # The first 9 values should be NaN if min_periods wasn't 1, but logic uses min_periods=1
    assert not df['AAPL_MA10'].isnull().all()
    
    # Verify values for a known sequence
    # AAPL is 100, 101, 102... 
    # At index 0 (value 100), MA10 (min_periods=1) should be 100
    assert df['AAPL_MA10'].iloc[0] == 100.0
    
    # At index 9 (value 109), MA10 is avg(100...109) = 104.5
    assert df['AAPL_MA10'].iloc[9] == 104.5

def test_add_52w_high_low(sample_price_df):
    df = sample_price_df.copy()
    # Ensure enough data or check min_periods behavior
    # Code uses min_periods=1
    df = add_52w_high_low(df)
    
    assert 'AAPL_52w_high' in df.columns
    assert 'AAPL_52w_low' in df.columns
    
    # For monotonically increasing AAPL (100 to 199)
    # The 52w high at the last point should be the current price
    assert df['AAPL_52w_high'].iloc[-1] == 199
    # The 52w low at the last point should be the price 52 weeks ago (or start of data)
    # Since we only have 100 days, it's the min of the whole window so far, which is 100
    assert df['AAPL_52w_low'].iloc[-1] == 100

def test_calculate_rsi(sample_price_df):
    df = sample_price_df.copy()
    rsi_df = calculate_rsi(df)
    
    assert 'AAPL' in rsi_df.columns
    assert 'GOOG' in rsi_df.columns
    
    # RSI should be between 0 and 100
    assert rsi_df.max().max() <= 100
    assert rsi_df.min().min() >= 0
    
    # For a constantly increasing stock (AAPL), RSI should be high (near 100)
    # Use a slice to avoid initial warmup period
    assert rsi_df['AAPL'].iloc[-1] > 70
