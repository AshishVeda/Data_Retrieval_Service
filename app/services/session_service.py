from flask import session
from datetime import datetime

class SessionService:
    @staticmethod
    def is_first_time_call(api_name, symbol=None):
        """Check if this is the first time an API is being called for a specific symbol"""
        if 'api_calls' not in session:
            session['api_calls'] = {}
        
        cache_key = f"{api_name}_{symbol}" if symbol else api_name
        
        if cache_key not in session['api_calls']:
            session['api_calls'][cache_key] = {
                'first_call': True,
                'timestamp': datetime.now().isoformat()
            }
            return True
        return False

    @staticmethod
    def mark_api_called(api_name, symbol=None):
        """Mark an API as called for a specific symbol"""
        if 'api_calls' not in session:
            session['api_calls'] = {}
        
        cache_key = f"{api_name}_{symbol}" if symbol else api_name
        
        session['api_calls'][cache_key] = {
            'first_call': False,
            'timestamp': datetime.now().isoformat()
        }
        session.modified = True 