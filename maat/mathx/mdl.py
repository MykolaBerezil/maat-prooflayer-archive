"""
Minimum Description Length (MDL) analysis.
Computes description length delta between model and null hypothesis.
"""
import math
from typing import List


def _linear_fit_residuals(values: List[float]) -> List[float]:
    """
    Compute residuals from linear least-squares fit.
    
    Args:
        values: Time series data
        
    Returns:
        List of residuals (actual - predicted)
    """
    n = len(values)
    if n < 2:
        return [0.0 for _ in values]
    
    # Fit y = a + b*x
    xs = list(range(n))
    meanx = sum(xs) / n
    meany = sum(values) / n
    
    num = sum((x - meanx) * (y - meany) for x, y in zip(xs, values))
    den = sum((x - meanx) ** 2 for x in xs)
    
    if abs(den) < 1e-12:
        # Degenerate case: no variance in x
        return [y - meany for y in values]
    
    b = num / den
    a = meany - b * meanx
    
    return [y - (a + b * x) for x, y in zip(xs, values)]


def _gaussian_code_length(values: List[float], sigma: float) -> float:
    """
    Compute Gaussian code length in nats.
    
    Args:
        values: Data values
        sigma: Standard deviation
        
    Returns:
        Code length in nats
    """
    n = len(values)
    if n == 0:
        return 0.0
    
    # L(data|sigma) = 0.5 * n * (1 + log(2*pi*sigma^2))
    return 0.5 * n * (1.0 + math.log(2 * math.pi * sigma * sigma))


def mdl_delta_bits(values: List[float], model: str = "linear", params: int = 2) -> float:
    """
    Compute MDL delta bits: L(model) + L(data|model) - L(null).
    
    Negative values indicate the model compresses better than null hypothesis.
    
    Args:
        values: Time series data
        model: Model type ("linear" or "null")
        params: Number of model parameters (for complexity penalty)
        
    Returns:
        Delta bits (negative = model is better)
    """
    n = len(values)
    if n == 0:
        return 0.0
    
    # Null model: constant mean
    mu0 = sum(values) / n
    var0 = sum((v - mu0) ** 2 for v in values) / max(1, n - 1)
    sigma0 = math.sqrt(var0) if var0 > 0 else 1e-12
    
    # Model residuals
    if model == "linear":
        resid = _linear_fit_residuals(values)
    else:
        resid = [v - mu0 for v in values]
    
    # Model variance
    var1 = sum(r * r for r in resid) / max(1, n - 1)
    sigma1 = math.sqrt(var1) if var1 > 0 else 1e-12
    
    # Code lengths
    L_null = _gaussian_code_length(values, sigma0)
    L_model_data = _gaussian_code_length(resid, sigma1)
    L_model_params = 0.5 * params * math.log(n + 1e-12)  # BIC-style penalty
    
    # Delta in nats, convert to bits
    delta_nats = (L_model_data + L_model_params) - L_null
    return float(delta_nats / math.log(2.0))


def mdl_score(values: List[float], model: str = "linear") -> float:
    """
    Compute MDL score for a time series.
    
    Args:
        values: Time series data
        model: Model type ("linear" or "null")
        
    Returns:
        MDL delta bits (negative = good compression)
    """
    return mdl_delta_bits(values, model=model, params=2)

