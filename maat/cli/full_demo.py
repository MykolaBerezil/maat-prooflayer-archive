# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""
Full end-to-end MA'AT demo with all features:
- Recursive reactor (inner/outer)
- LLM adapter with --hyp-file
- Causal DAG scaffolding
- Learned gating policy
- Control rods and SCRAM
"""
import argparse
import json
from pathlib import Path

from ..reactor.reactor import RecursiveMAAT
from ..core.canonical import read_jsonl
from ..engine.generator import LLMAdapter, HybridGenerator
from ..engine.causal import CausalGraph
from ..engine.policy import LearnedGatesPolicy


def print_ledger_tail(path: Path, n: int = 5):
    """Print last n lines of a ledger."""
    if not path.exists():
        print(f"  (no records)")
        return
    
    records = read_jsonl(path)
    for rec in records[-n:]:
        if "status" in rec:  # Receipt
            print(f"  - {rec['status']}: hyp={rec['hyp'][:16]}... slot={rec['slot_id']}")
        elif "decision" in rec:  # Decision
            print(f"  - {rec['decision']}: hyp={rec['hyp'][:16]}...")
        else:
            print(f"  - {rec.get('id', rec.get('ukh', 'unknown'))[:16]}...")


def main():
    parser = argparse.ArgumentParser(description="MA'AT Full System Demo")
    parser.add_argument("--out", type=str, default="./out", help="Output directory")
    parser.add_argument("--cycles", type=int, default=100, help="Number of cycles to run")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--stress", action="store_true", help="Enable stress mode (lower SCRAM thresholds)")
    parser.add_argument("--use-llm-file", type=str, default=None, help="Path to hypotheses file for LLM emulation")
    parser.add_argument("--use-policy", action="store_true", help="Enable learned gating policy")
    parser.add_argument("--use-causal", action="store_true", help="Enable causal DAG scaffolding")
    parser.add_argument("--verbose", action="store_true", help="Verbose output every cycle")
    
    args = parser.parse_args()
    
    outdir = Path(args.out)
    
    print(f"MA'AT Full System Demo")
    print(f"=" * 60)
    print(f"Output directory: {outdir}")
    print(f"Cycles: {args.cycles}")
    print(f"Seed: {args.seed}")
    print(f"Features:")
    print(f"  - Recursive reactor: ✓")
    print(f"  - LLM adapter: {'✓' if args.use_llm_file else '✗'}")
    print(f"  - Learned policy: {'✓' if args.use_policy else '✗'}")
    print(f"  - Causal DAG: {'✓' if args.use_causal else '✗'}")
    print(f"  - Stress mode: {'✓' if args.stress else '✗'}")
    print()
    
    # Create reactor
    reactor = RecursiveMAAT(outdir, seed=args.seed)
    
    # Configure LLM adapter if requested
    if args.use_llm_file:
        print(f"Using LLM file: {args.use_llm_file}")
        llm_adapter = LLMAdapter(hyp_file=Path(args.use_llm_file))
        hybrid_gen = HybridGenerator(llm_adapter)
        reactor.inner.generator = hybrid_gen
        reactor.outer.generator = hybrid_gen
        print()
    
    # Configure learned policy if requested
    policy = None
    if args.use_policy:
        print("Enabling learned gating policy")
        policy = LearnedGatesPolicy(target_accept_min=0.20, target_accept_max=0.35)
        
        # Load existing policy if available
        policy_path = outdir / "policy.json"
        if policy_path.exists():
            policy.load(policy_path)
            print(f"  Loaded existing policy from {policy_path}")
        print()
    
    # Configure causal DAG if requested
    causal_graph = None
    if args.use_causal:
        print("Enabling causal DAG scaffolding")
        causal_graph = CausalGraph()
        
        # Load existing graph if available
        causal_path = outdir / "causal_graph.json"
        if causal_path.exists():
            causal_graph.load(causal_path)
            print(f"  Loaded existing graph from {causal_path}")
        print()
    
    if args.stress:
        print("STRESS MODE: Lowering SCRAM thresholds")
        reactor.scram.criticality_limit = 1.3
        reactor.scram.temperature_limit = 0.6
        print()
    
    # Run cycles
    print("Running reactor cycles...")
    print()
    
    for i in range(args.cycles):
        result = reactor.cycle()
        
        # Update learned policy if enabled
        if policy:
            # Get recent decisions and evidence
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
            
            # Update reactor thresholds
            reactor.inner.hemi_R.thresholds.bayes = new_thresholds.bayes
            reactor.inner.hemi_R.thresholds.coh = new_thresholds.coh
            reactor.inner.hemi_R.thresholds.mdl = new_thresholds.mdl
        
        # Update causal graph if enabled
        if causal_graph:
            # Read recent receipts and update graph
            R_receipts = read_jsonl(reactor.inner.hemi_R.receipts_path)
            for receipt in R_receipts[-3:]:
                # For now, just track that we're using the graph
                # In a real implementation, we'd extract causal structure from hypotheses
                pass
        
        # Print every 10 cycles or on SCRAM or if verbose
        if args.verbose or (i + 1) % 10 == 0 or result["status"] == "SCRAM":
            print(f"Cycle {result['cycle']}: {result['status']}")
            print(f"  Criticality: {result['state']['criticality']:.3f}")
            print(f"  Temperature: {result['state']['temperature']:.3f}")
            print(f"  Pressure: {result['state']['pressure']:.3f}")
            print(f"  Reality correlation: {result['state']['reality_corr']:.3f}")
            
            if policy:
                print(f"  Policy thresholds:")
                print(f"    Bayes: {policy.thresholds.bayes:.3f}")
                print(f"    Coherence: {policy.thresholds.coh:.3f}")
                print(f"    MDL: {policy.thresholds.mdl:.3f}")
                print(f"    Updates: {policy.update_count}")
            
            if args.verbose:
                print(f"  Control rods:")
                for rod, depth in result['rods'].items():
                    print(f"    {rod}: {depth:.3f}")
        
        if result["status"] == "SCRAM":
            print()
            print("!!! SCRAM TRIGGERED !!!")
            print(f"Reactor shut down at cycle {result['cycle']}")
            break
    
    print()
    print("=" * 60)
    print("Final System State")
    print("=" * 60)
    print()
    
    # Save policy if enabled
    if policy:
        policy_path = outdir / "policy.json"
        policy.save(policy_path)
        print(f"Saved policy to {policy_path}")
        
        policy_report_path = outdir / "policy_report.json"
        with open(policy_report_path, 'w') as f:
            json.dump(policy.get_report(), f, indent=2)
        print(f"Saved policy report to {policy_report_path}")
        print()
    
    # Save causal graph if enabled
    if causal_graph:
        causal_path = outdir / "causal_graph.json"
        causal_graph.save(causal_path)
        print(f"Saved causal graph to {causal_path}")
        
        causal_report_path = outdir / "causal_report.json"
        with open(causal_report_path, 'w') as f:
            json.dump(causal_graph.get_stats(), f, indent=2)
        print(f"Saved causal report to {causal_report_path}")
        print()
    
    print("Final ledger tails:")
    print()
    
    print("Inner R Receipts (last 5):")
    print_ledger_tail(outdir / "inner_R_receipts.jsonl", 5)
    print()
    
    print("Inner L Receipts (last 5):")
    print_ledger_tail(outdir / "inner_L_receipts.jsonl", 5)
    print()
    
    print("Outer R Receipts (last 5):")
    print_ledger_tail(outdir / "outer_R_receipts.jsonl", 5)
    print()
    
    print("Outer L Receipts (last 5):")
    print_ledger_tail(outdir / "outer_L_receipts.jsonl", 5)
    print()
    
    # Print stats
    inner_stats = reactor.inner.get_stats()
    outer_stats = reactor.outer.get_stats()
    
    print("Engine Statistics:")
    print(f"  Inner R: {inner_stats['R']['total']} total, "
          f"{inner_stats['R']['accept']} accept, "
          f"{inner_stats['R']['accept_rate']:.1%} rate")
    print(f"  Inner L: {inner_stats['L']['total']} total, "
          f"{inner_stats['L']['accept']} accept, "
          f"{inner_stats['L']['accept_rate']:.1%} rate")
    print(f"  Outer R: {outer_stats['R']['total']} total, "
          f"{outer_stats['R']['accept']} accept, "
          f"{outer_stats['R']['accept_rate']:.1%} rate")
    print(f"  Outer L: {outer_stats['L']['total']} total, "
          f"{outer_stats['L']['accept']} accept, "
          f"{outer_stats['L']['accept_rate']:.1%} rate")
    
    print()
    print("=" * 60)
    print("Demo complete!")
    print(f"All ledgers written to: {outdir}")
    print("=" * 60)


if __name__ == "__main__":
    main()

