import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd
from app.services.session_service import SessionService
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class StockService:
    @staticmethod
    def get_historical_prices(symbol, period='1y'):
        """Get historical prices for a symbol"""
        try:
            logger.debug(f"Fetching historical prices for {symbol} with period {period}")
            
            # Always fetch fresh data from YFinance
            stock = yf.Ticker(symbol)
            hist = stock.history(period=period)
            
            if hist.empty:
                logger.error(f"No historical data found for {symbol}")
                return {
                    'status': 'error',
                    'message': f'No historical data found for symbol {symbol}'
                }
            
            # Convert to dictionary format
            data = {
                'dates': hist.index.strftime('%Y-%m-%d').tolist(),
                'prices': hist['Close'].tolist(),
                'volumes': hist['Volume'].tolist()
            }
            
            logger.debug(f"Successfully fetched historical data for {symbol}")
            return {
                'status': 'success',
                'data': data,
                'message': 'Historical prices fetched successfully'
            }
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {str(e)}")
            return {
                'status': 'error',
                'message': f'Error fetching historical data: {str(e)}'
            } 