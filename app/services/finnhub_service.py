import finnhub
from datetime import datetime, timedelta
import os
import logging
from typing import Dict, List
from app.services.vector_service import VectorService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FinnhubService:
    def __init__(self):
        # Get API key from environment variable
        self.finnhub_api_key = os.getenv("FINNHUB_API_KEY", "")
        self.finnhub_client = finnhub.Client(api_key=self.finnhub_api_key)
        self.vector_service = VectorService()
        logger.info("FinnhubService initialized")
        
        # List of top companies to fetch news for
        self.companies = ['AAPL', 'MSFT', 'AMZN', 'GOOGL', 'META', 'TSLA', 'NVDA', 'JPM', 'V', 'WMT']
    
    def fetch_company_news(self, symbol: str, weeks: int = 3) -> Dict:
        """Fetch news from Finnhub for a specific company and store in VectorDB"""
        try:
            # Calculate date range (today to n weeks ago)
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(weeks=weeks)).strftime('%Y-%m-%d')
            
            # Fetch news from Finnhub
            news = self.finnhub_client.company_news(symbol, _from=start_date, to=end_date)
            
            if not news:
                logger.info(f"No news found for {symbol}")
                return {
                    'status': 'success',
                    'message': f'No news found for {symbol}',
                    'data': []
                }
            
            # Process articles before storing
            processed_articles = []
            for article in news:
                try:
                    # Convert Unix timestamp to datetime
                    article_date = datetime.fromtimestamp(article.get('datetime', 0))
                    
                    # Format the article for storage
                    processed_articles.append({
                        'symbol': symbol,
                        'title': article.get('headline', 'No headline'),
                        'link': article.get('url', ''),
                        'url': article.get('url', ''),
                        'published': article_date.isoformat(),
                        'summary': article.get('summary', ''),
                        'source': 'Finnhub',
                        'timestamp': datetime.now().isoformat()
                    })
                    
                except Exception as e:
                    logger.error(f"Error processing news article: {str(e)}")
                    continue
            
            # Store in vector database
            if processed_articles:
                storage_success = self.vector_service.store_news(processed_articles)
                if not storage_success:
                    logger.error(f"Failed to store news articles in vector database")
            
            return {
                'status': 'success',
                'message': f'Fetched and stored {len(processed_articles)} news articles for {symbol}',
                'data': {
                    'article_count': len(processed_articles),
                    'date_range': {
                        'from': start_date,
                        'to': end_date,
                        'total_articles': len(news)
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Error fetching Finnhub news for {symbol}: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def fetch_all_company_news(self) -> Dict:
        """Fetch news for a list of predefined companies"""
        try:
            results = {}
            for symbol in self.companies:
                try:
                    # Fetch news for each company
                    company_result = self.fetch_company_news(symbol)
                    
                    if company_result['status'] == 'success':
                        results[symbol] = {
                            'status': 'success',
                            'article_count': company_result['data'].get('article_count', 0)
                        }
                    else:
                        results[symbol] = {
                            'status': 'error',
                            'message': company_result['message']
                        }
                    
                except Exception as e:
                    logger.error(f"Error fetching Finnhub news for {symbol}: {str(e)}")
                    results[symbol] = {
                        'status': 'error',
                        'message': str(e)
                    }
            
            return {
                'status': 'success',
                'message': 'Completed fetching news for all companies',
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Error in fetch all company news: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def get_stored_finnhub_news(self, symbol: str, limit: int = 10) -> Dict:
        """Retrieve stored Finnhub news for a specific company from vector DB"""
        try:
            # Get news from vector DB - fetch significantly more to ensure we have enough after filtering
            news_items = self.vector_service.get_news_by_symbol(symbol, limit=250)
            
            # Filter for only Finnhub sources
            finnhub_news = []
            for item in news_items:
                source = item.get('source', '')
                if source and 'Finnhub' in source:
                    finnhub_news.append(item)
            
            # Trim to requested limit
            finnhub_news = finnhub_news[:limit]
            
            return {
                'status': 'success',
                'message': f'Retrieved {len(finnhub_news)} Finnhub news items for {symbol}',
                'data': finnhub_news
            }
            
        except Exception as e:
            logger.error(f"Error retrieving Finnhub news for {symbol}: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            } 