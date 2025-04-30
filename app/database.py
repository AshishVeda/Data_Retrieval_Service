import os
import pymysql
import logging
from pymysql.cursors import DictCursor
from app.config import Config

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.connection = None
        self.connect()
        
    def connect(self):
        """Establish a connection to the MySQL RDS database"""
        try:
            # First connect without specifying a database
            initial_connection = pymysql.connect(
                host=Config.RDS_HOST,
                user=Config.RDS_USER,
                password=Config.RDS_PASSWORD,
                charset='utf8mb4',
                connect_timeout=5
            )
            
            # Create the database if it doesn't exist
            with initial_connection.cursor() as cursor:
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS {Config.RDS_DB_NAME}")
                logger.info(f"Database {Config.RDS_DB_NAME} created or verified")
            
            initial_connection.close()
            
            # Now connect to the specific database
            self.connection = pymysql.connect(
                host=Config.RDS_HOST,
                user=Config.RDS_USER,
                password=Config.RDS_PASSWORD,
                db=Config.RDS_DB_NAME,
                charset='utf8mb4',
                cursorclass=DictCursor,
                connect_timeout=5
            )
            logger.info("Database connection established")
            
            # Create tables if they don't exist
            self._create_tables()
            
        except Exception as e:
            logger.error(f"Failed to connect to database: {str(e)}")
            self.connection = None
    
    def _create_tables(self):
        """Create necessary tables if they don't exist"""
        try:
            with self.connection.cursor() as cursor:
                # Create users table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    cognito_sub VARCHAR(255) NOT NULL UNIQUE,
                    username VARCHAR(255) NOT NULL UNIQUE,
                    email VARCHAR(255) NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                );
                """)
                
                # Create portfolios table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS portfolios (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );
                """)
                
                # Create portfolio_stocks table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS portfolio_stocks (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    portfolio_id INT NOT NULL,
                    symbol VARCHAR(20) NOT NULL,
                    quantity DECIMAL(10,2) NOT NULL,
                    purchase_price DECIMAL(10,2) NOT NULL,
                    purchase_date DATE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE
                );
                """)
                
                # Create user_preferences table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    default_dashboard VARCHAR(255),
                    theme VARCHAR(50) DEFAULT 'light',
                    email_notifications BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );
                """)
                
                self.connection.commit()
                logger.info("Database tables created or verified")
                
        except Exception as e:
            logger.error(f"Error creating tables: {str(e)}")
    
    def query(self, sql, params=None):
        """Execute a query and return results"""
        if not self.connection:
            self.connect()
            
        if not self.connection:
            logger.error("Cannot execute query - no database connection")
            return None
            
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql, params or ())
                self.connection.commit()
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Query error: {str(e)}, SQL: {sql}")
            self.connection.rollback()
            return None
    
    def execute(self, sql, params=None):
        """Execute a command (like INSERT, UPDATE, DELETE)"""
        if not self.connection:
            self.connect()
            
        if not self.connection:
            logger.error("Cannot execute command - no database connection")
            return False
            
        try:
            with self.connection.cursor() as cursor:
                result = cursor.execute(sql, params or ())
                self.connection.commit()
                return result
        except Exception as e:
            logger.error(f"Execution error: {str(e)}, SQL: {sql}")
            self.connection.rollback()
            return False
    
    def insert(self, sql, params=None):
        """Insert data and return the last inserted ID"""
        if not self.connection:
            self.connect()
            
        if not self.connection:
            logger.error("Cannot execute insert - no database connection")
            return None
            
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql, params or ())
                self.connection.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Insert error: {str(e)}, SQL: {sql}")
            self.connection.rollback()
            return None
    
    def close(self):
        """Close the database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Database connection closed")

# Create a singleton instance
db = Database() 