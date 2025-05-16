# Stock Analysis Application

A comprehensive Flask-based application for stock analysis, prediction, and backtesting using historical data, news sentiment, and social media analysis powered by LLM technology.

## Project Overview

This application provides stock market analysis and predictions by combining multiple data sources:

- Historical stock price data from financial APIs
- News articles with semantic search capabilities
- Social media sentiment analysis from Reddit
- LLM-powered predictions with specific price targets
- Backtesting framework to validate prediction accuracy

The system uses a multistep approach to gather data, process it through specialized services, and generate detailed stock predictions with confidence scores and price targets.

## Key Features

- **Historical Data Analysis**: Retrieves and processes stock price history
- **News Aggregation**: Collects news from various sources with semantic relevance
- **Reddit Sentiment Analysis**: Analyzes social media sentiment for stocks
- **User Authentication**: Secure login with AWS Cognito
- **Portfolio Management**: Track and manage stock portfolios
- **Multistep Prediction API**: Structured workflow for comprehensive analysis
- **Backtesting Framework**: Validate prediction models using historical data

## Multistep Prediction API

The application uses a structured multistep API approach for generating predictions:

1. **Historical Data** (`/api/prediction/multistep/historical`): 
   - Fetches 3 weeks of price history for the target stock
   - Processes and caches data for 15 minutes

2. **News Analysis** (`/api/prediction/multistep/news`): 
   - Uses semantic search to find relevant news articles
   - Falls back to direct API calls if semantic search returns insufficient results
   - Analyzes sentiment in retrieved articles

3. **Social Media Analysis** (`/api/prediction/multistep/socialmedia`): 
   - Retrieves and analyzes Reddit sentiment for the stock
   - Calculates aggregate sentiment metrics

4. **Final Prediction** (`/api/prediction/multistep/result`): 
   - Combines all data sources into a comprehensive dataset
   - Processes through LLM for detailed analysis
   - Returns structured prediction with price targets

5. **Follow-up Questions** (`/api/prediction/multistep/followup`): 
   - Processes contextual follow-up queries about predictions
   - Uses previous context for more accurate responses

## Semantic Search

The application uses ChromaDB for vector-based semantic search:

- **Document Embedding**: News articles are embedded and stored in a vector database
- **Query Processing**: User queries are transformed into vector embeddings
- **Similarity Matching**: Retrieves articles most semantically relevant to queries
- **Fallback Mechanisms**: Uses direct API calls when semantic search returns insufficient results
- **Data Retention**: Automatically cleans up articles older than the configured retention period

Implementation details:
- Uses persistent storage with fallback to in-memory when needed
- Employs cosine similarity for matching
- Handles deduplication of similar content
- Supports filtering by stock symbol and time range

## LLM Integration

The system leverages Large Language Models for advanced analysis:

- **Structured Prompts**: Creates detailed prompts with historical data, news, and sentiment
- **Context Preservation**: Maintains conversation context for follow-up questions
- **Response Parsing**: Extracts structured data from LLM responses
- **Specific Predictions**: Ensures predictions include exact price targets
- **Confidence Scoring**: Provides confidence levels for predictions
- **Response Refinement**: Uses additional LLM pass to structure and improve initial responses

The application supports:
- Configurable token limits for comprehensive analysis
- Fallback mechanisms for handling API failures
- Caching to reduce redundant API calls

## Backtesting Framework

A comprehensive backtesting framework validates prediction accuracy:

- Uses historical data from previous weeks as test data
- Makes predictions using data that excludes the test period
- Utilizes news and sentiment data from before the test period
- Compares percentage differences between actual and predicted values
- Generates detailed reports on prediction accuracy

## Setup Steps

### Prerequisites

- Python 3.8+
- Docker and Docker Compose (for containerized deployment)
- Required API keys:
  - Alpha Vantage (stock data)
  - Reddit API (social sentiment)
  - Finnhub (financial news)
  - LLM API key (Groq, OpenAI, etc.)
  - AWS Cognito credentials (user authentication)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/stock-analysis-app.git
   cd stock-analysis-app
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

### Running the Application

#### Local Development

1. Start the Flask application:
   ```bash
   python run.py
   ```
   
2. The application will be available at http://localhost:5000

#### Docker Deployment

1. Build and start the containers:
   ```bash
   docker-compose up -d
   ```

2. The application will be available at http://localhost:5001

### Running Backtests

To validate the prediction model:

1. Navigate to the backtesting directory:
   ```bash
   cd backtesting
   ```

2. Run the backtesting script:
   ```bash
   python run_backtest.py
   ```

3. View results in the generated JSON file in the backtest_reports directory.

## Contributing

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/new-feature`
3. Commit your changes: `git commit -am 'Add new feature'`
4. Push to the branch: `git push origin feature/new-feature`
5. Submit a pull request

## License

[MIT License](LICENSE) 