from flask import Blueprint, request, jsonify
import logging
from app.services.finnhub_service import FinnhubService

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

finnhub_bp = Blueprint('finnhub', __name__)
finnhub_service = FinnhubService()

@finnhub_bp.route('/fetch-news/<symbol>', methods=['GET'])
def fetch_company_news(symbol):
    """Fetch news from Finnhub for a specific company and store in VectorDB"""
    try:
        # Get the number of weeks to look back (default is 3)
        weeks = request.args.get('weeks', default=3, type=int)
        
        # Call the service method
        result = finnhub_service.fetch_company_news(symbol, weeks)
        
        # Return the result
        if result['status'] == 'error':
            return jsonify(result), 500
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in fetch_company_news route: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@finnhub_bp.route('/fetch-all-news', methods=['GET'])
def fetch_all_company_news():
    """Fetch news for a list of predefined companies"""
    try:
        # Call the service method
        result = finnhub_service.fetch_all_company_news()
        
        # Return the result
        if result['status'] == 'error':
            return jsonify(result), 500
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in fetch_all_company_news route: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@finnhub_bp.route('/stored-news/<symbol>', methods=['GET'])
def get_stored_finnhub_news(symbol):
    """Get stored Finnhub news for a specific company"""
    try:
        # Get the limit parameter (default is 10)
        limit = request.args.get('limit', default=10, type=int)
        
        # Call the service method
        result = finnhub_service.get_stored_finnhub_news(symbol, limit)
        
        # Return the result
        if result['status'] == 'error':
            return jsonify(result), 500
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in get_stored_finnhub_news route: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
