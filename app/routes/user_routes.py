from flask import Blueprint, request, jsonify, session
from app.services.user_service import UserService
from functools import wraps
import jwt
from app.config import Config
import logging
import json
from datetime import datetime, timedelta
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

user_bp = Blueprint('user', __name__)
user_service = UserService()

# Create a cache for the JWT keys
jwks_cache = {
    'keys': None,
    'last_updated': None
}

def validate_request_data(*required_fields):
    """Decorator to validate required fields in request data"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            data = request.get_json()
            if not data:
                return jsonify({'status': 'error', 'message': 'No data provided'}), 400
            
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                return jsonify({
                    'status': 'error',
                    'message': f'Missing required fields: {", ".join(missing_fields)}'
                }), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_cognito_jwks():
    """Fetch the JSON Web Key Set from Cognito for token verification"""
    global jwks_cache
    
    # Return cached keys if available and not expired (cache for 24 hours)
    if (jwks_cache['keys'] is not None and jwks_cache['last_updated'] is not None and
            datetime.now() - jwks_cache['last_updated'] < timedelta(hours=24)):
        return jwks_cache['keys']
    
    try:
        region = Config.AWS_REGION
        pool_id = Config.COGNITO_USER_POOL_ID
        
        if not region or not pool_id:
            logger.error("AWS_REGION or COGNITO_USER_POOL_ID not configured")
            return None
            
        url = f'https://cognito-idp.{region}.amazonaws.com/{pool_id}/.well-known/jwks.json'
        response = requests.get(url)
        
        if response.status_code != 200:
            logger.error(f"Failed to get JWKS from Cognito: {response.status_code}")
            return None
            
        jwks = response.json()
        
        # Cache the keys
        jwks_cache['keys'] = jwks
        jwks_cache['last_updated'] = datetime.now()
        
        return jwks
    except Exception as e:
        logger.error(f"Error fetching Cognito JWKS: {str(e)}")
        return None

def verify_jwt_token(token):
    """Verify the JWT token from Cognito"""
    try:
        # Get the key id from the token header
        header = jwt.get_unverified_header(token)
        kid = header['kid']
        
        # Get the JWKS
        jwks = get_cognito_jwks()
        if not jwks:
            return None
            
        # Find the key matching the kid
        key = None
        for k in jwks['keys']:
            if k['kid'] == kid:
                key = k
                break
                
        if not key:
            logger.error(f"No matching key found for kid: {kid}")
            return None
            
        # Convert the key to PEM format
        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
        
        # Verify the token
        payload = jwt.decode(
            token,
            public_key,
            algorithms=['RS256'],
            options={"verify_exp": True, "verify_aud": False},
            audience=Config.COGNITO_APP_CLIENT_ID
        )
        
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.error(f"Invalid token: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error verifying token: {str(e)}")
        return None

def jwt_required(f):
    """Decorator to require JWT token for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Skip auth if BYPASS_AUTH is set (for testing)
        
        from flask import current_app
        if current_app.config.get('BYPASS_AUTH', False):
            # Set a test user for the request
            request.user = {
                'user_id': 'test_user_123',
                'username': 'testuser',
                'email': 'test@example.com',
                'token_payload': {}
            }
            return f(*args, **kwargs)
        
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({
                'status': 'error',
                'message': 'Authorization header is missing'
            }), 401
            
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return jsonify({
                'status': 'error',
                'message': 'Authorization header must be in format "Bearer token"'
            }), 401
            
        token = parts[1]
        
        # Verify token
        payload = verify_jwt_token(token)
        if not payload:
            return jsonify({
                'status': 'error',
                'message': 'Invalid or expired token'
            }), 401
            
        # Add user info to request context
        request.user = {
            'user_id': payload.get('sub'),
            'username': payload.get('username', payload.get('cognito:username')),
            'email': payload.get('email'),
            'token_payload': payload
        }
        
        return f(*args, **kwargs)
    return decorated_function

def login_required(f):
    """Decorator to require login for routes - checks both JWT and session"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # First try JWT authentication
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split()[1]
            payload = verify_jwt_token(token)
            if payload:
                request.user = {
                    'user_id': payload.get('sub'),
                    'username': payload.get('username', payload.get('cognito:username')),
                    'email': payload.get('email'),
                    'token_payload': payload
                }
                return f(*args, **kwargs)
        
        # Fallback to session
        if 'user_id' not in session:
            return jsonify({
                'status': 'error',
                'message': 'Authentication required'
            }), 401
        return f(*args, **kwargs)
    return decorated_function

@user_bp.route('/register', methods=['POST'])
@validate_request_data('username', 'password', 'email')
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        email = data.get('email')
        
        if not username or not password or not email:
            return jsonify({
                'status': 'error',
                'message': 'Username, password, and email are required'
            }), 400
            
        result = user_service.register_user(username, password, email)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in register: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@user_bp.route('/confirm', methods=['POST'])
@validate_request_data('username', 'confirmation_code')
def confirm_registration():
    """Confirm user registration"""
    data = request.get_json()
    result = user_service.confirm_registration(
        username=data['username'],
        confirmation_code=data['confirmation_code']
    )
    
    if result['status'] == 'success':
        return jsonify(result), 200
    return jsonify(result), 400

@user_bp.route('/login', methods=['POST'])
@validate_request_data('username', 'password')
def login():
    """Login user"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({
                'status': 'error',
                'message': 'Username and password are required'
            }), 400
            
        result = user_service.login(username, password)
        
        if result['status'] == 'success':
            # Set session data for backward compatibility
            session['user_id'] = result.get('user_id')
            session['username'] = username
            session.permanent = True
            
            # Get JWT tokens from Cognito
            tokens = {
                'id_token': result.get('id_token'),
                'access_token': result.get('access_token'),
                'refresh_token': result.get('refresh_token')
            }
            
            # Create response with tokens
            response = jsonify({
                'status': 'success',
                'data': {
                    'user_id': result.get('user_id'),
                    'username': username,
                    'profile': result.get('user_data'),
                    'tokens': tokens
                },
                'message': 'Login successful'
            })
            
            return response
            
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in login: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@user_bp.route('/logout', methods=['POST'])
def logout():
    """Logout user"""
    try:
        # Clear the session
        session.clear()
        logger.info("User logged out successfully")
        return jsonify({
            'status': 'success',
            'message': 'Logged out successfully'
        })
    except Exception as e:
        logger.error(f"Error in logout: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@user_bp.route('/check-auth', methods=['GET'])
def check_auth():
    """Check if user is authenticated"""
    try:
        # First try JWT authentication
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split()[1]
            payload = verify_jwt_token(token)
            
            if payload:
                user_id = payload.get('sub')
                username = payload.get('username', payload.get('cognito:username'))
                email = payload.get('email')
                
                # Get user data from the database
                user_data = user_service.get_user_by_id(user_id)
                
                return jsonify({
                    'status': 'success',
                    'data': {
                        'user_id': user_id,
                        'username': username,
                        'email': email,
                        'profile': user_data.get('data', {})
                    },
                    'message': 'User is authenticated with JWT'
                })
        
        # Fallback to session
        if 'user_id' in session:
            # Get user data from the database
            user_data = user_service.get_user_by_id(session['user_id'])
            
            return jsonify({
                'status': 'success',
                'data': {
                    'user_id': session['user_id'],
                    'username': session['username'],
                    'profile': user_data.get('data', {})
                },
                'message': 'User is authenticated with session'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'User is not authenticated'
            }), 401
    except Exception as e:
        logger.error(f"Error in check_auth: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@user_bp.route('/profile', methods=['GET'])
@login_required
def get_profile():
    """Get user profile"""
    try:
        # Check if request has user from JWT authentication
        if hasattr(request, 'user'):
            user_id = request.user['user_id']
        else:
            user_id = session.get('user_id')
            
        user_data = user_service.get_user_by_id(user_id)
        
        if user_data['status'] == 'success':
            return jsonify(user_data)
        
        return jsonify(user_data), 404
    except Exception as e:
        logger.error(f"Error getting user profile: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@user_bp.route('/preferences', methods=['GET'])
@login_required
def get_preferences():
    """Get user preferences"""
    try:
        # Check if request has user from JWT authentication
        if hasattr(request, 'user'):
            user_id = request.user['user_id']
        else:
            user_id = session.get('user_id')
            
        preferences = user_service.get_user_preferences(user_id)
        
        if preferences['status'] == 'success':
            return jsonify(preferences)
        
        return jsonify(preferences), 404
    except Exception as e:
        logger.error(f"Error getting user preferences: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@user_bp.route('/preferences', methods=['PUT'])
@login_required
@validate_request_data('preferences')
def update_preferences():
    """Update user preferences"""
    try:
        # Check if request has user from JWT authentication
        if hasattr(request, 'user'):
            user_id = request.user['user_id']
        else:
            user_id = session.get('user_id')
            
        data = request.get_json()
        preferences = data.get('preferences', {})
        
        result = user_service.update_user_preferences(user_id, preferences)
        
        if result['status'] == 'success':
            return jsonify(result)
        
        return jsonify(result), 400
    except Exception as e:
        logger.error(f"Error updating user preferences: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@user_bp.route('/refresh-token', methods=['POST'])
@validate_request_data('refresh_token')
def refresh_token():
    """Refresh the access token using refresh token"""
    try:
        data = request.get_json()
        refresh_token = data.get('refresh_token')
        
        result = user_service.refresh_token(refresh_token)
        
        if result['status'] == 'success':
            return jsonify(result)
        
        return jsonify(result), 401
    except Exception as e:
        logger.error(f"Error refreshing token: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500 