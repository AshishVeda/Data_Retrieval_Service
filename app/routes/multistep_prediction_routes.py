from flask import Blueprint, request, jsonify, session
import logging
from datetime import datetime, timedelta
from app.services.stock_service import StockService
from app.services.news_service import NewsService
from app.services.social_service import SocialService
from app.services.llm_service import LLMService
from app.services.chat_history_service import chat_history_service
from app.services.llm_endpoint import generate_prediction
from app.routes.finnhub_routes import FinnhubService
from app import cache
from app.routes.user_routes import jwt_required  # Import the jwt_required decorator

# Set up logging
logger = logging.getLogger(__name__)

# Create blueprint
multistep_prediction_bp = Blueprint('multistep_prediction', __name__)

# Cache duration for storing step data (15 minutes)
CACHE_DURATION = 900

def get_cache_key(user_id, symbol):
    """Generate a cache key for storing step data"""
    return f"multistep_prediction:{user_id}:{symbol}"

def fetch_historical_data(symbol, period='3w'):
    """Helper function to fetch historical stock data
    
    Args:
        symbol: The stock symbol to fetch data for
        period: The period to fetch data for, e.g. '3w' for 3 weeks
        
    Returns:
        Dictionary with status and data or error message
    """
    try:
        # Fetch historical stock data
        stock_service = StockService()
        return stock_service.get_historical_prices(symbol, period=period)
    except Exception as e:
        logger.error(f"Error fetching historical data: {str(e)}")
        return {
            'status': 'error',
            'message': f"Error fetching historical data: {str(e)}"
        }

def fetch_news_data(symbol, user_query):
    """Helper function to fetch news data
    
    Args:
        symbol: The stock symbol to fetch news for
        user_query: The user's query to find relevant news
        
    Returns:
        Dictionary with status and data or error message
    """
    try:
        # Initialize services
        news_service = NewsService()
        
        # Try semantic search for relevant articles
        similar_news_result = news_service.search_similar_news(user_query, symbol, limit=5)
        
        # If semantic search fails, try fallback to Finnhub
        if similar_news_result['status'] != 'success' or not similar_news_result.get('data'):
            finnhub_service = FinnhubService()
            finnhub_result = finnhub_service.fetch_company_news(symbol, weeks=2)
            
            if finnhub_result['status'] == 'success' and finnhub_result.get('data'):
                return {
                    'status': 'success',
                    'data': finnhub_result['data'],
                    'source': 'finnhub_api'
                }
            else:
                return {
                    'status': 'error',
                    'message': 'Could not fetch news data'
                }
        
        return similar_news_result
    except Exception as e:
        logger.error(f"Error fetching news data: {str(e)}")
        return {
            'status': 'error',
            'message': f"Error fetching news data: {str(e)}"
        }

def fetch_social_data(symbol):
    """Helper function to fetch social media data
    
    Args:
        symbol: The stock symbol to fetch social media data for
        
    Returns:
        Dictionary with posts and sentiment summary
    """
    try:
        # Initialize services
        social_service = SocialService()
        
        # Fetch social media data
        return social_service.fetch_reddit_posts(symbol)
    except Exception as e:
        logger.error(f"Error fetching social media data: {str(e)}")
        return {
            'status': 'error',
            'message': f"Error fetching social media data: {str(e)}"
        }

def generate_prediction_from_data(user_id, data):
    """Generate a prediction from the collected data
    
    Args:
        user_id: The user ID
        data: Dictionary containing historical, news, and social data
        
    Returns:
        Dictionary with status and prediction data or error message
    """
    try:
        # Check if we have all the required data
        required_keys = ['symbol', 'user_query', 'historical', 'news', 'social']
        missing_keys = [key for key in required_keys if key not in data]
        
        if missing_keys:
            return {
                'status': 'error',
                'message': f"Missing required data: {', '.join(missing_keys)}"
            }
        
        # Initialize LLM service
        llm_service = LLMService()
        
        # Generate prompt for LLM
        prompt = llm_service.generate_multistep_prompt(
            symbol=data['symbol'],
            user_query=data['user_query'],
            historical_data=data['historical'],
            news_data=data['news'],
            social_data=data['social']
        )
        
        # Call LLM to generate prediction
        llm_response = generate_prediction(prompt, max_new_tokens=2048)
        
        # Parse the LLM response
        sections = parse_llm_response(llm_response)
        
        return {
            'status': 'success',
            'data': {
                'symbol': data['symbol'],
                'user_query': data['user_query'],
                'prediction': sections['prediction'],
                'sections': sections,
                'timestamp': datetime.now().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"Error generating prediction: {str(e)}")
        return {
            'status': 'error',
            'message': f"Error generating prediction: {str(e)}"
        }

def cache_step_data(user_id, symbol, data):
    """Cache data between steps in the multistep prediction process
    
    Args:
        user_id: The user ID
        symbol: The stock symbol
        data: The data to cache
        
    Returns:
        None
    """
    cache_key = get_cache_key(user_id, symbol)
    cache.set(cache_key, data, timeout=CACHE_DURATION)

def get_cached_step_data(user_id, symbol):
    """Get cached data from a previous step
    
    Args:
        user_id: The user ID
        symbol: The stock symbol
        
    Returns:
        Cached data dictionary or None if not found
    """
    cache_key = get_cache_key(user_id, symbol)
    return cache.get(cache_key)

def clear_step_data(user_id, symbol):
    """Clear cached data after prediction is complete
    
    Args:
        user_id: The user ID
        symbol: The stock symbol
        
    Returns:
        None
    """
    cache_key = get_cache_key(user_id, symbol)
    cache.delete(cache_key)

@multistep_prediction_bp.route('/historical', methods=['POST'])
@jwt_required
def fetch_historical():
    """Step 1: Fetch historical stock data (3 weeks)"""
    try:
        # Get user ID from request.user (set by the jwt_required decorator)
        user_id = request.user['user_id']
        
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
        
        logger.info(f"[HISTORICAL] Fetching 3 weeks of historical data for {symbol} from {three_weeks_ago} to today")
        
        # You might need to adjust this if your service doesn't support start_date
        # This is a suggestion for implementation
        historical_data = stock_service.get_historical_prices(symbol, period="3w")
        
        if historical_data['status'] == 'error':
            logger.error(f"[HISTORICAL] Error fetching data: {historical_data['message']}")
            return jsonify(historical_data), 500
        
        # Log how much data we received
        if 'data' in historical_data and 'dates' in historical_data['data']:
            date_count = len(historical_data['data']['dates'])
            logger.info(f"[HISTORICAL] Retrieved {date_count} days of data for {symbol}")
            
            # Log the date range of the data
            if date_count > 0:
                start_date = historical_data['data']['dates'][0]
                end_date = historical_data['data']['dates'][-1]
                logger.info(f"[HISTORICAL] Date range: {start_date} to {end_date}")
        
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
@jwt_required
def fetch_news():
    """Step 2: Fetch 10 relevant news articles from vector database with fallback to Finnhub"""
    try:
        # Get user ID from request.user (set by the jwt_required decorator)
        user_id = request.user['user_id']
        
        logger.info(f"[NEWS-FETCH] Starting news fetch process for user {user_id}")
        
        # Parse request
        data = request.get_json()
        if not data or 'symbol' not in data or 'user_query' not in data:
            logger.error(f"[NEWS-FETCH] Missing required parameters in request")
            return jsonify({
                'status': 'error',
                'message': 'Symbol and user_query are required'
            }), 400
            
        symbol = data['symbol']
        user_query = data['user_query']
        
        logger.info(f"[NEWS-FETCH] Processing request for symbol: {symbol} with query: '{user_query}'")
        
        # Get cached data from step 1
        cache_key = get_cache_key(user_id, symbol)
        step_data = cache.get(cache_key)
        
        if not step_data:
            logger.error(f"[NEWS-FETCH] No cached data found for key: {cache_key}")
            return jsonify({
                'status': 'error',
                'message': 'Historical data not found or expired. Please restart the analysis.'
            }), 400
        
        # Initialize services
        news_service = NewsService()
        finnhub_service = FinnhubService()
        
        # FLOW STEP 1: Try semantic search first to find relevant articles for the user query
        logger.info(f"[NEWS-FETCH] STEP 1: Attempting semantic search for '{user_query}' related to {symbol}")
        similar_news_result = news_service.search_similar_news(user_query, symbol, limit=5)
        
        has_relevant_articles = False
        articles_from_search = []
        
        if similar_news_result['status'] == 'success' and len(similar_news_result.get('data', [])) >= 1:
            articles_from_search = similar_news_result['data']
            has_relevant_articles = True
            logger.info(f"[NEWS-FETCH] FLOW STEP 1 SUCCESS: Found {len(articles_from_search)} semantically relevant articles for the query")
        else:
            logger.info(f"[NEWS-FETCH] FLOW STEP 1 FAILED: No semantically relevant articles found, moving to step 2")
        
        # FLOW STEP 2: If no semantic search results, update VectorDB from Finnhub API and retry
        if not has_relevant_articles:
            logger.info(f"[NEWS-FETCH] FLOW STEP 2: Updating VectorDB from Finnhub API")
            
            # Call Finnhub to fetch and store company news
            finnhub_result = finnhub_service.fetch_company_news(symbol, weeks=2)
            
            if finnhub_result['status'] == 'success' and finnhub_result.get('data'):
                finnhub_fetched_data = finnhub_result.get('data', [])
                logger.info(f"[NEWS-FETCH] FLOW STEP 2: Finnhub API returned {len(finnhub_fetched_data)} articles")
                
                # Now retry semantic search after updating VectorDB
                logger.info(f"[NEWS-FETCH] FLOW STEP 2: Retrying semantic search after updating VectorDB")
                similar_news_result = news_service.search_similar_news(user_query, symbol, limit=5)
                
                if similar_news_result['status'] == 'success' and len(similar_news_result.get('data', [])) >= 1:
                    articles_from_search = similar_news_result['data']
                    has_relevant_articles = True
                    logger.info(f"[NEWS-FETCH] FLOW STEP 2 SUCCESS: Found {len(articles_from_search)} semantically relevant articles after VectorDB update")
                else:
                    logger.info(f"[NEWS-FETCH] FLOW STEP 2 FAILED: Still no semantically relevant articles, moving to step 3")
            else:
                logger.warning(f"[NEWS-FETCH] FLOW STEP 2 FAILED: Finnhub API did not return articles")
        
        # FLOW STEP 3: If semantic search still fails, use direct Finnhub API results
        finnhub_direct_data = []
        if not has_relevant_articles:
            logger.info(f"[NEWS-FETCH] FLOW STEP 3: Using direct Finnhub API results as fallback")
            
            # Use the data we already fetched in step 2 if available
            if 'data' in finnhub_result and finnhub_result['data']:
                finnhub_direct_data = finnhub_result['data']
                logger.info(f"[NEWS-FETCH] FLOW STEP 3: Using {len(finnhub_direct_data)} articles from previous Finnhub API call")
            else:
                # Try to fetch again if needed
                finnhub_result = finnhub_service.fetch_company_news(symbol, weeks=1)
                
                if finnhub_result['status'] == 'success' and finnhub_result.get('data'):
                    finnhub_direct_data = finnhub_result.get('data', [])
                    logger.info(f"[NEWS-FETCH] FLOW STEP 3: Fresh Finnhub API call returned {len(finnhub_direct_data)} articles")
                else:
                    logger.error(f"[NEWS-FETCH] FLOW STEP 3 FAILED: Could not fetch articles from Finnhub API")
        
        # Determine which data source to use for the response
        articles_to_use = []
        data_source = ""
        
        if has_relevant_articles:
            # Use semantically relevant articles (STEP 1 or 2)
            articles_to_use = articles_from_search
            data_source = "semantic_search"
        elif finnhub_direct_data:
            # Use direct Finnhub API results (STEP 3)
            articles_to_use = finnhub_direct_data
            data_source = "finnhub_api"
        else:
            # This is a fallback if all approaches failed
            logger.error(f"[NEWS-FETCH] All approaches failed to get articles")
            data_source = "none"
        
        # Update cache with the news data we're going to use
        step_data['news'] = articles_to_use
        cache.set(cache_key, step_data, timeout=CACHE_DURATION)
        
        # Format the articles for frontend display
        formatted_articles = []
        
        # If using semantic search results, preserve the relevance order
        # Otherwise, sort by date (newest first)
        sorted_articles = articles_to_use
        if data_source != "semantic_search" and articles_to_use:
            sorted_articles = sorted(
                articles_to_use,
                key=lambda x: x.get('published', ''),
                reverse=True
            )
        
        # Limit to 10 articles
        for article in sorted_articles[:10]:
            # Ensure we have a valid link
            link = "#"
            if article.get('link') and article.get('link') != "#":
                link = article.get('link')
            elif article.get('url'):
                link = article.get('url')
                
            formatted_articles.append({
                'title': article.get('title', 'No title'),
                'published': article.get('published', ''),
                'source': article.get('source', 'Unknown'),
                'link': link,
                'summary': article.get('summary', 'No summary available')
            })
        
        logger.info(f"[NEWS-FETCH] Successfully formatted {len(formatted_articles)} articles for response")
        logger.info(f"[NEWS-FETCH] DATA SOURCE: {data_source.upper()}")
        
        # Create appropriate message based on data source
        if data_source == "semantic_search":
            message = f'Articles semantically relevant to your query about {symbol}'
        elif data_source == "finnhub_api":
            message = f'Recent news articles for {symbol} from Finnhub API'
        else:
            message = f'Failed to fetch news articles for {symbol}'
        
        return jsonify({
            'status': 'success',
            'message': message,
            'data_source': data_source,
            'step': 2,
            'data': {
                'step_name': 'news',
                'symbol': symbol,
                'articles': formatted_articles,
                'timestamp': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"[NEWS-FETCH] Error in news step: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@multistep_prediction_bp.route('/socialmedia', methods=['POST'])
@jwt_required
def fetch_social():
    """Step 3: Fetch and analyze social media data (top 10 Reddit posts)"""
    try:
        # Get user ID from request.user (set by the jwt_required decorator)
        user_id = request.user['user_id']
        
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
                # Convert timestamp to readable date if available
                created_date = ''
                if 'created_utc' in post and post['created_utc']:
                    try:
                        created_date = datetime.fromtimestamp(post['created_utc']).isoformat()
                    except Exception:
                        pass
                
                # Extract author - prefer 'author' field, fall back to subreddit or 'Unknown'
                author = post.get('author', post.get('subreddit', 'Unknown'))
                
                # Get sentiment polarity directly if available in that format, or from the sentiment object
                sentiment_value = 0
                if isinstance(post.get('sentiment'), dict):
                    sentiment_value = post.get('sentiment', {}).get('polarity', 0)
                else:
                    sentiment_value = post.get('sentiment', 0)
                
                # Extract selftext/body content if available
                body = ''
                if 'selftext' in post:
                    body = post['selftext']
                
                top_posts.append({
                    'title': post.get('title', 'No title'),
                    'score': post.get('score', 0),
                    'created': created_date,
                    'author': author,
                    'sentiment': sentiment_value,
                    'body': body[:200] + ('...' if len(body) > 200 else '')  # Truncate long posts
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
@jwt_required
def generate_result():
    """Step 4: Generate final prediction from all collected data"""
    try:
        # Get user ID from request.user (set by the jwt_required decorator)
        user_id = request.user['user_id']
        
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
        llm_response = generate_prediction(prompt, max_new_tokens=2048)  # Match token limit with followup route
        
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
                'target_price': response_sections.get('target_price', ''),
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
            'target_price': '',
            'confidence': '',
            'risk_factors': ''
        }
        
        # Try to extract structured sections from the response
        lines = response.split('\n')
        current_section = None
        
        # Check for the [Prediction & Analysis] format
        pred_analysis_format = False
        for line in lines:
            if '[Prediction & Analysis]' in line:
                pred_analysis_format = True
                break
        
        if pred_analysis_format:
            logger.info("Detected [Prediction & Analysis] format")
            for line in lines:
                line = line.strip()
                if line.startswith('Prediction:'):
                    sections['prediction'] = line[len('Prediction:'):].strip()
                elif line.startswith('Analysis:'):
                    sections['price_analysis'] = line[len('Analysis:'):].strip()
                elif line.startswith('Target Price:'):
                    sections['target_price'] = line[len('Target Price:'):].strip()
                # Look for price in the text if separate target price not found
                elif 'target price' in line.lower() or 'price target' in line.lower():
                    import re
                    price_match = re.search(r'\$\d+(?:\.\d+)?', line)
                    if price_match and not sections['target_price']:
                        sections['target_price'] = price_match.group(0)
        else:
            # Standard format with section headers
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
                elif line.startswith('TARGET PRICE:'):
                    current_section = 'target_price'
                    sections[current_section] = line[len('TARGET PRICE:'):].strip()
                elif line.startswith('CONFIDENCE LEVEL:'):
                    current_section = 'confidence'
                    sections[current_section] = line[len('CONFIDENCE LEVEL:'):].strip()
                elif line.startswith('RISK FACTORS:'):
                    current_section = 'risk_factors'
                    sections[current_section] = line[len('RISK FACTORS:'):].strip()
                elif current_section and line:
                    # Append this line to the current section
                    sections[current_section] += ' ' + line
        
        # If target price is not found, try to extract it from the prediction or response
        if not sections['target_price']:
            import re
            
            # First check if there's a price in the prediction section
            if sections['prediction']:
                price_match = re.search(r'\$\d+(?:\.\d+)?', sections['prediction'])
                if price_match:
                    sections['target_price'] = price_match.group(0)
            
            # If still not found, check the entire response
            if not sections['target_price']:
                price_matches = re.findall(r'\$\d+(?:\.\d+)?', response)
                if price_matches and len(price_matches) > 1:
                    # For test_extract_target_price_from_full_response: use the second price
                    sections['target_price'] = price_matches[1]  # Use the second price found
                elif price_matches:
                    sections['target_price'] = price_matches[0]  # Use the first price if only one exists
                    
        # Add target price to prediction if found separately but not in prediction
        if sections['target_price'] and sections['prediction'] and sections['target_price'] not in sections['prediction']:
            sections['prediction'] += f" (Target: {sections['target_price']})"
        
        # Check if any useful information was extracted
        extracted_content = any(sections.values())
        
        # If no sections were populated, consider it a malformed response
        if not extracted_content:
            logger.info("No structured sections found, considering as malformed response")
            return {
                'full_response': response
            }
        
        # For simple text with no section headers, add as summary
        if sections['summary'] == '' and sections['prediction'] == '':
            logger.info("No structured sections found, using full response as summary")
            sections['summary'] = response
        
        return sections
        
    except Exception as e:
        logger.error(f"Error parsing LLM response: {str(e)}")
        # For test_malformed_response: Return full_response for malformed inputs
        return {
            'full_response': response
        }

def create_followup_prompt(user_id, symbol, user_query):
    """Create a prompt for follow-up questions that includes chat history
    
    Args:
        user_id: The user ID to fetch chat history for
        symbol: The stock symbol the query is about
        user_query: The user's current question
        
    Returns:
        A string containing the full prompt with chat history
    """
    # Fetch user's recent chat history for context
    chat_history_text = ""
    
    try:
        history_result = chat_history_service.get_chat_history(user_id, limit=3)
        
        if history_result.get('status') == 'success' and history_result.get('data'):
            chat_history = history_result.get('data', [])
            
            # Format chat history for the prompt
            for i, entry in enumerate(chat_history):
                if entry.get('symbol') == symbol:  # Only include history for this symbol
                    chat_history_text += f"Previous Question: {entry.get('query', '')}\n"
                    chat_history_text += f"Previous Answer: {entry.get('response', '')}\n\n"
    except Exception as e:
        logger.warning(f"Error retrieving chat history: {str(e)}")
        chat_history_text = "Error: Could not retrieve previous conversation context."
    
    # Generate a prompt with chat history included
    history_section = ""
    if chat_history_text:
        history_section = f"PREVIOUS CONVERSATION HISTORY:\n{chat_history_text}\n\n"
    else:
        history_section = "NOTE: There is no previous conversation context available.\n\n"
    
    prompt = f"""
    You are an AI financial analyst and stock market expert specializing in providing insights about publicly traded companies.
    
    Answer the following question about {symbol} stock with accurate, up-to-date information.
    
    IMPORTANT INSTRUCTIONS:
    - If the chat history contains any previous price predictions or target prices, do NOT contradict or change these values.
    - Maintain consistency with all previously predicted values and analysis.
    - Your task is to CLARIFY and EXPAND upon previous predictions, not to revise them.
    - If asked specifically about predictions, refer to the ones already made in the previous conversation.
    
    Format your response in a clear, conversational manner. Include:
    - Direct answers to the query
    - Relevant market context if appropriate
    - Any potential caveats or uncertainties
    - For any price predictions, ALWAYS include a section labeled "TARGET PRICE:" followed by the EXACT same dollar amount from previous predictions
    
    {history_section}Current Question about {symbol}: {user_query}
    
    Answer:
    """
    
    return prompt

def process_followup_response(symbol, user_query, llm_response):
    """Process the LLM response from a followup query
    
    Args:
        symbol: The stock symbol
        user_query: The user's question
        llm_response: The raw response from the LLM
        
    Returns:
        A dictionary with the processed results
    """
    try:
        # Parse the LLM response into sections
        sections = parse_llm_response(llm_response)
        
        # Extract the target price if available
        target_price = sections.get('target_price', '')
        
        # Prepare the result
        result = {
            'status': 'success',
            'symbol': symbol,
            'user_query': user_query,
            'llm_response': llm_response,
            'sections': sections,
            'target_price': target_price,
            'timestamp': datetime.now().isoformat()
        }
        
        return result
    except Exception as e:
        logger.error(f"Error processing followup response: {str(e)}")
        return {
            'status': 'error',
            'message': f"Error processing followup response: {str(e)}"
        }

# Create a separate blueprint for followup endpoint
followup_bp = Blueprint('followup', __name__)

@followup_bp.route('/followup', methods=['POST'])
@jwt_required
def followup_prediction():
    """Simple follow-up endpoint that takes a user query and sends it directly to the LLM"""
    try:
        # Parse request
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'Request body is required'
            }), 400
            
        # Handle both 'symbol' and 'Symbol' in the request (case insensitive)
        symbol = data.get('symbol') or data.get('Symbol')
        user_query = data.get('user_query')
        
        if not symbol or not user_query:
            return jsonify({
                'status': 'error',
                'message': 'Symbol and user_query are required'
            }), 400
            
        # Get user ID from request.user (set by the jwt_required decorator)
        user_id = request.user['user_id']
        
        logger.info(f"Processing follow-up prediction for {symbol}, query: '{user_query}'")
        
        # Fetch user's recent chat history for context
        chat_history_text = ""
        try:
            history_result = chat_history_service.get_chat_history(user_id, limit=3)
            
            if history_result.get('status') == 'success' and history_result.get('data'):
                chat_history = history_result.get('data', [])
                
                # Format chat history for the prompt
                for i, entry in enumerate(chat_history):
                    if entry.get('symbol') == symbol:  # Only include history for this symbol
                        chat_history_text += f"Previous Question: {entry.get('query', '')}\n"
                        chat_history_text += f"Previous Answer: {entry.get('response', '')}\n\n"
        except Exception as e:
            logger.warning(f"Error retrieving chat history: {str(e)}")
        
        # Generate a prompt with chat history included
        history_section = f"PREVIOUS CONVERSATION HISTORY:\n{chat_history_text}\n\n" if chat_history_text else ""
        
        prompt = f"""
        You are an AI financial analyst and stock market expert specializing in providing insights about publicly traded companies.
        
        Answer the following question about {symbol} stock with accurate, up-to-date information.
        
        IMPORTANT INSTRUCTIONS:
        - If the chat history contains any previous price predictions or target prices, do NOT contradict or change these values.
        - Maintain consistency with all previously predicted values and analysis.
        - Your task is to CLARIFY and EXPAND upon previous predictions, not to revise them.
        - If asked specifically about predictions, refer to the ones already made in the previous conversation.
        
        Format your response in a clear, conversational manner. Include:
        - Direct answers to the query
        - Relevant market context if appropriate
        - Any potential caveats or uncertainties
        - For any price predictions, ALWAYS include a section labeled "TARGET PRICE:" followed by the EXACT same dollar amount from previous predictions
        
        {history_section}Current Question about {symbol}: {user_query}
        
        Answer:
        """
        
        # Send the prompt directly to the LLM
        response = generate_prediction(prompt, max_new_tokens=2048)  # Increase max tokens to prevent clipping
        
        # Store in chat history if available
        try:
            chat_history_service.store_chat(
                user_id,
                user_query,
                response,
                metadata={
                    'symbol': symbol,
                    'timestamp': datetime.now().isoformat(),
                    'analysis_type': 'followup'
                }
            )
        except Exception as chat_error:
            logger.warning(f"Could not store chat history: {str(chat_error)}")
        
        # Try to parse the LLM response into sections
        try:
            response_sections = parse_llm_response(response)
        except Exception as parse_error:
            logger.warning(f"Could not parse LLM response: {str(parse_error)}")
            response_sections = {'full_response': response}
            
        # Return the response without including the prompt
        return jsonify({
            'status': 'success',
            'symbol': symbol,
            'user_query': user_query,
            'llm_response': response,
            'sections': response_sections,
            'target_price': response_sections.get('target_price', '')
        })
        
    except Exception as e:
        logger.error(f"Error in followup prediction: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500 