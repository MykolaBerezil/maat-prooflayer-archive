"""
Recursive MA'AT Reactor with control rods and SCRAM kill switch.
Inner MA'AT observes external stream; outer MA'AT observes inner's receipts.
"""
import math
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from ..engine.maat import create_maat_engine
from ..core.canonical import read_jsonl


@dataclass
class ControlRod:
    """A control rod that moderates reactor behavior."""
    name: str
    depth: float = 0.0  # 0.0 = fully withdrawn, 1.0 = fully inserted
    
    def insert(self, amount: float):
        """Insert rod (increase damping)."""
        self.depth = min(1.0, self.depth + amount)
    
    def withdraw(self, amount: float):
        """Withdraw rod (decrease damping)."""
        self.depth = max(0.0, self.depth - amount)


@dataclass
class ReactorControl:
    """Control system for the reactor with four control rods."""
    recursion_damper: ControlRod = field(default_factory=lambda: ControlRod("recursion_damper"))
    resource_governor: ControlRod = field(default_factory=lambda: ControlRod("resource_governor"))
    reality_anchor: ControlRod = field(default_factory=lambda: ControlRod("reality_anchor"))
    semantic_filter: ControlRod = field(default_factory=lambda: ControlRod("semantic_filter"))
    
    # Telemetry
    criticality: float = 0.0
    temperature: float = 0.0
    pressure: float = 0.0
    
    def moderate_generation(self, k: int) -> int:
        """
        Moderate hypothesis generation count based on control rod positions.
        
        Args:
            k: Base generation count
            
        Returns:
            Moderated generation count
        """
        damp = (0.4 * self.recursion_damper.depth +
                0.4 * self.resource_governor.depth +
                0.2 * self.semantic_filter.depth)
        return max(1, int(k * (1.0 - damp)))
    
    def auto_adjust(self):
        """Automatically adjust control rods based on telemetry."""
        # Temperature too high: reduce resource consumption
        if self.temperature > 0.8:
            self.resource_governor.insert(0.2)
        
        # Pressure too high: reduce recursion
        if self.pressure > 0.7:
            self.recursion_damper.insert(0.2)
        
        # Criticality too high: insert multiple rods
        if self.criticality > 1.2:
            self.recursion_damper.insert(0.2)
            self.semantic_filter.insert(0.1)
        
        # Criticality too low: withdraw rods to increase activity
        if self.criticality < 0.8:
            self.recursion_damper.withdraw(0.1)
            self.resource_governor.withdraw(0.05)
    
    def get_state(self) -> Dict[str, float]:
        """Get current control rod positions."""
        return {
            "recursion_damper": self.recursion_damper.depth,
            "resource_governor": self.resource_governor.depth,
            "reality_anchor": self.reality_anchor.depth,
            "semantic_filter": self.semantic_filter.depth
        }


@dataclass
class SCRAM:
    """Safety Control Rod Axe Man - emergency shutdown system."""
    enabled: bool = True
    criticality_limit: float = 1.8
    temperature_limit: float = 0.95
    reality_corr_limit: float = 0.05
    
    def should_scram(self, state: Dict[str, float]) -> bool:
        """
        Determine if SCRAM should be triggered.
        
        Args:
            state: Reactor state dictionary
            
        Returns:
            True if SCRAM should trigger
        """
        if not self.enabled:
            return False
        
        return (state.get("criticality", 0) > self.criticality_limit or
                state.get("temperature", 0) > self.temperature_limit or
                state.get("reality_corr", 1.0) < self.reality_corr_limit)


class RecursiveMAAT:
    """
    Recursive MA'AT reactor with inner and outer engines.
    
    Inner: Observes external world
    Outer: Observes inner's receipts (meta-cognition)
    """
    
    def __init__(self, outdir: Path, seed: int = 42):
        """
        Initialize recursive MA'AT reactor.
        
        Args:
            outdir: Output directory for all ledgers
            seed: Random seed for determinism
        """
        self.outdir = outdir
        self.outdir.mkdir(parents=True, exist_ok=True)
        
        # Create inner and outer engines
        self.inner = create_maat_engine("inner", outdir, seed=seed)
        self.outer = create_maat_engine("outer", outdir, seed=seed + 1000)
        
        # Control systems
        self.rods = ReactorControl()
        self.scram = SCRAM()
        
        # External data generator
        self.external_series: List[float] = []
        self.rng = random.Random(seed)
        self.cycle_count = 0
    
    def _next_external(self, n: int = 64) -> List[float]:
        """
        Generate next batch of external observations.
        Simulates a noisy periodic signal with drift.
        
        Args:
            n: Number of samples to generate
            
        Returns:
            List of float values
        """
        base = len(self.external_series)
        vals = []
        for t in range(n):
            # Two sine waves with different periods
            x = 0.8 * math.sin(2 * math.pi * (t + base) / 16.0)
            x += 0.2 * math.sin(2 * math.pi * (t + base) / 7.0)
            # Add noise and drift
            x += self.rng.uniform(-0.15, 0.15)
            x += 0.002 * (t + base)
            vals.append(x)
        
        self.external_series = vals
        return vals
    
    def _outer_series_from_inner_receipts(self, window: int = 32) -> List[float]:
        """
        Extract time series from inner receipts for outer observation.
        Converts acceptance/rejection pattern into a smoothed signal.
        
        Args:
            window: Number of recent receipts to consider
            
        Returns:
            Smoothed time series
        """
        inner_receipts = read_jsonl(self.inner.hemi_R.receipts_path)
        
        # Convert status to binary signal
        acc = [1.0 if r.get("status") == "accepted" else 0.0 
               for r in inner_receipts[-window:]]
        
        if not acc:
            return [0.0] * min(4, window)
        
        # Exponential smoothing
        series = []
        s = 0.0
        for a in acc:
            s = 0.7 * s + 0.3 * a
            series.append(s)
        
        return series
    
    def cycle(self, k_gen: int = 3) -> Dict[str, Any]:
        """
        Run one reactor cycle.
        
        Args:
            k_gen: Base hypothesis generation count
            
        Returns:
            Cycle results dictionary
        """
        start_time = time.time()
        self.cycle_count += 1
        
        # Generate external observations
        ext = self._next_external(64)
        
        # Inner MA'AT processes external stream
        inner_res = self.inner.cycle(ext, "external:world")
        
        # Extract meta-series from inner receipts
        meta_series = self._outer_series_from_inner_receipts(32)
        
        # Update telemetry
        elapsed = time.time() - start_time
        self.rods.temperature = min(1.0, elapsed / 0.25)  # Normalize to 0.25s baseline
        self.rods.pressure = min(1.0, len(meta_series) / 32.0)
        
        # Auto-adjust control rods
        self.rods.auto_adjust()
        
        # Moderate generation (for future use with LLM generator)
        k_eff = self.rods.moderate_generation(k_gen)
        
        # Outer MA'AT processes inner's receipts
        outer_res = self.outer.cycle(meta_series[-64:] if len(meta_series) >= 64 else meta_series,
                                     "internal:inner_receipts")
        
        # Compute criticality (ratio of outer to inner activity)
        inner_accepts = sum(1 for r in read_jsonl(self.inner.hemi_R.decisions_path)[-3:]
                           if r.get("decision") == "accept")
        outer_accepts = sum(1 for r in read_jsonl(self.outer.hemi_R.decisions_path)[-3:]
                           if r.get("decision") == "accept")
        self.rods.criticality = (outer_accepts + 1) / (inner_accepts + 1)
        
        # Compute reality correlation
        mu_ext = sum(ext) / len(ext) if ext else 0.0
        mu_meta = sum(meta_series) / len(meta_series) if meta_series else 0.0
        reality_corr = 1.0 - min(1.0, abs(mu_ext - mu_meta))
        
        # Check SCRAM conditions
        state = {
            "criticality": self.rods.criticality,
            "temperature": self.rods.temperature,
            "pressure": self.rods.pressure,
            "reality_corr": reality_corr
        }
        
        if self.scram.should_scram(state):
            # Emergency shutdown: insert all rods
            self.rods.recursion_damper.depth = 1.0
            self.rods.resource_governor.depth = 1.0
            self.rods.semantic_filter.depth = 1.0
            
            return {
                "status": "SCRAM",
                "cycle": self.cycle_count,
                "state": state,
                "rods": self.rods.get_state(),
                "outer": outer_res,
                "inner": inner_res
            }
        
        return {
            "status": "OK",
            "cycle": self.cycle_count,
            "state": state,
            "rods": self.rods.get_state(),
            "outer": outer_res,
            "inner": inner_res
        }
    
    def run(self, cycles: int) -> List[Dict[str, Any]]:
        """
        Run multiple reactor cycles.
        
        Args:
            cycles: Number of cycles to run
            
        Returns:
            List of cycle results
        """
        results = []
        for i in range(cycles):
            res = self.cycle()
            results.append(res)
            
            if res["status"] == "SCRAM":
                print(f"SCRAM triggered at cycle {i+1}")
                break
        
        return results

