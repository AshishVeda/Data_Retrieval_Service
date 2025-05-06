import numpy as np
from typing import Dict, Any, List, Optional, Union, Tuple

def calculate_percentage_error(predicted: float, actual: float) -> float:
    """
    Calculate the percentage error between predicted and actual values
    
    Args:
        predicted (float): Predicted value
        actual (float): Actual value
        
    Returns:
        float: Percentage error
    """
    if predicted is None or actual is None:
        return float('nan')
    
    if actual == 0:
        return float('inf')
    
    return abs((predicted - actual) / actual) * 100

def calculate_direction_accuracy(predicted: float, last_train_price: float, actual_price: float) -> bool:
    """
    Calculate if the direction prediction was correct (up or down)
    
    Args:
        predicted (float): Predicted end price
        last_train_price (float): Price at the end of training period
        actual_price (float): Actual price on test date
        
    Returns:
        bool: True if direction was predicted correctly, False otherwise
    """
    if predicted is None or last_train_price is None or actual_price is None:
        return None
    
    # Determine predicted direction
    predicted_direction = 1 if predicted > last_train_price else (-1 if predicted < last_train_price else 0)
    
    # Determine actual direction
    actual_direction = 1 if actual_price > last_train_price else (-1 if actual_price < last_train_price else 0)
    
    # Check if the directions match
    return predicted_direction == actual_direction

def calculate_metrics(predicted_price: Optional[float], 
                     last_train_price: Optional[float], 
                     actual_price: Optional[float]) -> Dict[str, Any]:
    """
    Calculate simplified metrics to evaluate prediction accuracy
    
    Args:
        predicted_price (float, optional): Predicted price for the test date
        last_train_price (float, optional): Price at the end of training period
        actual_price (float, optional): Actual price on the test date
        
    Returns:
        dict: Dictionary with calculated metrics (only percentage error and direction correct)
    """
    metrics = {
        'has_prediction': predicted_price is not None,
        'percentage_error': None,
        'direction_correct': None
    }
    
    # Calculate prediction accuracy metrics if we have a prediction
    if predicted_price is not None and actual_price is not None:
        # Percentage error
        percentage_error = calculate_percentage_error(predicted_price, actual_price)
        metrics['percentage_error'] = percentage_error
        
        # Direction accuracy
        if last_train_price is not None:
            direction_correct = calculate_direction_accuracy(predicted_price, last_train_price, actual_price)
            metrics['direction_correct'] = direction_correct
    
    return metrics

def aggregate_metrics(individual_metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregate metrics across multiple predictions
    
    Args:
        individual_metrics (list): List of metric dictionaries
        
    Returns:
        dict: Dictionary with aggregated metrics
    """
    # Filter out metrics where we have a prediction
    valid_metrics = [m for m in individual_metrics if m.get('has_prediction', False)]
    
    if not valid_metrics:
        return {
            'count': 0,
            'valid_predictions': 0,
            'avg_percentage_error': None,
            'direction_accuracy': None
        }
    
    # Count metrics
    count = len(individual_metrics)
    valid_count = len(valid_metrics)
    
    # Aggregate error metrics
    pct_errors = [m.get('percentage_error') for m in valid_metrics if m.get('percentage_error') is not None]
    directions = [m.get('direction_correct') for m in valid_metrics if m.get('direction_correct') is not None]
    
    avg_pct_error = np.mean(pct_errors) if pct_errors else None
    direction_accuracy = (sum(1 for d in directions if d) / len(directions)) if directions else None
    
    return {
        'count': count,
        'valid_predictions': valid_count,
        'avg_percentage_error': avg_pct_error,
        'direction_accuracy': direction_accuracy
    } 