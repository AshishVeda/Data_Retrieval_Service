import sys
import os
from datetime import datetime, timedelta
import logging

# Add the project root to the path so we can import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.routes.finnhub_routes import FinnhubService
from app.services.news_service import NewsService

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BacktestNewsDataFetcher:
    """
    Class to fetch news data for backtesting purposes.
    Fetches news from prior to the testing period (before 1 week ago).
    """
    
    def __init__(self):
        """Initialize the news data fetcher using the app's services"""
        self.finnhub_service = FinnhubService()
        self.news_service = NewsService()
    
    def get_date_ranges(self):
        """
        Get the date ranges for training period (before 1 week ago)
        
        Returns:
            tuple: (train_start, train_end, test_start, test_end) datetime objects
        """
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Calculate date ranges
        test_end = today - timedelta(days=1)  # Yesterday
        test_start = today - timedelta(days=7)  # 1 week ago
        train_end = test_start - timedelta(days=1)  # 1 day before test start
        train_start = today - timedelta(days=28)  # 4 weeks ago (to get enough data)
        
        return train_start, train_end, test_start, test_end
    
    def fetch_news_data(self, symbol, user_query=None):
        """
        Fetch news data for the training period (before 1 week ago)
        
        Args:
            symbol (str): The stock symbol to fetch news for
            user_query (str, optional): User query to find relevant news
            
        Returns:
            dict: Dictionary with status and news data
        """
        train_start, train_end, _, _ = self.get_date_ranges()
        
        logger.info(f"Fetching news data for {symbol} from {train_start.strftime('%Y-%m-%d')} to {train_end.strftime('%Y-%m-%d')}")
        
        # Try semantic search if user query is provided
        if user_query:
            news_result = self.news_service.search_similar_news(user_query, symbol, limit=10)
            
            if news_result['status'] == 'success' and len(news_result.get('data', [])) > 0:
                news_data = news_result['data']
                
                # Filter by date to only include training period
                filtered_news = []
                for article in news_data:
                    if 'published' in article:
                        try:
                            pub_date = datetime.strptime(article['published'], '%Y-%m-%dT%H:%M:%SZ')
                        except ValueError:
                            try:
                                pub_date = datetime.strptime(article['published'].split('.')[0], '%Y-%m-%dT%H:%M:%S')
                            except ValueError:
                                continue  # Skip if date format cannot be parsed
                                
                        if train_start <= pub_date <= train_end:
                            filtered_news.append(article)
                
                if filtered_news:
                    return {
                        'status': 'success',
                        'data': filtered_news,
                        'source': 'semantic_search',
                        'date_range': {
                            'start': train_start.strftime('%Y-%m-%d'),
                            'end': train_end.strftime('%Y-%m-%d')
                        }
                    }
        
        # Fall back to Finnhub API
        news_result = self.finnhub_service.fetch_company_news(symbol, weeks=3)  # Get 3 weeks worth of data
        
        if news_result['status'] != 'success':
            logger.error(f"Failed to fetch news data: {news_result.get('message', 'Unknown error')}")
            return news_result
        
        # Filter news data to training period only
        filtered_news = []
        for article in news_result.get('data', []):
            if 'datetime' in article:
                try:
                    pub_date = datetime.fromtimestamp(article['datetime'])
                    if train_start <= pub_date <= train_end:
                        filtered_news.append(article)
                except (ValueError, TypeError):
                    continue
            elif 'published' in article:
                try:
                    pub_date = datetime.strptime(article['published'], '%Y-%m-%dT%H:%M:%SZ')
                except ValueError:
                    try:
                        pub_date = datetime.strptime(article['published'].split('.')[0], '%Y-%m-%dT%H:%M:%S')
                    except ValueError:
                        continue  # Skip if date format cannot be parsed
                        
                if train_start <= pub_date <= train_end:
                    filtered_news.append(article)
        
        # Format the news data to a standard structure
        formatted_news = []
        for article in filtered_news:
            formatted_article = {
                'title': article.get('headline', article.get('title', 'No title')),
                'summary': article.get('summary', 'No summary available'),
                'source': article.get('source', 'Unknown'),
                'link': article.get('url', article.get('link', '#')),
            }
            
            # Add published date in a consistent format
            if 'datetime' in article:
                try:
                    formatted_article['published'] = datetime.fromtimestamp(article['datetime']).strftime('%Y-%m-%dT%H:%M:%SZ')
                except (ValueError, TypeError):
                    formatted_article['published'] = 'Unknown date'
            elif 'published' in article:
                formatted_article['published'] = article['published']
            else:
                formatted_article['published'] = 'Unknown date'
                
            formatted_news.append(formatted_article)
        
        # Sort by date (newest first)
        formatted_news = sorted(
            formatted_news,
            key=lambda x: x.get('published', ''),
            reverse=True
        )
        
        return {
            'status': 'success',
            'data': formatted_news[:10],  # Limit to top 10 articles
            'source': 'finnhub_api',
            'date_range': {
                'start': train_start.strftime('%Y-%m-%d'),
                'end': train_end.strftime('%Y-%m-%d')
            }
        }


if __name__ == "__main__":
    # Example usage
    fetcher = BacktestNewsDataFetcher()
    result = fetcher.fetch_news_data('AAPL', user_query="Apple earnings")
    
    if result['status'] == 'success':
        articles = result['data']
        
        print(f"Training period: {result['date_range']['start']} to {result['date_range']['end']}")
        print(f"Source: {result['source']}")
        print(f"News articles found: {len(articles)}")
        
        for i, article in enumerate(articles):
            print(f"\n{i+1}. {article['title']}")
            print(f"   Published: {article['published']}")
            print(f"   Source: {article['source']}")
            print(f"   Link: {article['link']}")
            print(f"   Summary: {article['summary'][:100]}...")
    else:
        print(f"Error: {result.get('message', 'Unknown error')}") 