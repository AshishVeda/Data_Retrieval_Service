import sys
import os
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import logging

# Add the project root to the path so we can import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.services.stock_service import StockService

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BacktestStockDataFetcher:
    """
    Class to fetch historical stock data for backtesting purposes.
    Fetches data from 3 weeks ago to 1 week ago (excludes the most recent week).
    """
    
    def __init__(self):
        """Initialize the stock data fetcher using the app's stock service"""
        self.stock_service = StockService()
    
    def get_date_ranges(self):
        """
        Get the date ranges for training (3 weeks to 1 week ago) and 
        test period (only yesterday, for a single-day prediction)
        
        Returns:
            tuple: (train_start, train_end, test_date) datetime objects
        """
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Calculate date ranges
        test_date = today - timedelta(days=1)  # Yesterday only
        train_end = test_date - timedelta(days=1)  # 1 day before test date
        train_start = today - timedelta(days=21)  # 3 weeks ago
        
        return train_start, train_end, test_date
    
    def fetch_training_data(self, symbol):
        """
        Fetch historical stock data for the training period (3 weeks to 1 week ago)
        
        Args:
            symbol (str): The stock symbol to fetch data for
            
        Returns:
            dict: Dictionary with status and training data
        """
        train_start, train_end, _ = self.get_date_ranges()
        
        logger.info(f"Fetching training data for {symbol} from {train_start.strftime('%Y-%m-%d')} to {train_end.strftime('%Y-%m-%d')}")
        
        # Use the standard app stock service but we'll filter the dates
        result = self.stock_service.get_historical_prices(symbol, period="3w")
        
        if result['status'] != 'success':
            logger.error(f"Failed to fetch historical data: {result.get('message', 'Unknown error')}")
            return result
        
        # Extract data
        data = result['data']
        dates = data.get('dates', [])
        prices = data.get('prices', [])
        volumes = data.get('volumes', [])
        
        # Convert string dates to datetime objects for comparison
        datetime_dates = [datetime.strptime(date, '%Y-%m-%d') if isinstance(date, str) else date for date in dates]
        
        # Filter data to training period only
        filtered_data = {
            'dates': [],
            'prices': [],
            'volumes': []
        }
        
        for i, date in enumerate(datetime_dates):
            if train_start <= date <= train_end:
                filtered_data['dates'].append(dates[i])
                filtered_data['prices'].append(prices[i])
                if i < len(volumes):
                    filtered_data['volumes'].append(volumes[i])
        
        return {
            'status': 'success',
            'data': filtered_data,
            'date_range': {
                'start': train_start.strftime('%Y-%m-%d'),
                'end': train_end.strftime('%Y-%m-%d')
            }
        }
    
    def fetch_test_data(self, symbol):
        """
        Fetch historical stock data for the test period (only yesterday)
        
        Args:
            symbol (str): The stock symbol to fetch data for
            
        Returns:
            dict: Dictionary with status and test data
        """
        _, _, test_date = self.get_date_ranges()
        
        logger.info(f"Fetching test data for {symbol} for date {test_date.strftime('%Y-%m-%d')}")
        
        # Use the standard app stock service but we'll filter for just one day
        result = self.stock_service.get_historical_prices(symbol, period="1w")
        
        if result['status'] != 'success':
            logger.error(f"Failed to fetch test data: {result.get('message', 'Unknown error')}")
            return result
        
        # Extract data
        data = result['data']
        dates = data.get('dates', [])
        prices = data.get('prices', [])
        volumes = data.get('volumes', [])
        
        # Convert string dates to datetime objects for comparison
        datetime_dates = [datetime.strptime(date, '%Y-%m-%d') if isinstance(date, str) else date for date in dates]
        
        # Filter data to just the test date
        filtered_data = {
            'dates': [],
            'prices': [],
            'volumes': []
        }
        
        for i, date in enumerate(datetime_dates):
            if date.date() == test_date.date():
                filtered_data['dates'].append(dates[i])
                filtered_data['prices'].append(prices[i])
                if i < len(volumes):
                    filtered_data['volumes'].append(volumes[i])
        
        # If we couldn't find the exact date, use the closest date available
        if not filtered_data['dates'] and datetime_dates:
            # Find the closest date
            closest_idx = min(range(len(datetime_dates)), 
                             key=lambda i: abs((datetime_dates[i] - test_date).total_seconds()))
            
            filtered_data['dates'].append(dates[closest_idx])
            filtered_data['prices'].append(prices[closest_idx])
            if closest_idx < len(volumes):
                filtered_data['volumes'].append(volumes[closest_idx])
                
            logger.warning(f"Exact test date not found. Using closest date {filtered_data['dates'][0]}")
        
        return {
            'status': 'success',
            'data': filtered_data,
            'date_range': {
                'date': test_date.strftime('%Y-%m-%d')
            }
        }
    
    def fetch_data(self, symbol):
        """
        Fetch both training and test data for a given symbol
        
        Args:
            symbol (str): The stock symbol to fetch data for
            
        Returns:
            dict: Dictionary with status, training data, and test data
        """
        training_data = self.fetch_training_data(symbol)
        test_data = self.fetch_test_data(symbol)
        
        if training_data['status'] != 'success' or test_data['status'] != 'success':
            return {
                'status': 'error',
                'message': 'Failed to fetch data'
            }
        
        return {
            'status': 'success',
            'training_data': training_data['data'],
            'test_data': test_data['data'],
            'training_period': training_data['date_range'],
            'test_date': test_data['date_range']['date']
        }


if __name__ == "__main__":
    # Example usage
    fetcher = BacktestStockDataFetcher()
    result = fetcher.fetch_data('AAPL')
    
    if result['status'] == 'success':
        train_dates = result['training_data']['dates']
        train_prices = result['training_data']['prices']
        test_dates = result['test_data']['dates']
        test_prices = result['test_data']['prices']
        
        print(f"Training period: {result['training_period']['start']} to {result['training_period']['end']}")
        print(f"Test date: {result['test_date']}")
        print(f"Training data points: {len(train_dates)}")
        print(f"Test data point: {len(test_dates)}")
        
        if train_prices and test_prices:
            last_train_price = train_prices[-1]
            test_price = test_prices[0] if test_prices else None
            
            print(f"Last training price: ${last_train_price:.2f}")
            if test_price:
                print(f"Test date price: ${test_price:.2f}")
                print(f"Price change: {((test_price - last_train_price) / last_train_price) * 100:.2f}%")
    else:
        print(f"Error: {result.get('message', 'Unknown error')}") 