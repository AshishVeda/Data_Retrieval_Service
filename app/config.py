import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # AWS Cognito Configuration
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
    COGNITO_USER_POOL_ID = os.getenv('COGNITO_USER_POOL_ID')
    COGNITO_APP_CLIENT_ID = os.getenv('COGNITO_APP_CLIENT_ID')
    COGNITO_APP_CLIENT_SECRET = os.getenv('COGNITO_APP_CLIENT_SECRET')
    
    # AWS RDS Configuration
    RDS_HOST = os.getenv('RDS_HOST')
    RDS_USER = os.getenv('RDS_USER')
    RDS_PASSWORD = os.getenv('RDS_PASSWORD')
    RDS_DB_NAME = os.getenv('RDS_DB_NAME', 'stocks_db')
    
    # Alpha Vantage API Configuration
    ALPHA_VANTAGE_API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY', 'demo')
    
    # AWS DynamoDB Configuration
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    DYNAMODB_CHAT_TABLE = os.getenv('DYNAMODB_CHAT_TABLE', 'stock_app_chat_history')
    
    # LLM API Configuration
    API_URL = os.getenv('API_URL')
    HF_TOKEN = os.getenv('HF_TOKEN')

    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    
    # Other configuration... 