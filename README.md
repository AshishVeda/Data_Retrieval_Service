# Stock Analysis Application

A Flask-based application for stock analysis, news fetching, and sentiment analysis.

## Features

- Historical stock data retrieval using Alpha Vantage API
- News aggregation from various sources
- Reddit sentiment analysis
- User authentication with AWS Cognito
- Portfolio management with MySQL database

## Docker Setup

### Prerequisites

- Docker and Docker Compose installed on your system
- AWS Cognito credentials (for user authentication)
- Alpha Vantage API key (for stock data)
- Reddit API credentials (for sentiment analysis)
- Finnhub API key (for financial news)

### Environment Variables

Copy the `.env.example` file to `.env` and fill in your API keys and credentials:

```bash
cp .env.example .env
```

Then edit the `.env` file with your specific credentials.

### Running with Docker Compose

1. Build and start the containers:

```bash
docker-compose up -d
```

2. Check the logs to ensure everything is running correctly:

```bash
docker-compose logs -f
```

3. The application will be available at http://localhost:5001

### Development Mode

The Docker setup is configured for development by default, with code hot-reloading enabled.

### Production Deployment

For production deployment, update the `docker-compose.yml` file:

```yaml
environment:
  - FLASK_ENV=production
```

## API Endpoints

### User Authentication

- `POST /api/users/register` - Register a new user
- `POST /api/users/login` - Log in a user
- `POST /api/users/logout` - Log out a user


## Data Retrieval Service

The data retrieval system is a core component that utilizes several specialized services to gather and process financial information.

### VectorService

The VectorService is responsible for semantic search and document storage:

- **Semantic Search**: Utilizes ChromaDB to perform vector similarity searches for news articles related to specific stocks. Each article is embedded and stored for efficient retrieval.
- **Article Management**: Stores and indexes news articles with metadata for up to 7 days.
- **Data Cleanup**: Automatically removes articles older than the configured retention period (3 days by default).

```bash
# Example API call that uses semantic search
curl -X POST -H "Content-Type: application/json" -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"symbol":"MSFT","user_query":"What is the outlook for Microsoft stock next week?"}' \
  http://localhost:5001/api/prediction/multistep/news
```

### Multistep Prediction API

The multistep prediction workflow retrieves data in discrete steps:

1. **Historical Data** (`/api/prediction/multistep/historical`): Fetches 3 weeks of price history.
2. **News Articles** (`/api/prediction/multistep/news`): Retrieves relevant news using semantic search with fallback to direct API.
3. **Social Media Analysis** (`/api/prediction/multistep/socialmedia`): Analyzes Reddit sentiment for the stock.
4. **Final Prediction** (`/api/prediction/multistep/result`): Combines all data sources for a comprehensive analysis.
5. **Follow-up Questions** (`/api/prediction/multistep/followup`): Handles contextual follow-up queries about stocks.

Each step uses cached data from previous steps with a 15-minute TTL.

### Scheduled Data Updates

Two automated jobs maintain data freshness:

- **Daily News Cleanup (6:45 AM)**: Removes news articles older than 3 days from the database.
- **Daily News Update (7:00 AM)**: Fetches fresh articles for tracked stocks and indexes them in the vector database.

### LLM Integration

The application integrates with LLM APIs for natural language processing:

- Sends structured prompts with assembled financial data
- Receives detailed stock analyses and predictions
- Processes and parses responses into structured sections (summary, prediction, price analysis, etc.)
- Supports up to 1024 tokens in responses for comprehensive analyses

## Troubleshooting

- **Database connection issues**: Check that the MySQL container is running properly.
- **API errors**: Verify your API keys in the `.env` file.
- **Permission issues**: The `docker-entrypoint.sh` script should be executable.
- **Port conflicts**: If port 5001 is also in use, you can change it in the docker-compose.yml file.

## License

[MIT License](LICENSE) 
