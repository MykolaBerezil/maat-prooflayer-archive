# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
from maat.mathx.multiscale import MultiScaleAnalyzer

def test_multiscale_coherence_runs():
    """Test multi-scale analyzer produces coherence map."""
    x = [(-1)**i for i in range(32)]
    m = MultiScaleAnalyzer().wavelet_coherence(x)
    assert m["levels"] >= 2
    assert len(m["coherence"]) == m["levels"]
    print(f"✓ Multi-scale test passed: {m['levels']} levels, coherence={m['coherence'][:3]}")

if __name__ == "__main__":
    test_multiscale_coherence_runs()
