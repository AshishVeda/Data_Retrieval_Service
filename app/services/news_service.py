import feedparser
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Optional
from app.services.vector_service import VectorService

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class NewsService:
    # List of top tech companies
    TECH_COMPANIES = [
        "AAPL",  # Apple
        "MSFT",  # Microsoft
        "GOOGL", # Alphabet (Google)
        "AMZN",  # Amazon
        "META",  # Meta (Facebook)
        "NVDA",  # NVIDIA
        "TSLA",  # Tesla
        "INTC",  # Intel
        "AMD",   # Advanced Micro Devices
        "IBM"    # IBM
    ]

    def __init__(self):
        self.vector_service = VectorService()
        logger.info("NewsService initialized with VectorService")

    def get_company_news(self, symbol: str) -> Dict:
        """Get news for a company using Google RSS feeds and store in vector DB"""
        try:
            logger.debug(f"Fetching news for {symbol}")
            
            # Google News RSS feed URL
            url = f'https://news.google.com/rss/search?q={symbol}+stock&hl=en-US&gl=US&ceid=US:en'
            logger.debug(f"Fetching from URL: {url}")
            
            # Fetch and parse RSS feed
            feed = feedparser.parse(url)
            logger.debug(f"Feed status: {feed.status}, Feed entries: {len(feed.entries)}")
            
            # Process news items
            news_items = []
            three_days_ago = datetime.now() - timedelta(days=3)
            logger.debug(f"Filtering news newer than: {three_days_ago}")
            
            # Sort entries by date (newest first)
            sorted_entries = sorted(
                feed.entries,
                key=lambda x: datetime.strptime(x.published, '%a, %d %b %Y %H:%M:%S %Z') if hasattr(x, 'published') else datetime.now(),
                reverse=True
            )
            
            for entry in sorted_entries:
                # Parse the published date
                try:
                    # Try different date formats
                    try:
                        published_date = datetime.strptime(entry.published, '%a, %d %b %Y %H:%M:%S %Z')
                    except ValueError:
                        try:
                            published_date = datetime.strptime(entry.published, '%a, %d %b %Y %H:%M:%S %z')
                        except ValueError:
                            # If both formats fail, use the current time
                            published_date = datetime.now()
                            logger.warning(f"Could not parse date: {entry.published}, using current time")
                    
                    logger.debug(f"Article date: {published_date}, Title: {entry.title}")
                    
                    # Only include news from the last 3 days
                    if published_date >= three_days_ago:
                        news_item = {
                            'title': entry.title,
                            'link': entry.link,
                            'published': entry.published,
                            'summary': entry.summary if hasattr(entry, 'summary') else '',
                            'symbol': symbol,
                            'timestamp': datetime.now().isoformat()
                        }
                        news_items.append(news_item)
                        logger.debug(f"Added article: {entry.title}")
                        
                        # Stop if we've reached 30 articles
                        if len(news_items) >= 30:
                            logger.info(f"Reached maximum of 30 articles for {symbol}")
                            break
                    else:
                        logger.debug(f"Skipped old article: {entry.title}")
                except Exception as e:
                    logger.error(f"Error processing article: {str(e)}")
                    continue
            
            # Store news items in vector DB
            if news_items:
                self.vector_service.store_news(news_items)
                logger.debug(f"Stored {len(news_items)} news items in vector DB")
            else:
                logger.warning(f"No news items found for {symbol} in the last 3 days")
            
            return {
                'status': 'success',
                'data': news_items,
                'message': f'News fetched and stored successfully for {symbol}'
            }
        except Exception as e:
            logger.error(f"Error fetching news for {symbol}: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }

    def fetch_all_tech_news(self) -> Dict:
        """Fetch news for all tech companies"""
        try:
            all_results = []
            for symbol in self.TECH_COMPANIES:
                result = self.get_company_news(symbol)
                if result['status'] == 'success':
                    all_results.append({
                        'symbol': symbol,
                        'news_count': len(result['data']),
                        'message': result['message']
                    })
                else:
                    all_results.append({
                        'symbol': symbol,
                        'error': result['message']
                    })
            
            return {
                'status': 'success',
                'data': all_results,
                'message': f'News fetched for {len(self.TECH_COMPANIES)} companies'
            }
        except Exception as e:
            logger.error(f"Error fetching all tech news: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }

    def get_stored_news(self, symbol: str, limit: int = 10) -> Dict:
        """Retrieve stored news for a specific company from vector DB"""
        try:
            news_items = self.vector_service.get_news_by_symbol(symbol, limit)
            
            return {
                'status': 'success',
                'data': news_items,
                'message': f'Retrieved {len(news_items)} stored news items'
            }
        except Exception as e:
            logger.error(f"Error retrieving stored news for {symbol}: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }

    def search_similar_news(self, query: str, symbol: Optional[str] = None, limit: int = 5) -> Dict:
        """Search for similar news items based on a query"""
        try:
            similar_news = self.vector_service.search_similar_news(query, symbol, limit)
            
            return {
                'status': 'success',
                'data': similar_news,
                'message': f'Found {len(similar_news)} similar news items'
            }
        except Exception as e:
            logger.error(f"Error searching similar news: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }

    def cleanup_old_news(self) -> Dict:
        """Remove news items older than 3 days"""
        try:
            self.vector_service.cleanup_old_news(days=3)
            
            return {
                'status': 'success',
                'message': 'Cleaned up news items older than 3 days'
            }
        except Exception as e:
            logger.error(f"Error cleaning up old news: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }

    @staticmethod
    def get_all_companies_news(symbols: List[str]) -> Dict:
        """Get news for all companies in the list"""
        all_news = []
        for symbol in symbols:
            result = NewsService.get_company_news(symbol)
            if result['status'] == 'success':
                all_news.extend(result['data'])
        
        return {
            'status': 'success',
            'data': all_news,
            'message': f'News fetched for {len(symbols)} companies'
        } 