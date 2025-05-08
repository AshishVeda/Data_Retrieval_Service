import logging
from app.services.dynamodb_service import dynamodb_service
from app.database import db

logger = logging.getLogger(__name__)

class ChatHistoryService:
    def __init__(self):
        """Initialize the chat history service"""
        logger.info("Chat History Service initialized")
    
    def store_chat(self, user_id, query, response, metadata=None):
        """Store a chat interaction in history. user_id is always the Cognito sub (UUID)."""
        try:
            # Verify the user exists in the MySQL database by cognito_sub
            user_exists = self._verify_user_exists(user_id)
            
            if not user_exists:
                logger.warning(f"Attempted to store chat for non-existent user: {user_id}")
                return {
                    'status': 'error',
                    'message': f'User with ID {user_id} does not exist'
                }
            
            # Store the chat in DynamoDB
            result = dynamodb_service.store_chat(user_id, query, response, metadata)
            return result
            
        except Exception as e:
            logger.error(f"Error storing chat history: {str(e)}")
            return {
                'status': 'error',
                'message': f'Failed to store chat history: {str(e)}'
            }
    
    def get_chat_history(self, user_id, limit=10):
        """Get chat history for a user. user_id is always the Cognito sub (UUID)."""
        try:
            # Verify the user exists in the MySQL database by cognito_sub
            user_exists = self._verify_user_exists(user_id)
            
            if not user_exists:
                logger.warning(f"Attempted to retrieve chat for non-existent user: {user_id}")
                return {
                    'status': 'error',
                    'message': f'User with ID {user_id} does not exist'
                }
            
            # Get chat history from DynamoDB
            result = dynamodb_service.get_chat_history(user_id, limit)
            return result
            
        except Exception as e:
            logger.error(f"Error retrieving chat history: {str(e)}")
            return {
                'status': 'error',
                'message': f'Failed to retrieve chat history: {str(e)}'
            }
    
    def format_chat_history_for_prompt(self, chat_history, max_entries=5):
        """Format chat history for inclusion in an LLM prompt"""
        try:
            # Sort chats by timestamp (newest first)
            sorted_chats = sorted(chat_history, key=lambda x: x.get('timestamp', 0), reverse=True)
            
            # Take only the most recent entries
            recent_chats = sorted_chats[:max_entries]
            
            # Reverse to get chronological order (oldest first)
            recent_chats.reverse()
            
            # Format for prompt
            formatted_history = []
            for chat in recent_chats:
                formatted_history.append(f"User: {chat.get('query', '')}")
                formatted_history.append(f"Assistant: {chat.get('response', '')}")
            
            # Join with double newlines for better formatting
            return "\n\n".join(formatted_history)
            
        except Exception as e:
            logger.error(f"Error formatting chat history for prompt: {str(e)}")
            return "Error retrieving chat history."
    
    def _verify_user_exists(self, user_id):
        """Verify that a user exists in the MySQL database by cognito_sub (UUID)"""
        try:
            result = db.query("SELECT id FROM users WHERE cognito_sub = %s", (user_id,))
            return result and len(result) > 0
        except Exception as e:
            logger.error(f"Error verifying user existence: {str(e)}")
            return False

# Create a singleton instance
chat_history_service = ChatHistoryService() 