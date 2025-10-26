# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""
CLI demo for MA'AT reactor.
"""
import argparse
from pathlib import Path

from ..reactor.reactor import RecursiveMAAT
from ..core.canonical import read_jsonl
from ..engine.generator import LLMAdapter, HybridGenerator


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
    parser = argparse.ArgumentParser(description="MA'AT Reactor Demo")
    parser.add_argument("--out", type=str, default="./out", help="Output directory")
    parser.add_argument("--cycles", type=int, default=50, help="Number of cycles to run")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--stress", action="store_true", help="Enable stress mode (lower SCRAM thresholds)")
    parser.add_argument("--use-llm-file", type=str, default=None, help="Path to hypotheses file for LLM emulation")
    
    args = parser.parse_args()
    
    outdir = Path(args.out)
    
    print(f"MA'AT Reactor Demo")
    print(f"==================")
    print(f"Output directory: {outdir}")
    print(f"Cycles: {args.cycles}")
    print(f"Seed: {args.seed}")
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
        
        # Print every 10 cycles or on SCRAM
        if (i + 1) % 10 == 0 or result["status"] == "SCRAM":
            print(f"Cycle {result['cycle']}: {result['status']}")
            print(f"  Criticality: {result['state']['criticality']:.3f}")
            print(f"  Temperature: {result['state']['temperature']:.3f}")
            print(f"  Pressure: {result['state']['pressure']:.3f}")
            print(f"  Reality correlation: {result['state']['reality_corr']:.3f}")
            print(f"  Control rods:")
            for rod, depth in result['rods'].items():
                print(f"    {rod}: {depth:.3f}")
        
        if result["status"] == "SCRAM":
            print()
            print("!!! SCRAM TRIGGERED !!!")
            print(f"Reactor shut down at cycle {result['cycle']}")
            break
    
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


if __name__ == "__main__":
    main()

