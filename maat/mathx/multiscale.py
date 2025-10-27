# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""
Multi-scale analyzer using a pure-Python Haar DWT baseline.
Provides:
- wavelet_coherence(): scale energy map
- detect_scale_invariant_patterns(): find persistent features across scales
Deterministic; no external deps.
"""
from __future__ import annotations
from typing import List, Dict
import math

def _haar_dwt(x: List[float]) -> List[List[float]]:
    levels = []
    s = x[:]
    while len(s) >= 2:
        a, d = [], []
        for i in range(0, len(s)-1, 2):
            a.append((s[i]+s[i+1])/math.sqrt(2))
            d.append((s[i]-s[i+1])/math.sqrt(2))
        levels.append(d)
        s = a
        if len(s) == 1:  # final approx
            levels.append(s)
            break
    return levels  # [details L1, details L2, ..., approx]

class MultiScaleAnalyzer:
    def wavelet_coherence(self, series: List[float]) -> Dict:
        levels = _haar_dwt(series)
        energies = [sum(v*v for v in lvl)/max(1,len(lvl)) for lvl in levels]
        total = sum(energies) or 1e-12
        coherence = [e/total for e in energies]
        return {"energies": energies, "coherence": coherence, "levels": len(levels)}

    def detect_scale_invariant_patterns(self, series: List[float]) -> List[Dict]:
        m = self.wavelet_coherence(series)
        coh = m["coherence"]
        avg = sum(coh)/len(coh)
        res = []
        for i, c in enumerate(coh):
            if abs(c - avg) < 0.05:  # near-uniform energy → scale invariance hint
                res.append({"level": i+1, "score": round(c,4), "kind": "scale-invariant"})
        return res
