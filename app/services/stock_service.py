from alpha_vantage.timeseries import TimeSeries
from datetime import datetime, timedelta
import pandas as pd
from app.services.session_service import SessionService
from app.config import Config
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StockService:
    @staticmethod
    def get_historical_prices(symbol, period='1y'):
        """Get historical prices for a symbol using Alpha Vantage instead of YFinance"""
        try:
            logger.info(f"Fetching historical prices for {symbol} with period {period}")
            
            # Initialize Alpha Vantage client
            ts = TimeSeries(key=Config.ALPHA_VANTAGE_API_KEY, output_format='pandas')
            
            # Determine the output size based on period
            if period == '1m' or period == '1mo':
                output_size = 'compact'  # last 100 data points
            else:
                output_size = 'full'     # up to 20 years of data
                
            # Fetch data from Alpha Vantage
            data, meta_data = ts.get_daily(symbol=symbol, outputsize=output_size)
            
            # Check if data is empty
            if data.empty:
                logger.error(f"No historical data found for {symbol}")
                return {
                    'status': 'error',
                    'message': f'No historical data found for symbol {symbol}'
                }
            
            # Filter data based on period
            end_date = datetime.now()
            
            if period == '1d':
                start_date = end_date - timedelta(days=1)
            elif period == '5d':
                start_date = end_date - timedelta(days=5)
            elif period == '1mo' or period == '1m':
                start_date = end_date - timedelta(days=30)
            elif period == '3mo' or period == '3m':
                start_date = end_date - timedelta(days=90)
            elif period == '6mo' or period == '6m':
                start_date = end_date - timedelta(days=180)
            elif period == '1y':
                start_date = end_date - timedelta(days=365)
            elif period == '2y':
                start_date = end_date - timedelta(days=365*2)
            elif period == '5y':
                start_date = end_date - timedelta(days=365*5)
            else:
                start_date = end_date - timedelta(days=365)  # Default to 1 year
            
            # Convert datetime to string for comparison
            start_date_str = start_date.strftime('%Y-%m-%d')
            
            # Filter data to the specified period
            filtered_data = data[data.index >= start_date_str]
            
            if filtered_data.empty:
                logger.error(f"No data found for {symbol} in the specified period")
                return {
                    'status': 'error',
                    'message': f'No data found for {symbol} in the specified period'
                }
            
            # Convert to dictionary format
            result = {
                'dates': filtered_data.index.strftime('%Y-%m-%d').tolist(),
                'prices': filtered_data['4. close'].tolist(),
                'volumes': filtered_data['5. volume'].tolist()
            }
            
            logger.info(f"Successfully fetched historical data for {symbol} using Alpha Vantage")
            
            return {
                'status': 'success',
                'data': result,
                'message': 'Historical prices fetched successfully'
            }
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {str(e)}")
            return {
                'status': 'error',
                'message': f'Error fetching historical data: {str(e)}'
            } 