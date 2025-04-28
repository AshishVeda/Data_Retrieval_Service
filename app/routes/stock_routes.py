from flask import Blueprint, request, jsonify
from app.services.stock_service import StockService
import yfinance as yf
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

stock_bp = Blueprint('stock', __name__)


@stock_bp.route('/search', methods=['GET'])
def search_stock():
    try:
        symbol = request.args.get('symbol')
        if not symbol:
            return jsonify({"error": "Stock symbol is required"}), 400

        stock = yf.Ticker(symbol)
        # print(stock.news)
        info = stock.info

        return jsonify({
            "name": info.get("shortName"),
            "symbol": symbol.upper(),
            "industry": info.get("industry")
        })
    except Exception as e:
        logger.error(f"Error in search_stock: {str(e)}")
        return jsonify({"error": str(e)}), 500


@stock_bp.route('/historical/<symbol>', methods=['GET'])
def get_historical_prices(symbol):
    """Get historical prices for a symbol"""
    try:
        period = request.args.get('period', '1y')
        logger.debug(f"Received request for {symbol} with period {period}")
        
        result = StockService.get_historical_prices(symbol, period)
        
        if result['status'] == 'error':
            return jsonify(result), 400
            
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in get_historical_prices: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Internal server error: {str(e)}'
        }), 500
