"""
Performance utilities for trading metrics.
"""
import numpy as np
from typing import List


def calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.0) -> float:
    """
    Calculate the annualized Sharpe ratio.
    """
    if not returns:
        return 0.0
    
    returns_arr = np.array(returns)
    excess_returns = returns_arr - (risk_free_rate / 252) # Assuming daily
    
    if np.std(excess_returns) == 0:
        return 0.0
        
    return np.sqrt(252) * np.mean(excess_returns) / np.std(excess_returns)


def calculate_max_drawdown(equity_curve: List[float]) -> float:
    """
    Calculate the maximum drawdown from an equity curve.
    """
    if not equity_curve:
        return 0.0
        
    equity = np.array(equity_curve)
    peak = np.maximum.accumulate(equity)
    drawdown = (equity - peak) / peak
    return float(np.min(drawdown))
