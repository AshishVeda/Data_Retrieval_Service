from flask import Flask, jsonify
from flask_cors import CORS
from flask_caching import Cache
import os
from datetime import timedelta
import logging
from app.scheduler import init_scheduler

# ✅ Initialize Cache
cache = Cache()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)
    
    # Configure CORS to properly support credentials with specific origins
    CORS(app,
        origins=["http://thestockai.online"],
        allow_headers=["Content-Type", "Authorization"],
        expose_headers=["Content-Range", "X-Content-Range"],
        supports_credentials=True)

    # Configure Flask
    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')
    app.config['CACHE_TYPE'] = 'simple'
    
    # Configure session timeout
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)  # Session expires after 30 minutes of inactivity
    app.config['SESSION_REFRESH_EACH_REQUEST'] = True  # Refresh session on each request
    
    cache.init_app(app)

    # Initialize database (this will create the tables if they don't exist)
    from app.database import db
    
    # Register all blueprints
    from app.routes.stock_routes import stock_bp
    from app.routes.news_routes import news_bp
    from app.routes.social_routes import social_bp
    from app.routes.user_routes import user_bp
    from app.routes.prediction_routes import prediction_bp
    from app.routes.finnhub_routes import finnhub_bp
    from app.routes.multistep_prediction_routes import multistep_prediction_bp, followup_bp

    app.register_blueprint(stock_bp, url_prefix='/api/stocks')
    app.register_blueprint(news_bp, url_prefix='/api/news')
    app.register_blueprint(social_bp, url_prefix='/api/social')
    app.register_blueprint(user_bp, url_prefix='/api/users')
    app.register_blueprint(prediction_bp, url_prefix='/api/prediction')
    app.register_blueprint(finnhub_bp, url_prefix='/api/finnhub')
    app.register_blueprint(multistep_prediction_bp, url_prefix='/api/prediction/multistep')
    app.register_blueprint(followup_bp, url_prefix='/api/prediction/multistep')
    
    # Initialize the scheduler for background tasks
    init_scheduler(app)
    
    @app.route("/ping")
    def ping():
        return "pong", 200
    
    logger.info("Application initialized")

    return app
