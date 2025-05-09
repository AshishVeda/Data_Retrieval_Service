import os
import requests
from datetime import datetime, timedelta
import logging
import json
from flask import Blueprint, jsonify, request
from app.config import Config
from app.services.vector_service import VectorService
import hashlib

logger = logging.getLogger(__name__)

# Define Blueprint
finnhub_bp = Blueprint('finnhub', __name__)

class FinnhubService:
    def __init__(self):
        self.api_key = os.getenv("FINNHUB_API_KEY")
        self.vector_service = VectorService()
        logger.info("FinnhubService initialized with VectorService")
        
        # List of companies to track
        self.companies = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'BRKB', 'META', 'TSLA',
            'LLY', 'UNH', 'JNJ', 'V', 'JPM', 'XOM', 'PG', 'MA', 'HD', 'BAC',
            'PFE', 'KO', 'CVX', 'PEP', 'ABBV', 'WMT', 'COST'
        ]

    def fetch_company_news(self, symbol, weeks=3):
        """Fetch news for a specific company and store in VectorDB"""
        try:
            if not self.api_key:
                logger.error("Finnhub API key not configured")
                return {
                    'status': 'error',
                    'message': 'Finnhub API key not configured. Please set FINNHUB_API_KEY environment variable.'
                }
            
            # Calculate dates
            end_date = datetime.now()
            start_date = end_date - timedelta(weeks=weeks)
            
            # Format dates for Finnhub API
            from_date = start_date.strftime('%Y-%m-%d')
            to_date = end_date.strftime('%Y-%m-%d')
            
            logger.info(f"Fetching Finnhub news for {symbol} from {from_date} to {to_date}")
            
            # Make API request
            url = f"https://finnhub.io/api/v1/company-news"
            params = {
                'symbol': symbol,
                'from': from_date,
                'to': to_date,
                'token': self.api_key
            }
            
            response = requests.get(url, params=params)
            
            if response.status_code != 200:
                logger.error(f"Finnhub API error: {response.status_code} - {response.text}")
                return {
                    'status': 'error',
                    'message': f'Finnhub API error: {response.status_code}'
                }
            
            news_data = response.json()
            
            if not news_data:
                logger.warning(f"No news found for {symbol}")
                return {
                    'status': 'success',
                    'data': [],
                    'message': f'No news found for {symbol}'
                }
            
            # Process and store articles
            processed_articles = []
            articles_stored = 0
            storage_failures = 0
            
            # Create a list of news items for bulk storage
            news_items_to_store = []
            
            for article in news_data:
                try:
                    # Skip articles without required fields
                    if not article.get('headline') or not article.get('url'):
                        continue
                    
                    # Format timestamp to datetime
                    if article.get('datetime'):
                        date = datetime.fromtimestamp(article['datetime'])
                    else:
                        date = datetime.now()
                    
                    # Create article object
                    formatted_article = {
                        'title': article.get('headline', ''),
                        'summary': article.get('summary', ''),
                        'link': article.get('url', ''),
                        'source': article.get('source', 'Finnhub'),
                        'published': date.isoformat(),
                        'symbol': symbol,
                        'timestamp': datetime.now().isoformat(),
                        'related': article.get('related', ''),
                        'image': article.get('image', ''),
                        'category': article.get('category', '')
                    }
                    
                    processed_articles.append(formatted_article)
                    news_items_to_store.append(formatted_article)
                
                except Exception as e:
                    logger.error(f"Error processing Finnhub article: {str(e)}")
                    continue
            
            # Store all articles in vector database at once
            if news_items_to_store:
                try:
                    logger.info(f"Storing {len(news_items_to_store)} Finnhub articles in VectorDB")
                    success = self.vector_service.store_news(news_items_to_store)
                    if success:
                        articles_stored = len(news_items_to_store)
                        logger.info(f"Successfully stored {articles_stored} Finnhub articles in VectorDB")
                    else:
                        storage_failures = len(news_items_to_store)
                        logger.error(f"Failed to store Finnhub articles in VectorDB - returned False")
                except Exception as storage_error:
                    storage_failures = len(news_items_to_store)
                    logger.error(f"Exception storing Finnhub articles in VectorDB: {str(storage_error)}")
            
            logger.info(f"Finnhub news summary for {symbol}: {len(processed_articles)} articles found, {articles_stored} stored in VectorDB, {storage_failures} storage failures")
            
            # Return the processed articles
            return {
                'status': 'success',
                'data': processed_articles,
                'message': f'Fetched {len(processed_articles)} articles for {symbol}, stored {articles_stored} in VectorDB'
            }
            
        except Exception as e:
            logger.error(f"Error in fetch_company_news: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }

    def fetch_all_company_news(self):
        """Fetch news for all tracked companies"""
        try:
            results = {}
            total_stored = 0
            
            for symbol in self.companies:
                result = self.fetch_company_news(symbol)
                if result['status'] == 'success':
                    # Extract just the number of articles stored from the message
                    import re
                    stored_count = 0
                    match = re.search(r'stored (\d+) in VectorDB', result['message'])
                    if match:
                        stored_count = int(match.group(1))
                    
                    results[symbol] = {
                        'count': len(result.get('data', [])),
                        'stored': stored_count
                    }
                    total_stored += stored_count
                else:
                    results[symbol] = {
                        'error': result.get('message', 'Unknown error')
                    }
            
            return {
                'status': 'success',
                'data': results,
                'message': f'Fetched news for {len(self.companies)} companies, stored {total_stored} articles in VectorDB'
            }
            
        except Exception as e:
            logger.error(f"Error in fetch_all_company_news: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }

    def get_stored_finnhub_news(self, symbol, limit=10):
        """Get stored Finnhub news from VectorDB"""
        try:
            # Get news from vector DB
            news_items = self.vector_service.get_news_by_symbol(symbol, limit)
            
            if not news_items:
                return {
                    'status': 'success',
                    'data': [],
                    'message': f'No stored news found for {symbol}'
                }
            
            return {
                'status': 'success',
                'data': news_items,
                'message': f'Retrieved {len(news_items)} stored news items for {symbol}'
            }
            
        except Exception as e:
            logger.error(f"Error in get_stored_finnhub_news: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }

# Initialize service for route handlers
finnhub_service = FinnhubService()

@finnhub_bp.route('/news/<symbol>', methods=['GET'])
def get_finnhub_news(symbol):
    """Get stored Finnhub news for a specific symbol"""
    try:
        limit = request.args.get('limit', default=10, type=int)
        result = finnhub_service.get_stored_finnhub_news(symbol, limit)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in get_finnhub_news: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@finnhub_bp.route('/fetch/<symbol>', methods=['GET'])
def fetch_finnhub_news(symbol):
    """Fetch and store news from Finnhub API for a specific symbol"""
    try:
        weeks = request.args.get('weeks', default=3, type=int)
        result = finnhub_service.fetch_company_news(symbol, weeks)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in fetch_finnhub_news: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@finnhub_bp.route('/fetch/all', methods=['GET'])
def fetch_all_finnhub_news():
    """Fetch and store news for all tracked companies"""
    try:
        result = finnhub_service.fetch_all_company_news()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in fetch_all_finnhub_news: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500