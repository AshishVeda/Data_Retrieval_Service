import boto3
from botocore.exceptions import ClientError
from app.config import Config
import hmac
import base64
import hashlib
import logging
from app.database import db
import json

logger = logging.getLogger(__name__)

class UserService:
    def __init__(self):
        self.client = boto3.client('cognito-idp', region_name=Config.AWS_REGION)
        self.user_pool_id = Config.COGNITO_USER_POOL_ID
        self.client_id = Config.COGNITO_APP_CLIENT_ID
        self.client_secret = Config.COGNITO_APP_CLIENT_SECRET

    def _get_secret_hash(self, username):
        """Generate a secret hash for Cognito authentication"""
        msg = username + self.client_id
        dig = hmac.new(
            str(self.client_secret).encode('utf-8'),
            msg=str(msg).encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        return base64.b64encode(dig).decode()

    def register_user(self, username, password, email):
        """Register a new user in Cognito and store in RDS"""
        try:
            # Register user in Cognito
            response = self.client.sign_up(
                ClientId=self.client_id,
                SecretHash=self._get_secret_hash(username),
                Username=username,
                Password=password,
                UserAttributes=[
                    {
                        'Name': 'email',
                        'Value': email
                    }
                ]
            )
            
            cognito_sub = response['UserSub']
            
            # Store user in RDS
            self._store_user_in_rds(cognito_sub, username, email)
            
            return {
                'status': 'success',
                'message': 'User registration successful',
                'user_sub': cognito_sub
            }
        except ClientError as e:
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def _store_user_in_rds(self, cognito_sub, username, email):
        """Store user data in RDS database"""
        try:
            # Check if user already exists
            existing_user = db.query(
                "SELECT * FROM users WHERE cognito_sub = %s OR username = %s OR email = %s", 
                (cognito_sub, username, email)
            )
            
            if existing_user:
                logger.info(f"User already exists in RDS with cognito_sub: {cognito_sub}")
                return
                
            # Insert user into RDS
            user_id = db.insert(
                "INSERT INTO users (cognito_sub, username, email) VALUES (%s, %s, %s)",
                (cognito_sub, username, email)
            )
            
            if user_id:
                logger.info(f"User stored in RDS with ID: {user_id}")
                
                # Create default preferences
                db.insert(
                    "INSERT INTO user_preferences (user_id, theme, email_notifications) VALUES (%s, %s, %s)",
                    (user_id, 'light', False)
                )
                logger.info(f"Default preferences created for user ID: {user_id}")
            else:
                logger.error(f"Failed to store user in RDS: {username}")
                
        except Exception as e:
            logger.error(f"Error storing user in RDS: {str(e)}")

    def confirm_registration(self, username, confirmation_code):
        """Confirm user registration with verification code"""
        try:
            self.client.confirm_sign_up(
                ClientId=self.client_id,
                SecretHash=self._get_secret_hash(username),
                Username=username,
                ConfirmationCode=confirmation_code
            )
            return {
                'status': 'success',
                'message': 'User confirmation successful'
            }
        except ClientError as e:
            return {
                'status': 'error',
                'message': str(e)
            }

    def login(self, username, password):
        """Authenticate a user and return JWT tokens from Cognito"""
        try:
            response = self.client.initiate_auth(
                ClientId=self.client_id,
                AuthFlow='USER_PASSWORD_AUTH',
                AuthParameters={
                    'USERNAME': username,
                    'PASSWORD': password,
                    'SECRET_HASH': self._get_secret_hash(username)
                }
            )
            
            # Get user info from RDS
            user_data = self._get_user_from_rds(username)
            
            # Extract tokens from response
            access_token = response['AuthenticationResult']['AccessToken']
            id_token = response['AuthenticationResult']['IdToken'] 
            refresh_token = response['AuthenticationResult']['RefreshToken']
            expires_in = response['AuthenticationResult']['ExpiresIn']
            
            return {
                'status': 'success',
                'message': 'Login successful',
                'user_id': user_data.get('id') if user_data else None,
                'username': username,
                'email': user_data.get('email') if user_data else None,
                'access_token': access_token,
                'id_token': id_token,
                'refresh_token': refresh_token,
                'expires_in': expires_in
            }
        except ClientError as e:
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def refresh_token(self, refresh_token):
        """Refresh the user's JWT tokens"""
        try:
            response = self.client.initiate_auth(
                ClientId=self.client_id,
                AuthFlow='REFRESH_TOKEN_AUTH',
                AuthParameters={
                    'REFRESH_TOKEN': refresh_token,
                    'SECRET_HASH': self._get_secret_hash(self._get_username_from_refresh_token(refresh_token))
                }
            )
            
            return {
                'status': 'success',
                'message': 'Token refreshed successfully',
                'access_token': response['AuthenticationResult']['AccessToken'],
                'id_token': response['AuthenticationResult']['IdToken'],
                'expires_in': response['AuthenticationResult']['ExpiresIn']
            }
        except ClientError as e:
            return {
                'status': 'error',
                'message': str(e)
            } 
    
    def _get_username_from_refresh_token(self, refresh_token):
        """Extract username from refresh token"""
        try:
            # This is a placeholder - in real implementation, you would need to 
            # use the refresh token to get the username, possibly by making a Cognito API call
            # or by having stored the username-token mapping
            user_data = db.query("SELECT username FROM users WHERE refresh_token = %s", (refresh_token,))
            if user_data and len(user_data) > 0:
                return user_data[0]['username']
            return None
        except Exception as e:
            logger.error(f"Error extracting username from refresh token: {str(e)}")
            return None
    
    def _get_user_from_rds(self, username):
        """Get user data from RDS"""
        try:
            user_data = db.query("SELECT * FROM users WHERE username = %s", (username,))
            if user_data and len(user_data) > 0:
                return user_data[0]
            return None
        except Exception as e:
            logger.error(f"Error fetching user from RDS: {str(e)}")
            return None
    
    def get_user_by_id(self, user_id):
        """Get user details by ID"""
        try:
            user_data = db.query("SELECT * FROM users WHERE id = %s", (user_id,))
            if user_data and len(user_data) > 0:
                return {
                    'status': 'success',
                    'data': user_data[0],
                    'message': 'User found'
                }
            return {
                'status': 'error',
                'message': 'User not found'
            }
        except Exception as e:
            logger.error(f"Error fetching user by ID from RDS: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def get_user_preferences(self, user_id):
        """Get user preferences"""
        try:
            prefs = db.query("SELECT * FROM user_preferences WHERE user_id = %s", (user_id,))
            if prefs and len(prefs) > 0:
                return {
                    'status': 'success',
                    'data': prefs[0],
                    'message': 'Preferences found'
                }
            return {
                'status': 'error',
                'message': 'Preferences not found'
            }
        except Exception as e:
            logger.error(f"Error fetching user preferences from RDS: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def update_user_preferences(self, user_id, preferences):
        """Update user preferences"""
        try:
            # Check if preferences exist
            existing_prefs = db.query("SELECT * FROM user_preferences WHERE user_id = %s", (user_id,))
            
            if existing_prefs and len(existing_prefs) > 0:
                # Update existing preferences
                update_fields = []
                update_values = []
                
                for key, value in preferences.items():
                    if key in ['theme', 'default_dashboard', 'email_notifications']:
                        update_fields.append(f"{key} = %s")
                        update_values.append(value)
                
                if update_fields:
                    sql = f"UPDATE user_preferences SET {', '.join(update_fields)} WHERE user_id = %s"
                    update_values.append(user_id)
                    
                    result = db.execute(sql, tuple(update_values))
                    if result:
                        return {
                            'status': 'success',
                            'message': 'Preferences updated'
                        }
            
            return {
                'status': 'error',
                'message': 'Failed to update preferences'
            }
        except Exception as e:
            logger.error(f"Error updating user preferences in RDS: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            } 