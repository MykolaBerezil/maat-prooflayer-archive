"""
Coherence analysis using FFT peak-to-mean ratio.
Provides both NumPy-accelerated and pure-Python fallback implementations.
"""
import math
from typing import List

# Try to import numpy, fall back to pure Python if unavailable
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


def _pure_python_fft_peak_mean(values: List[float]) -> float:
    """
    Pure Python implementation of FFT peak-to-mean ratio.
    Uses O(n²) DFT when NumPy is unavailable.
    
    Args:
        values: Time series data
        
    Returns:
        Ratio of max FFT magnitude to mean magnitude
    """
    n = len(values)
    if n < 4:
        return 0.0
    
    # Detrend by removing mean
    meanv = sum(values) / n
    xs = [x - meanv for x in values]
    
    # Compute DFT magnitudes
    mags = []
    for k in range(n // 2 + 1):
        re = sum(xs[t] * math.cos(2 * math.pi * k * t / n) for t in range(n))
        im = -sum(xs[t] * math.sin(2 * math.pi * k * t / n) for t in range(n))
        mags.append(math.hypot(re, im))
    
    # Compute peak-to-mean ratio
    if not mags:
        return 0.0
    
    mean_mag = sum(mags) / len(mags)
    if mean_mag <= 1e-12:
        return 0.0
    
    return max(mags) / mean_mag


def _numpy_fft_peak_mean(values: List[float]) -> float:
    """
    NumPy-accelerated FFT peak-to-mean ratio.
    
    Args:
        values: Time series data
        
    Returns:
        Ratio of max FFT magnitude to mean magnitude
    """
    n = len(values)
    if n < 4:
        return 0.0
    
    # Detrend by removing mean
    arr = np.array(values)
    arr = arr - np.mean(arr)
    
    # Compute FFT magnitudes
    fft_result = np.fft.rfft(arr)
    mags = np.abs(fft_result)
    
    # Compute peak-to-mean ratio
    mean_mag = np.mean(mags)
    if mean_mag <= 1e-12:
        return 0.0
    
    return float(np.max(mags) / mean_mag)


def fft_peak_mean(values: List[float]) -> float:
    """
    Compute FFT peak-to-mean coherence ratio.
    Uses NumPy if available, otherwise falls back to pure Python.
    
    Args:
        values: Time series data
        
    Returns:
        Ratio of max FFT magnitude to mean magnitude (higher = more coherent/periodic)
    """
    if HAS_NUMPY:
        return _numpy_fft_peak_mean(values)
    else:
        return _pure_python_fft_peak_mean(values)


def coherence_score(values: List[float], window_size: int = None) -> float:
    """
    Compute coherence score for a time series.
    
    Args:
        values: Time series data
        window_size: Optional window size (defaults to full series)
        
    Returns:
        Coherence score (FFT peak-to-mean ratio)
    """
    if window_size is not None and len(values) > window_size:
        # Use most recent window
        values = values[-window_size:]
    
    return fft_peak_mean(values)

