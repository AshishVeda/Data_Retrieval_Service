#!/usr/bin/env python3
import os
import sys
import json
import argparse
import logging
from datetime import datetime
from typing import List

# Add the project root to the path so we can import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backtesting.services.backtesting_service import BacktestingService
from backtesting.utils.visualization import generate_report

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Run backtesting for stock price predictions')
    
    parser.add_argument('--symbols', type=str, nargs='+', default=['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META'],
                       help='List of stock symbols to run backtest for')
    
    parser.add_argument('--output-dir', type=str, default='backtest_reports',
                       help='Directory to save text reports')
    
    parser.add_argument('--results-file', type=str, 
                       help='Path to existing results file for reporting only')
    
    parser.add_argument('--report-only', action='store_true',
                       help='Only generate text report from existing results file')
    
    return parser.parse_args()

def run_backtest(symbols: List[str], output_dir: str = 'backtest_reports'):
    """
    Run backtest for specified symbols
    
    Args:
        symbols (list): List of stock symbols
        output_dir (str): Directory to save reports
        
    Returns:
        str: Path to results file
    """
    logger.info(f"Starting backtest for symbols: {', '.join(symbols)}")
    
    # Create the backtesting service
    backtest = BacktestingService()
    
    # Run the backtest
    result = backtest.run_backtest(symbols)
    
    if result['status'] != 'success':
        logger.error(f"Backtest failed: {result.get('message', 'Unknown error')}")
        return None
    
    # Generate text report
    results_file = result['output_file']
    logger.info(f"Backtest completed. Results saved to {results_file}")
    
    if generate_report(results_file, output_dir):
        logger.info(f"Text report generated in {output_dir}")
    
    return results_file

def main():
    """Main function"""
    args = parse_arguments()
    
    if args.report_only:
        if not args.results_file:
            logger.error("Must provide --results-file when using --report-only")
            return
        
        logger.info(f"Generating text report from {args.results_file}")
        if generate_report(args.results_file, args.output_dir):
            logger.info(f"Report generated in {args.output_dir}")
        return
    
    # Run backtest with specified symbols
    results_file = run_backtest(args.symbols, args.output_dir)
    
    if results_file:
        # Print summary
        try:
            with open(results_file, 'r') as f:
                results = json.load(f)
            
            # Count successful predictions and direction accuracy
            successful = 0
            direction_correct = 0
            total = len(results)
            
            for symbol, result in results.items():
                if 'evaluation' in result and 'metrics' in result['evaluation']:
                    metrics = result['evaluation']['metrics']
                    if metrics.get('has_prediction', False):
                        successful += 1
                        if metrics.get('direction_correct', False):
                            direction_correct += 1
            
            print("\nBacktest Summary:")
            print(f"Total symbols tested: {total}")
            print(f"Successful predictions: {successful}/{total} ({successful/total*100:.1f}%)")
            
            if successful > 0:
                print(f"Direction accuracy: {direction_correct}/{successful} ({direction_correct/successful*100:.1f}%)")
            
            print(f"\nResults saved to: {results_file}")
            print(f"Text report saved to: {args.output_dir}")
        except Exception as e:
            logger.error(f"Error printing summary: {str(e)}")

if __name__ == "__main__":
    main() 