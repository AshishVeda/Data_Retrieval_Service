from flask import Blueprint, jsonify, request
from app.services.social_service import SocialService
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# ✅ Define Blueprint
social_bp = Blueprint('social', __name__)
social_service = SocialService()

@social_bp.route('/fetch/<symbol>', methods=['GET'])
def fetch_social_data(symbol: str):
    """Endpoint to fetch social media data"""
    try:
        logger.info(f"Fetching social media data for {symbol}")
        result = social_service.fetch_reddit_posts(symbol)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in fetch_social_data: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@social_bp.route('/analyze/<symbol>', methods=['GET'])
def analyze_sentiment(symbol: str):
    """Endpoint to analyze sentiment of fetched data"""
    try:
        logger.info(f"Analyzing sentiment for {symbol}")
        # First fetch the data
        fetch_result = social_service.fetch_reddit_posts(symbol)
        if fetch_result['status'] == 'error':
            return jsonify(fetch_result), 500
        
        # Then analyze the sentiment
        result = social_service.analyze_sentiment(fetch_result['data']['posts'])
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in analyze_sentiment: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@social_bp.route('/sentiment/<symbol>', methods=['GET'])
def get_social_sentiment(symbol: str):
    """Combined endpoint to fetch and analyze social media data"""
    try:
        logger.info(f"Getting social media sentiment for {symbol}")
        result = social_service.get_reddit_posts(symbol)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in get_social_sentiment: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500