import chromadb
from chromadb.config import Settings
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VectorService:
    def __init__(self):
        # Initialize ChromaDB client with persistent storage
        try:
            # Ensure data directory exists
            data_dir = "data/chroma"
            os.makedirs(data_dir, exist_ok=True)
            
            self.client = chromadb.PersistentClient(
                path=data_dir,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                    is_persistent=True
                )
            )
            
            # Create or get the news collection
            self.news_collection = self.client.get_or_create_collection(
                name="stock_news",
                metadata={"hnsw:space": "cosine"}
            )
            
            logger.info("VectorService initialized with ChromaDB persistent storage")
        except Exception as e:
            logger.error(f"Error initializing ChromaDB: {str(e)}")
            # Fallback to in-memory client if persistent fails
            try:
                self.client = chromadb.Client(Settings(
                    anonymized_telemetry=False
                ))
                
                # Create or get the news collection
                self.news_collection = self.client.get_or_create_collection(
                    name="stock_news",
                    metadata={"hnsw:space": "cosine"}
                )
                logger.warning("VectorService using in-memory fallback (data will not persist)")
            except Exception as fallback_error:
                logger.critical(f"Failed to initialize even fallback ChromaDB: {str(fallback_error)}")
                # Create dummy object to prevent errors
                self.client = None
                self.news_collection = None

    def store_news(self, news_items: List[Dict]) -> bool:
        """Store news items in ChromaDB and clean up old news"""
        try:
            if not news_items:
                return False

            # First, clean up news older than 3 days
            self.cleanup_old_news(days=3)

            # Prepare data for ChromaDB
            ids = []
            documents = []
            metadatas = []

            for item in news_items:
                # Create a unique ID for each news item
                news_id = f"{item['symbol']}_{item['published']}_{hash(item['title'])}"
                
                # Combine title and summary for embedding
                document_text = item['title']
                if 'summary' in item:
                    document_text += " " + item['summary']
                
                # Prepare metadata
                metadata = {
                    'symbol': item['symbol'],
                    'title': item['title'],
                    'published': item['published'],
                    'source': item.get('source', 'Unknown'),
                    'timestamp': item.get('timestamp', datetime.now().isoformat())
                }
                
                # Handle url/link field variations
                if 'url' in item:
                    metadata['url'] = item['url']
                elif 'link' in item:
                    metadata['url'] = item['link']
                else:
                    metadata['url'] = ''

                ids.append(news_id)
                documents.append(document_text)
                metadatas.append(metadata)

            # Add to ChromaDB
            self.news_collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )

            return True

        except Exception as e:
            logger.error(f"Error storing news items: {str(e)}")
            return False

    def get_news_by_symbol(self, symbol: str, limit: int = 10) -> List[Dict]:
        """Retrieve news items for a specific symbol"""
        try:
            # Get all items to ensure we're not missing any
            if limit > 1000:
                limit = 1000
            
            # Query with just the symbol filter, without date filtering
            results = self.news_collection.get(
                where={"symbol": symbol},
                limit=limit
            )

            # Format results
            news_items = []
            for i in range(len(results['ids'])):
                news_items.append({
                    'id': results['ids'][i],
                    'title': results['metadatas'][i]['title'],
                    'url': results['metadatas'][i].get('url', results['metadatas'][i].get('link', '')),
                    'published': results['metadatas'][i]['published'],
                    'source': results['metadatas'][i].get('source', 'Unknown'),
                    'symbol': results['metadatas'][i]['symbol']
                })

            return news_items

        except Exception as e:
            logger.error(f"Error retrieving news for {symbol}: {str(e)}")
            return []

    def search_similar_news(self, query: str, symbol: Optional[str] = None, limit: int = 5) -> List[Dict]:
        """Search for similar news items based on a query"""
        try:
            logger.info(f"VECTOR-SEARCH: Running semantic search with query: '{query}'")
            
            # Build where clause based only on symbol, not timestamp
            where_clause = {}
            if symbol:
                where_clause = {"symbol": symbol}
            
            logger.info(f"VECTOR-SEARCH: Using where clause: {where_clause}")
            
            # First check if we have any data matching the filters
            check_results = self.news_collection.get(
                where=where_clause,
                limit=1
            )
            
            if not check_results or len(check_results['ids']) == 0:
                logger.warning(f"VECTOR-SEARCH: No articles found matching the filter criteria")
                return []
                
            # Proceed with semantic search
            results = self.news_collection.query(
                query_texts=[query],
                where=where_clause,
                n_results=limit
            )
            
            logger.info(f"VECTOR-SEARCH: Query returned {len(results['ids'][0]) if results and 'ids' in results and results['ids'] else 0} results")

            # Format results
            similar_news = []
            if results and 'ids' in results and results['ids'] and len(results['ids'][0]) > 0:
                # Get current time for filtering recent articles (use last 30 days instead of 3)
                now = datetime.now()
                cutoff_date = now - timedelta(days=30)  # Increased from 3 to 30 days for testing
                
                for i in range(len(results['ids'][0])):
                    try:
                        # Parse the published date to filter out old articles
                        published_str = results['metadatas'][0][i]['published']
                        
                        # Verify published date format, handle multiple formats
                        try:
                            published_date = datetime.fromisoformat(published_str)
                        except ValueError:
                            # Try alternative date formats if ISO format fails
                            try:
                                # Try Unix timestamp
                                published_date = datetime.fromtimestamp(float(published_str))
                            except ValueError:
                                # As a fallback, don't filter by date
                                published_date = now
                        
                        # Skip articles older than cutoff date, less strict for semantic search
                        # Temporarily disabled date filtering for debugging
                        # if published_date < cutoff_date:
                        #     logger.debug(f"VECTOR-SEARCH: Skipping old article from {published_str}")
                        #     continue
                            
                        # Extract link or URL
                        link = "#"
                        if 'url' in results['metadatas'][0][i]:
                            link = results['metadatas'][0][i]['url']
                        elif 'link' in results['metadatas'][0][i]:
                            link = results['metadatas'][0][i]['link']
                            
                        article = {
                            'id': results['ids'][0][i],
                            'title': results['metadatas'][0][i]['title'],
                            'url': link,
                            'published': published_str,
                            'source': results['metadatas'][0][i].get('source', 'Unknown'),
                            'symbol': results['metadatas'][0][i]['symbol'],
                            'similarity': results['distances'][0][i] if 'distances' in results else 0,
                            'link': link,
                            'summary': results['metadatas'][0][i].get('summary', 'No summary available')
                        }
                        similar_news.append(article)
                        logger.info(f"VECTOR-SEARCH: Article '{article['title'][:30]}...' added to results (published: {published_str})")
                    except Exception as e:
                        logger.warning(f"VECTOR-SEARCH: Error formatting article: {str(e)}")
                        continue
                
                logger.info(f"VECTOR-SEARCH: Formatted {len(similar_news)} articles for response")
                if similar_news:
                    logger.info(f"VECTOR-SEARCH: First result title: '{similar_news[0]['title']}' similarity: {similar_news[0]['similarity']}")
            else:
                logger.warning(f"VECTOR-SEARCH: No similar articles found for query '{query}'")

            # Return the most relevant articles first (lowest distance score = most similar)
            return sorted(similar_news, key=lambda x: x.get('similarity', 1.0))

        except Exception as e:
            logger.error(f"VECTOR-SEARCH: Error searching similar news: {str(e)}")
            return []

    def cleanup_old_news(self, days: int = 3):
        """Remove news items older than specified days (default 3 days)"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # Get all news items
            results = self.news_collection.get()
            
            # Find IDs of old news items
            old_ids = []
            for i in range(len(results['ids'])):
                if results['metadatas'][i]['timestamp'] < cutoff_date:
                    old_ids.append(results['ids'][i])

            if old_ids:
                # Delete old news items
                self.news_collection.delete(ids=old_ids)
                logger.info(f"Deleted {len(old_ids)} old news items")

        except Exception as e:
            logger.error(f"Error cleaning up old news: {str(e)}")

    def store_social_data(self, symbol: str, social_data: List[Dict]) -> bool:
        """Store social media data in ChromaDB"""
        try:
            if not social_data:
                return False

            # Prepare data for ChromaDB
            ids = []
            documents = []
            metadatas = []

            for item in social_data:
                # Create a unique ID for each post
                post_id = f"social_{symbol}_{item['created_utc']}_{hash(item['title'])}"
                
                # Combine title and comments for embedding
                comments_text = " ".join(comment['text'] for comment in item['comments'])
                document = f"{item['title']} {comments_text}"
                
                # Prepare metadata
                metadata = {
                    'symbol': symbol,
                    'title': item['title'],
                    'url': item['url'],
                    'score': item['score'],
                    'created_utc': item['created_utc'],
                    'sentiment': item['sentiment'],
                    'comment_count': len(item['comments']),
                    'timestamp': datetime.now().isoformat()
                }

                ids.append(post_id)
                documents.append(document)
                metadatas.append(metadata)

            # Add to ChromaDB
            self.news_collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )

            return True

        except Exception as e:
            logger.error(f"Error storing social media data: {str(e)}")
            return False

    def get_social_data(self, symbol: str, limit: int = 10) -> List[Dict]:
        """Retrieve social media data for a specific symbol"""
        try:
            # Get current time and 3 days ago
            now = datetime.now()
            three_days_ago = (now - timedelta(days=3)).isoformat()

            # Query with time filter
            results = self.news_collection.get(
                where={
                    "$and": [
                        {"symbol": symbol},
                        {"timestamp": {"$gte": three_days_ago}}
                    ]
                },
                limit=limit
            )

            # Format results
            social_data = []
            for i in range(len(results['ids'])):
                social_data.append({
                    'id': results['ids'][i],
                    'title': results['metadatas'][i]['title'],
                    'url': results['metadatas'][i]['url'],
                    'score': results['metadatas'][i]['score'],
                    'created_utc': results['metadatas'][i]['created_utc'],
                    'sentiment': results['metadatas'][i]['sentiment'],
                    'comment_count': results['metadatas'][i]['comment_count']
                })

            return social_data

        except Exception as e:
            logger.error(f"Error retrieving social media data for {symbol}: {str(e)}")
            return [] 