import logging
from typing import Dict
import os

logging.basicConfig(level=logging.DEBUG)
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