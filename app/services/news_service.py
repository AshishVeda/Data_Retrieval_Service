import feedparser
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Optional
from app.services.vector_service import VectorService
from textblob import TextBlob
import os
from dotenv import load_dotenv
import hashlib

# Load environment variables
load_dotenv()

# Set logging level to INFO to reduce debug noise
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NewsService:
    # List of top companies across various sectors
    TRACKED_COMPANIES = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'BRKB', 'META', 'TSLA',
        'LLY', 'UNH', 'JNJ', 'V', 'JPM', 'XOM', 'PG', 'MA', 'HD', 'BAC',
        'PFE', 'KO', 'CVX', 'PEP', 'ABBV', 'WMT', 'COST'
    ]

    def __init__(self):
        self.vector_service = VectorService()
        self.news_cache = {}
        logger.info("NewsService initialized with VectorService")

    def get_company_news(self, symbol: str) -> Dict:
        """Fetch news articles for a company and store them in vector DB"""
        try:
            # Check cache first
            if symbol in self.news_cache:
                cache_time, cached_news = self.news_cache[symbol]
                if datetime.now() - cache_time < timedelta(hours=1):
                    return {
                        'status': 'success',
                        'data': cached_news,
                        'message': f'News fetched from cache for {symbol}'
                    }
            
            # Fetch fresh news
            logger.info(f"Fetching fresh news for {symbol} from Google News RSS")
            feed = feedparser.parse(f'https://news.google.com/rss/search?q={symbol}+stock&hl=en-US&gl=US&ceid=US:en')
            
            if feed.status != 200:
                logger.error(f"Failed to fetch news feed for {symbol}, status: {feed.status}")
                return {
                    'status': 'error',
                    'message': f'Failed to fetch news for {symbol}'
                }
            
            logger.info(f"Found {len(feed.entries)} raw entries for {symbol}")
            
            articles = []
            articles_stored = 0
            storage_failures = 0
            news_items_to_store = []
            
            for entry in feed.entries:
                try:
                    # Parse date with multiple format attempts
                    date_formats = [
                        '%a, %d %b %Y %H:%M:%S %Z',  # GMT format
                        '%a, %d %b %Y %H:%M:%S %z',  # Timezone offset format
                        '%a, %d %b %Y %H:%M:%S'      # No timezone format
                    ]
                    
                    parsed_date = None
                    for fmt in date_formats:
                        try:
                            parsed_date = datetime.strptime(entry.published, fmt)
                            break
                        except ValueError:
                            continue
                    
                    if not parsed_date:
                        parsed_date = datetime.now()
                        logger.warning(f"Couldn't parse date for article: {entry.title[:30]}..., using current time")
                    
                    # Only include articles from last 3 days
                    if datetime.now() - parsed_date > timedelta(days=3):
                        logger.debug(f"Skipping old article from {parsed_date.isoformat()}")
                        continue
                    
                    # Create article object
                    article = {
                        'title': entry.title,
                        'link': entry.link,
                        'published': parsed_date.isoformat(),
                        'source': entry.source.title if hasattr(entry, 'source') else 'Unknown',
                        'summary': entry.get('summary', ''),
                        'symbol': symbol,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    articles.append(article)
                    news_items_to_store.append(article)
                    
                except Exception as article_error:
                    logger.error(f"Error processing article: {str(article_error)}")
                    continue
            
            # Store all articles in vector database at once
            if news_items_to_store:
                try:
                    logger.info(f"Storing {len(news_items_to_store)} articles in VectorDB")
                    success = self.vector_service.store_news(news_items_to_store)
                    
                    if success:
                        articles_stored = len(news_items_to_store)
                        logger.info(f"Successfully stored {articles_stored} articles in VectorDB")
                    else:
                        storage_failures = len(news_items_to_store)
                        logger.error(f"Failed to store articles in VectorDB - returned False")
                except Exception as storage_error:
                    storage_failures = len(news_items_to_store)
                    logger.error(f"Exception while storing articles in VectorDB: {str(storage_error)}")
            
            # Update cache
            self.news_cache[symbol] = (datetime.now(), articles)
            
            logger.info(f"News fetch summary for {symbol}: {len(articles)} articles found, {articles_stored} stored in VectorDB, {storage_failures} storage failures")
            
            return {
                'status': 'success',
                'data': articles,
                'message': f'News fetched for {symbol}: {articles_stored} of {len(articles)} articles stored in VectorDB'
            }
            
        except Exception as e:
            logger.error(f"Error in get_company_news for {symbol}: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }

    def fetch_all_tech_news(self) -> Dict:
        """Fetch news for all tech companies"""
        try:
            all_results = []
            for symbol in self.TRACKED_COMPANIES:
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
                'message': f'News fetched for {len(self.TRACKED_COMPANIES)} companies'
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
            logger.info(f"SEMANTIC-SEARCH: Performing semantic search for query: '{query}' symbol: '{symbol}' limit: {limit}")
            similar_news = self.vector_service.search_similar_news(query, symbol, limit)
            
            logger.info(f"SEMANTIC-SEARCH: Found {len(similar_news)} semantically similar articles")
            if len(similar_news) > 0:
                logger.info(f"SEMANTIC-SEARCH: First result title: '{similar_news[0].get('title', 'No title')}', published: {similar_news[0].get('published', 'Unknown date')}")
                
                # Log all article titles and dates for debugging
                for i, article in enumerate(similar_news):
                    logger.info(f"SEMANTIC-SEARCH: Result #{i+1}: '{article.get('title', 'No title')}', published: {article.get('published', 'Unknown date')}")
            else:
                logger.warning(f"SEMANTIC-SEARCH: No results found for semantic search")
            
            
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

    def get_company_social_media_data(self, symbol: str) -> Dict:
        """Fetch social media data for a company"""
        try:
            # Check if Reddit credentials are available
            if not os.getenv('REDDIT_CLIENT_ID') or not os.getenv('REDDIT_CLIENT_SECRET'):
                logger.warning("Reddit credentials not configured. Skipping Reddit data fetch.")
                return {
                    'status': 'success',
                    'data': {
                        'posts': [],
                        'sentiment_summary': {
                            'post_count': 0,
                            'comment_count': 0,
                            'average_post_polarity': 0,
                            'average_post_subjectivity': 0,
                            'average_comment_polarity': 0,
                            'average_comment_subjectivity': 0
                        }
                    },
                    'message': 'Reddit credentials not configured. Please set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET environment variables.'
                }
            
            # Search for posts
            posts = []
            for post in self.reddit.subreddit("all").search(f"{symbol} stock", limit=10):
                # Get top 3 comments for each post
                comments = []
                post.comments.replace_more(limit=0)
                for comment in post.comments.list()[:3]:
                    comments.append({
                        'text': comment.body,
                        'score': comment.score
                    })
                
                posts.append({
                    'title': post.title,
                    'url': post.url,
                    'score': post.score,
                    'created_utc': post.created_utc,
                    'comments': comments
                })
            
            # Analyze sentiment for real data
            analysis_result = self.analyze_sentiment(posts)
            return {
                'status': 'success',
                'data': analysis_result['data'],
                'message': f'Social media data fetched for {symbol}'
            }
        except Exception as e:
            logger.error(f"Error in social media data fetch for {symbol}: {str(e)}")
            return {
                'status': 'success',
                'data': {
                    'posts': [],
                    'sentiment_summary': {
                        'post_count': 0,
                        'comment_count': 0,
                        'average_post_polarity': 0,
                        'average_post_subjectivity': 0,
                        'average_comment_polarity': 0,
                        'average_comment_subjectivity': 0
                    }
                },
                'message': f'No social media data available: {str(e)}'
            }

    def analyze_sentiment(self, posts: List[Dict]) -> Dict:
        """Perform sentiment analysis on fetched posts and comments"""
        try:
            # Initialize variables
            total_posts = len(posts)
            total_comments = 0
            analyzed_posts = []
            
            if total_posts == 0:
                return {
                    'status': 'success',
                    'data': {
                        'posts': [],
                        'sentiment_summary': {
                            'post_count': 0,
                            'comment_count': 0,
                            'average_post_polarity': 0,
                            'average_post_subjectivity': 0,
                            'average_comment_polarity': 0,
                            'average_comment_subjectivity': 0
                        }
                    },
                    'message': 'No posts to analyze'
                }
            
            # Initialize sentiment accumulators
            total_post_polarity = 0
            total_post_subjectivity = 0
            total_comment_polarity = 0
            total_comment_subjectivity = 0
            
            for post in posts:
                # Analyze post title
                post_sentiment = TextBlob(post['title']).sentiment
                total_post_polarity += post_sentiment.polarity
                total_post_subjectivity += post_sentiment.subjectivity
                
                # Analyze comments
                analyzed_comments = []
                for comment in post['comments']:
                    comment_sentiment = TextBlob(comment['text']).sentiment
                    total_comment_polarity += comment_sentiment.polarity
                    total_comment_subjectivity += comment_sentiment.subjectivity
                    
                    analyzed_comments.append({
                        'text': comment['text'],
                        'score': comment['score'],
                        'sentiment': {
                            'polarity': comment_sentiment.polarity,
                            'subjectivity': comment_sentiment.subjectivity
                        }
                    })
                
                analyzed_posts.append({
                    'title': post['title'],
                    'url': post['url'],
                    'score': post['score'],
                    'created_utc': post['created_utc'],
                    'sentiment': {
                        'polarity': post_sentiment.polarity,
                        'subjectivity': post_sentiment.subjectivity
                    },
                    'comments': analyzed_comments
                })
            
            # Calculate average sentiment
            if total_posts > 0:
                avg_polarity = total_post_polarity / total_posts
                avg_subjectivity = total_post_subjectivity / total_posts
                
                # Count total comments
                total_comments = sum(len(post['comments']) for post in analyzed_posts)
                if total_comments > 0:
                    # Calculate average comment sentiment
                    avg_comment_polarity = total_comment_polarity / total_comments
                    avg_comment_subjectivity = total_comment_subjectivity / total_comments
                else:
                    avg_comment_polarity = 0
                    avg_comment_subjectivity = 0
            else:
                avg_polarity = 0
                avg_subjectivity = 0
                avg_comment_polarity = 0
                avg_comment_subjectivity = 0
            
            return {
                'status': 'success',
                'data': {
                    'posts': analyzed_posts,
                    'sentiment_summary': {
                        'post_count': total_posts,
                        'comment_count': total_comments,
                        'average_post_polarity': avg_polarity,
                        'average_post_subjectivity': avg_subjectivity,
                        'average_comment_polarity': avg_comment_polarity,
                        'average_comment_subjectivity': avg_comment_subjectivity
                    }
                },
                'message': 'Sentiment analysis completed'
            }
        except Exception as e:
            logger.error(f"Error in sentiment analysis: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }

    def get_all_news(self, symbols: List[str]) -> Dict:
        """Fetch news for multiple companies"""
        all_news = {}
        for symbol in symbols:
            result = self.get_company_news(symbol)
            if result['status'] == 'success':
                all_news[symbol] = result['data']
        
        return {
            'status': 'success',
            'data': all_news,
            'message': f'News fetched for {len(symbols)} companies'
        }

    def _initialize_collections(self):
        """Initialize ChromaDB collections if they don't exist"""
        try:
            logger.info("Initializing ChromaDB collections")
            
            # Initialize client if needed
            if not hasattr(self, 'client') or not self.client:
                try:
                    import chromadb
                    logger.info(f"Creating ChromaDB client, version: {chromadb.__version__}")
                    self.client = chromadb.PersistentClient(path="./chromadb")
                except ImportError:
                    logger.error("ChromaDB is not installed. Please install with: pip install chromadb")
                    return False
                except Exception as client_error:
                    logger.error(f"Error creating ChromaDB client: {str(client_error)}")
                    return False
            
            # Initialize news collection
            try:
                # Try to get existing collection
                self.news_collection = self.client.get_collection("news_articles")
                logger.info("Retrieved existing news_collection")
            except Exception as collection_error:
                logger.info(f"Creating new news_collection: {str(collection_error)}")
                try:
                    # Create new collection
                    self.news_collection = self.client.create_collection(
                        name="news_articles",
                        metadata={"hnsw:space": "cosine"}
                    )
                    logger.info("Successfully created news_collection")
                except Exception as create_error:
                    logger.error(f"Failed to create news_collection: {str(create_error)}")
                    return False
                
            return True
        except Exception as e:
            logger.error(f"Error in _initialize_collections: {str(e)}")
            return False 