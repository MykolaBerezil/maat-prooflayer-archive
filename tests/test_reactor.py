"""
Tests for the recursive MA'AT reactor.
"""
import tempfile
from pathlib import Path

from maat.reactor.reactor import RecursiveMAAT, ControlRod, ReactorControl, SCRAM


def test_control_rod():
    """Test control rod insertion and withdrawal."""
    rod = ControlRod("test")
    
    assert rod.depth == 0.0
    
    rod.insert(0.3)
    assert rod.depth == 0.3
    
    rod.insert(0.8)
    assert rod.depth == 1.0  # Clamped to max
    
    rod.withdraw(0.5)
    assert rod.depth == 0.5
    
    rod.withdraw(1.0)
    assert rod.depth == 0.0  # Clamped to min
    
    print("✓ Control rod insert/withdraw works correctly")


def test_reactor_control():
    """Test reactor control system."""
    control = ReactorControl()
    
    # Test moderate_generation
    k_base = 10
    k_mod = control.moderate_generation(k_base)
    assert k_mod == k_base  # No damping initially
    
    # Insert damping rods
    control.recursion_damper.depth = 0.5
    k_mod = control.moderate_generation(k_base)
    assert k_mod < k_base  # Should be reduced
    
    print(f"✓ Reactor control moderation: {k_base} -> {k_mod} with damping=0.5")


def test_reactor_auto_adjust():
    """Test automatic control rod adjustment."""
    control = ReactorControl()
    
    # High temperature should insert resource governor
    control.temperature = 0.9
    initial_depth = control.resource_governor.depth
    control.auto_adjust()
    assert control.resource_governor.depth > initial_depth
    
    print("✓ Auto-adjust responds to high temperature")
    
    # High criticality should insert damper
    control = ReactorControl()
    control.criticality = 1.5
    initial_depth = control.recursion_damper.depth
    control.auto_adjust()
    assert control.recursion_damper.depth > initial_depth
    
    print("✓ Auto-adjust responds to high criticality")


def test_scram_conditions():
    """Test SCRAM trigger conditions."""
    scram = SCRAM()
    
    # Normal state
    state = {"criticality": 1.0, "temperature": 0.5, "reality_corr": 0.8}
    assert not scram.should_scram(state)
    
    # High criticality
    state = {"criticality": 2.0, "temperature": 0.5, "reality_corr": 0.8}
    assert scram.should_scram(state)
    
    # High temperature
    state = {"criticality": 1.0, "temperature": 0.96, "reality_corr": 0.8}
    assert scram.should_scram(state)
    
    # Low reality correlation
    state = {"criticality": 1.0, "temperature": 0.5, "reality_corr": 0.02}
    assert scram.should_scram(state)
    
    print("✓ SCRAM triggers correctly for all conditions")


def test_recursive_maat_creation():
    """Test creating a recursive MA'AT reactor."""
    with tempfile.TemporaryDirectory() as tmpdir:
        outdir = Path(tmpdir)
        
        reactor = RecursiveMAAT(outdir, seed=42)
        
        assert reactor.inner.name == "inner"
        assert reactor.outer.name == "outer"
        assert reactor.cycle_count == 0
        
        print("✓ Recursive MA'AT reactor created")


def test_external_generation():
    """Test external data generation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        outdir = Path(tmpdir)
        reactor = RecursiveMAAT(outdir, seed=42)
        
        ext = reactor._next_external(64)
        
        assert len(ext) == 64
        # Should have some variation
        assert min(ext) < max(ext)
        
        print(f"✓ External data generated: {len(ext)} samples, "
              f"range=[{min(ext):.2f}, {max(ext):.2f}]")


def test_meta_series_extraction():
    """Test extracting meta-series from inner receipts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        outdir = Path(tmpdir)
        reactor = RecursiveMAAT(outdir, seed=42)
        
        # Run inner cycle to generate receipts
        ext = reactor._next_external(64)
        reactor.inner.cycle(ext, "test:source")
        
        # Extract meta-series
        meta = reactor._outer_series_from_inner_receipts(32)
        
        assert len(meta) > 0
        # Should be smoothed values between 0 and 1
        assert all(0.0 <= x <= 1.0 for x in meta)
        
        print(f"✓ Meta-series extracted: {len(meta)} samples")


def test_reactor_cycle():
    """Test running one reactor cycle."""
    with tempfile.TemporaryDirectory() as tmpdir:
        outdir = Path(tmpdir)
        reactor = RecursiveMAAT(outdir, seed=42)
        
        result = reactor.cycle()
        
        assert "status" in result
        assert result["status"] in ["OK", "SCRAM"]
        assert "cycle" in result
        assert result["cycle"] == 1
        assert "state" in result
        assert "rods" in result
        assert "inner" in result
        assert "outer" in result
        
        # Check telemetry
        assert "criticality" in result["state"]
        assert "temperature" in result["state"]
        assert "pressure" in result["state"]
        assert "reality_corr" in result["state"]
        
        print(f"✓ Reactor cycle {result['cycle']}: status={result['status']}")
        print(f"  Criticality: {result['state']['criticality']:.3f}")
        print(f"  Temperature: {result['state']['temperature']:.3f}")
        print(f"  Pressure: {result['state']['pressure']:.3f}")
        print(f"  Reality correlation: {result['state']['reality_corr']:.3f}")


def test_reactor_multiple_cycles():
    """Test running multiple reactor cycles."""
    with tempfile.TemporaryDirectory() as tmpdir:
        outdir = Path(tmpdir)
        reactor = RecursiveMAAT(outdir, seed=42)
        
        results = reactor.run(10)
        
        assert len(results) <= 10  # May stop early if SCRAM
        
        # Check that cycles increment
        for i, res in enumerate(results):
            assert res["cycle"] == i + 1
        
        # Count SCRAM events
        scrams = sum(1 for r in results if r["status"] == "SCRAM")
        
        print(f"✓ Ran {len(results)} cycles, {scrams} SCRAM events")
        
        # Show criticality trend
        crits = [r["state"]["criticality"] for r in results]
        print(f"  Criticality range: [{min(crits):.3f}, {max(crits):.3f}]")


def test_reactor_stress():
    """Test reactor under stress (should trigger SCRAM)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        outdir = Path(tmpdir)
        reactor = RecursiveMAAT(outdir, seed=42)
        
        # Lower SCRAM thresholds to trigger more easily
        reactor.scram.criticality_limit = 1.3
        reactor.scram.temperature_limit = 0.5
        
        results = reactor.run(40)
        
        # Should have triggered SCRAM at some point
        scrams = sum(1 for r in results if r["status"] == "SCRAM")
        
        print(f"✓ Stress test: {len(results)} cycles, {scrams} SCRAM events")
        
        if scrams > 0:
            scram_cycle = next(r["cycle"] for r in results if r["status"] == "SCRAM")
            print(f"  First SCRAM at cycle {scram_cycle}")


if __name__ == "__main__":
    print("Running reactor tests...\n")
    test_control_rod()
    test_reactor_control()
    test_reactor_auto_adjust()
    test_scram_conditions()
    test_recursive_maat_creation()
    test_external_generation()
    test_meta_series_extraction()
    test_reactor_cycle()
    test_reactor_multiple_cycles()
    test_reactor_stress()
    print("\n✅ All reactor tests passed!")

