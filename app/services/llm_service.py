import logging
from typing import Dict
import os

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

    def generate_prediction_prompt(self, data: Dict, user_query: str) -> str:
        """Generate a prompt for the LLM based on the data and user query"""
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
                    
                    historical_summary = f"""
                    Recent Price Movement:
                    - Last 5 days prices: {', '.join([f'${p:.2f}' for p in recent_prices])}
                    - Last 5 days dates: {', '.join(recent_dates)}
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
            
            # Generate the final prompt
            prompt = f"""
            Analyze the following data for {symbol} and provide a detailed prediction:

            1. Historical Data:
            {historical_summary}

            2. Finnhub News Analysis:
            {news_summary}

            3. Reddit Social Media Sentiment:
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