import pytest
from unittest.mock import MagicMock, patch
from news import get_news

@patch('news.yf.Ticker')
def test_get_news(mock_ticker):
    # Mock data structure matching yfinance news format
    mock_news_data = [
        {
            'content': {
                'title': 'Stock goes up',
                'canonicalUrl': {'url': 'http://example.com/news1'}
            },
            'publisher': 'The News Publisher'
        },
        {
            'content': {
                'title': 'Market crash?',
                # Missing url test
            },
            # Missing publisher test
        }
    ]
    
    mock_instance = MagicMock()
    mock_instance.news = mock_news_data
    mock_ticker.return_value = mock_instance
    
    news_list = get_news('TEST')
    
    assert len(news_list) == 2
    assert news_list[0]['headline'] == 'Stock goes up'
    assert news_list[0]['link'] == 'http://example.com/news1'
    assert news_list[0]['publisher'] == 'The News Publisher'
    
    # Check defaults
    assert news_list[1]['headline'] == 'Market crash?'
    assert news_list[1]['link'] == 'N/A - No Link Found'
    assert news_list[1]['publisher'] == 'N/A - No Publisher'

@patch('news.yf.Ticker')
def test_get_news_empty(mock_ticker):
    mock_instance = MagicMock()
    mock_instance.news = []
    mock_ticker.return_value = mock_instance
    
    news_list = get_news('EMPTY')
    assert news_list == []
