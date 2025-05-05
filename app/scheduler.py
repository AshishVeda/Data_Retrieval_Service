from flask_apscheduler import APScheduler
import logging
from datetime import datetime, timedelta
from app.services.news_service import NewsService
from app.routes.finnhub_routes import FinnhubService

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize scheduler
scheduler = APScheduler()

def daily_news_update():
    """Fetch and update news for all companies in the watchlist daily"""
    try:
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logger.info(f"[SCHEDULED-TASK] Starting daily news update at {current_time}")
        
        # Initialize services
        news_service = NewsService()
        finnhub_service = FinnhubService()
        
        # First, clean up articles older than 3 days
        try:
            logger.info("[SCHEDULED-TASK] Cleaning up articles older than 3 days")
            cleanup_result = news_service.cleanup_old_news()
            logger.info(f"[SCHEDULED-TASK] Cleanup result: {cleanup_result.get('message', 'No message')}")
        except Exception as e:
            logger.error(f"[SCHEDULED-TASK] Error cleaning up old news: {str(e)}")
        
        # Get list of companies to fetch news for
        companies = news_service.TECH_COMPANIES
        logger.info(f"[SCHEDULED-TASK] Updating news for {len(companies)} companies")
        
        # Track success and failures
        success_count = 0
        failure_count = 0
        articles_count = 0
        
        # Process each company
        for symbol in companies:
            try:
                logger.info(f"[SCHEDULED-TASK] Fetching news for {symbol}")
                
                # Fetch from both Google News (via NewsService) and Finnhub
                google_result = news_service.get_company_news(symbol)
                finnhub_result = finnhub_service.fetch_company_news(symbol, weeks=1)  # Only get 1 week of articles
                
                # Log results from Google News
                if google_result['status'] == 'success':
                    google_count = len(google_result.get('data', []))
                    logger.info(f"[SCHEDULED-TASK] {symbol}: Retrieved {google_count} articles from Google News")
                    articles_count += google_count
                    success_count += 1
                else:
                    logger.error(f"[SCHEDULED-TASK] {symbol}: Failed to fetch from Google News - {google_result.get('message')}")
                    failure_count += 1
                
                # Log results from Finnhub
                if finnhub_result['status'] == 'success':
                    finnhub_count = len(finnhub_result.get('data', []))
                    logger.info(f"[SCHEDULED-TASK] {symbol}: Retrieved {finnhub_count} articles from Finnhub")
                    articles_count += finnhub_count
                else:
                    logger.error(f"[SCHEDULED-TASK] {symbol}: Failed to fetch from Finnhub - {finnhub_result.get('message')}")
                
            except Exception as e:
                logger.error(f"[SCHEDULED-TASK] Error processing {symbol}: {str(e)}")
                failure_count += 1
        
        # Run a final cleanup to ensure we only have the last 3 days of articles
        try:
            logger.info("[SCHEDULED-TASK] Running final cleanup to ensure only last 3 days of articles remain")
            news_service.cleanup_old_news()
        except Exception as e:
            logger.error(f"[SCHEDULED-TASK] Error in final cleanup: {str(e)}")
        
        # Log summary
        logger.info(f"[SCHEDULED-TASK] Daily news update completed: {success_count} companies succeeded, "
                    f"{failure_count} failed, {articles_count} total articles fetched")
        logger.info("[SCHEDULED-TASK] Database now contains only articles from the last 3 days")
        
    except Exception as e:
        logger.error(f"[SCHEDULED-TASK] Error in daily news update: {str(e)}")

def init_scheduler(app):
    """Initialize the scheduler with the Flask app"""
    scheduler.init_app(app)
    
    # Add job: Run every day at 7:00 AM
    scheduler.add_job(
        id='daily_news_update',
        func=daily_news_update,
        trigger='cron',
        hour=7,
        minute=0,
        second=0,
        day_of_week='*',  # Every day of the week
        replace_existing=True
    )
    
    # Add a separate cleanup job to run at 6:45 AM (before the main update)
    # This ensures we always have a clean database before the new articles arrive
    scheduler.add_job(
        id='daily_news_cleanup',
        func=lambda: NewsService().cleanup_old_news(),
        trigger='cron',
        hour=6,
        minute=45,
        second=0,
        day_of_week='*',  # Every day of the week
        replace_existing=True
    )
    
    # Start the scheduler
    scheduler.start()
    logger.info("Scheduler initialized with two jobs:")
    logger.info("1. Daily news cleanup at 6:45 AM - Removes articles older than 3 days")
    logger.info("2. Daily news update at 7:00 AM - Fetches fresh articles") 