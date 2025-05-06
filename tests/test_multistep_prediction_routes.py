import unittest
from unittest.mock import patch, MagicMock
import json
from datetime import datetime
import pytest
from flask import Flask
from app import create_app
from app.routes.multistep_prediction_routes import (
    get_cache_key, parse_llm_response, multistep_prediction_bp, followup_bp,
    create_followup_prompt, process_followup_response
)

class TestMultistepPredictionRoutes(unittest.TestCase):
    def setUp(self):
        # Create Flask app with testing config
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['BYPASS_AUTH'] = True  # Bypass JWT authentication for testing
        self.app.config['CACHE_TYPE'] = 'simple'  # Use simple cache for testing
        
        # Create test client
        self.client = self.app.test_client()
        
        # Mock cache for testing
        self.cache_data = {}
        
        # Common test data
        self.test_symbol = 'AAPL'
        self.test_user_id = 'test_user_123'
        self.test_user_query = 'Will the stock price increase next week?'
        
    @patch('app.routes.multistep_prediction_routes.StockService')
    def test_historical_endpoint(self, mock_stock_service):
        # Setup mock return value for StockService.get_historical_prices
        mock_instance = mock_stock_service.return_value
        mock_instance.get_historical_prices.return_value = {
            'status': 'success',
            'data': {
                'dates': ['2023-01-01', '2023-01-02', '2023-01-03'],
                'prices': [150.0, 152.5, 153.75],
                'volumes': [1000000, 1200000, 900000]
            }
        }
        
        # Setup cache mock
        with patch('app.routes.multistep_prediction_routes.cache') as mock_cache:
            # Mock the cache.set method
            mock_cache.set = MagicMock()
            
            # Make the request
            response = self.client.post(
                '/api/prediction/multistep/historical',
                json={
                    'symbol': self.test_symbol,
                    'user_query': self.test_user_query
                }
            )
            
            # Assert response
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertEqual(data['status'], 'success')
            self.assertEqual(data['data']['symbol'], self.test_symbol)
            self.assertEqual(len(data['data']['historical_prices']), 3)
            
            # Verify StockService was called correctly
            mock_instance.get_historical_prices.assert_called_once_with(
                self.test_symbol, period="3w"
            )
            
            # Verify cache was set
            mock_cache.set.assert_called_once()
    
    @patch('app.routes.multistep_prediction_routes.cache')
    @patch('app.routes.multistep_prediction_routes.NewsService')
    @patch('app.routes.multistep_prediction_routes.FinnhubService')
    def test_news_endpoint_semantic_search(self, mock_finnhub, mock_news, mock_cache):
        # Setup mock for cache.get
        mock_cache.get.return_value = {
            'symbol': self.test_symbol,
            'user_query': self.test_user_query,
            'timestamp': datetime.now().isoformat(),
            'historical': {
                'dates': ['2023-01-01', '2023-01-02', '2023-01-03'],
                'prices': [150.0, 152.5, 153.75]
            }
        }
        
        # Setup mock return value for NewsService.search_similar_news
        mock_news_instance = mock_news.return_value
        mock_news_instance.search_similar_news.return_value = {
            'status': 'success',
            'data': [
                {
                    'title': 'Apple Reports Record Earnings',
                    'published': '2023-01-02T14:30:00Z',
                    'source': 'TechNews',
                    'link': 'https://technews.com/apple-earnings',
                    'summary': 'Apple reported record earnings for Q4 2022.'
                },
                {
                    'title': 'Apple Stock Surges on AI Announcement',
                    'published': '2023-01-01T10:15:00Z',
                    'source': 'FinanceDaily',
                    'link': 'https://financedaily.com/apple-ai',
                    'summary': 'Apple stock surged after announcing new AI features.'
                }
            ]
        }
        
        # Make the request
        response = self.client.post(
            '/api/prediction/multistep/news',
            json={
                'symbol': self.test_symbol,
                'user_query': self.test_user_query
            }
        )
        
        # Assert response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['data']['symbol'], self.test_symbol)
        self.assertEqual(len(data['data']['articles']), 2)
        self.assertEqual(data['data_source'], 'semantic_search')
        
        # Verify NewsService was called correctly
        mock_news_instance.search_similar_news.assert_called_once_with(
            self.test_user_query, self.test_symbol, limit=5
        )
        
        # Verify cache was updated
        mock_cache.set.assert_called_once()
    
    @patch('app.routes.multistep_prediction_routes.cache')
    @patch('app.routes.multistep_prediction_routes.SocialService')
    def test_social_endpoint(self, mock_social, mock_cache):
        # Setup mock for cache.get
        mock_cache.get.return_value = {
            'symbol': self.test_symbol,
            'user_query': self.test_user_query,
            'timestamp': datetime.now().isoformat(),
            'historical': {
                'dates': ['2023-01-01', '2023-01-02', '2023-01-03'],
                'prices': [150.0, 152.5, 153.75]
            },
            'news': [
                {
                    'title': 'Apple Reports Record Earnings',
                    'published': '2023-01-02T14:30:00Z',
                    'source': 'TechNews',
                    'link': 'https://technews.com/apple-earnings',
                    'summary': 'Apple reported record earnings for Q4 2022.'
                }
            ]
        }
        
        # Setup mock return value for SocialService.fetch_reddit_posts
        mock_social_instance = mock_social.return_value
        mock_social_instance.fetch_reddit_posts.return_value = {
            'posts': [
                {
                    'title': 'AAPL to the moon!',
                    'score': 150,
                    'created_utc': 1673550000,
                    'author': 'apple_fan',
                    'sentiment': {'polarity': 0.8},
                    'selftext': 'I think Apple will have a great year with all the new products.'
                },
                {
                    'title': 'Thoughts on Apple stock?',
                    'score': 100,
                    'created_utc': 1673460000,
                    'author': 'investor123',
                    'sentiment': {'polarity': 0.2},
                    'selftext': 'What do you think about Apple stock for the next quarter?'
                }
            ],
            'sentiment_summary': {
                'avg_sentiment': 0.5,
                'positive_posts': 15,
                'negative_posts': 5,
                'neutral_posts': 10
            }
        }
        
        # Make the request
        response = self.client.post(
            '/api/prediction/multistep/socialmedia',
            json={
                'symbol': self.test_symbol,
                'user_query': self.test_user_query
            }
        )
        
        # Assert response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['data']['symbol'], self.test_symbol)
        self.assertEqual(len(data['data']['posts']), 2)
        self.assertTrue('sentiment_summary' in data['data'])
        
        # Verify SocialService was called correctly
        mock_social_instance.fetch_reddit_posts.assert_called_once_with(
            self.test_symbol
        )
        
        # Verify cache was updated
        mock_cache.set.assert_called_once()
    
    @patch('app.routes.multistep_prediction_routes.cache')
    @patch('app.routes.multistep_prediction_routes.LLMService')
    @patch('app.routes.multistep_prediction_routes.generate_prediction')
    @patch('app.routes.multistep_prediction_routes.chat_history_service')
    def test_result_endpoint(self, mock_chat_history, mock_generate_prediction, mock_llm, mock_cache):
        # Setup mock for cache.get
        mock_cache.get.return_value = {
            'symbol': self.test_symbol,
            'user_query': self.test_user_query,
            'timestamp': datetime.now().isoformat(),
            'historical': {
                'dates': ['2023-01-01', '2023-01-02', '2023-01-03'],
                'prices': [150.0, 152.5, 153.75]
            },
            'news': [
                {
                    'title': 'Apple Reports Record Earnings',
                    'published': '2023-01-02T14:30:00Z',
                    'source': 'TechNews',
                    'link': 'https://technews.com/apple-earnings',
                    'summary': 'Apple reported record earnings for Q4 2022.'
                }
            ],
            'social': {
                'posts': [
                    {
                        'title': 'AAPL to the moon!',
                        'score': 150,
                        'sentiment': {'polarity': 0.8}
                    }
                ],
                'sentiment_summary': {
                    'avg_sentiment': 0.5
                }
            }
        }
        
        # Setup mock for LLMService.generate_multistep_prompt
        mock_llm_instance = mock_llm.return_value
        mock_llm_instance.generate_multistep_prompt.return_value = "Test prompt for prediction"
        
        # Setup mock for generate_prediction
        mock_generate_prediction.return_value = """
        SUMMARY: Apple's stock is likely to increase next week.
        PRICE ANALYSIS: Recent price trends show upward momentum.
        NEWS IMPACT: Positive earnings report will drive growth.
        SENTIMENT ANALYSIS: Social sentiment is overwhelmingly positive.
        PREDICTION: AAPL will increase by 5-7% next week.
        TARGET PRICE: $175.50
        CONFIDENCE LEVEL: High
        RISK FACTORS: Market volatility could impact performance.
        """
        
        # Setup mock for chat_history_service
        mock_chat_history.store_chat = MagicMock()
        
        # Make the request
        response = self.client.post(
            '/api/prediction/multistep/result',
            json={
                'symbol': self.test_symbol,
                'user_query': self.test_user_query
            }
        )
        
        # Assert response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['data']['symbol'], self.test_symbol)
        self.assertEqual(data['data']['user_query'], self.test_user_query)
        self.assertTrue('prediction' in data['data'])
        self.assertTrue('sections' in data['data'])
        self.assertEqual(data['data']['target_price'], '$175.50')
        
        # Verify LLMService was called correctly
        mock_llm_instance.generate_multistep_prompt.assert_called_once()
        
        # Verify generate_prediction was called
        mock_generate_prediction.assert_called_once_with(
            "Test prompt for prediction", max_new_tokens=2048
        )
        
        # Verify chat history was stored
        mock_chat_history.store_chat.assert_called_once()
        
        # Verify cache was deleted after completion
        mock_cache.delete.assert_called_once()
    
    @patch('app.routes.multistep_prediction_routes.chat_history_service')
    @patch('app.routes.multistep_prediction_routes.generate_prediction')
    def test_followup_endpoint(self, mock_generate_prediction, mock_chat_history):
        # Setup mock for chat_history_service.get_chat_history
        mock_chat_history.get_chat_history.return_value = {
            'status': 'success',
            'data': [
                {
                    'symbol': self.test_symbol,
                    'query': 'What will be Apple stock price next week?',
                    'response': 'I predict Apple stock will rise to $175 next week based on positive earnings.'
                }
            ]
        }
        
        # Setup mock for chat_history_service.store_chat
        mock_chat_history.store_chat = MagicMock()
        
        # Setup mock for generate_prediction
        mock_generate_prediction.return_value = """
        Based on the previous prediction and recent market movements, Apple's stock will likely continue its upward momentum.
        
        The strong earnings report released last week has positively impacted investor sentiment.
        
        TARGET PRICE: $175.00
        
        Keep in mind that market volatility could affect this prediction.
        """
        
        # Make the request
        response = self.client.post(
            '/api/prediction/multistep/followup',
            json={
                'symbol': self.test_symbol,
                'user_query': 'Why do you think Apple stock will rise?'
            }
        )
        
        # Assert response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['symbol'], self.test_symbol)
        self.assertEqual(data['user_query'], 'Why do you think Apple stock will rise?')
        self.assertTrue('llm_response' in data)
        self.assertTrue('sections' in data)
        # Check that target price starts with the expected value
        self.assertTrue(data['target_price'].startswith('$175.00'))
        
        # Verify chat_history_service.get_chat_history was called
        mock_chat_history.get_chat_history.assert_called_once_with(
            self.test_user_id, limit=3
        )
        
        # Verify generate_prediction was called with the correct prompt
        mock_generate_prediction.assert_called_once()
        
        # Verify chat history was stored
        mock_chat_history.store_chat.assert_called_once()
    
    def test_parse_llm_response(self):
        # Test standard format with section headers
        llm_response = """
        SUMMARY: Apple's stock is likely to increase next week.
        PRICE ANALYSIS: Recent price trends show upward momentum.
        NEWS IMPACT: Positive earnings report will drive growth.
        SENTIMENT ANALYSIS: Social sentiment is overwhelmingly positive.
        PREDICTION: AAPL will increase by 5-7% next week.
        TARGET PRICE: $175.50
        CONFIDENCE LEVEL: High
        RISK FACTORS: Market volatility could impact performance.
        """
        
        result = parse_llm_response(llm_response)
        
        self.assertEqual(result['summary'], "Apple's stock is likely to increase next week.")
        self.assertEqual(result['price_analysis'], "Recent price trends show upward momentum.")
        self.assertEqual(result['news_impact'], "Positive earnings report will drive growth.")
        self.assertEqual(result['sentiment_analysis'], "Social sentiment is overwhelmingly positive.")
        # Check that prediction includes the target price
        self.assertTrue(result['prediction'].startswith("AAPL will increase by 5-7% next week"))
        self.assertTrue("$175.50" in result['prediction'])
        self.assertEqual(result['target_price'], "$175.50")
        self.assertEqual(result['confidence'], "High")
        self.assertEqual(result['risk_factors'], "Market volatility could impact performance.")
    
    def test_parse_llm_response_prediction_analysis_format(self):
        # Test [Prediction & Analysis] format
        llm_response = """
        [Prediction & Analysis]
        Prediction: AAPL will increase by 5-7% next week.
        Analysis: Recent price trends show upward momentum.
        Target Price: $175.50
        """
        
        result = parse_llm_response(llm_response)
        
        # Check that prediction includes the target price
        self.assertTrue(result['prediction'].startswith("AAPL will increase by 5-7% next week"))
        self.assertTrue("$175.50" in result['prediction'])
        self.assertEqual(result['price_analysis'], "Recent price trends show upward momentum.")
        self.assertEqual(result['target_price'], "$175.50")
    
    def test_parse_llm_response_extract_target_price(self):
        # Test extracting target price from prediction
        llm_response = """
        SUMMARY: Apple's stock is likely to increase next week.
        PREDICTION: AAPL will increase by 5-7% next week to reach $175.50.
        """
        
        result = parse_llm_response(llm_response)
        
        self.assertEqual(result['summary'], "Apple's stock is likely to increase next week.")
        # No modification needed here since target price is already in the prediction text
        self.assertEqual(result['prediction'], "AAPL will increase by 5-7% next week to reach $175.50.")
        self.assertEqual(result['target_price'], "$175.50")
    
    def test_parse_llm_response_malformed(self):
        # Test handling malformed response
        llm_response = "Apple stock might go up or down depending on market conditions."
        
        result = parse_llm_response(llm_response)
        
        self.assertTrue('full_response' in result)
        self.assertEqual(result['full_response'], "Apple stock might go up or down depending on market conditions.")
    
    def test_get_cache_key(self):
        # Test cache key generation
        key = get_cache_key(self.test_user_id, self.test_symbol)
        expected_key = f"multistep_prediction:{self.test_user_id}:{self.test_symbol}"
        self.assertEqual(key, expected_key)
    
    def test_create_followup_prompt(self):
        # Test followup prompt creation with chat history
        with patch('app.routes.multistep_prediction_routes.chat_history_service') as mock_chat_history:
            mock_chat_history.get_chat_history.return_value = {
                'status': 'success',
                'data': [
                    {
                        'symbol': self.test_symbol,
                        'query': 'What will be Apple stock price next week?',
                        'response': 'I predict Apple stock will rise to $175 next week based on positive earnings.'
                    }
                ]
            }
            
            prompt = create_followup_prompt(self.test_user_id, self.test_symbol, self.test_user_query)
            
            self.assertTrue(self.test_symbol in prompt)
            self.assertTrue(self.test_user_query in prompt)
            self.assertTrue('PREVIOUS CONVERSATION HISTORY' in prompt)
            self.assertTrue('Previous Question:' in prompt)
            self.assertTrue('Previous Answer:' in prompt)
    
    def test_process_followup_response(self):
        # Test processing followup response
        llm_response = """
        Based on the previous prediction and recent market movements, Apple's stock will likely continue its upward momentum.
        
        The strong earnings report released last week has positively impacted investor sentiment.
        
        TARGET PRICE: $175.00
        
        Keep in mind that market volatility could affect this prediction.
        """
        
        result = process_followup_response(self.test_symbol, self.test_user_query, llm_response)
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['symbol'], self.test_symbol)
        self.assertEqual(result['user_query'], self.test_user_query)
        self.assertEqual(result['llm_response'], llm_response)
        self.assertTrue('sections' in result)
        # Check that target price starts with the expected value
        self.assertTrue(result['target_price'].startswith('$175.00'))

if __name__ == '__main__':
    unittest.main() 