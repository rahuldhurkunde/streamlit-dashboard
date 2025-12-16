import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from utils import get_price_data

@patch('utils.yf.Ticker')
def test_get_price_data(mock_ticker):
    # Setup mock return data
    mock_hist = pd.DataFrame({
        'Open': [100, 102],
        'High': [105, 106],
        'Low': [99, 101],
        'Close': [101, 105],
    }, index=pd.to_datetime(['2023-01-01', '2023-01-02']))
    mock_hist.index.name = 'Date'
    
    mock_instance = MagicMock()
    mock_instance.history.return_value = mock_hist
    mock_ticker.return_value = mock_instance
    
    start = '2023-01-01'
    end = '2023-01-03'
    tickers = ['TEST']
    
    df = get_price_data(tickers, start, end)
    
    assert not df.empty
    assert 'Ticker' in df.columns
    assert 'Price' in df.columns
    assert df['Ticker'].iloc[0] == 'TEST'
    assert df['Price'].iloc[0] == 101 # Close price renamed to Price
    
@patch('utils.yf.Ticker')
def test_get_price_data_empty(mock_ticker):
    # Setup mock to return empty
    mock_instance = MagicMock()
    mock_instance.history.return_value = pd.DataFrame()
    mock_ticker.return_value = mock_instance
    
    df = get_price_data(['EMPTY'], '2023-01-01', '2023-01-02')
    
    assert df.empty
    assert 'Ticker' in df.columns
    assert 'Price' in df.columns
