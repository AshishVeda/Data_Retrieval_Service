import praw
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Optional
from textblob import TextBlob
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class SocialService:
    def __init__(self):
        logger.info("SocialService initialized")
        # Initialize Reddit client with environment variables
        self.reddit = praw.Reddit(
            client_id=os.getenv('REDDIT_CLIENT_ID'),
            client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
            user_agent=os.getenv('REDDIT_USER_AGENT', 'StockAnalysisBot/1.0')
        )

    def fetch_reddit_posts(self, symbol: str) -> Dict:
        """Fetch Reddit posts and comments for a company"""
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

    def get_reddit_posts(self, symbol: str) -> Dict:
        """Main method to fetch and analyze social media data"""
        # Step 1: Fetch data
        fetch_result = self.fetch_reddit_posts(symbol)
        if fetch_result['status'] == 'error':
            return fetch_result
        
        # Step 2: Analyze sentiment
        analysis_result = self.analyze_sentiment(fetch_result['data']['posts'])
        return analysis_result 