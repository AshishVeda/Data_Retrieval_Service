import boto3
from botocore.exceptions import ClientError
from app.config import Config
import hmac
import base64
import hashlib

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
        """Register a new user in Cognito"""
        try:
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
            return {
                'status': 'success',
                'message': 'User registration successful',
                'user_sub': response['UserSub']
            }
        except ClientError as e:
            return {
                'status': 'error',
                'message': str(e)
            }

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
        """Authenticate a user and return tokens"""
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
            return {
                'status': 'success',
                'message': 'Login successful',
                'user_id': response['AuthenticationResult']['IdToken'],
                'tokens': {
                    'access_token': response['AuthenticationResult']['AccessToken'],
                    'id_token': response['AuthenticationResult']['IdToken'],
                    'refresh_token': response['AuthenticationResult']['RefreshToken']
                }
            }
        except ClientError as e:
            return {
                'status': 'error',
                'message': str(e)
            } 