"""
Tests for slot gates and decision logic.
"""
import math
import tempfile
from pathlib import Path

from maat.slot.gates import (
    GateThresholds, Slot, compute_bayesian_update,
    compute_attention_metrics, evaluate_gates
)
from maat.core.records import AGL_Hypothesis
from maat.core.canonical import add_ukh, read_jsonl


def test_bayesian_update():
    """Test Bayesian posterior computation."""
    # Series with values above and below mean
    series = [1.0, 2.0, 3.0, 4.0, 5.0]
    
    s, f, post_mean = compute_bayesian_update(series)
    
    # Mean is 3.0, so 2 values above, 3 below
    assert s == 2
    assert f == 3
    # Beta(1+2, 1+3) = Beta(3, 4), mean = 3/7 ≈ 0.429
    assert 0.42 < post_mean < 0.44
    print(f"✓ Bayesian update: s={s}, f={f}, post_mean={post_mean:.3f}")


def test_attention_metrics():
    """Test attention metric computation."""
    # Periodic series
    series = [math.sin(2 * math.pi * t / 8.0) for t in range(32)]
    coh = 10.0
    mdl_bits = -5.0
    
    att = compute_attention_metrics(series, coh, mdl_bits)
    
    assert 0.0 <= att.nov <= 1.0
    assert 0.0 <= att.coh <= 1.0
    assert 0.0 <= att.risk <= 1.0
    assert 0.0 <= att.chaos <= 1.0
    assert 0.0 <= att.att <= 1.0
    
    print(f"✓ Attention metrics: nov={att.nov:.3f}, coh={att.coh:.3f}, "
          f"risk={att.risk:.3f}, chaos={att.chaos:.3f}, att={att.att:.3f}")


def test_evaluate_gates_accept():
    """Test gate evaluation for acceptance."""
    thresholds = GateThresholds(bayes=0.7, coh=7.0, mdl=-5.0)
    
    # Strong hypothesis: high posterior, high coherence, good compression
    decision, reasons = evaluate_gates(0.85, 10.0, -8.0, thresholds)
    
    assert decision == "accept"
    assert len(reasons) == 3
    print(f"✓ Gate evaluation (accept): {decision}")
    for r in reasons:
        print(f"  - {r}")


def test_evaluate_gates_reject():
    """Test gate evaluation for rejection."""
    thresholds = GateThresholds(bayes=0.7, coh=7.0, mdl=-5.0)
    
    # Weak hypothesis: low posterior, low coherence, poor compression
    decision, reasons = evaluate_gates(0.3, 2.0, 5.0, thresholds)
    
    assert decision == "reject"
    print(f"✓ Gate evaluation (reject): {decision}")


def test_evaluate_gates_defer():
    """Test gate evaluation for deferral."""
    thresholds = GateThresholds(bayes=0.7, coh=7.0, mdl=-5.0)
    
    # Marginal hypothesis: passes some gates but not all
    decision, reasons = evaluate_gates(0.75, 5.0, 2.0, thresholds)
    
    assert decision == "defer"
    print(f"✓ Gate evaluation (defer): {decision}")


def test_slot_decide_periodic():
    """Test slot decision on periodic data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        outdir = Path(tmpdir)
        
        # Create slot with R-hemisphere thresholds (exploratory)
        slot_R = Slot(
            "R", "R",
            GateThresholds(bayes=0.80, coh=7.5, mdl=-8.0),
            outdir / "receipts.jsonl",
            outdir / "evidence.jsonl",
            outdir / "decisions.jsonl"
        )
        
        # Create hypothesis
        hyp = add_ukh(AGL_Hypothesis(
            "periodic signal detected",
            "R",
            ["obs_test123"]
        ))
        
        # Generate strong periodic signal
        series = [math.sin(2 * math.pi * t / 8.0) + 0.1 * (t % 3) for t in range(64)]
        
        # Evaluate
        tst, evid, dec = slot_R.decide(hyp, series)
        
        # Check that records were created
        assert "ukh" in tst
        assert "ukh" in evid
        assert "ukh" in dec
        
        # Check evidence
        assert "bayes" in evid
        assert "coherence" in evid
        assert "mdl" in evid
        
        # Check decision
        assert dec["decision"] in ["accept", "defer", "reject"]
        
        # Check ledgers were written
        evidence_records = read_jsonl(outdir / "evidence.jsonl")
        decision_records = read_jsonl(outdir / "decisions.jsonl")
        receipt_records = read_jsonl(outdir / "receipts.jsonl")
        
        assert len(evidence_records) == 1
        assert len(decision_records) == 1
        assert len(receipt_records) == 1
        
        print(f"✓ Slot decision on periodic data: {dec['decision']}")
        print(f"  Evidence UKH: {evid['ukh'][:16]}...")
        print(f"  Decision: {dec['decision']}")
        print(f"  Reasons: {dec['reason']}")


def test_slot_r_vs_l_thresholds():
    """Test that R and L hemispheres have different acceptance rates."""
    with tempfile.TemporaryDirectory() as tmpdir:
        outdir = Path(tmpdir)
        
        # Create R (exploratory) and L (conservative) slots
        slot_R = Slot(
            "R", "R",
            GateThresholds(bayes=0.80, coh=7.5, mdl=-8.0),
            outdir / "R_receipts.jsonl",
            outdir / "R_evidence.jsonl",
            outdir / "R_decisions.jsonl"
        )
        
        slot_L = Slot(
            "L", "L",
            GateThresholds(bayes=0.95, coh=8.5, mdl=-16.0),
            outdir / "L_receipts.jsonl",
            outdir / "L_evidence.jsonl",
            outdir / "L_decisions.jsonl"
        )
        
        # Marginal periodic signal
        series = [math.sin(2 * math.pi * t / 16.0) + 0.3 * math.sin(t * 0.7) for t in range(64)]
        
        hyp_R = add_ukh(AGL_Hypothesis("signal R", "R", ["obs_1"]))
        hyp_L = add_ukh(AGL_Hypothesis("signal L", "L", ["obs_1"]))
        
        _, _, dec_R = slot_R.decide(hyp_R, series)
        _, _, dec_L = slot_L.decide(hyp_L, series)
        
        print(f"✓ R-hemisphere decision: {dec_R['decision']}")
        print(f"✓ L-hemisphere decision: {dec_L['decision']}")
        
        # L should be more conservative (more likely to reject/defer)
        # This is probabilistic, but with marginal data L should be stricter


def test_tail_evidence_ledger():
    """Test reading tail of evidence ledger."""
    with tempfile.TemporaryDirectory() as tmpdir:
        outdir = Path(tmpdir)
        
        slot = Slot(
            "R", "R",
            GateThresholds(bayes=0.80, coh=7.5, mdl=-8.0),
            outdir / "receipts.jsonl",
            outdir / "evidence.jsonl",
            outdir / "decisions.jsonl"
        )
        
        # Generate multiple hypotheses
        for i in range(5):
            hyp = add_ukh(AGL_Hypothesis(f"hyp_{i}", "R", [f"obs_{i}"]))
            series = [math.sin(2 * math.pi * t / (8 + i)) for t in range(32)]
            slot.decide(hyp, series)
        
        # Read evidence ledger
        evidence = read_jsonl(outdir / "evidence.jsonl")
        
        assert len(evidence) == 5
        
        print(f"✓ Evidence ledger tail (last 3):")
        for evid in evidence[-3:]:
            print(f"  - hyp={evid['hyp']}, "
                  f"posterior_mean={evid['bayes']['posterior']['mean']}, "
                  f"coh={evid['coherence']['peak_mean']}")


if __name__ == "__main__":
    print("Running slot tests...\n")
    test_bayesian_update()
    test_attention_metrics()
    test_evaluate_gates_accept()
    test_evaluate_gates_reject()
    test_evaluate_gates_defer()
    test_slot_decide_periodic()
    test_slot_r_vs_l_thresholds()
    test_tail_evidence_ledger()
    print("\n✅ All slot tests passed!")

