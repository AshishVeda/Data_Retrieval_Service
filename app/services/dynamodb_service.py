import boto3
import json
import logging
import time
import uuid
from datetime import datetime
from app.config import Config

logger = logging.getLogger(__name__)

class DynamoDBService:
    def __init__(self):
        """Initialize the DynamoDB service with AWS credentials"""
        # Connect directly to AWS DynamoDB
        self.dynamodb = boto3.resource(
            'dynamodb',
            region_name=Config.AWS_REGION,
            aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY
        )
        
        # Set the table name
        self.table_name = Config.DYNAMODB_CHAT_TABLE
        self._ensure_table_exists()
        
        self.table = self.dynamodb.Table(self.table_name)
        logger.info(f"DynamoDB service initialized with table: {self.table_name}")
        
    def _ensure_table_exists(self):
        """Create the chat history table if it doesn't exist"""
        try:
            existing_tables = self.dynamodb.meta.client.list_tables()['TableNames']
            
            if self.table_name not in existing_tables:
                logger.info(f"Creating DynamoDB table: {self.table_name}")
                
                # Create the table in AWS
                table = self.dynamodb.create_table(
                    TableName=self.table_name,
                    KeySchema=[
                        {'AttributeName': 'user_id', 'KeyType': 'HASH'},  # Partition key
                        {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}  # Sort key
                    ],
                    AttributeDefinitions=[
                        {'AttributeName': 'user_id', 'AttributeType': 'S'},
                        {'AttributeName': 'timestamp', 'AttributeType': 'N'}
                    ],
                    ProvisionedThroughput={
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                )
                
                # Wait until the table exists
                table.meta.client.get_waiter('table_exists').wait(TableName=self.table_name)
                logger.info(f"Table {self.table_name} created successfully")
            else:
                logger.info(f"Table {self.table_name} already exists in AWS DynamoDB")
                
        except Exception as e:
            logger.error(f"Error creating DynamoDB table: {str(e)}")
            raise
            
    def store_chat(self, user_id, query, response, metadata=None):
        """Store a chat interaction in DynamoDB"""
        try:
            timestamp = int(time.time() * 1000)  # Current time in milliseconds
            chat_id = str(uuid.uuid4())
            
            # Prepare item to store
            item = {
                'user_id': str(user_id),
                'timestamp': timestamp,
                'chat_id': chat_id,
                'query': query,
                'response': response,
                'date': datetime.now().isoformat()
            }
            
            # Add metadata if provided
            if metadata:
                item['metadata'] = json.dumps(metadata)
                
            # Store in DynamoDB
            self.table.put_item(Item=item)
            
            logger.info(f"Stored chat for user {user_id} with chat_id {chat_id}")
            return {
                'status': 'success',
                'chat_id': chat_id,
                'message': 'Chat stored successfully'
            }
            
        except Exception as e:
            logger.error(f"Error storing chat in DynamoDB: {str(e)}")
            return {
                'status': 'error',
                'message': f'Failed to store chat: {str(e)}'
            }
            
    def get_chat_history(self, user_id, limit=10):
        """Retrieve chat history for a user"""
        try:
            response = self.table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key('user_id').eq(str(user_id)),
                ScanIndexForward=False,  # Sort descending (newest first)
                Limit=limit
            )
            
            chats = response.get('Items', [])
            
            logger.info(f"Retrieved {len(chats)} chat entries for user {user_id}")
            return {
                'status': 'success',
                'data': chats,
                'message': f'Retrieved {len(chats)} chat entries'
            }
            
        except Exception as e:
            logger.error(f"Error retrieving chat history from DynamoDB: {str(e)}")
            return {
                'status': 'error',
                'message': f'Failed to retrieve chat history: {str(e)}'
            }
            
    def get_chat_by_id(self, user_id, chat_id):
        """Retrieve a specific chat by ID"""
        try:
            # Since we don't have a global secondary index on chat_id,
            # we need to scan the table and filter results
            response = self.table.scan(
                FilterExpression=boto3.dynamodb.conditions.Key('user_id').eq(str(user_id)) & 
                                 boto3.dynamodb.conditions.Key('chat_id').eq(chat_id)
            )
            
            items = response.get('Items', [])
            
            if not items:
                return {
                    'status': 'error',
                    'message': f'Chat not found with id {chat_id}'
                }
                
            return {
                'status': 'success',
                'data': items[0],
                'message': 'Chat retrieved successfully'
            }
            
        except Exception as e:
            logger.error(f"Error retrieving chat by ID from DynamoDB: {str(e)}")
            return {
                'status': 'error',
                'message': f'Failed to retrieve chat: {str(e)}'
            }
            
    def delete_chat(self, user_id, timestamp):
        """Delete a specific chat entry"""
        try:
            self.table.delete_item(
                Key={
                    'user_id': str(user_id),
                    'timestamp': timestamp
                }
            )
            
            logger.info(f"Deleted chat for user {user_id} with timestamp {timestamp}")
            return {
                'status': 'success',
                'message': 'Chat deleted successfully'
            }
            
        except Exception as e:
            logger.error(f"Error deleting chat from DynamoDB: {str(e)}")
            return {
                'status': 'error',
                'message': f'Failed to delete chat: {str(e)}'
            }

# Create a singleton instance
dynamodb_service = DynamoDBService() 