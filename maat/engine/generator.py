"""
Hypothesis generators: Programmatic and LLM-based.
Provides pluggable generation strategies for MA'AT.
"""
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ..core.records import AGL_Hypothesis
from ..core.canonical import add_ukh
from ..mathx.mdl import _linear_fit_residuals
from ..mathx.coherence import fft_peak_mean


class ProgrammaticGenerator:
    """
    Deterministic programmatic hypothesis generator.
    Generates hypotheses based on statistical properties of the data.
    """
    
    def generate(self, obs_ids: List[str], series: List[float], hemi: str = "R") -> List[Dict[str, Any]]:
        """
        Generate hypotheses from time series data.
        
        Args:
            obs_ids: List of observation IDs
            series: Time series data
            hemi: Hemisphere ("R" or "L")
            
        Returns:
            List of hypothesis records
        """
        if not series:
            return []
        
        mu = sum(series) / len(series)
        
        # Compute slope from linear fit
        resid = _linear_fit_residuals(series)
        slope = (resid[-1] - resid[0]) / len(resid) if len(resid) > 1 else 0.0
        
        # Compute coherence
        coh = fft_peak_mean(series)
        
        # Generate three deterministic hypotheses
        claims = [
            f"mean>{mu:.3f} implies stability",
            f"slope>{slope:.3f} implies trend",
            f"coherence>{coh:.2f} implies periodic pattern"
        ]
        
        hyps = []
        for claim in claims:
            hyp = add_ukh(AGL_Hypothesis(claim, hemi, obs_ids))
            hyps.append(hyp)
        
        return hyps


class LLMAdapter:
    """
    Adapter for LLM-based hypothesis generation.
    Accepts a local callable LLM function (no network calls).
    """
    
    def __init__(self, llm_fn: Optional[Callable[[str], str]] = None,
                 hyp_file: Optional[Path] = None):
        """
        Initialize LLM adapter.
        
        Args:
            llm_fn: Optional LLM function (prompt -> response)
            hyp_file: Optional file path for offline hypothesis emulation
        """
        self.llm_fn = llm_fn
        self.hyp_file = hyp_file
        self.hyp_file_lines: List[str] = []
        self.hyp_file_index = 0
        
        if hyp_file and Path(hyp_file).exists():
            with open(hyp_file, 'r') as f:
                self.hyp_file_lines = [line.strip() for line in f if line.strip()]
    
    def _call_llm(self, prompt: str) -> str:
        """
        Call LLM function or read from file.
        
        Args:
            prompt: Prompt string
            
        Returns:
            LLM response string
        """
        # If hyp_file is provided, read from file instead of calling LLM
        if self.hyp_file_lines:
            if self.hyp_file_index >= len(self.hyp_file_lines):
                # Wrap around
                self.hyp_file_index = 0
            
            response = self.hyp_file_lines[self.hyp_file_index]
            self.hyp_file_index += 1
            return response
        
        # Otherwise, call LLM function if provided
        if self.llm_fn:
            return self.llm_fn(prompt)
        
        # Fallback: return empty
        return ""
    
    def parse_hypotheses(self, text: str, obs_ids: List[str], hemi: str = "R") -> List[Dict[str, Any]]:
        """
        Parse LLM output into hypothesis records.
        
        Expected format: one hypothesis per line, or comma-separated.
        
        Args:
            text: LLM output text
            obs_ids: List of observation IDs
            hemi: Hemisphere ("R" or "L")
            
        Returns:
            List of hypothesis records
        """
        # Split by newlines or commas
        claims = []
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Split by comma if multiple claims per line
            for claim in line.split(','):
                claim = claim.strip()
                if claim:
                    # Remove common prefixes
                    for prefix in ['- ', '* ', '• ', '1. ', '2. ', '3. ']:
                        if claim.startswith(prefix):
                            claim = claim[len(prefix):].strip()
                    
                    if claim:
                        claims.append(claim)
        
        # Create hypothesis records
        hyps = []
        for claim in claims:
            hyp = add_ukh(AGL_Hypothesis(claim, hemi, obs_ids))
            hyps.append(hyp)
        
        return hyps
    
    def generate(self, obs_ids: List[str], series: List[float], hemi: str = "R") -> List[Dict[str, Any]]:
        """
        Generate hypotheses using LLM.
        
        Args:
            obs_ids: List of observation IDs
            series: Time series data
            hemi: Hemisphere ("R" or "L")
            
        Returns:
            List of hypothesis records
        """
        if not series:
            return []
        
        # Compute basic statistics for prompt
        mu = sum(series) / len(series)
        min_val = min(series)
        max_val = max(series)
        n = len(series)
        
        # Create prompt
        prompt = f"""Given a time series with {n} samples:
- Mean: {mu:.3f}
- Min: {min_val:.3f}
- Max: {max_val:.3f}

Generate 3 testable hypotheses about this data.
Format: one hypothesis per line."""
        
        # Call LLM
        response = self._call_llm(prompt)
        
        # Parse response into hypotheses
        return self.parse_hypotheses(response, obs_ids, hemi)


class HybridGenerator:
    """
    Hybrid generator that combines programmatic and LLM-based generation.
    Falls back to programmatic if LLM is unavailable.
    """
    
    def __init__(self, llm_adapter: Optional[LLMAdapter] = None):
        """
        Initialize hybrid generator.
        
        Args:
            llm_adapter: Optional LLM adapter
        """
        self.llm_adapter = llm_adapter
        self.programmatic = ProgrammaticGenerator()
    
    def generate(self, obs_ids: List[str], series: List[float], hemi: str = "R",
                 use_llm: bool = True) -> List[Dict[str, Any]]:
        """
        Generate hypotheses using LLM if available, otherwise programmatic.
        
        Args:
            obs_ids: List of observation IDs
            series: Time series data
            hemi: Hemisphere ("R" or "L")
            use_llm: Whether to use LLM (if available)
            
        Returns:
            List of hypothesis records
        """
        if use_llm and self.llm_adapter:
            hyps = self.llm_adapter.generate(obs_ids, series, hemi)
            if hyps:
                return hyps
        
        # Fallback to programmatic
        return self.programmatic.generate(obs_ids, series, hemi)

