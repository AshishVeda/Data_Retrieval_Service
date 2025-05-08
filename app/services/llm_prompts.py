"""
Prompt templates for LLM interactions
"""
from datetime import datetime
import textwrap

def get_multistep_prediction_prompt(symbol, historical_summary, news_summary, sentiment_summary, 
                                    user_query, chat_history=""):
    """
    Generate an enhanced prompt template for the multi-step analysis process.
    This prompt is structured to provide detailed instructions to the LLM on how to analyze
    the various data sources and generate a comprehensive prediction.
    
    Args:
        symbol: Stock symbol
        historical_summary: Summary of historical price data
        news_summary: Summary of relevant news
        sentiment_summary: Summary of social media sentiment
        user_query: The user's question
        chat_history: Previous conversation history (optional)
    
    Returns:
        Structured prompt for the LLM
    """
    # Get current date dynamically in the format "Month Day, Year"
    current_date = datetime.now().strftime('%B %d, %Y')
    
    prompt = f"""
You are FinanceGPT, a specialized stock market analysis assistant trained on financial data through 2025.
Today is {current_date}.

TASK: Analyze the provided data for {symbol} and answer the following user query: "{user_query}"

I'll provide you with three key sources of information:
1. Historical stock data (prices, volumes, trends)
2. Recent news articles relevant to {symbol}
3. Social media sentiment analysis from Reddit discussions

===== HISTORICAL DATA =====
{historical_summary}

===== RECENT NEWS =====
{news_summary}

===== SOCIAL MEDIA SENTIMENT =====
{sentiment_summary}

"""

    if chat_history:
        prompt += f"""
===== PREVIOUS CONVERSATION HISTORY =====
{chat_history}
"""

    prompt += f"""
===== ANALYSIS INSTRUCTIONS =====
1. Analyze the historical price data first - identify key trends, patterns, and anomalies
2. Cross-reference price movements with news events - look for correlations
3. Consider social media sentiment as a measure of market psychology
4. Synthesize all three data sources to form a cohesive analysis
5. Address the user's specific query directly

Keep your analysis professional, nuanced and data-driven. Avoid generic advice and be specific to {symbol}.
"""
    
    return textwrap.dedent(prompt).strip() 