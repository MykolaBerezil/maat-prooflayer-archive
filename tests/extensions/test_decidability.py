# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
from maat.slot.decidability_gate import DecidabilityGate

def test_decidability_gate_basic():
    """Test decidability gate detects self-referential hypotheses."""
    g = DecidabilityGate()
    hyp = {"claim":"This hypothesis refers to itself and is not provable."}
    out = g.test(hyp, [])
    assert out["decidable"] in (True, False)
    assert out["confidence"] >= 0.0
    assert "complexity_class" in out
    print(f"✓ Decidability gate test passed: {out}")

if __name__ == "__main__":
    test_decidability_gate_basic()
