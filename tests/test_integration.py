"""
Integration test for the complete MA'AT system.
Tests all components working together.
"""
import tempfile
from pathlib import Path

from maat.reactor.reactor import RecursiveMAAT
from maat.engine.generator import LLMAdapter, HybridGenerator
from maat.engine.causal import CausalGraph
from maat.engine.policy import LearnedGatesPolicy
from maat.core.canonical import read_jsonl


def test_full_system_integration():
    """Test complete system with all features enabled."""
    with tempfile.TemporaryDirectory() as tmpdir:
        outdir = Path(tmpdir)
        
        print("Testing full MA'AT system integration...")
        print()
        
        # Create reactor
        reactor = RecursiveMAAT(outdir, seed=42)
        
        # Create LLM adapter with test file
        hyp_file = Path("/home/ubuntu/maat_project/hypotheses.txt")
        if hyp_file.exists():
            llm_adapter = LLMAdapter(hyp_file=hyp_file)
            hybrid_gen = HybridGenerator(llm_adapter)
            reactor.inner.generator = hybrid_gen
            reactor.outer.generator = hybrid_gen
            print("✓ LLM adapter configured")
        
        # Create policy
        policy = LearnedGatesPolicy()
        print("✓ Learned policy created")
        
        # Create causal graph
        causal_graph = CausalGraph()
        print("✓ Causal graph created")
        
        print()
        print("Running 30 cycles...")
        
        # Run cycles
        for i in range(30):
            result = reactor.cycle()
            
            # Update policy
            R_decisions = read_jsonl(reactor.inner.hemi_R.decisions_path)
            R_evidence = read_jsonl(reactor.inner.hemi_R.evidence_path)
            
            recent_accepts = sum(1 for d in R_decisions[-10:] if d.get('decision') == 'accept')
            accept_rate = recent_accepts / 10.0 if len(R_decisions) >= 10 else 0.0
            
            metrics = {
                'acceptance_rate': accept_rate,
                'recent_decisions': R_decisions[-20:],
                'recent_evidence': R_evidence[-20:]
            }
            
            new_thresholds = policy.step(metrics)
            reactor.inner.hemi_R.thresholds.bayes = new_thresholds.bayes
            reactor.inner.hemi_R.thresholds.coh = new_thresholds.coh
            reactor.inner.hemi_R.thresholds.mdl = new_thresholds.mdl
            
            assert result["status"] in ["OK", "SCRAM"]
        
        print("✓ 30 cycles completed")
        print()
        
        # Verify ledgers exist
        assert (outdir / "inner_observations.jsonl").exists()
        assert (outdir / "inner_R_evidence.jsonl").exists()
        assert (outdir / "inner_R_decisions.jsonl").exists()
        assert (outdir / "outer_observations.jsonl").exists()
        print("✓ All ledgers created")
        
        # Save policy and causal graph
        policy.save(outdir / "policy.json")
        causal_graph.save(outdir / "causal_graph.json")
        print("✓ Policy and causal graph saved")
        
        # Verify stats
        inner_stats = reactor.inner.get_stats()
        outer_stats = reactor.outer.get_stats()
        
        assert inner_stats['R']['total'] == 30
        assert outer_stats['R']['total'] == 30
        print("✓ Statistics verified")
        
        print()
        print(f"Final policy thresholds:")
        print(f"  Bayes: {policy.thresholds.bayes:.3f}")
        print(f"  Coherence: {policy.thresholds.coh:.3f}")
        print(f"  MDL: {policy.thresholds.mdl:.3f}")
        print(f"  Updates: {policy.update_count}")
        
        print()
        print("✅ Full system integration test passed!")


if __name__ == "__main__":
    test_full_system_integration()
