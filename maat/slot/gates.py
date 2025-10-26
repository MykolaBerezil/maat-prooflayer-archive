"""
Slot decision logic with triple-gate testing and attention allocation.
Implements Bayesian, coherence, and MDL gates for hypothesis evaluation.
"""
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from ..core.canonical import add_ukh, append_jsonl
from ..core.records import AGL_Test, AGL_Evidence, AGL_SlotDecision, AGL_Receipt
from ..mathx.coherence import fft_peak_mean
from ..mathx.mdl import mdl_delta_bits


@dataclass
class GateThresholds:
    """Gate threshold values for hypothesis testing."""
    bayes: float  # Minimum posterior mean
    coh: float    # Minimum coherence peak-to-mean
    mdl: float    # Maximum MDL delta bits (negative = better compression)


@dataclass
class AttentionMetrics:
    """Attention allocation metrics."""
    nov: float     # Novelty (0-1)
    coh: float     # Coherence (0-1)
    risk: float    # Risk (0-1)
    chaos: float   # Chaos/entropy (0-1)
    att: float     # Overall attention (0-1)


def compute_bayesian_update(series: List[float], prior_a: float = 1.0, prior_b: float = 1.0) -> Tuple[int, int, float]:
    """
    Compute Bayesian update using Beta-Bernoulli conjugate prior.
    
    Args:
        series: Time series data
        prior_a: Prior alpha (successes + 1)
        prior_b: Prior beta (failures + 1)
        
    Returns:
        Tuple of (successes, failures, posterior_mean)
    """
    if not series:
        return 0, 0, prior_a / (prior_a + prior_b)
    
    mu = sum(series) / len(series)
    successes = sum(1 for x in series if x > mu)
    failures = len(series) - successes
    
    # Beta posterior: Beta(a + s, b + f)
    post_a = prior_a + successes
    post_b = prior_b + failures
    post_mean = post_a / (post_a + post_b)
    
    return successes, failures, post_mean


def compute_attention_metrics(series: List[float], coh: float, mdl_bits: float) -> AttentionMetrics:
    """
    Compute attention allocation metrics.
    
    Args:
        series: Time series data
        coh: Coherence score
        mdl_bits: MDL delta bits
        
    Returns:
        AttentionMetrics object
    """
    if not series:
        return AttentionMetrics(0.0, 0.0, 0.0, 0.0, 0.0)
    
    mu = sum(series) / len(series)
    
    # Novelty: distance from baseline (normalized)
    nov = min(1.0, abs(mu) / (1 + abs(mu)))
    
    # Coherence: normalized to [0, 1]
    coh_n = min(1.0, coh / 12.0)
    
    # Risk: potential for false positive (from MDL)
    risk = max(0.0, -min(0.0, mdl_bits))
    risk_n = min(1.0, risk / 16.0)
    
    # Chaos: entropy/unpredictability
    chaos = min(1.0, sum(abs(x - mu) for x in series) / (len(series) * (1 + abs(mu))))
    
    # Overall attention (sigmoid of weighted combination)
    att_logit = 0.4 * nov + 0.3 * coh_n - 0.2 * risk_n - 0.1 * chaos
    att = 1.0 / (1.0 + math.exp(-att_logit))
    
    return AttentionMetrics(nov, coh_n, risk_n, chaos, att)


def evaluate_gates(post_mean: float, coh: float, mdl_bits: float, 
                   thresholds: GateThresholds) -> Tuple[str, List[str]]:
    """
    Evaluate hypothesis against triple gates.
    
    Args:
        post_mean: Bayesian posterior mean
        coh: Coherence score
        mdl_bits: MDL delta bits
        thresholds: Gate threshold values
        
    Returns:
        Tuple of (decision, reasons)
        decision: "accept", "reject", or "defer"
        reasons: List of human-readable explanations
    """
    ok_bayes = post_mean >= thresholds.bayes
    ok_coh = coh >= thresholds.coh
    ok_mdl = mdl_bits <= thresholds.mdl
    
    reasons = []
    reasons.append(f"posterior_mean={post_mean:.3f} {'>=' if ok_bayes else '<'} {thresholds.bayes:.2f}")
    reasons.append(f"coherence={coh:.2f} {'>=' if ok_coh else '<'} {thresholds.coh:.2f}")
    reasons.append(f"mdl_bits={mdl_bits:.2f} {'<=' if ok_mdl else '>'} {thresholds.mdl:.2f}")
    
    # Decision logic
    if ok_bayes and ok_coh and ok_mdl:
        decision = "accept"
    elif ok_bayes or ok_coh:
        decision = "defer"
    else:
        decision = "reject"
    
    return decision, reasons


class Slot:
    """
    A processing slot with specific gate thresholds.
    Evaluates hypotheses and writes receipts to ledgers.
    """
    
    def __init__(self, name: str, hemi: str, thresholds: GateThresholds,
                 receipts_path: Path, evidence_path: Path, decisions_path: Path):
        """
        Initialize a slot.
        
        Args:
            name: Slot name
            hemi: Hemisphere ("R" or "L")
            thresholds: Gate threshold values
            receipts_path: Path to receipts ledger
            evidence_path: Path to evidence ledger
            decisions_path: Path to decisions ledger
        """
        self.name = name
        self.hemi = hemi
        self.thresholds = thresholds
        self.receipts_path = receipts_path
        self.evidence_path = evidence_path
        self.decisions_path = decisions_path
    
    def decide(self, hyp: Dict[str, Any], series: List[float]) -> Tuple[Dict, Dict, Dict]:
        """
        Evaluate a hypothesis against the time series data.
        
        Args:
            hyp: Hypothesis record
            series: Time series data
            
        Returns:
            Tuple of (test_obj, evidence_obj, decision_obj)
        """
        # Compute metrics
        successes, failures, post_mean = compute_bayesian_update(series)
        coh = fft_peak_mean(series)
        mdl_bits = mdl_delta_bits(series, model="linear", params=2)
        
        # Create test record
        tst_obj = add_ukh(AGL_Test(hyp["id"]))
        
        # Create evidence record
        evid_obj = add_ukh(AGL_Evidence(
            tst_obj["id"], hyp["id"],
            post_mean, coh, mdl_bits,
            successes, failures
        ))
        
        # Compute attention metrics
        att_metrics = compute_attention_metrics(series, coh, mdl_bits)
        
        # Evaluate gates
        decision, reasons = evaluate_gates(post_mean, coh, mdl_bits, self.thresholds)
        
        # Create decision record
        dec_obj = add_ukh(AGL_SlotDecision(
            hyp["id"], tst_obj["id"], decision,
            {
                "bayes": self.thresholds.bayes,
                "coh": self.thresholds.coh,
                "mdl": self.thresholds.mdl
            },
            {
                "nov": att_metrics.nov,
                "coh": att_metrics.coh,
                "risk": att_metrics.risk,
                "chaos": att_metrics.chaos,
                "att": att_metrics.att
            },
            reasons
        ))
        
        # Create receipt
        rec_obj = add_ukh(AGL_Receipt(
            f"slot_{self.hemi}",
            decision + "ed",  # "accept" -> "accepted"
            hyp["id"],
            evid_obj["ukh"],
            dec_obj["ukh"],
            note=f"hemi={self.hemi}"
        ))
        
        # Append to ledgers
        append_jsonl(self.evidence_path, evid_obj)
        append_jsonl(self.decisions_path, dec_obj)
        append_jsonl(self.receipts_path, rec_obj)
        
        return tst_obj, evid_obj, dec_obj

