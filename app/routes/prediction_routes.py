from flask import Blueprint, request, jsonify, session
from app.services.stock_service import StockService
from app.services.news_service import NewsService
from app.services.social_service import SocialService
from app.services.llm_service import LLMService
import logging
from typing import Dict, Optional
from datetime import datetime

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

prediction_bp = Blueprint('prediction', __name__)

@prediction_bp.route('/query', methods=['POST'])
def process_prediction_query():
    """Process user query for stock prediction"""
    try:
        # Debug session information
        logger.debug(f"Session data: {dict(session)}")
        logger.debug(f"Session ID: {session.get('_id')}")
        logger.debug(f"User ID in session: {session.get('user_id')}")
        
        # Check authentication
        if 'user_id' not in session:
            logger.warning("No user_id found in session")
            return jsonify({
                'status': 'error',
                'message': 'Authentication required. Please login first.'
            }), 401

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
        llm_service = LLMService()

        # Step 1: Data Fetching
        logger.info(f"Step 1: Fetching data for {symbol}")
        
        # Fetch historical prices
        historical_data = stock_service.get_historical_prices(symbol)
        if historical_data['status'] == 'error':
            return jsonify(historical_data), 500

        # Fetch Reddit posts
        reddit_data = social_service.fetch_reddit_posts(symbol)
        if reddit_data['status'] == 'error':
            return jsonify(reddit_data), 500

        # Fetch company news
        news_data = news_service.get_company_news(symbol)
        if news_data['status'] == 'error':
            return jsonify(news_data), 500

        # Step 2: Sentiment Analysis
        logger.info(f"Step 2: Analyzing sentiment for {symbol}")
        sentiment_data = social_service.analyze_sentiment(reddit_data['data']['posts'])
        if sentiment_data['status'] == 'error':
            return jsonify(sentiment_data), 500

        # Step 3: Prepare LLM Prompt
        logger.info(f"Step 3: Preparing LLM prompt for {symbol}")
        prompt_data = {
            'symbol': symbol,
            'historical_data': historical_data.get('data', {}),
            'news_data': news_data.get('data', []),
            'sentiment_data': sentiment_data.get('data', {}),
            'user_query': user_query
        }

        # Generate prompt
        prompt = llm_service.prepare_prompt(prompt_data)

        # Return prompt and metadata
        return jsonify({
            'status': 'success',
            'data': {
                'prompt': prompt,
                'metadata': {
                    'steps_completed': ['data_fetch', 'sentiment_analysis', 'prompt_generation'],
                    'timestamp': datetime.now().isoformat(),
                    'raw_data': {
                        'historical': historical_data.get('data', {}),
                        'news': news_data.get('data', []),
                        'sentiment': sentiment_data.get('data', {})
                    }
                }
            },
            'message': 'Prompt generated successfully'
        })
    except Exception as e:
        logger.error(f"Error in prediction query: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500 