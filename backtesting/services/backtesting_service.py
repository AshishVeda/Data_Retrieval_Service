import sys
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

# Add the project root to the path so we can import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.services.llm_service import LLMService
from app.services.stock_service import StockService
from app.routes.multistep_prediction_routes import generate_prediction, parse_llm_response
from backtesting.data.fetch_historic_data import BacktestStockDataFetcher
from backtesting.data.fetch_news_data import BacktestNewsDataFetcher
from backtesting.utils.metrics import calculate_metrics

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BacktestingService:
    """
    Service for backtesting stock price predictions against historical data
    """
    
    def __init__(self):
        """Initialize the backtesting service"""
        self.stock_fetcher = BacktestStockDataFetcher()
        self.news_fetcher = BacktestNewsDataFetcher()
        self.llm_service = LLMService()
        self.stock_service = StockService()
    
    def get_prediction_date(self) -> str:
        """
        Get the date to use for prediction (current training end date)
        
        Returns:
            str: The date string in YYYY-MM-DD format
        """
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        # Predict from 2 days ago (for yesterday's price)
        prediction_date = today - timedelta(days=2)
        return prediction_date.strftime('%Y-%m-%d')
    
    def prepare_prediction_data(self, symbol: str) -> Dict[str, Any]:
        """
        Prepare the data needed for making a prediction
        
        Args:
            symbol (str): The stock symbol
            
        Returns:
            dict: Dictionary with historical data and news
        """
        # Get historical stock data for training
        stock_data = self.stock_fetcher.fetch_training_data(symbol)
        if stock_data['status'] != 'success':
            return {'status': 'error', 'message': f"Failed to fetch stock data: {stock_data.get('message', 'Unknown error')}"}
        
        # Get news data for training period
        news_data = self.news_fetcher.fetch_news_data(symbol, user_query=f"{symbol} stock price movement factors")
        if news_data['status'] != 'success':
            logger.warning(f"No news data found for {symbol}. Continuing with stock data only.")
            news_data = {'data': []}
        
        return {
            'status': 'success',
            'stock_data': stock_data['data'],
            'news_data': news_data.get('data', []),
            'date_range': stock_data.get('date_range', {})
        }
    
    def make_prediction(self, symbol: str) -> Dict[str, Any]:
        """
        Make a prediction for the given symbol using historical data
        
        Args:
            symbol (str): The stock symbol
            
        Returns:
            dict: Dictionary with prediction result
        """
        prediction_date = self.get_prediction_date()
        logger.info(f"Making prediction for {symbol} based on data from {prediction_date}")
        
        # Prepare data for prediction
        data = self.prepare_prediction_data(symbol)
        if data['status'] != 'success':
            return data
        
        # Construct user query for prediction
        # Changed to predict for the next day (yesterday) instead of a week
        user_query = f"What will be the price of {symbol} tomorrow based on the data from {prediction_date}?"
        
        # Format data for the multistep prompt system
        formatted_data = {
            'symbol': symbol,
            'historical': {
                'dates': data['stock_data'].get('dates', []),
                'prices': data['stock_data'].get('prices', []),
                'volumes': data['stock_data'].get('volumes', [])
            },
            'news': data['news_data'],
            'social': {
                'sentiment_summary': {
                    'avg_post_polarity': 0,
                    'avg_post_subjectivity': 0,
                    'avg_comment_polarity': 0,
                    'avg_comment_subjectivity': 0,
                    'post_count': 0,
                    'comment_count': 0
                },
                'posts': []
            }
        }
        
        try:
            # Generate the multistep prompt
            prompt = self.llm_service.generate_multistep_prompt(
                data=formatted_data,
                user_query=user_query
            )
            
            # Use the prediction generator from the multistep route
            llm_response = generate_prediction(prompt, max_new_tokens=2048)
            
            # Parse the response to extract structured sections
            response_sections = parse_llm_response(llm_response)
            
            return {
                'status': 'success',
                'prediction': {
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
                },
                'timestamp': datetime.now().isoformat(),
                'test_date': prediction_date
            }
        except Exception as e:
            logger.error(f"Error making prediction: {str(e)}")
            return {
                'status': 'error',
                'message': f"Failed to make prediction: {str(e)}",
                'timestamp': datetime.now().isoformat(),
                'test_date': prediction_date
            }
    
    def evaluate_prediction(self, symbol: str, prediction: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a prediction against actual historical data for a single day
        using simplified metrics (percentage error and direction accuracy)
        
        Args:
            symbol (str): The stock symbol
            prediction (dict): The prediction result
            
        Returns:
            dict: Dictionary with evaluation metrics
        """
        # Get actual test data (single day)
        test_data = self.stock_fetcher.fetch_test_data(symbol)
        if test_data['status'] != 'success':
            return {'status': 'error', 'message': f"Failed to fetch test data: {test_data.get('message', 'Unknown error')}"}
        
        # Extract the predicted price
        predicted_price = None
        target_price = None
        
        if prediction['status'] == 'success':
            pred_data = prediction['prediction'].get('data', {})
            target_price = pred_data.get('target_price', '')
            
            if target_price:
                # Handle different formats of target price
                if isinstance(target_price, str):
                    # Try to extract the numeric value
                    import re
                    price_match = re.search(r'[\$]?([0-9]+(?:\.[0-9]+)?)', target_price)
                    if price_match:
                        predicted_price = float(price_match.group(1))
                elif isinstance(target_price, (int, float)):
                    predicted_price = float(target_price)
        
        # Get actual price (now just a single day)
        actual_prices = test_data['data'].get('prices', [])
        if not actual_prices:
            return {'status': 'error', 'message': "No actual price data found"}
        
        # Since we're only looking at a single day, there's just one price
        actual_price = actual_prices[0] if actual_prices else None
        
        # For direction accuracy, we need the last training price too
        training_data = self.stock_fetcher.fetch_training_data(symbol)
        train_prices = training_data['data'].get('prices', []) if training_data['status'] == 'success' else []
        last_train_price = train_prices[-1] if train_prices else None
        
        # Calculate simplified metrics
        metrics = calculate_metrics(predicted_price, last_train_price, actual_price)
        
        return {
            'status': 'success',
            'symbol': symbol,
            'test_date': test_data['date_range'].get('date', ''),
            'prediction': {
                'predicted_price': predicted_price,
                'target_price_raw': target_price
            },
            'actual': {
                'last_train_price': last_train_price,
                'actual_price': actual_price,
                'date': test_data['data'].get('dates', [''])[0] if test_data['data'].get('dates') else ''
            },
            'metrics': metrics
        }
    
    def run_backtest(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Run a backtest for multiple symbols
        
        Args:
            symbols (list): List of stock symbols
            
        Returns:
            dict: Dictionary with results for each symbol
        """
        results = {}
        
        for symbol in symbols:
            logger.info(f"Running backtest for {symbol}")
            
            # Make prediction
            prediction = self.make_prediction(symbol)
            
            # Store prediction result
            results[symbol] = prediction
            
            # If prediction was successful, evaluate it
            if prediction['status'] == 'success':
                evaluation = self.evaluate_prediction(symbol, prediction)
                if evaluation['status'] == 'success':
                    results[symbol]['evaluation'] = evaluation
        
        # Generate timestamp for result file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        result_file = f"backtest_results_{timestamp}.json"
        
        # Save results to file
        with open(result_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Backtest results saved to {result_file}")
        
        return {
            'status': 'success',
            'results': results,
            'output_file': result_file
        }


if __name__ == "__main__":
    # Example usage
    backtest = BacktestingService()
    result = backtest.run_backtest(['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META'])
    
    if result['status'] == 'success':
        print(f"Backtest completed successfully. Results saved to {result['output_file']}")
    else:
        print(f"Backtest failed: {result.get('message', 'Unknown error')}") 