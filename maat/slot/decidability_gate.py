# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""
Heuristic decidability gate:
- Detects self-reference loops, unbounded recursion patterns, paradox phrasing.
- Classifies rough complexity class hints (P/NP/EXPTIME/UNDECIDABLE) by patterns.
Deterministic, conservative: only flags when evidence is strong.
"""
from __future__ import annotations
import re
from typing import Dict, List

SELFREF_PAT = re.compile(r"\b(this\s+hypothesis|itself|self-referential|not\s+provable)\b", re.I)
LOOP_PAT = re.compile(r"\b(while\s+true|for\s*\(;;\)|infinite\s+loop)\b", re.I)
PARADOX_PAT = re.compile(r"\b(contradiction|paradox|liar\s+sentence)\b", re.I)
HALT_PAT = re.compile(r"\b(halts\?|halt\s+problem|turing\s+complete)\b", re.I)

def _confidence(flags: List[bool]) -> float:
    w = [0.4, 0.3, 0.2, 0.1]
    return min(1.0, sum(w[i] for i,f in enumerate(flags) if f))

class DecidabilityGate:
    def test(self, hypothesis: Dict, evidence: List[Dict]) -> Dict:
        claim = (hypothesis.get("claim") or "").strip()
        text = claim + " " + " ".join(str(e) for e in evidence)
        f_self = bool(SELFREF_PAT.search(text))
        f_loop = bool(LOOP_PAT.search(text))
        f_paradox = bool(PARADOX_PAT.search(text))
        f_halt = bool(HALT_PAT.search(text))
        conf = _confidence([f_self, f_loop, f_paradox, f_halt])

        if f_paradox or (f_self and f_halt):
            clazz = "UNDECIDABLE"
            decidable = False
            reason = "Self-reference/paradox indicative of undecidability"
        elif f_loop or f_halt:
            clazz = "EXPTIME"
            decidable = True
            reason = "Potentially intractable; treat as high complexity"
        elif len(claim) > 0 and len(claim) < 140 and not any([f_self,f_loop,f_paradox,f_halt]):
            clazz = "P"
            decidable = True
            reason = "Simple bounded claim; likely decidable"
        else:
            clazz = "NP"
            decidable = True
            reason = "Complex but no paradox detected"

        return {
            "decidable": decidable,
            "complexity_class": clazz,
            "confidence": round(conf, 3),
            "reason": reason
        }
