# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""
Cross-domain translator (deterministic baseline).
Implements simple, information-preserving mappings between domains with a fidelity score.
"""
from __future__ import annotations
from typing import Dict

class DomainTranslator:
    DOMAINS = ['numeric','boolean','linguistic','temporal','causal','spatial','probabilistic','logical']

    def translate(self, hypothesis: Dict, source_domain: str, target_domain: str) -> Dict:
        h = dict(hypothesis)  # shallow copy
        claim = str(h.get("claim",""))
        meta = h.setdefault("meta", {})
        meta["translation"] = {"from": source_domain, "to": target_domain}

        if source_domain == target_domain:
            meta["translation"]["fidelity"] = 1.0
            return h

        # numeric -> boolean: threshold at median-like heuristic (length-based if no numbers)
        if source_domain == "numeric" and target_domain == "boolean":
            meta["translation"]["rule"] = "threshold>0"
            h["claim"] = f"(numeric-claim > 0) implies ({claim})"
            meta["translation"]["fidelity"] = 0.8

        # boolean -> probabilistic: map True/False hint to Beta prior mean
        elif source_domain == "boolean" and target_domain == "probabilistic":
            h["claim"] = f"Pr({claim}) >= 0.5"
            meta["translation"]["rule"] = "boolean→beta-mean"
            meta["translation"]["fidelity"] = 0.7

        # linguistic -> logical: wrap in predicate form
        elif source_domain == "linguistic" and target_domain == "logical":
            h["claim"] = f"ASSERT({claim})"
            meta["translation"]["rule"] = "predicate-wrap"
            meta["translation"]["fidelity"] = 0.75

        # numeric -> probabilistic: normalize to [0,1] with safe clamp
        elif source_domain == "numeric" and target_domain == "probabilistic":
            h["claim"] = f"Pr({claim}) in [0,1]"
            meta["translation"]["rule"] = "normalize"
            meta["translation"]["fidelity"] = 0.65

        else:
            meta["translation"]["rule"] = "identity-fallback"
            meta["translation"]["fidelity"] = 0.6

        return h

    def verify_translation_fidelity(self, original: Dict, translated: Dict) -> float:
        mt = translated.get("meta",{}).get("translation",{})
        return float(mt.get("fidelity", 0.5))
