from flask import Blueprint, request, jsonify, session
import logging
from datetime import datetime, timedelta
from app.services.stock_service import StockService
from app.services.news_service import NewsService
from app.services.social_service import SocialService
from app.services.llm_service import LLMService
from app.services.chat_history_service import chat_history_service
from app.services.llm_endpoint import generate_prediction
from app import cache

# Set up logging
logger = logging.getLogger(__name__)

# Create blueprint
multistep_prediction_bp = Blueprint('multistep_prediction', __name__)

# Cache duration for storing step data (15 minutes)
CACHE_DURATION = 900

def get_cache_key(user_id, symbol):
    """Generate a cache key for storing step data"""
    return f"multistep_prediction:{user_id}:{symbol}"

@multistep_prediction_bp.route('/historical', methods=['POST'])
def fetch_historical():
    """Step 1: Fetch historical stock data (3 weeks)"""
    try:
        # Verify user authentication
        if 'user_id' not in session:
            return jsonify({
                'status': 'error',
                'message': 'Authentication required'
            }), 401
            
        user_id = session.get('user_id')
        
        # Parse request
        data = request.get_json()
        if not data or 'symbol' not in data or 'user_query' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Symbol and user_query are required'
            }), 400
            
        symbol = data['symbol']
        user_query = data['user_query']
        
        # Fetch historical stock data - 3 weeks
        stock_service = StockService()
        
        # Get data for past 3 weeks (21 days)
        three_weeks_ago = (datetime.now() - timedelta(days=21)).strftime('%Y-%m-%d')
        
        # You might need to adjust this if your service doesn't support start_date
        # This is a suggestion for implementation
        historical_data = stock_service.get_historical_prices(symbol, period="3w")
        
        if historical_data['status'] == 'error':
            return jsonify(historical_data), 500
        
        # Cache the data and query for subsequent steps
        cache_key = get_cache_key(user_id, symbol)
        step_data = {
            'symbol': symbol,
            'user_query': user_query,
            'timestamp': datetime.now().isoformat(),
            'historical': historical_data.get('data', {})
        }
        cache.set(cache_key, step_data, timeout=CACHE_DURATION)
        
        # Format a friendlier response for the frontend
        historical_prices = []
        
        # Structure the historical data response
        if 'dates' in historical_data.get('data', {}) and 'prices' in historical_data.get('data', {}):
            dates = historical_data['data']['dates']
            prices = historical_data['data']['prices']
            volumes = historical_data['data'].get('volumes', [])
            
            for i in range(min(len(dates), len(prices))):
                price_data = {
                    'date': dates[i],
                    'price': prices[i],
                }
                if i < len(volumes):
                    price_data['volume'] = volumes[i]
                historical_prices.append(price_data)
        
        return jsonify({
            'status': 'success',
            'message': f'Historical data fetched for {symbol} (last 3 weeks)',
            'step': 1,
            'data': {
                'step_name': 'historical',
                'symbol': symbol,
                'historical_prices': historical_prices,
                'timestamp': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error in historical data step: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@multistep_prediction_bp.route('/news', methods=['POST'])
def fetch_news():
    """Step 2: Fetch 10 relevant news articles from the last 3 weeks"""
    try:
        # Verify user authentication
        if 'user_id' not in session:
            return jsonify({
                'status': 'error',
                'message': 'Authentication required'
            }), 401
            
        user_id = session.get('user_id')
        
        # Parse request
        data = request.get_json()
        if not data or 'symbol' not in data or 'user_query' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Symbol and user_query are required'
            }), 400
            
        symbol = data['symbol']
        user_query = data['user_query']
        
        # Get cached data from step 1
        cache_key = get_cache_key(user_id, symbol)
        step_data = cache.get(cache_key)
        
        if not step_data:
            return jsonify({
                'status': 'error',
                'message': 'Historical data not found or expired. Please restart the analysis.'
            }), 400
        
        # Fetch news articles - the get_company_news method doesn't support limit or from_date parameters
        news_service = NewsService()
        news_data = news_service.get_company_news(symbol)
        
        # Update cache with news data
        step_data['news'] = news_data.get('data', [])
        cache.set(cache_key, step_data, timeout=CACHE_DURATION)
        
        # Format the articles for frontend display - take only the 10 most recent articles
        formatted_articles = []
        
        # Sort articles by date (newest first)
        articles = sorted(
            news_data.get('data', []),
            key=lambda x: x.get('published', ''),
            reverse=True
        )
        
        # Take only the 10 most recent ones
        for article in articles[:10]:
            formatted_articles.append({
                'title': article.get('title', 'No title'),
                'published': article.get('published', ''),
                'source': article.get('source', 'Unknown'),
                'link': article.get('link', '#'),
                'summary': article.get('summary', 'No summary available')
            })
        
        return jsonify({
            'status': 'success',
            'message': f'10 news articles fetched for {symbol} from the last 3 weeks',
            'step': 2,
            'data': {
                'step_name': 'news',
                'symbol': symbol,
                'articles': formatted_articles,
                'timestamp': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error in news step: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@multistep_prediction_bp.route('/socialmedia', methods=['POST'])
def fetch_social():
    """Step 3: Fetch and analyze social media data (top 10 Reddit posts)"""
    try:
        # Verify user authentication
        if 'user_id' not in session:
            return jsonify({
                'status': 'error',
                'message': 'Authentication required'
            }), 401
            
        user_id = session.get('user_id')
        
        # Parse request
        data = request.get_json()
        if not data or 'symbol' not in data or 'user_query' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Symbol and user_query are required'
            }), 400
            
        symbol = data['symbol']
        user_query = data['user_query']
        
        # Get cached data from previous steps
        cache_key = get_cache_key(user_id, symbol)
        step_data = cache.get(cache_key)
        
        if not step_data:
            return jsonify({
                'status': 'error',
                'message': 'Previous steps data not found or expired. Please restart the analysis.'
            }), 400
        
        # Fetch social media data
        social_service = SocialService()
        social_data = social_service.fetch_reddit_posts(symbol)
        
        # Update cache with social data
        step_data['social'] = social_data
        cache.set(cache_key, step_data, timeout=CACHE_DURATION)
        
        # Format the top 10 Reddit posts for frontend display
        top_posts = []
        
        # Get top 10 posts by score
        posts = social_data.get('posts', [])
        if posts:
            # Sort by score (highest first)
            sorted_posts = sorted(posts, key=lambda x: x.get('score', 0) if isinstance(x, dict) else 0, reverse=True)
            
            # Take top 10
            for post in sorted_posts[:10]:
                top_posts.append({
                    'title': post.get('title', 'No title'),
                    'score': post.get('score', 0),
                    'created': post.get('created', ''),
                    'author': post.get('author', 'Unknown'),
                    'sentiment': post.get('sentiment', {}).get('polarity', 0),
                    'body': post.get('body', '')[:200] + ('...' if len(post.get('body', '')) > 200 else '')  # Truncate long posts
                })
        
        # Get sentiment summary
        sentiment_summary = social_data.get('sentiment_summary', {})
        
        return jsonify({
            'status': 'success',
            'message': f'Top 10 Reddit posts fetched for {symbol}',
            'step': 3,
            'data': {
                'step_name': 'socialmedia',
                'symbol': symbol,
                'posts': top_posts,
                'sentiment_summary': sentiment_summary,
                'timestamp': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error in social media step: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@multistep_prediction_bp.route('/result', methods=['POST'])
def generate_result():
    """Step 4: Generate final prediction from all collected data"""
    try:
        # Verify user authentication
        if 'user_id' not in session:
            return jsonify({
                'status': 'error',
                'message': 'Authentication required'
            }), 401
            
        user_id = session.get('user_id')
        
        # Parse request
        data = request.get_json()
        if not data or 'symbol' not in data or 'user_query' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Symbol and user_query are required'
            }), 400
            
        symbol = data['symbol']
        user_query = data['user_query']
        
        # Get cached data from all previous steps
        cache_key = get_cache_key(user_id, symbol)
        step_data = cache.get(cache_key)
        
        if not step_data:
            return jsonify({
                'status': 'error',
                'message': 'Analysis data not found or expired. Please restart the analysis.'
            }), 400
        
        # Verify we have all required data
        if 'historical' not in step_data:
            return jsonify({
                'status': 'error',
                'message': 'Missing historical data. Please complete all steps.'
            }), 400
            
        if 'news' not in step_data:
            return jsonify({
                'status': 'error',
                'message': 'Missing news data. Please complete all steps.'
            }), 400
            
        if 'social' not in step_data:
            return jsonify({
                'status': 'error',
                'message': 'Missing social media data. Please complete all steps.'
            }), 400
        
        # Generate LLM prompt using the multi-step format
        llm_service = LLMService()
        prompt = llm_service.generate_multistep_prompt(
            data=step_data,
            user_query=user_query,
            user_id=user_id
        )
        
        logger.info(f"Generated multi-step prompt for {symbol}")
        
        # Call LLM to generate prediction
        llm_response = generate_prediction(prompt)
        
        logger.info(f"Got LLM response for {symbol}")
        
        # Store in chat history
        chat_history_service.store_chat(
            user_id,
            user_query,
            llm_response,
            metadata={
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'analysis_type': 'multi-step'
            }
        )
        
        # Clear cache after successful completion
        cache.delete(cache_key)
        
        # Construct sections from the LLM response for better frontend display
        response_sections = parse_llm_response(llm_response)
        
        return jsonify({
            'status': 'success',
            'message': f'Prediction generated for {symbol}',
            'step': 4,
            'data': {
                'step_name': 'result',
                'symbol': symbol,
                'user_query': user_query,
                'prediction': llm_response,
                'sections': response_sections,
                'timestamp': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error in result generation step: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

def parse_llm_response(response):
    """Parse the LLM response into sections for structured display"""
    try:
        sections = {
            'summary': '',
            'price_analysis': '',
            'news_impact': '',
            'sentiment_analysis': '',
            'prediction': '',
            'confidence': '',
            'risk_factors': ''
        }
        
        # Try to extract structured sections from the response
        lines = response.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            # Check if this is a section header
            if line.startswith('SUMMARY:'):
                current_section = 'summary'
                sections[current_section] = line[len('SUMMARY:'):].strip()
            elif line.startswith('PRICE ANALYSIS:'):
                current_section = 'price_analysis'
                sections[current_section] = line[len('PRICE ANALYSIS:'):].strip()
            elif line.startswith('NEWS IMPACT:'):
                current_section = 'news_impact'
                sections[current_section] = line[len('NEWS IMPACT:'):].strip()
            elif line.startswith('SENTIMENT ANALYSIS:'):
                current_section = 'sentiment_analysis'
                sections[current_section] = line[len('SENTIMENT ANALYSIS:'):].strip()
            elif line.startswith('PREDICTION:'):
                current_section = 'prediction'
                sections[current_section] = line[len('PREDICTION:'):].strip()
            elif line.startswith('CONFIDENCE LEVEL:'):
                current_section = 'confidence'
                sections[current_section] = line[len('CONFIDENCE LEVEL:'):].strip()
            elif line.startswith('RISK FACTORS:'):
                current_section = 'risk_factors'
                sections[current_section] = line[len('RISK FACTORS:'):].strip()
            elif current_section and line:
                # Append this line to the current section
                sections[current_section] += ' ' + line
        
        return sections
        
    except Exception as e:
        logger.error(f"Error parsing LLM response: {str(e)}")
        return {
            'full_response': response
        } 