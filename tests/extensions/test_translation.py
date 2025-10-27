# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
from maat.engine.translation import DomainTranslator

def test_translation_fidelity():
    """Test cross-domain translation preserves fidelity score."""
    dt = DomainTranslator()
    h = {"claim": "signal exceeds baseline"}
    t = dt.translate(h, "linguistic","logical")
    assert "ASSERT(" in t["claim"]
    fid = dt.verify_translation_fidelity(h,t)
    assert fid >= 0.6, f"Fidelity {fid} should be >= 0.6"
    print(f"✓ Translation test passed: fidelity={fid}, claim={t['claim']}")

if __name__ == "__main__":
    test_translation_fidelity()
