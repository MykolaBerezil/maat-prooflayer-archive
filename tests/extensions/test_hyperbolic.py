# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
from maat.extensions.hyperbolic import HyperbolicCausalDAG

def test_hyperbolic_distance_monotone():
    """Test that hyperbolic distance increases with depth in DAG."""
    g = {"A":["B","C"], "B":["D"], "C":[], "D":[]}
    h = HyperbolicCausalDAG(g)
    dAB = h.hyperbolic_distance("A","B")
    dAD = h.hyperbolic_distance("A","D")
    assert dAD >= dAB, f"Distance A->D ({dAD}) should be >= A->B ({dAB})"
    print(f"✓ Hyperbolic distance test passed: dAB={dAB:.3f}, dAD={dAD:.3f}")

if __name__ == "__main__":
    test_hyperbolic_distance_monotone()
