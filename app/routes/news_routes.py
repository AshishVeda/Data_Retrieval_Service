import requests  # Import for HTTP requests
from flask import Blueprint, request, jsonify  # Flask imports
# from bs4 import BeautifulSoup  # Import for web scraping
import os
from dotenv import load_dotenv  # Load environment variables
import xmltodict
from app import cache  # ✅ Import cache from app/__init__.py
from app.services.news_service import NewsService
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load API Keys from .env file
load_dotenv()
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")

# ✅ Define Blueprint before using it
news_bp = Blueprint('news', __name__)

news_service = NewsService()

# ✅ Alpha Vantage News API
@news_bp.route('/alpha_vantage', methods=['GET'])
def fetch_alpha_vantage_news():
    symbol = request.args.get('symbol', '').upper().strip()
    if not symbol:
        return jsonify({"error": "Stock symbol is required"}), 400
    print(f"Using API Key: {ALPHA_VANTAGE_API_KEY}")
    print(f"Using API Key: {symbol}")
    url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={symbol}&apikey={ALPHA_VANTAGE_API_KEY}"

    try:
        response = requests.get(url)
        news_data = response.json()
        print(news_data)
        if "feed" not in news_data:
            return jsonify({"error": "No news found"}), 404

        articles = [
            {
                "title": item["title"],
                "summary": item.get("summary", ""),
                "link": item["url"],
                "source": item["source"],
                "publishedAt": item["time_published"]
            }
            for item in news_data["feed"]
        ]

        return jsonify(articles[:10])  # Return top 10 articles

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@cache.memoize(timeout=600)  # ✅ Cache API calls for 10 minutes
def fetch_google_news(query):
    """Fetch Google News RSS and convert XML to JSON."""
    url = f"https://news.google.com/rss/search?q={query}+stock"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        # Parse XML to JSON
        data = xmltodict.parse(response.content)
        articles = []

        if "rss" in data and "channel" in data["rss"] and "item" in data["rss"]["channel"]:
            for item in data["rss"]["channel"]["item"]:
                articles.append({
                    "title": item["title"],
                    "link": item["link"],
                    "publishedAt": item["pubDate"],
                    "summary": item.get("description", "No summary available")
                })

        return articles if articles else {"message": "No news articles found."}

    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to fetch Google News RSS: {str(e)}"}


# ✅ API Endpoint for Google News
@news_bp.route('/google_rss', methods=['GET'])
def get_google_rss():
    """API endpoint to fetch stock-related news from Google News RSS."""
    stock_symbol = request.args.get('symbol', default="AAPL", type=str)
    news_articles = fetch_google_news(stock_symbol)
    return jsonify(news_articles)

@news_bp.route('/fetch-all', methods=['GET'])
def fetch_all_tech_news():
    """Fetch news for all tech companies"""
    try:
        result = news_service.fetch_all_tech_news()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in fetch_all_tech_news: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@news_bp.route('/company/<symbol>', methods=['GET'])
def get_company_news(symbol):
    """Get and store news for a specific company (last 3 days only)"""
    try:
        result = news_service.get_company_news(symbol)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in get_company_news: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@news_bp.route('/stored/<symbol>', methods=['GET'])
def get_stored_news(symbol):
    """Get stored news for a specific company from vector DB (last 3 days only)"""
    try:
        limit = request.args.get('limit', default=10, type=int)
        result = news_service.get_stored_news(symbol, limit)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in get_stored_news: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@news_bp.route('/search', methods=['GET'])
def search_similar_news():
    """Search for similar news items (last 3 days only)"""
    try:
        query = request.args.get('query', '')
        symbol = request.args.get('symbol', None)
        limit = request.args.get('limit', default=5, type=int)
        
        if not query:
            return jsonify({
                'status': 'error',
                'message': 'Query parameter is required'
            }), 400
        
        result = news_service.search_similar_news(query, symbol, limit)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in search_similar_news: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@news_bp.route('/cleanup', methods=['POST'])
def cleanup_old_news():
    """Clean up news items older than 3 days"""
    try:
        result = news_service.cleanup_old_news()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in cleanup_old_news: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500