import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional, Union, Tuple

def generate_text_report(results: Dict[str, Any], output_dir: str = 'backtest_reports'):
    """
    Generate a text-based report from backtest results
    
    Args:
        results (dict): Backtest results dictionary
        output_dir (str): Directory to save reports
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Current timestamp for file names
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = os.path.join(output_dir, f'backtest_report_{timestamp}.txt')
    
    with open(report_file, 'w') as f:
        f.write("===== STOCK PREDICTION BACKTEST REPORT =====\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Overall metrics
        successful = 0
        direction_correct = 0
        total = len(results)
        all_pct_errors = []
        
        # Process each symbol
        for symbol, result in results.items():
            f.write(f"\n----- {symbol} -----\n")
            
            if 'status' in result and result['status'] != 'success':
                f.write(f"Status: {result['status']}\n")
                f.write(f"Message: {result.get('message', 'Unknown error')}\n")
                continue
                
            if 'evaluation' not in result:
                f.write("No evaluation data available\n")
                continue
                
            evaluation = result['evaluation']
            
            # Write prediction details
            pred_data = evaluation.get('prediction', {})
            actual_data = evaluation.get('actual', {})
            metrics = evaluation.get('metrics', {})
            
            predicted_price = pred_data.get('predicted_price')
            target_price_raw = pred_data.get('target_price_raw', '')
            
            f.write(f"Prediction date: {result.get('test_date', 'Unknown')}\n")
            f.write(f"Test date: {evaluation.get('test_date', 'Unknown')}\n")
            
            if predicted_price is not None:
                f.write(f"Predicted price: ${predicted_price:.2f}\n")
            else:
                f.write(f"Predicted price: Not available\n")
                if target_price_raw:
                    f.write(f"Raw target price: {target_price_raw}\n")
            
            # Write actual data (now for a single day)
            last_train_price = actual_data.get('last_train_price')
            actual_price = actual_data.get('actual_price')
            test_date = actual_data.get('date', 'Unknown')
            
            if last_train_price is not None:
                f.write(f"Last training price: ${last_train_price:.2f}\n")
            
            if actual_price is not None:
                f.write(f"Actual price on {test_date}: ${actual_price:.2f}\n")
            
            # Write metrics
            if metrics:
                if metrics.get('has_prediction', False):
                    successful += 1
                    
                    pct_error = metrics.get('percentage_error')
                    if pct_error is not None:
                        f.write(f"Percentage error: {pct_error:.2f}%\n")
                        all_pct_errors.append(pct_error)
                    
                    direction = metrics.get('direction_correct')
                    if direction is not None:
                        f.write(f"Direction prediction correct: {direction}\n")
                        if direction:
                            direction_correct += 1
        
        # Write summary statistics
        f.write("\n===== SUMMARY STATISTICS =====\n")
        f.write(f"Total symbols tested: {total}\n")
        f.write(f"Successful predictions: {successful}/{total}")
        if total > 0:
            f.write(f" ({successful/total*100:.1f}%)")
        f.write("\n")
        
        if successful > 0:
            f.write(f"Direction accuracy: {direction_correct}/{successful}")
            f.write(f" ({direction_correct/successful*100:.1f}%)\n")
            
            if all_pct_errors:
                avg_pct_error = sum(all_pct_errors) / len(all_pct_errors)
                f.write(f"Average percentage error: {avg_pct_error:.2f}%\n")
    
    print(f"Text report generated successfully in {report_file}")
    return report_file

def generate_report(results_file: str, output_dir: str = 'backtest_reports'):
    """
    Generate a text report from backtest results
    
    Args:
        results_file (str): Path to the JSON results file
        output_dir (str): Directory to save reports
    """
    try:
        # Load results from file
        with open(results_file, 'r') as f:
            results = json.load(f)
        
        # Generate text report
        report_file = generate_text_report(results, output_dir)
        
        return True
    except Exception as e:
        print(f"Error generating report: {str(e)}")
        return False

if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) > 1:
        results_file = sys.argv[1]
        generate_report(results_file)
    else:
        print("Please provide the path to a results file") 