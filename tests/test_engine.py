# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""
Tests for the bicameral MA'AT engine.
"""
import math
import tempfile
from pathlib import Path

from maat.engine.maat import create_maat_engine
from maat.core.canonical import read_jsonl


def test_maat_engine_creation():
    """Test creating a MA'AT engine."""
    with tempfile.TemporaryDirectory() as tmpdir:
        outdir = Path(tmpdir)
        
        engine = create_maat_engine("test", outdir, seed=42)
        
        assert engine.name == "test"
        assert engine.seed == 42
        assert engine.hemi_R.hemi == "R"
        assert engine.hemi_L.hemi == "L"
        
        # R should have looser thresholds than L
        assert engine.hemi_R.thresholds.bayes < engine.hemi_L.thresholds.bayes
        assert engine.hemi_R.thresholds.coh < engine.hemi_L.thresholds.coh
        assert engine.hemi_R.thresholds.mdl > engine.hemi_L.thresholds.mdl
        
        print("✓ MA'AT engine created with correct configuration")


def test_hypothesis_generation():
    """Test deterministic hypothesis generation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        outdir = Path(tmpdir)
        engine = create_maat_engine("test", outdir, seed=42)
        
        # Generate hypotheses from a series
        series = [1.0, 2.0, 3.0, 4.0, 5.0]
        hyps = engine.generate_hypotheses(["obs_test"], series)
        
        # Should generate 3 hypotheses
        assert len(hyps) == 3
        
        # All should have UKH
        for hyp in hyps:
            assert "ukh" in hyp
            assert hyp["hemi"] == "R"
            assert "obs_test" in hyp["from"]
        
        print(f"✓ Generated {len(hyps)} hypotheses:")
        for hyp in hyps:
            print(f"  - {hyp['claim']}")


def test_maat_cycle():
    """Test running one MA'AT cycle."""
    with tempfile.TemporaryDirectory() as tmpdir:
        outdir = Path(tmpdir)
        engine = create_maat_engine("test", outdir, seed=42)
        
        # Generate periodic series
        series = [math.sin(2 * math.pi * t / 8.0) for t in range(64)]
        
        # Run one cycle
        result = engine.cycle(series, "test:source")
        
        assert "obs" in result
        assert "src" in result
        assert result["src"] == "test:source"
        assert "results" in result
        assert len(result["results"]) == 3  # 3 hypotheses
        
        # Check that observation was written
        obs_records = read_jsonl(outdir / "test_observations.jsonl")
        assert len(obs_records) == 1
        assert obs_records[0]["id"] == result["obs"]
        
        print(f"✓ MA'AT cycle completed:")
        print(f"  Observation: {result['obs']}")
        for r in result["results"]:
            print(f"  - {r['claim']}: R={r['R']}, L={r['L']}")


def test_callosum_transfer():
    """Test that R-accepted hypotheses are transferred to L."""
    with tempfile.TemporaryDirectory() as tmpdir:
        outdir = Path(tmpdir)
        engine = create_maat_engine("test", outdir, seed=42)
        
        # Generate strong periodic signal that R should accept
        series = [math.sin(2 * math.pi * t / 8.0) for t in range(64)]
        
        result = engine.cycle(series, "test:source")
        
        # Check if any hypotheses were accepted by R
        R_accepts = [r for r in result["results"] if r["R"] == "accept"]
        
        # For accepted hypotheses, L should have evaluated them
        for r in R_accepts:
            assert r["L"] != "n/a", "L should evaluate R-accepted hypotheses"
        
        # For non-accepted hypotheses, L should not evaluate
        R_non_accepts = [r for r in result["results"] if r["R"] != "accept"]
        for r in R_non_accepts:
            assert r["L"] == "n/a", "L should not evaluate R-rejected hypotheses"
        
        print(f"✓ Callosum transfer verified:")
        print(f"  R accepts: {len(R_accepts)}")
        print(f"  R non-accepts: {len(R_non_accepts)}")


def test_ledger_consistency():
    """Test that all ledgers have consistent UKH values."""
    with tempfile.TemporaryDirectory() as tmpdir:
        outdir = Path(tmpdir)
        engine = create_maat_engine("test", outdir, seed=42)
        
        # Run multiple cycles
        for i in range(3):
            series = [math.sin(2 * math.pi * t / (8 + i)) + 0.1 * i for t in range(32)]
            engine.cycle(series, f"test:source_{i}")
        
        # Read all ledgers
        observations = read_jsonl(outdir / "test_observations.jsonl")
        R_evidence = read_jsonl(outdir / "test_R_evidence.jsonl")
        R_decisions = read_jsonl(outdir / "test_R_decisions.jsonl")
        R_receipts = read_jsonl(outdir / "test_R_receipts.jsonl")
        
        # Check counts
        assert len(observations) == 3
        assert len(R_evidence) == 9  # 3 cycles * 3 hypotheses
        assert len(R_decisions) == 9
        assert len(R_receipts) == 9
        
        # Check UKH consistency
        for evid in R_evidence:
            assert "ukh" in evid
            assert len(evid["ukh"]) == 64
        
        for dec in R_decisions:
            assert "ukh" in dec
            assert len(dec["ukh"]) == 64
        
        for rec in R_receipts:
            assert "ukh" in rec
            assert len(rec["ukh"]) == 64
            # Receipt should reference evidence and decision UKHs
            assert "evid" in rec
            assert "decision_ukh" in rec
        
        print("✓ Ledger consistency verified:")
        print(f"  Observations: {len(observations)}")
        print(f"  R Evidence: {len(R_evidence)}")
        print(f"  R Decisions: {len(R_decisions)}")
        print(f"  R Receipts: {len(R_receipts)}")


def test_engine_stats():
    """Test engine statistics computation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        outdir = Path(tmpdir)
        engine = create_maat_engine("test", outdir, seed=42)
        
        # Run cycles
        for i in range(5):
            series = [math.sin(2 * math.pi * t / 8.0) + 0.2 * i for t in range(32)]
            engine.cycle(series, f"test:source_{i}")
        
        # Get stats
        stats = engine.get_stats()
        
        assert "R" in stats
        assert "L" in stats
        assert stats["R"]["total"] == 15  # 5 cycles * 3 hypotheses
        assert "accept_rate" in stats["R"]
        assert "accept_rate" in stats["L"]
        
        print("✓ Engine statistics:")
        print(f"  R: total={stats['R']['total']}, accept={stats['R']['accept']}, "
              f"reject={stats['R']['reject']}, defer={stats['R']['defer']}, "
              f"rate={stats['R']['accept_rate']:.2%}")
        print(f"  L: total={stats['L']['total']}, accept={stats['L']['accept']}, "
              f"reject={stats['L']['reject']}, defer={stats['L']['defer']}, "
              f"rate={stats['L']['accept_rate']:.2%}")


def test_ledger_tails():
    """Test reading tails of ledgers."""
    with tempfile.TemporaryDirectory() as tmpdir:
        outdir = Path(tmpdir)
        engine = create_maat_engine("test", outdir, seed=42)
        
        # Run cycles
        for i in range(3):
            series = [math.sin(2 * math.pi * t / 8.0) for t in range(32)]
            engine.cycle(series, f"test:source_{i}")
        
        # Read ledger tails
        R_receipts = read_jsonl(outdir / "test_R_receipts.jsonl")
        L_receipts = read_jsonl(outdir / "test_L_receipts.jsonl")
        
        print("✓ Last 5 R receipts:")
        for rec in R_receipts[-5:]:
            print(f"  - status={rec['status']}, hyp={rec['hyp']}, slot={rec['slot_id']}")
        
        if L_receipts:
            print("✓ Last 5 L receipts:")
            for rec in L_receipts[-5:]:
                print(f"  - status={rec['status']}, hyp={rec['hyp']}, slot={rec['slot_id']}")
        else:
            print("✓ No L receipts (no R accepts transferred)")


if __name__ == "__main__":
    print("Running engine tests...\n")
    test_maat_engine_creation()
    test_hypothesis_generation()
    test_maat_cycle()
    test_callosum_transfer()
    test_ledger_consistency()
    test_engine_stats()
    test_ledger_tails()
    print("\n✅ All engine tests passed!")

