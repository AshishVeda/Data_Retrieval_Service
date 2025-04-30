from flask import Blueprint, request, jsonify, session
from app.services.user_service import UserService
from functools import wraps
import jwt
from app.config import Config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

user_bp = Blueprint('user', __name__)
user_service = UserService()

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

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
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
            # Set session data
            session['user_id'] = result.get('user_id')
            session['username'] = username
            session.permanent = True  # Make session permanent
            
            # Create response
            response = jsonify({
                'status': 'success',
                'data': {
                    'user_id': session['user_id'],
                    'username': username,
                    'profile': result.get('user_data')
                },
                'message': 'Login successful'
            })
            
            # Flask will automatically set the session cookie
            # No need to manually set the cookie header
            
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
                'message': 'User is authenticated'
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