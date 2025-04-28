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