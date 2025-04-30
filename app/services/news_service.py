import feedparser
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Optional
from app.services.vector_service import VectorService
from textblob import TextBlob
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set logging level to INFO to reduce debug noise
logging.basicConfig(level=logging.INFO)
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
        self.news_cache = {}
        logger.info("NewsService initialized with VectorService")

    def get_company_news(self, symbol: str) -> Dict:
        """Fetch news articles for a company"""
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
            feed = feedparser.parse(f'https://news.google.com/rss/search?q={symbol}+stock&hl=en-US&gl=US&ceid=US:en')
            
            if feed.status != 200:
                return {
                    'status': 'error',
                    'message': f'Failed to fetch news for {symbol}'
                }
            
            articles = []
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
                    
                    # Only include articles from last 3 days
                    if datetime.now() - parsed_date > timedelta(days=3):
                        continue
                    
                    articles.append({
                        'title': entry.title,
                        'link': entry.link,
                        'published': parsed_date.isoformat(),
                        'source': entry.source.title if hasattr(entry, 'source') else 'Unknown'
                    })
                    
                    # Store in vector database
                    self.vector_service.store_news(symbol, entry.title, entry.link, parsed_date)
                    
                except Exception as e:
                    continue
            
            # Update cache
            self.news_cache[symbol] = (datetime.now(), articles)
            
            return {
                'status': 'success',
                'data': articles,
                'message': f'News fetched for {symbol}'
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