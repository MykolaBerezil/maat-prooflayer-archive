"""
Bicameral MA'AT engine with R (exploratory) and L (conservative) hemispheres.
Implements hypothesis generation, testing, and callosum transfer.
"""
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.canonical import add_ukh, append_jsonl
from ..core.records import AGL_Observation, AGL_Hypothesis
from ..slot.gates import Slot, GateThresholds
from ..mathx.mdl import _linear_fit_residuals
from .generator import ProgrammaticGenerator, HybridGenerator


@dataclass
class MAAT:
    """
    Bicameral MA'AT engine with dual hemispheres.
    
    Right hemisphere (R): Exploratory, looser thresholds, generates novel hypotheses
    Left hemisphere (L): Conservative, stricter thresholds, verifies and compresses
    """
    name: str
    hemi_R: Slot
    hemi_L: Slot
    observations_path: Path
    generator: Any = field(default_factory=ProgrammaticGenerator)
    seed: int = 0
    rng: random.Random = field(default_factory=random.Random)
    
    def __post_init__(self):
        """Initialize random number generator with deterministic seed."""
        self.rng.seed(self.seed or (hash(self.name) & 0xffffffff))
    
    def generate_hypotheses(self, obs_ids: List[str], series: List[float]) -> List[Dict[str, Any]]:
        """
        Generate hypotheses from observation data.
        Uses configured generator (programmatic or hybrid).
        
        Args:
            obs_ids: List of observation IDs that generated these hypotheses
            series: Time series data
            
        Returns:
            List of hypothesis records
        """
        return self.generator.generate(obs_ids, series, "R")
    
    def cycle(self, series: List[float], src: str) -> Dict[str, Any]:
        """
        Run one MA'AT cycle: observe, generate hypotheses, test with both hemispheres.
        
        Args:
            series: Time series data to process
            src: Source identifier for the observation
            
        Returns:
            Dictionary with cycle results
        """
        # Create observation
        obs_obj = add_ukh(AGL_Observation(src, {"x": series}))
        append_jsonl(self.observations_path, obs_obj)
        
        # Generate hypotheses
        hyps = self.generate_hypotheses([obs_obj["id"]], series)
        
        results = []
        
        for hyp in hyps:
            # Test with R hemisphere (exploratory)
            _, _, dec_R = self.hemi_R.decide(hyp, series)
            
            # If R accepts, transfer to L via callosum
            if dec_R["decision"] == "accept":
                _, _, dec_L = self.hemi_L.decide(hyp, series)
                results.append({
                    "hyp": hyp["id"],
                    "claim": hyp["claim"],
                    "R": dec_R["decision"],
                    "L": dec_L["decision"]
                })
            else:
                results.append({
                    "hyp": hyp["id"],
                    "claim": hyp["claim"],
                    "R": dec_R["decision"],
                    "L": "n/a"
                })
        
        return {
            "obs": obs_obj["id"],
            "src": src,
            "results": results
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the MA'AT engine state.
        
        Returns:
            Dictionary with statistics
        """
        from ..core.canonical import read_jsonl
        
        R_decisions = read_jsonl(self.hemi_R.decisions_path)
        L_decisions = read_jsonl(self.hemi_L.decisions_path)
        
        R_accepts = sum(1 for d in R_decisions if d.get("decision") == "accept")
        R_rejects = sum(1 for d in R_decisions if d.get("decision") == "reject")
        R_defers = sum(1 for d in R_decisions if d.get("decision") == "defer")
        
        L_accepts = sum(1 for d in L_decisions if d.get("decision") == "accept")
        L_rejects = sum(1 for d in L_decisions if d.get("decision") == "reject")
        L_defers = sum(1 for d in L_decisions if d.get("decision") == "defer")
        
        return {
            "R": {
                "total": len(R_decisions),
                "accept": R_accepts,
                "reject": R_rejects,
                "defer": R_defers,
                "accept_rate": R_accepts / len(R_decisions) if R_decisions else 0.0
            },
            "L": {
                "total": len(L_decisions),
                "accept": L_accepts,
                "reject": L_rejects,
                "defer": L_defers,
                "accept_rate": L_accepts / len(L_decisions) if L_decisions else 0.0
            }
        }


def create_maat_engine(name: str, outdir: Path, seed: int = 0,
                       R_thresholds: Optional[GateThresholds] = None,
                       L_thresholds: Optional[GateThresholds] = None,
                       generator: Optional[Any] = None) -> MAAT:
    """
    Factory function to create a MA'AT engine with standard configuration.
    
    Args:
        name: Engine name
        outdir: Output directory for ledgers
        seed: Random seed for determinism
        R_thresholds: Optional custom thresholds for R hemisphere
        L_thresholds: Optional custom thresholds for L hemisphere
        
    Returns:
        Configured MAAT engine
    """
    outdir.mkdir(parents=True, exist_ok=True)
    
    # Default thresholds
    if R_thresholds is None:
        R_thresholds = GateThresholds(bayes=0.80, coh=7.5, mdl=-8.0)
    if L_thresholds is None:
        L_thresholds = GateThresholds(bayes=0.95, coh=8.5, mdl=-16.0)
    
    # Create paths
    prefix = f"{name}_"
    observations_path = outdir / f"{prefix}observations.jsonl"
    R_receipts = outdir / f"{prefix}R_receipts.jsonl"
    R_evidence = outdir / f"{prefix}R_evidence.jsonl"
    R_decisions = outdir / f"{prefix}R_decisions.jsonl"
    L_receipts = outdir / f"{prefix}L_receipts.jsonl"
    L_evidence = outdir / f"{prefix}L_evidence.jsonl"
    L_decisions = outdir / f"{prefix}L_decisions.jsonl"
    
    # Create slots
    hemi_R = Slot("R", "R", R_thresholds, R_receipts, R_evidence, R_decisions)
    hemi_L = Slot("L", "L", L_thresholds, L_receipts, L_evidence, L_decisions)
    
    return MAAT(
        name=name,
        hemi_R=hemi_R,
        hemi_L=hemi_L,
        observations_path=observations_path,
        generator=generator or ProgrammaticGenerator(),
        seed=seed
    )

