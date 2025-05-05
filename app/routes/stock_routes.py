from flask import Blueprint, request, jsonify
from app.services.stock_service import StockService
from alpha_vantage.timeseries import TimeSeries
from alpha_vantage.fundamentaldata import FundamentalData
from app.config import Config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

stock_bp = Blueprint('stock', __name__)


@stock_bp.route('/search', methods=['GET'])
def search_stock():
    try:
        symbol = request.args.get('symbol')
        if not symbol:
            return jsonify({"error": "Stock symbol is required"}), 400

        # Use Alpha Vantage to get company overview
        fd = FundamentalData(key=Config.ALPHA_VANTAGE_API_KEY)
        data, _ = fd.get_company_overview(symbol)
        
        # Check if data was found
        if not data or 'Symbol' not in data:
            return jsonify({
                "error": f"No data found for symbol {symbol}"
            }), 404
            
        return jsonify({
            "name": data.get("Name"),
            "symbol": data.get("Symbol"),
            "industry": data.get("Industry"),
            "sector": data.get("Sector"),
            "description": data.get("Description"),
            "exchange": data.get("Exchange"),
            "country": data.get("Country"),
            "employees": data.get("FullTimeEmployees")
        })
    except Exception as e:
        logger.error(f"Error in search_stock: {str(e)}")
        return jsonify({"error": str(e)}), 500


@stock_bp.route('/historical/<symbol>', methods=['GET'])
def get_historical_prices(symbol):
    """Get historical prices for a symbol"""
    try:
        period = request.args.get('period', '1y')
        logger.info(f"Received request for {symbol} with period {period}")
        
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


@stock_bp.route('/company/<symbol>', methods=['GET'])
def get_company_data(symbol):
    """Get detailed company information"""
    try:
        fd = FundamentalData(key=Config.ALPHA_VANTAGE_API_KEY)
        
        # Get company overview
        overview, _ = fd.get_company_overview(symbol)
        
        # Get company income statement
        try:
            income, _ = fd.get_income_statement_annual(symbol)
            income_data = income.get('annualReports', [])
        except Exception as e:
            logger.warning(f"Could not fetch income statement for {symbol}: {str(e)}")
            income_data = []
        
        # Get company balance sheet
        try:
            balance, _ = fd.get_balance_sheet_annual(symbol)
            balance_data = balance.get('annualReports', [])
        except Exception as e:
            logger.warning(f"Could not fetch balance sheet for {symbol}: {str(e)}")
            balance_data = []
        
        result = {
            'status': 'success',
            'data': {
                'overview': overview,
                'income_statement': income_data[:2] if income_data else [],  # Last 2 years only
                'balance_sheet': balance_data[:2] if balance_data else []    # Last 2 years only
            },
            'message': f'Company data fetched successfully for {symbol}'
        }
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in get_company_data: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error fetching company data: {str(e)}'
        }), 500