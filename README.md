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

### Stock Data

- `GET /api/stocks/historical/{symbol}` - Get historical stock data
- `GET /api/stocks/company/{symbol}` - Get company profile

### News and Sentiment

- `GET /api/news/fetch-all` - Fetch news for all symbols
- `GET /api/news/{symbol}` - Fetch news for a specific symbol
- `GET /api/social/{symbol}` - Get social media sentiment for a symbol

### Predictions

- `POST /api/prediction/query` - Get stock predictions based on user query

## Troubleshooting

- **Database connection issues**: Check that the MySQL container is running properly.
- **API errors**: Verify your API keys in the `.env` file.
- **Permission issues**: The `docker-entrypoint.sh` script should be executable.
- **Port conflicts**: If port 5001 is also in use, you can change it in the docker-compose.yml file.

## License

[MIT License](LICENSE) 