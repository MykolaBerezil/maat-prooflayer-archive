"""
AGL (Atman Governance Language) v1.0 record factories.
Defines all canonical record types for the MA'AT system.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .canonical import _decimal_string


def now_iso() -> str:
    """Generate ISO8601 timestamp with Z suffix."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def gen_id(prefix: str) -> str:
    """Generate unique ID with prefix."""
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def AGL_Observation(src: str, fields: Dict[str, Any], meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Create an AGL/Observation record.
    
    Args:
        src: Source identifier (e.g., "sensor:temp", "user:input")
        fields: Arbitrary observation data
        meta: Optional metadata
        
    Returns:
        Observation record dictionary
    """
    return {
        "spec": "AGL/1.0",
        "schema": "AGL/Observation",
        "ts": now_iso(),
        "id": gen_id("obs"),
        "src": src,
        "fields": fields,
        "meta": meta or {}
    }


def AGL_Hypothesis(claim: str, hemi: str, from_ids: List[str], 
                   prior: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Create an AGL/Hypothesis record.
    
    Args:
        claim: Natural language hypothesis statement
        hemi: Hemisphere ("R" for right/exploratory, "L" for left/conservative)
        from_ids: List of observation IDs that generated this hypothesis
        prior: Optional Bayesian prior (defaults to Beta(1,1))
        
    Returns:
        Hypothesis record dictionary
    """
    return {
        "spec": "AGL/1.0",
        "schema": "AGL/Hypothesis",
        "ts": now_iso(),
        "id": gen_id("hyp"),
        "hemi": hemi,
        "claim": claim,
        "from": from_ids,
        "prior": prior or {"dist": "Beta", "a": "1", "b": "1"},
        "rules": [],
        "windows": []
    }


def AGL_Test(hyp_id: str, design: Optional[Dict[str, Any]] = None,
             metrics: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
    """
    Create an AGL/Test record.
    
    Args:
        hyp_id: Hypothesis ID being tested
        design: Test methodology specification
        metrics: List of metrics to compute
        
    Returns:
        Test record dictionary
    """
    return {
        "spec": "AGL/1.0",
        "schema": "AGL/Test",
        "ts": now_iso(),
        "id": gen_id("tst"),
        "hyp": hyp_id,
        "design": design or {"type": "rolling", "holdout": "0.2"},
        "metrics": metrics or [
            {"name": "posterior_mean"},
            {"name": "coh_peak_mean"},
            {"name": "mdl_delta_bits"}
        ],
        "power": {"alpha": "0.05", "beta": "0.2"}
    }


def AGL_Evidence(tst_id: str, hyp_id: str, 
                 post_mean: float, coh: float, mdl_bits: float,
                 successes: int, failures: int) -> Dict[str, Any]:
    """
    Create an AGL/Evidence record.
    
    Args:
        tst_id: Test ID
        hyp_id: Hypothesis ID
        post_mean: Bayesian posterior mean
        coh: Coherence peak-to-mean ratio
        mdl_bits: MDL delta bits
        successes: Count of successes for Bayesian update
        failures: Count of failures for Bayesian update
        
    Returns:
        Evidence record dictionary
    """
    return {
        "spec": "AGL/1.0",
        "schema": "AGL/Evidence",
        "ts": now_iso(),
        "tst": tst_id,
        "hyp": hyp_id,
        "bayes": {
            "posterior": {
                "dist": "Beta",
                "a": _decimal_string(1 + successes),
                "b": _decimal_string(1 + failures),
                "mean": _decimal_string(post_mean)
            }
        },
        "coherence": {
            "peak_mean": _decimal_string(coh),
            "multi_scale": {"T": _decimal_string(coh)}
        },
        "mdl": {
            "bits_delta": _decimal_string(mdl_bits)
        },
        "residuals": {
            "norm": _decimal_string(0.0),
            "outlier_rate": _decimal_string(0.0)
        }
    }


def AGL_SlotDecision(hyp_id: str, tst_id: str, decision_str: str,
                     gates: Dict[str, float], attention: Dict[str, float],
                     reason: List[str]) -> Dict[str, Any]:
    """
    Create an AGL/SlotDecision record.
    
    Args:
        hyp_id: Hypothesis ID
        tst_id: Test ID
        decision_str: Decision ("accept", "reject", or "defer")
        gates: Gate threshold values
        attention: Attention allocation metrics
        reason: Human-readable explanation of decision
        
    Returns:
        SlotDecision record dictionary
    """
    return {
        "spec": "AGL/1.0",
        "schema": "AGL/SlotDecision",
        "ts": now_iso(),
        "hyp": hyp_id,
        "tst": tst_id,
        "gate": {
            "bayes_threshold": _decimal_string(gates["bayes"]),
            "coherence_threshold": _decimal_string(gates["coh"]),
            "mdl_threshold": _decimal_string(gates["mdl"])
        },
        "decision": decision_str,
        "attention": {k: _decimal_string(v) for k, v in attention.items()},
        "reason": reason
    }


def AGL_Receipt(slot_id: str, status: str, hyp_id: str,
                evid_ukh: str, decision_ukh: str, note: str = "") -> Dict[str, Any]:
    """
    Create an AGL/Receipt record.
    
    Args:
        slot_id: Slot identifier (e.g., "slot_R", "slot_L")
        status: Final status ("accepted", "rejected", "deferred")
        hyp_id: Hypothesis ID
        evid_ukh: UKH of the evidence object
        decision_ukh: UKH of the decision object
        note: Optional notes
        
    Returns:
        Receipt record dictionary
    """
    return {
        "spec": "AGL/1.0",
        "schema": "AGL/Receipt",
        "ts": now_iso(),
        "slot_id": slot_id,
        "status": status,
        "hyp": hyp_id,
        "evid": evid_ukh,
        "decision_ukh": decision_ukh,
        "note": note
    }

