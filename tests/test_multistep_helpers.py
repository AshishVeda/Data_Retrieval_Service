import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
import pytest
from app.routes.multistep_prediction_routes import (
    fetch_historical_data, fetch_news_data, fetch_social_data,
    generate_prediction_from_data, get_cache_key,
    cache_step_data, get_cached_step_data, clear_step_data
)

class TestMultistepHelpers(unittest.TestCase):
    def setUp(self):
        # Common test data
        self.test_symbol = 'AAPL'
        self.test_user_id = 'test_user_123'
        self.test_user_query = 'Will the stock price increase next week?'
    
    @patch('app.routes.multistep_prediction_routes.StockService')
    def test_fetch_historical_data(self, mock_stock_service):
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
        
        # Call the function
        result = fetch_historical_data(self.test_symbol, period='3w')
        
        # Verify the result
        self.assertEqual(result['status'], 'success')
        self.assertTrue('data' in result)
        self.assertEqual(len(result['data']['dates']), 3)
        
        # Verify StockService was called correctly
        mock_instance.get_historical_prices.assert_called_once_with(
            self.test_symbol, period='3w'
        )
    
    @patch('app.routes.multistep_prediction_routes.StockService')
    def test_fetch_historical_data_error(self, mock_stock_service):
        # Setup mock to raise an exception
        mock_instance = mock_stock_service.return_value
        mock_instance.get_historical_prices.side_effect = Exception("API error")
        
        # Call the function
        result = fetch_historical_data(self.test_symbol)
        
        # Verify the result
        self.assertEqual(result['status'], 'error')
        self.assertTrue('message' in result)
        self.assertTrue('API error' in result['message'])
    
    @patch('app.routes.multistep_prediction_routes.NewsService')
    @patch('app.routes.multistep_prediction_routes.FinnhubService')
    def test_fetch_news_data_semantic_search(self, mock_finnhub, mock_news):
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
                }
            ]
        }
        
        # Call the function
        result = fetch_news_data(self.test_symbol, self.test_user_query)
        
        # Verify the result
        self.assertEqual(result['status'], 'success')
        self.assertTrue('data' in result)
        self.assertEqual(len(result['data']), 1)
        
        # Verify NewsService was called correctly
        mock_news_instance.search_similar_news.assert_called_once_with(
            self.test_user_query, self.test_symbol, limit=5
        )
        
        # Verify FinnhubService was not called
        mock_finnhub.assert_not_called()
    
    @patch('app.routes.multistep_prediction_routes.NewsService')
    @patch('app.routes.multistep_prediction_routes.FinnhubService')
    def test_fetch_news_data_finnhub_fallback(self, mock_finnhub, mock_news):
        # Setup mock return value for NewsService.search_similar_news (empty result)
        mock_news_instance = mock_news.return_value
        mock_news_instance.search_similar_news.return_value = {
            'status': 'success',
            'data': []  # No semantic search results
        }
        
        # Setup mock return value for FinnhubService.fetch_company_news
        mock_finnhub_instance = mock_finnhub.return_value
        mock_finnhub_instance.fetch_company_news.return_value = {
            'status': 'success',
            'data': [
                {
                    'title': 'Apple Announces New Products',
                    'published': '2023-01-03T10:00:00Z',
                    'source': 'TechBlog',
                    'url': 'https://techblog.com/apple-products',
                    'summary': 'Apple announced new products at their event.'
                }
            ]
        }
        
        # Call the function
        result = fetch_news_data(self.test_symbol, self.test_user_query)
        
        # Verify the result
        self.assertEqual(result['status'], 'success')
        self.assertTrue('data' in result)
        self.assertEqual(len(result['data']), 1)
        self.assertEqual(result['source'], 'finnhub_api')
        
        # Verify both services were called
        mock_news_instance.search_similar_news.assert_called_once()
        mock_finnhub_instance.fetch_company_news.assert_called_once_with(
            self.test_symbol, weeks=2
        )
    
    @patch('app.routes.multistep_prediction_routes.NewsService')
    @patch('app.routes.multistep_prediction_routes.FinnhubService')
    def test_fetch_news_data_error(self, mock_finnhub, mock_news):
        # Setup both services to fail
        mock_news_instance = mock_news.return_value
        mock_news_instance.search_similar_news.side_effect = Exception("API error")
        
        # Call the function
        result = fetch_news_data(self.test_symbol, self.test_user_query)
        
        # Verify the result
        self.assertEqual(result['status'], 'error')
        self.assertTrue('message' in result)
        self.assertTrue('API error' in result['message'])
    
    @patch('app.routes.multistep_prediction_routes.SocialService')
    def test_fetch_social_data(self, mock_social):
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
                }
            ],
            'sentiment_summary': {
                'avg_sentiment': 0.8,
                'positive_posts': 10,
                'negative_posts': 2,
                'neutral_posts': 3
            }
        }
        
        # Call the function
        result = fetch_social_data(self.test_symbol)
        
        # Verify the result
        self.assertTrue('posts' in result)
        self.assertTrue('sentiment_summary' in result)
        self.assertEqual(len(result['posts']), 1)
        
        # Verify SocialService was called correctly
        mock_social_instance.fetch_reddit_posts.assert_called_once_with(
            self.test_symbol
        )
    
    @patch('app.routes.multistep_prediction_routes.SocialService')
    def test_fetch_social_data_error(self, mock_social):
        # Setup mock to raise an exception
        mock_social_instance = mock_social.return_value
        mock_social_instance.fetch_reddit_posts.side_effect = Exception("API error")
        
        # Call the function
        result = fetch_social_data(self.test_symbol)
        
        # Verify the result
        self.assertEqual(result['status'], 'error')
        self.assertTrue('message' in result)
        self.assertTrue('API error' in result['message'])
    
    @patch('app.routes.multistep_prediction_routes.LLMService')
    @patch('app.routes.multistep_prediction_routes.generate_prediction')
    def test_generate_prediction_from_data(self, mock_generate_prediction, mock_llm):
        # Setup test data
        data = {
            'symbol': self.test_symbol,
            'user_query': self.test_user_query,
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
                    'avg_sentiment': 0.8
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
        PREDICTION: AAPL will increase by 5-7% next week.
        TARGET PRICE: $175.50
        """
        
        # Call the function
        result = generate_prediction_from_data(self.test_user_id, data)
        
        # Verify the result
        self.assertEqual(result['status'], 'success')
        self.assertTrue('data' in result)
        self.assertEqual(result['data']['symbol'], self.test_symbol)
        self.assertEqual(result['data']['user_query'], self.test_user_query)
        self.assertTrue('prediction' in result['data'])
        self.assertTrue('sections' in result['data'])
        
        # Verify LLMService was called correctly
        mock_llm_instance.generate_multistep_prompt.assert_called_once_with(
            symbol=self.test_symbol,
            user_query=self.test_user_query,
            historical_data=data['historical'],
            news_data=data['news'],
            social_data=data['social']
        )
        
        # Verify generate_prediction was called
        mock_generate_prediction.assert_called_once_with(
            "Test prompt for prediction", max_new_tokens=2048
        )
    
    @patch('app.routes.multistep_prediction_routes.LLMService')
    def test_generate_prediction_from_data_missing_data(self, mock_llm):
        # Setup test data with missing required fields
        data = {
            'symbol': self.test_symbol,
            'user_query': self.test_user_query,
            # Missing historical, news, social
        }
        
        # Call the function
        result = generate_prediction_from_data(self.test_user_id, data)
        
        # Verify the result
        self.assertEqual(result['status'], 'error')
        self.assertTrue('message' in result)
        self.assertTrue('Missing required data' in result['message'])
        
        # Verify LLMService was not called
        mock_llm.assert_not_called()
    
    @patch('app.routes.multistep_prediction_routes.cache')
    def test_cache_step_data(self, mock_cache):
        # Setup test data
        test_data = {
            'symbol': self.test_symbol,
            'user_query': self.test_user_query,
            'historical': {
                'dates': ['2023-01-01', '2023-01-02', '2023-01-03'],
                'prices': [150.0, 152.5, 153.75]
            }
        }
        
        # Call the function
        cache_step_data(self.test_user_id, self.test_symbol, test_data)
        
        # Verify cache.set was called correctly
        expected_key = f"multistep_prediction:{self.test_user_id}:{self.test_symbol}"
        
        mock_cache.set.assert_called_once_with(
            expected_key, test_data, timeout=900  # 900 seconds = 15 minutes
        )
    
    @patch('app.routes.multistep_prediction_routes.cache')
    def test_get_cached_step_data(self, mock_cache):
        # Setup mock for cache.get
        test_data = {
            'symbol': self.test_symbol,
            'user_query': self.test_user_query,
            'historical': {
                'dates': ['2023-01-01', '2023-01-02', '2023-01-03'],
                'prices': [150.0, 152.5, 153.75]
            }
        }
        mock_cache.get.return_value = test_data
        
        # Call the function
        result = get_cached_step_data(self.test_user_id, self.test_symbol)
        
        # Verify cache.get was called correctly
        expected_key = f"multistep_prediction:{self.test_user_id}:{self.test_symbol}"
        mock_cache.get.assert_called_once_with(expected_key)
        
        # Verify the result
        self.assertEqual(result, test_data)
    
    @patch('app.routes.multistep_prediction_routes.cache')
    def test_clear_step_data(self, mock_cache):
        # Call the function
        clear_step_data(self.test_user_id, self.test_symbol)
        
        # Verify cache.delete was called correctly
        expected_key = f"multistep_prediction:{self.test_user_id}:{self.test_symbol}"
        mock_cache.delete.assert_called_once_with(expected_key)

if __name__ == '__main__':
    unittest.main() 