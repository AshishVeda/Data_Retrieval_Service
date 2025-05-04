import logging
from typing import Dict
import os
from app.services.chat_history_service import chat_history_service
from datetime import datetime, timedelta
from app.services.llm_prompts import get_multistep_prediction_prompt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        logger.info("LLMService initialized")

    def prepare_prompt(self, data: Dict) -> str:
        """Prepare structured prompt for LLM"""
        try:
            # Extract data
            symbol = data['symbol']
            historical = data['historical_data']
            news = data['news_data']
            sentiment = data['sentiment_data']
            user_query = data['user_query']

            # Format historical data
            hist_summary = self._summarize_historical(historical)

            # Format news data
            news_summary = self._summarize_news(news)

            # Format sentiment data
            sentiment_summary = self._summarize_sentiment(sentiment)

            # Construct prompt
            prompt = f"""
            Analyze the following data for {symbol} and provide a detailed prediction:

            1. Historical Data:
            {hist_summary}

            2. News Analysis:
            {news_summary}

            3. Social Media Sentiment:
            {sentiment_summary}

            User Query: {user_query}

            Please provide:
            1. Short-term prediction (next week)
            2. Key factors influencing the prediction
            3. Potential risks to consider
            4. Confidence level in the prediction
            """

            return prompt

        except Exception as e:
            logger.error(f"Error in prompt preparation: {str(e)}")
            raise

    def _summarize_historical(self, data: Dict) -> str:
        """Summarize historical price data"""
        try:
            # Extract key metrics
            prices = data.get('prices', [])
            if not prices:
                return "No historical price data available"

            # Calculate basic statistics
            latest_price = prices[-1]['close']
            prev_price = prices[0]['close']
            price_change = ((latest_price - prev_price) / prev_price) * 100

            # Identify trends
            trend = "upward" if price_change > 0 else "downward"
            
            return f"""
            - Latest Price: ${latest_price:.2f}
            - Price Change: {price_change:.2f}%
            - Overall Trend: {trend}
            - Time Period: {len(prices)} days
            """
        except Exception as e:
            logger.error(f"Error summarizing historical data: {str(e)}")
            return "Error summarizing historical data"

    def _summarize_news(self, data: Dict) -> str:
        """Summarize news data"""
        try:
            articles = data.get('articles', [])
            if not articles:
                return "No recent news articles available"

            # Group by sentiment
            positive = []
            negative = []
            neutral = []

            for article in articles:
                sentiment = article.get('sentiment', 'neutral')
                if sentiment == 'positive':
                    positive.append(article['title'])
                elif sentiment == 'negative':
                    negative.append(article['title'])
                else:
                    neutral.append(article['title'])

            summary = []
            if positive:
                summary.append(f"Positive News ({len(positive)}):\n- " + "\n- ".join(positive))
            if negative:
                summary.append(f"Negative News ({len(negative)}):\n- " + "\n- ".join(negative))
            if neutral:
                summary.append(f"Neutral News ({len(neutral)}):\n- " + "\n- ".join(neutral))

            return "\n\n".join(summary)

        except Exception as e:
            logger.error(f"Error summarizing news data: {str(e)}")
            return "Error summarizing news data"

    def _summarize_sentiment(self, data: Dict) -> str:
        """Summarize sentiment data"""
        try:
            posts = data.get('posts', [])
            if not posts:
                return "No social media data available"

            # Calculate average sentiment
            total_posts = len(posts)
            avg_polarity = sum(post['sentiment']['polarity'] for post in posts) / total_posts
            avg_subjectivity = sum(post['sentiment']['subjectivity'] for post in posts) / total_posts

            # Get top discussions
            top_posts = sorted(posts, key=lambda x: x['score'], reverse=True)[:3]
            discussions = "\n".join([f"- {post['title']} (Score: {post['score']})" for post in top_posts])

            return f"""
            Overall Sentiment:
            - Average Polarity: {avg_polarity:.2f}
            - Average Subjectivity: {avg_subjectivity:.2f}
            
            Top Discussions:
            {discussions}
            """
        except Exception as e:
            logger.error(f"Error summarizing sentiment data: {str(e)}")
            return "Error summarizing sentiment data"

    def generate_prediction_prompt(self, data: Dict, user_query: str, user_id=None) -> str:
        """Generate a prompt for the LLM based on the data and user query, with chat history if available"""
        try:
            # Extract symbol
            symbol = data.get('symbol', 'the stock')
            
            # Extract data from the response
            raw_data = data.get('metadata', {}).get('raw_data', {})
            
            # Format historical data
            historical_summary = "No historical data available"
            historical = raw_data.get('historical', {})
            if historical and isinstance(historical, dict):
                dates = historical.get('dates', [])
                prices = historical.get('prices', [])
                volumes = historical.get('volumes', [])
                
                if dates and prices and len(dates) >= 5 and len(prices) >= 5:
                    # Get the last 5 days of data
                    recent_dates = dates[-5:]
                    recent_prices = prices[-5:]
                    
                    # Calculate price changes
                    price_changes = []
                    for i in range(1, len(recent_prices)):
                        prev_price = recent_prices[i-1]
                        current_price = recent_prices[i]
                        if prev_price > 0:  # Avoid division by zero
                            change = ((current_price - prev_price) / prev_price) * 100
                            price_changes.append(change)
                    
                    avg_change = sum(price_changes) / len(price_changes) if price_changes else 0
                    current_price = recent_prices[-1] if recent_prices else 0
                    
                    # Fix dates: Use current year (2025) instead of dates from historical data
                    # Get the current date
                    current_date = datetime.now()
                    
                    # Create dates going back from today
                    current_year_dates = []
                    for i in range(len(recent_dates)):
                        # Generate a date i days before current date
                        date = current_date - timedelta(days=i)
                        # Skip weekends (Saturday = 5, Sunday = 6)
                        while date.weekday() >= 5:  # Skip weekends
                            date = date - timedelta(days=1)
                        # Format as YYYY-MM-DD
                        current_year_dates.append(date.strftime('%Y-%m-%d'))
                    
                    # Reverse the list to get chronological order
                    current_year_dates.reverse()
                    
                    historical_summary = f"""
                    Recent Price Movement:
                    - Last 5 days prices: {', '.join([f'${p:.2f}' for p in recent_prices])}
                    - Last 5 days dates: {', '.join(current_year_dates)}
                    - Average daily change: {avg_change:.2f}%
                    - Current price: ${current_price:.2f}
                    """
            
            # Format news data - use only Finnhub news
            news_summary = "No recent news available"
            finnhub_news = raw_data.get('finnhub_news', [])
            
            # Process Finnhub news
            if finnhub_news and isinstance(finnhub_news, list) and len(finnhub_news) > 0:
                # Sort by publication date (newest first)
                try:
                    finnhub_news = sorted(finnhub_news, key=lambda x: x.get('published', ''), reverse=True)
                except:
                    pass
                
                # Take top 10 news items (reduced from 25)
                recent_news = finnhub_news[:10]
                
                news_summary = "\nRecent Finnhub News Headlines:\n"
                for item in recent_news:
                    if isinstance(item, dict):
                        title = item.get('title', 'No title')
                        published = item.get('published', '')
                        
                        # Update published date to current year if it's from a previous year
                        try:
                            pub_date = datetime.fromisoformat(published.replace('Z', '+00:00'))
                            if pub_date.year < current_date.year:
                                # Keep month/day but update year to current year
                                pub_date = pub_date.replace(year=current_date.year)
                                published = pub_date.isoformat()
                        except Exception as e:
                            logger.warning(f"Could not parse news date: {published}, {str(e)}")
                            
                        news_summary += f"- {title} - {published}\n"
            
            # Format sentiment data - updated to handle the new format from SocialService
            sentiment_summary = "No sentiment data available"
            sentiment = raw_data.get('sentiment', {})
            if sentiment and isinstance(sentiment, dict):
                sentiment_summary_data = sentiment.get('sentiment_summary', {})
                if sentiment_summary_data:
                    # Use the new keys from SocialService
                    sentiment_summary = f"""
                    Reddit Sentiment Analysis:
                    - Average Post Polarity: {sentiment_summary_data.get('avg_post_polarity', 0):.2f}
                    - Average Post Subjectivity: {sentiment_summary_data.get('avg_post_subjectivity', 0):.2f}
                    - Average Comment Polarity: {sentiment_summary_data.get('avg_comment_polarity', 0):.2f}
                    - Average Comment Subjectivity: {sentiment_summary_data.get('avg_comment_subjectivity', 0):.2f}
                    - Total Posts Analyzed: {sentiment_summary_data.get('post_count', 0)}
                    - Total Comments Analyzed: {sentiment_summary_data.get('comment_count', 0)}
                    
                    Top Reddit Discussions:
                    """
                    
                    # Get posts
                    posts = sentiment.get('posts', [])
                    if posts and isinstance(posts, list):
                        # Sort by score
                        sorted_posts = sorted(posts, key=lambda x: x.get('score', 0) if isinstance(x, dict) else 0, reverse=True)
                        top_posts = sorted_posts[:5]
                        
                        for post in top_posts:
                            if isinstance(post, dict):
                                title = post.get('title', 'No title')
                                score = post.get('score', 0)
                                polarity = post.get('sentiment', {}).get('polarity', 0)
                                sentiment_summary += f"- {title} (Score: {score}, Sentiment: {polarity:.2f})\n"
            
            # Get chat history if user_id is provided
            chat_history_text = ""
            if user_id:
                try:
                    history_result = chat_history_service.get_chat_history(user_id, limit=5)
                    
                    if history_result.get('status') == 'success' and history_result.get('data'):
                        chat_history = history_result.get('data', [])
                        chat_history_text = chat_history_service.format_chat_history_for_prompt(chat_history)
                        
                        if chat_history_text:
                            chat_history_text = f"\nPrevious Conversation History:\n{chat_history_text}\n"
                except Exception as e:
                    logger.error(f"Error retrieving chat history for prompt: {str(e)}")
            
            # Generate the final prompt
            current_date_str = current_date.strftime('%B %d, %Y')
            
            prompt = f"""
            Today is {current_date_str}. Analyze the following data for {symbol} and provide a detailed prediction:

            1. Historical Data:
            {historical_summary}

            2. Finnhub News Analysis:
            {news_summary}

            3. Reddit Social Media Sentiment:
            {sentiment_summary}
            {chat_history_text}
            User Query: {user_query}

            Please provide:
            1. Short-term prediction (next week)
            2. Key factors influencing the prediction
            3. Potential risks to consider
            4. Confidence level in the prediction
            """
            
            return prompt
            
        except Exception as e:
            logger.error(f"Error generating prediction prompt: {str(e)}")
            return f"""
            Analyze the following data for {data.get('symbol', 'the stock')} and provide a detailed prediction:

            1. Historical Data:
            Error summarizing historical data

            2. Finnhub News Analysis:
            Error summarizing news data

            3. Reddit Social Media Sentiment:
            {self._format_fallback_sentiment(data)}

            User Query: {user_query}

            Please provide:
            1. Short-term prediction (next week)
            2. Key factors influencing the prediction
            3. Potential risks to consider
            4. Confidence level in the prediction
            """
    
    def _format_fallback_sentiment(self, data: Dict) -> str:
        """Format sentiment data for fallback case"""
        try:
            sentiment = data.get('metadata', {}).get('raw_data', {}).get('sentiment', {})
            if not sentiment:
                return "No sentiment data available"
                
            summary = sentiment.get('sentiment_summary', {})
            if not summary:
                return "No sentiment summary available"
                
            result = f"""
            Overall Sentiment:
            - Average Polarity: {summary.get('avg_post_polarity', 0):.2f}
            - Average Subjectivity: {summary.get('avg_post_subjectivity', 0):.2f}
            
            Top Discussions:
            """
            
            posts = sentiment.get('posts', [])
            if posts and isinstance(posts, list):
                sorted_posts = sorted(posts, key=lambda x: x.get('score', 0) if isinstance(x, dict) else 0, reverse=True)
                top_posts = sorted_posts[:3]
                
                for post in top_posts:
                    if isinstance(post, dict):
                        title = post.get('title', 'No title')
                        score = post.get('score', 0)
                        result += f"- {title} (Score: {score})\n"
                        
            return result
            
        except Exception as e:
            logger.error(f"Error in fallback sentiment formatting: {str(e)}")
            return "Error formatting sentiment data"

    def generate_multistep_prompt(self, data: Dict, user_query: str, user_id=None) -> str:
        """
        Generate an enhanced prompt for the multi-step analysis process
        
        Args:
            data: Dictionary containing all the data from previous steps
            user_query: The user's query about the stock
            user_id: Optional user ID for retrieving chat history
            
        Returns:
            A structured prompt for the LLM
        """
        try:
            # Extract symbol
            symbol = data.get('symbol', 'the stock')
            
            # Extract and format historical data
            historical_data = data.get('historical', {})
            historical_summary = self._format_historical_data(historical_data)
            
            # Extract and format news data
            news_data = data.get('news', [])
            news_summary = self._format_news_data(news_data)
            
            # Extract and format social media data
            social_data = data.get('social', {})
            social_summary = self._format_social_data(social_data)
            
            # Get chat history if user_id is provided
            chat_history_text = ""
            if user_id:
                try:
                    history_result = chat_history_service.get_chat_history(user_id, limit=3)
                    
                    if history_result.get('status') == 'success' and history_result.get('data'):
                        chat_history = history_result.get('data', [])
                        chat_history_text = chat_history_service.format_chat_history_for_prompt(chat_history)
                except Exception as e:
                    logger.error(f"Error retrieving chat history for prompt: {str(e)}")
            
            # Generate the enhanced prompt using the template
            prompt = get_multistep_prediction_prompt(
                symbol=symbol,
                historical_summary=historical_summary,
                news_summary=news_summary,
                sentiment_summary=social_summary,
                user_query=user_query,
                chat_history=chat_history_text
            )
            
            return prompt
            
        except Exception as e:
            logger.error(f"Error generating multistep prompt: {str(e)}")
            # Fallback prompt in case of error
            return f"""
            Analyze the following data for {data.get('symbol', 'the stock')} and provide a detailed prediction:
            
            User Query: {user_query}
            
            Please provide:
            1. Short-term prediction
            2. Key factors influencing the prediction
            3. Potential risks to consider
            4. Confidence level in the prediction
            """
    
    def _format_historical_data(self, historical_data: Dict) -> str:
        """Format historical data for the prompt"""
        try:
            if not historical_data:
                return "No historical data available."
                
            dates = historical_data.get('dates', [])
            prices = historical_data.get('prices', [])
            volumes = historical_data.get('volumes', [])
            
            if not dates or not prices or len(dates) < 5 or len(prices) < 5:
                return "Insufficient historical data available."
            
            # Get last 15 days of data
            recent_dates = dates[-15:]
            recent_prices = prices[-15:]
            recent_volumes = volumes[-15:] if volumes and len(volumes) >= 15 else []
            
            # Calculate basic statistics
            current_price = recent_prices[-1] if recent_prices else 0
            prev_price = recent_prices[0] if recent_prices else 0
            price_change = ((current_price - prev_price) / prev_price * 100) if prev_price else 0
            
            # Calculate avg volume
            avg_volume = sum(recent_volumes) / len(recent_volumes) if recent_volumes else 0
            
            # Format the historical data summary
            result = f"Current Price: ${current_price:.2f}\n"
            result += f"Price Change (last 15 days): {price_change:.2f}%\n"
            result += f"Average Daily Volume: {int(avg_volume):,}\n\n"
            result += "Daily Prices (last 15 days):\n"
            
            # Add daily price data
            for i in range(len(recent_dates)):
                if i < len(recent_prices):
                    date = recent_dates[i]
                    price = recent_prices[i]
                    volume = recent_volumes[i] if i < len(recent_volumes) else 0
                    result += f"- {date}: ${price:.2f} (Volume: {int(volume):,})\n"
            
            return result
        except Exception as e:
            logger.error(f"Error formatting historical data: {str(e)}")
            return "Error processing historical data."
    
    def _format_news_data(self, news_data: list) -> str:
        """Format news data for the prompt"""
        try:
            if not news_data or not isinstance(news_data, list):
                return "No recent news available."
                
            result = ""
            
            # Sort news by publication date (newest first)
            try:
                sorted_news = sorted(news_data, key=lambda x: x.get('published', ''), reverse=True)
            except:
                sorted_news = news_data
            
            # Take top 5 news items
            top_news = sorted_news[:5]
            
            for i, article in enumerate(top_news, 1):
                title = article.get('title', 'No title')
                published = article.get('published', 'Unknown date')
                summary = article.get('summary', 'No summary available')
                source = article.get('source', 'Unknown source')
                
                result += f"{i}. {title}\n"
                result += f"   Source: {source}, Published: {published}\n"
                result += f"   Summary: {summary}\n\n"
            
            return result
        except Exception as e:
            logger.error(f"Error formatting news data: {str(e)}")
            return "Error processing news data."
    
    def _format_social_data(self, social_data: Dict) -> str:
        """Format social media data for the prompt"""
        try:
            if not social_data:
                return "No social media data available."
                
            result = ""
            
            # Format sentiment summary
            sentiment_summary = social_data.get('sentiment_summary', {})
            if sentiment_summary:
                result += "Overall Sentiment Metrics:\n"
                result += f"- Average Post Polarity: {sentiment_summary.get('avg_post_polarity', 0):.2f}\n"
                result += f"- Average Post Subjectivity: {sentiment_summary.get('avg_post_subjectivity', 0):.2f}\n"
                result += f"- Average Comment Polarity: {sentiment_summary.get('avg_comment_polarity', 0):.2f}\n"
                result += f"- Average Comment Subjectivity: {sentiment_summary.get('avg_comment_subjectivity', 0):.2f}\n"
                result += f"- Total Posts Analyzed: {sentiment_summary.get('post_count', 0)}\n"
                result += f"- Total Comments Analyzed: {sentiment_summary.get('comment_count', 0)}\n\n"
            
            # Format top posts
            posts = social_data.get('posts', [])
            if posts and isinstance(posts, list):
                # Sort by score (highest first)
                sorted_posts = sorted(posts, key=lambda x: x.get('score', 0) if isinstance(x, dict) else 0, reverse=True)
                top_posts = sorted_posts[:5]  # Top 5 posts
                
                result += "Top Reddit Discussions:\n"
                for i, post in enumerate(top_posts, 1):
                    if isinstance(post, dict):
                        title = post.get('title', 'No title')
                        score = post.get('score', 0)
                        created = post.get('created', 'Unknown date')
                        polarity = post.get('sentiment', {}).get('polarity', 0)
                        
                        result += f"{i}. {title}\n"
                        result += f"   Score: {score}, Created: {created}\n"
                        result += f"   Sentiment: {polarity:.2f}\n"
                        
                        # Add a snippet of content if available
                        content = post.get('body', '')
                        if content:
                            snippet = content[:150] + '...' if len(content) > 150 else content
                            result += f"   Content: {snippet}\n\n"
                        else:
                            result += "\n"
            
            return result
        except Exception as e:
            logger.error(f"Error formatting social data: {str(e)}")
            return "Error processing social media data." 