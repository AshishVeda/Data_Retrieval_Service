import unittest
from unittest.mock import patch, MagicMock
import json
from flask import Flask
from app import create_app

class TestMultistepErrorHandling(unittest.TestCase):
    def setUp(self):
        # Create Flask app with testing config
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['BYPASS_AUTH'] = True  # Bypass JWT authentication for testing
        self.app.config['CACHE_TYPE'] = 'simple'  # Use simple cache for testing
        
        # Create test client
        self.client = self.app.test_client()
        
        # Common test data
        self.test_symbol = 'AAPL'
        self.test_user_query = 'Will the stock price increase next week?'
    
    def test_historical_missing_params(self):
        """Test /historical endpoint with missing parameters"""
        # Missing symbol
        response = self.client.post(
            '/api/prediction/multistep/historical',
            json={'user_query': self.test_user_query}
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'error')
        
        # Missing user_query
        response = self.client.post(
            '/api/prediction/multistep/historical',
            json={'symbol': self.test_symbol}
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'error')
        
        # Empty request
        response = self.client.post(
            '/api/prediction/multistep/historical',
            json={}
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'error')
    
    @patch('app.routes.multistep_prediction_routes.StockService')
    def test_historical_service_error(self, mock_stock_service):
        """Test /historical endpoint when StockService returns error"""
        # Setup mock return value for StockService.get_historical_prices
        mock_instance = mock_stock_service.return_value
        mock_instance.get_historical_prices.return_value = {
            'status': 'error',
            'message': 'Service unavailable'
        }
        
        # Make the request
        response = self.client.post(
            '/api/prediction/multistep/historical',
            json={
                'symbol': self.test_symbol,
                'user_query': self.test_user_query
            }
        )
        
        # Assert response
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'error')
        self.assertTrue('Service unavailable' in data['message'])
    
    def test_news_missing_params(self):
        """Test /news endpoint with missing parameters"""
        # Missing symbol
        response = self.client.post(
            '/api/prediction/multistep/news',
            json={'user_query': self.test_user_query}
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'error')
        
        # Missing user_query
        response = self.client.post(
            '/api/prediction/multistep/news',
            json={'symbol': self.test_symbol}
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'error')
        
        # Empty request
        response = self.client.post(
            '/api/prediction/multistep/news',
            json={}
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'error')
    
    @patch('app.routes.multistep_prediction_routes.cache')
    def test_news_missing_cache_data(self, mock_cache):
        """Test /news endpoint when there's no cached data from previous step"""
        # Setup mock for cache.get
        mock_cache.get.return_value = None
        
        # Make the request
        response = self.client.post(
            '/api/prediction/multistep/news',
            json={
                'symbol': self.test_symbol,
                'user_query': self.test_user_query
            }
        )
        
        # Assert response
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'error')
        self.assertTrue('Historical data not found' in data['message'])
    
    def test_socialmedia_missing_params(self):
        """Test /socialmedia endpoint with missing parameters"""
        # Missing symbol
        response = self.client.post(
            '/api/prediction/multistep/socialmedia',
            json={'user_query': self.test_user_query}
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'error')
        
        # Missing user_query
        response = self.client.post(
            '/api/prediction/multistep/socialmedia',
            json={'symbol': self.test_symbol}
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'error')
        
        # Empty request
        response = self.client.post(
            '/api/prediction/multistep/socialmedia',
            json={}
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'error')
    
    @patch('app.routes.multistep_prediction_routes.cache')
    def test_socialmedia_missing_cache_data(self, mock_cache):
        """Test /socialmedia endpoint when there's no cached data from previous steps"""
        # Setup mock for cache.get
        mock_cache.get.return_value = None
        
        # Make the request
        response = self.client.post(
            '/api/prediction/multistep/socialmedia',
            json={
                'symbol': self.test_symbol,
                'user_query': self.test_user_query
            }
        )
        
        # Assert response
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'error')
        self.assertTrue('data not found' in data['message'])
    
    def test_result_missing_params(self):
        """Test /result endpoint with missing parameters"""
        # Missing symbol
        response = self.client.post(
            '/api/prediction/multistep/result',
            json={'user_query': self.test_user_query}
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'error')
        
        # Missing user_query
        response = self.client.post(
            '/api/prediction/multistep/result',
            json={'symbol': self.test_symbol}
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'error')
        
        # Empty request
        response = self.client.post(
            '/api/prediction/multistep/result',
            json={}
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'error')
    
    @patch('app.routes.multistep_prediction_routes.cache')
    def test_result_missing_cache_data(self, mock_cache):
        """Test /result endpoint when there's no cached data from previous steps"""
        # Setup mock for cache.get
        mock_cache.get.return_value = None
        
        # Make the request
        response = self.client.post(
            '/api/prediction/multistep/result',
            json={
                'symbol': self.test_symbol,
                'user_query': self.test_user_query
            }
        )
        
        # Assert response
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'error')
        self.assertTrue('Analysis data not found' in data['message'])
    
    @patch('app.routes.multistep_prediction_routes.cache')
    def test_result_missing_required_data(self, mock_cache):
        """Test /result endpoint when cached data is missing required fields"""
        # Setup mock for cache.get with incomplete data
        mock_cache.get.return_value = {
            'symbol': self.test_symbol,
            'user_query': self.test_user_query,
            'timestamp': '2023-01-01T12:00:00Z',
            # Missing 'historical', 'news', or 'social'
        }
        
        # Make the request
        response = self.client.post(
            '/api/prediction/multistep/result',
            json={
                'symbol': self.test_symbol,
                'user_query': self.test_user_query
            }
        )
        
        # Assert response
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'error')
        self.assertTrue('Missing' in data['message'])
    
    def test_followup_missing_params(self):
        """Test /followup endpoint with missing parameters"""
        # Missing symbol
        response = self.client.post(
            '/api/prediction/multistep/followup',
            json={'user_query': self.test_user_query}
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'error')
        self.assertTrue('Symbol' in data['message'])
        
        # Missing user_query
        response = self.client.post(
            '/api/prediction/multistep/followup',
            json={'symbol': self.test_symbol}
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'error')
        self.assertTrue('user_query' in data['message'])
        
        # Empty request
        response = self.client.post(
            '/api/prediction/multistep/followup',
            json={}
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'error')
    
    @patch('app.routes.multistep_prediction_routes.generate_prediction')
    def test_followup_llm_service_error(self, mock_generate_prediction):
        """Test /followup endpoint when LLM service fails"""
        # Setup mock to raise an exception
        mock_generate_prediction.side_effect = Exception("LLM service unavailable")
        
        # Make the request
        response = self.client.post(
            '/api/prediction/multistep/followup',
            json={
                'symbol': self.test_symbol,
                'user_query': self.test_user_query
            }
        )
        
        # Assert response
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'error')
        self.assertTrue('LLM service unavailable' in data['message'])

if __name__ == '__main__':
    unittest.main() 