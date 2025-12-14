import yfinance as yf

def get_news(ticker_symbol):
    """
    Fetches news for a given stock ticker.
    """
    ticker = yf.Ticker(ticker_symbol)
    company_news = ticker.news
    
    if not company_news:
        return []
    
    news_list = []
    for article in company_news:
        content = article.get('content', {})
        headline = content.get('title', 'N/A - No Title Found')
        canonical_url = content.get('canonicalUrl', {})
        link = canonical_url.get('url', 'N/A - No Link Found')
        publisher = article.get('publisher', 'N/A - No Publisher')
        
        news_list.append({
            'headline': headline,
            'link': link,
            'publisher': publisher
        })
        
    return news_list
