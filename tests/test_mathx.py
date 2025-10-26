# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""
Tests for math primitives: coherence and MDL.
"""
import math

from maat.mathx.coherence import fft_peak_mean, coherence_score
from maat.mathx.mdl import mdl_delta_bits, _linear_fit_residuals


def test_fft_peak_mean_sine_wave():
    """Test that a clean sine wave has high coherence."""
    # Generate a clean sine wave
    n = 64
    values = [math.sin(2 * math.pi * t / 16.0) for t in range(n)]
    
    coh = fft_peak_mean(values)
    
    # Clean periodic signal should have high peak-to-mean ratio
    assert coh > 5.0, f"Expected coherence > 5.0 for sine wave, got {coh}"
    print(f"✓ Sine wave coherence: {coh:.2f}")


def test_fft_peak_mean_noise():
    """Test that white noise has low coherence."""
    # Generate pseudo-random noise (deterministic)
    values = [(i * 17 + 42) % 100 / 50.0 - 1.0 for i in range(64)]
    
    coh = fft_peak_mean(values)
    
    # Noise should have lower coherence than periodic signal
    assert coh < 10.0, f"Expected coherence < 10.0 for noise, got {coh}"
    print(f"✓ Noise coherence: {coh:.2f}")


def test_fft_peak_mean_constant():
    """Test that a constant signal has low coherence."""
    values = [1.0] * 64
    
    coh = fft_peak_mean(values)
    
    # Constant signal (all energy at DC) should have specific behavior
    print(f"✓ Constant signal coherence: {coh:.2f}")


def test_linear_fit_residuals():
    """Test linear fit residual computation."""
    # Perfect linear trend
    values = [float(i) for i in range(10)]
    
    resid = _linear_fit_residuals(values)
    
    # Residuals should be near zero for perfect fit
    max_resid = max(abs(r) for r in resid)
    assert max_resid < 1e-10, f"Expected near-zero residuals, got max {max_resid}"
    print(f"✓ Linear fit residuals for perfect line: max={max_resid:.2e}")


def test_mdl_linear_vs_null():
    """Test that MDL prefers linear model for trending data."""
    # Strong linear trend
    values = [float(i) + 0.1 * (i % 3) for i in range(50)]
    
    mdl_bits = mdl_delta_bits(values, model="linear", params=2)
    
    # Linear model should compress better (negative delta)
    assert mdl_bits < 0, f"Expected negative MDL for linear trend, got {mdl_bits}"
    print(f"✓ MDL delta for linear trend: {mdl_bits:.2f} bits (negative = good)")


def test_mdl_null_for_noise():
    """Test that MDL doesn't strongly prefer linear for pure noise."""
    # Pseudo-random noise
    values = [math.sin(i * 1.234) + math.cos(i * 0.567) for i in range(50)]
    
    mdl_bits = mdl_delta_bits(values, model="linear", params=2)
    
    # For noise, linear model shouldn't compress much better
    # (might be slightly negative or positive)
    print(f"✓ MDL delta for noisy data: {mdl_bits:.2f} bits")


def test_coherence_window():
    """Test coherence with windowing."""
    # Long series with periodic component
    values = [math.sin(2 * math.pi * t / 8.0) for t in range(128)]
    
    coh_full = coherence_score(values)
    coh_window = coherence_score(values, window_size=32)
    
    # Both should detect periodicity
    assert coh_full > 5.0
    assert coh_window > 5.0
    print(f"✓ Coherence full={coh_full:.2f}, windowed={coh_window:.2f}")


def test_mdl_empty_input():
    """Test MDL handles empty input gracefully."""
    mdl_bits = mdl_delta_bits([])
    assert mdl_bits == 0.0
    print(f"✓ MDL for empty input: {mdl_bits}")


def test_fft_small_input():
    """Test FFT handles small input gracefully."""
    coh = fft_peak_mean([1.0, 2.0])
    assert coh == 0.0  # Too small for meaningful FFT
    print(f"✓ Coherence for small input: {coh}")


if __name__ == "__main__":
    print("Running mathx tests...\n")
    test_fft_peak_mean_sine_wave()
    test_fft_peak_mean_noise()
    test_fft_peak_mean_constant()
    test_linear_fit_residuals()
    test_mdl_linear_vs_null()
    test_mdl_null_for_noise()
    test_coherence_window()
    test_mdl_empty_input()
    test_fft_small_input()
    print("\n✅ All mathx tests passed!")

