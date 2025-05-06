# Stock Prediction Backtesting

This module implements a backtesting system for evaluating the accuracy of stock price predictions against historical data.

## Overview

The backtesting system:

1. Fetches historical stock data:
   - **Training data**: 3 weeks to 2 days ago
   - **Test data**: Yesterday (to compare against predictions)

2. Fetches news data for the training period

3. Makes predictions using the LLM prediction API

4. Compares predicted price with actual price from yesterday

5. Calculates performance metrics:
   - Absolute error
   - Percentage error
   - Direction accuracy (up/down prediction)

6. Generates text reports with results

## Directory Structure

```
backtesting/
├── data/                   # Data fetching utilities
│   ├── fetch_historic_data.py  # Fetches stock price data
│   └── fetch_news_data.py      # Fetches news data
├── services/               # Core services
│   └── backtesting_service.py  # Main backtesting logic
├── utils/                  # Utility functions
│   ├── metrics.py          # Evaluation metrics calculation
│   └── visualization.py    # Text report generation
├── run_backtest.py         # Command-line runner script
└── README.md               # This file
```

## Usage

### Basic Usage

Run a backtest with default symbols (AAPL, MSFT, GOOGL, AMZN, META):

```bash
python backtesting/run_backtest.py
```

### Custom Symbols

Specify custom symbols to test:

```bash
python backtesting/run_backtest.py --symbols AAPL NFLX DIS
```

### Generate Report Only

Generate a text report from an existing results file:

```bash
python backtesting/run_backtest.py --report-only --results-file backtest_results_20250505_223738.json
```

### Custom Output Directory

```bash
python backtesting/run_backtest.py --output-dir custom_reports
```

## Output

The backtesting system generates:

1. A JSON results file with detailed data for each symbol
2. A text report containing:
   - Individual stock results
   - Prediction accuracy
   - Error metrics
   - Summary statistics

## How It Works

1. **Data Collection**:
   - The system uses the app's services to fetch historical stock data and news
   - Training data is filtered to include data from 3 weeks ago to 2 days ago
   - Test data is a single data point from yesterday

2. **Prediction**:
   - Uses the existing LLM prediction API to generate predictions
   - Predicts the stock price for yesterday based on data up to 2 days ago
   - The prediction query is: "What will be the price of [SYMBOL] tomorrow based on the data from [DATE]?"

3. **Evaluation**:
   - Compares the predicted price with the actual price from yesterday
   - Calculates accuracy metrics
   - Determines if the direction prediction was correct (relative to the last training price)

4. **Reporting**:
   - Generates a comprehensive text report with results
   - Provides summary statistics across all stocks

## Extending the System

To add new metrics:
1. Implement them in `utils/metrics.py`
2. Update the `calculate_metrics` function
3. Update the text report generation in `utils/visualization.py`

To test different prediction strategies:
1. Modify the `make_prediction` method in `services/backtesting_service.py`

## Dependencies

- Python 3.7+
- NumPy
- All dependencies from the main app 