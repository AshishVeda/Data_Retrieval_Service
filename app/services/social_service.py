import praw
import json
import os
import logging
from datetime import datetime, timedelta
from textblob import TextBlob
from typing import Dict, List, Any, Optional
import math
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set logging level to INFO to reduce debug noise
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SocialService:
    def __init__(self):
        """Initialize the service with Reddit API credentials"""
        # Check if Reddit credentials exist
        self.has_credentials = all([
            os.environ.get('REDDIT_CLIENT_ID'),
            os.environ.get('REDDIT_CLIENT_SECRET'),
            os.environ.get('REDDIT_USER_AGENT')
        ])
        
        if self.has_credentials:
            # Initialize the Reddit client
            self.reddit = praw.Reddit(
                client_id=os.environ.get('REDDIT_CLIENT_ID'),
                client_secret=os.environ.get('REDDIT_CLIENT_SECRET'),
                user_agent=os.environ.get('REDDIT_USER_AGENT')
            )
            logger.info("Reddit client initialized")
        else:
            logger.warning("Reddit credentials not set")
            self.reddit = None

    def get_search_terms(self, symbol: str) -> List[str]:
        """
        Generate search terms for a given stock symbol.
        Default behavior is to search for the symbol and "$symbol".
        """
        company_names = {
            'AAPL': ['Apple', 'AAPL'],
            'MSFT': ['Microsoft', 'MSFT'],
            'GOOGL': ['Google', 'Alphabet', 'GOOGL'],
            'AMZN': ['Amazon', 'AMZN'],
            'META': ['Meta', 'Facebook', 'META'],
            'TSLA': ['Tesla', 'TSLA'],
            'NVDA': ['NVIDIA', 'NVDA'],
            'JPM': ['JPMorgan', 'JP Morgan', 'JPM'],
            'V': ['Visa', 'V stock'],
            'JNJ': ['Johnson & Johnson', 'JNJ'],
            'WMT': ['Walmart', 'WMT'],
            'PG': ['Procter & Gamble', 'P&G', 'PG stock'],
            'BAC': ['Bank of America', 'BAC'],
            'NFLX': ['Netflix', 'NFLX'],
            'DIS': ['Disney', 'DIS'],
        }
        
        # Generate search terms
        search_terms = [symbol, f"${symbol}"]
        
        # Add company name if available
        if symbol in company_names:
            search_terms.extend(company_names[symbol])
        
        return search_terms

    def fetch_reddit_posts(self, symbol: str, limit: int = 10) -> Dict[str, Any]:
        """
        Fetch recent posts from Reddit related to a specific stock symbol.
        If Reddit credentials are not available, returns mock data.
        """
        if not self.has_credentials or not self.reddit:
            logger.warning("Using mock data due to missing Reddit credentials")
            # Create mock posts for testing
            mock_posts = self._get_mock_posts(symbol)
            
            # Return analyzed sentiment data instead of just posts
            analyzed_data = self.analyze_sentiment(mock_posts)
            return {
                "posts": mock_posts, 
                "sentiment_summary": analyzed_data
            }
            
        try:
            # Get search terms for the symbol
            search_terms = self.get_search_terms(symbol)
            
            # Subreddits to search
            subreddits = ['stocks', 'investing', 'wallstreetbets']
            
            all_posts = []
            limit_per_search = math.ceil(limit / (len(search_terms) * len(subreddits)))
            
            # Search each subreddit with each search term
            for subreddit_name in subreddits:
                subreddit = self.reddit.subreddit(subreddit_name)
                
                for term in search_terms:
                    # Search for posts containing the term
                    search_results = subreddit.search(term, time_filter='week', limit=limit_per_search)
                    
                    for post in search_results:
                        # Skip duplicates
                        if any(p['id'] == post.id for p in all_posts):
                            continue
                            
                        # Process comments
                        comments = []
                        post.comments.replace_more(limit=0)  # Don't load MoreComments
                        for comment in list(post.comments)[:5]:  # Limit to 5 comments
                            comments.append({
                                'id': comment.id,
                                'text': comment.body,
                                'score': comment.score,
                                'created_utc': comment.created_utc
                            })
                        
                        # Add the post data
                        all_posts.append({
                            'id': post.id,
                            'title': post.title,
                            'url': f"https://www.reddit.com{post.permalink}",
                            'score': post.score,
                            'created_utc': post.created_utc,
                            'subreddit': post.subreddit.display_name,
                            'comments': comments
                        })
                        
                        if len(all_posts) >= limit:
                            break
                    
                    if len(all_posts) >= limit:
                        break
                        
                if len(all_posts) >= limit:
                    break
            
            logger.info(f"Found {len(all_posts)} relevant Reddit posts for {symbol}")
            
            # Analyze sentiment
            analyzed_data = self.analyze_sentiment(all_posts)
            
            return {
                "posts": all_posts, 
                "sentiment_summary": analyzed_data
            }
            
        except Exception as e:
            logger.error(f"Error fetching Reddit posts: {str(e)}")
            # Return empty result with zero sentiment values
            return {
                "posts": [],
                "sentiment_summary": {
                    "post_count": 0,
                    "comment_count": 0,
                    "avg_post_polarity": 0.0,
                    "avg_post_subjectivity": 0.0,
                    "avg_comment_polarity": 0.0,
                    "avg_comment_subjectivity": 0.0
                }
            }

    def analyze_sentiment(self, posts: List[Dict]) -> Dict[str, Any]:
        """
        Analyze sentiment of Reddit posts and comments.
        Returns a summary of sentiment analysis metrics.
        """
        if not posts:
            return {
                "post_count": 0,
                "comment_count": 0,
                "avg_post_polarity": 0.0,
                "avg_post_subjectivity": 0.0,
                "avg_comment_polarity": 0.0,
                "avg_comment_subjectivity": 0.0
            }
        
        # Extract text from posts and comments
        post_texts = [post['title'] for post in posts]
        
        comment_texts = []
        for post in posts:
            for comment in post.get('comments', []):
                comment_texts.append(comment['text'])
        
        # Calculate sentiment for posts
        post_sentiments = [TextBlob(text).sentiment for text in post_texts]
        post_polarities = [s.polarity for s in post_sentiments]
        post_subjectivities = [s.subjectivity for s in post_sentiments]
        
        avg_post_polarity = sum(post_polarities) / len(post_polarities) if post_polarities else 0
        avg_post_subjectivity = sum(post_subjectivities) / len(post_subjectivities) if post_subjectivities else 0
        
        # Calculate sentiment for comments
        comment_sentiments = [TextBlob(text).sentiment for text in comment_texts]
        comment_polarities = [s.polarity for s in comment_sentiments]
        comment_subjectivities = [s.subjectivity for s in comment_sentiments]
        
        avg_comment_polarity = sum(comment_polarities) / len(comment_polarities) if comment_polarities else 0
        avg_comment_subjectivity = sum(comment_subjectivities) / len(comment_subjectivities) if comment_subjectivities else 0
        
        # Add sentiment data to each post
        for i, post in enumerate(posts):
            post['sentiment'] = {
                'polarity': post_polarities[i],
                'subjectivity': post_subjectivities[i]
            }
            
            # Add sentiment to comments
            comment_index = 0
            for comment in post.get('comments', []):
                if comment_index < len(comment_sentiments):
                    comment['sentiment'] = {
                        'polarity': comment_polarities[comment_index],
                        'subjectivity': comment_subjectivities[comment_index]
                    }
                    comment_index += 1
        
        return {
            "post_count": len(posts),
            "comment_count": len(comment_texts),
            "avg_post_polarity": avg_post_polarity,
            "avg_post_subjectivity": avg_post_subjectivity,
            "avg_comment_polarity": avg_comment_polarity,
            "avg_comment_subjectivity": avg_comment_subjectivity
        }

    def _get_mock_posts(self, symbol: str) -> List[Dict]:
        """Generate mock posts for testing"""
        now = datetime.now()
        
        mock_posts = [
            {
                'id': f'mock_{symbol}_1',
                'title': f"{symbol} is looking bullish today with strong market indicators",
                'url': f"https://www.reddit.com/r/stocks/comments/mock_{symbol}_1",
                'score': 42,
                'created_utc': (now - timedelta(hours=4)).timestamp(),
                'subreddit': 'stocks',
                'comments': [
                    {
                        'id': f'comment_{symbol}_1_1',
                        'text': f"I agree! {symbol} has great potential in this market.",
                        'score': 15,
                        'created_utc': (now - timedelta(hours=3)).timestamp()
                    },
                    {
                        'id': f'comment_{symbol}_1_2',
                        'text': f"The latest earnings report for {symbol} exceeded expectations.",
                        'score': 8,
                        'created_utc': (now - timedelta(hours=2)).timestamp()
                    }
                ]
            },
            {
                'id': f'mock_{symbol}_2',
                'title': f"Should I invest in {symbol} at current prices?",
                'url': f"https://www.reddit.com/r/investing/comments/mock_{symbol}_2",
                'score': 28,
                'created_utc': (now - timedelta(days=1)).timestamp(),
                'subreddit': 'investing',
                'comments': [
                    {
                        'id': f'comment_{symbol}_2_1',
                        'text': f"I think {symbol} is overvalued right now, might be worth waiting.",
                        'score': 12,
                        'created_utc': (now - timedelta(hours=20)).timestamp()
                    },
                    {
                        'id': f'comment_{symbol}_2_2',
                        'text': f"Long term, {symbol} is a solid investment regardless of current price.",
                        'score': 17,
                        'created_utc': (now - timedelta(hours=19)).timestamp()
                    }
                ]
            },
            {
                'id': f'mock_{symbol}_3',
                'title': f"{symbol} technical analysis shows potential breakout",
                'url': f"https://www.reddit.com/r/wallstreetbets/comments/mock_{symbol}_3",
                'score': 56,
                'created_utc': (now - timedelta(days=2)).timestamp(),
                'subreddit': 'wallstreetbets',
                'comments': [
                    {
                        'id': f'comment_{symbol}_3_1',
                        'text': f"The RSI on {symbol} is looking very good right now.",
                        'score': 22,
                        'created_utc': (now - timedelta(days=2, hours=2)).timestamp()
                    },
                    {
                        'id': f'comment_{symbol}_3_2',
                        'text': f"I'm loading up on {symbol} calls for next month.",
                        'score': 31,
                        'created_utc': (now - timedelta(days=2, hours=1)).timestamp()
                    }
                ]
            }
        ]
        
        return mock_posts 