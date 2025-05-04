from flask import Blueprint, request, jsonify, session
from app.services.stock_service import StockService
from app.services.news_service import NewsService
from app.services.social_service import SocialService
from app.services.llm_service import LLMService
from app.services.finnhub_service import FinnhubService
from app.services.chat_history_service import chat_history_service
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
from app.services.llm_endpoint import generate_prediction
from app.routes.user_routes import jwt_required  # Import the jwt_required decorator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

prediction_bp = Blueprint('prediction', __name__)

@prediction_bp.route('/query', methods=['POST'])
@jwt_required
def process_prediction_query():
    """Process user query for stock prediction"""
    try:
        # Get user ID from request.user (set by the jwt_required decorator)
        user_id = request.user['user_id']

        # Validate request
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No JSON data provided'
            }), 400

        symbol = data.get('symbol')
        user_query = data.get('user_query')

        if not symbol or not user_query:
            return jsonify({
                'status': 'error',
                'message': 'Symbol and query are required'
            }), 400

        # Initialize services
        stock_service = StockService()
        news_service = NewsService()
        social_service = SocialService()
        finnhub_service = FinnhubService()
        llm_service = LLMService()

        # Step 1: Data Fetching
        logger.info(f"Fetching data for {symbol}")
        
        # Fetch historical prices
        historical_data = stock_service.get_historical_prices(symbol)
        if historical_data['status'] == 'error':
            return jsonify(historical_data), 500

        # Fetch Reddit posts - note the SocialService now returns data directly, not with status wrapper
        reddit_data = social_service.fetch_reddit_posts(symbol)
        
        # Check for Finnhub news in ChromaDB - limit to 10 articles
        finnhub_news_data = finnhub_service.get_stored_finnhub_news(symbol, limit=10)
        
        # Check if we have enough recent Finnhub news data (at least covering the past 3 weeks)
        three_weeks_ago = (datetime.now() - timedelta(weeks=3)).isoformat()
        has_enough_data = False
        
        if finnhub_news_data['status'] == 'success' and finnhub_news_data['data']:
            # Check if we have data from 3 weeks ago
            dates = [item.get('published', '') for item in finnhub_news_data['data']]
            oldest_date = min(dates) if dates else ''
            
            if oldest_date and oldest_date <= three_weeks_ago:
                # We have data going back at least 3 weeks
                has_enough_data = True
            
        # If we don't have enough data, fetch fresh data from Finnhub
        if not has_enough_data:
            logger.info(f"Fetching fresh Finnhub news data for {symbol}")
            fetch_result = finnhub_service.fetch_company_news(symbol, weeks=3)
            
            if fetch_result['status'] == 'success':
                # Get the updated data from the database
                finnhub_news_data = finnhub_service.get_stored_finnhub_news(symbol, 10)
            else:
                logger.warning(f"Failed to fetch Finnhub news data")
        
        # Handle errors in Finnhub news fetching
        if finnhub_news_data['status'] == 'error':
            finnhub_news_data = {'status': 'success', 'data': []}

        # Step 2: Sentiment Analysis is now done within the fetch_reddit_posts method
        logger.info(f"Analyzing sentiment for {symbol}")
        
        # The sentiment data is already in the reddit_data
        sentiment_data = {
            'posts': reddit_data.get('posts', []),
            'sentiment_summary': reddit_data.get('sentiment_summary', {})
        }

        # Step 3: Prepare LLM Prompt with chat history
        logger.info(f"Generating prediction prompt for {symbol} with chat history")
        
        # Generate prompt with the data and include user ID for chat history
        prompt = llm_service.generate_prediction_prompt(
            {
                'symbol': symbol,
                'metadata': {
                    'raw_data': {
                        'historical': historical_data.get('data', {}),
                        'finnhub_news': finnhub_news_data.get('data', []),
                        'sentiment': sentiment_data
                    }
                }
            }, 
            user_query,
            user_id  # Pass the user_id for chat history
        )

        # Step 4: Call the LLM API to get a response
        logger.info(f"Calling LLM API for prediction")
        llm_response = generate_prediction(prompt)
        
        # Prepare response with metadata and LLM response
        response_data = {
            'prompt': prompt,
            'prediction': llm_response,
            'metadata': {
                'steps_completed': ['data_fetch', 'sentiment_analysis', 'prompt_generation', 'llm_prediction'],
                'timestamp': datetime.now().isoformat(),
                'raw_data': {
                    'historical': historical_data.get('data', {}),
                    'finnhub_news': finnhub_news_data.get('data', []),
                    'sentiment': sentiment_data
                }
            }
        }

        # Store the query and response in chat history
        try:
            # Store the actual LLM response in chat history
            chat_history_service.store_chat(
                user_id, 
                user_query, 
                llm_response,
                metadata={
                    'symbol': symbol,
                    'timestamp': datetime.now().isoformat()
                }
            )
            logger.info(f"Stored chat history for user {user_id}")
        except Exception as e:
            logger.error(f"Error storing chat history: {str(e)}")

        # Return LLM response and metadata
        return jsonify({
            'status': 'success',
            'data': response_data,
            'message': 'Prediction generated successfully'
        })
    except Exception as e:
        logger.error(f"Error in prediction query: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@prediction_bp.route('/chat-history', methods=['GET'])
@jwt_required
def get_chat_history():
    """Get chat history for the current user"""
    try:
        # Get user ID from request.user (set by the jwt_required decorator)
        user_id = request.user['user_id']
        
        # Get limit parameter (default to 10)
        limit = request.args.get('limit', default=10, type=int)
        
        # Get chat history
        result = chat_history_service.get_chat_history(user_id, limit)
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error retrieving chat history: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500 