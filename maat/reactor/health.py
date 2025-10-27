# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""
System health metrics:
- Diversity: vocabulary & claim-shape variety
- Degradation: trend detectors for collapse/fixation
- Genuine learning rate: compression-based signal on receipts (zlib proxy)
Deterministic baselines.
"""
from __future__ import annotations
from typing import Dict, List
import re, zlib
from collections import Counter, deque

TOKEN = re.compile(r"[A-Za-z_]{3,}")

class SystemHealthMonitor:
    def compute_diversity_metrics(self, receipts: List[Dict]) -> Dict:
        claims = []
        for r in receipts:
            # try to fetch hyp claim if present
            try:
                claims.append(str(r.get("note") or r.get("hyp") or ""))
            except Exception:
                pass
        tokens = [t.lower() for c in claims for t in TOKEN.findall(c)]
        V = len(set(tokens))
        N = len(tokens) or 1
        freq = Counter(tokens)
        simpson = 1.0 - sum((n/N)**2 for n in freq.values())
        return {"vocab_size": V, "token_count": N, "simpson_diversity": round(simpson,4)}

    def detect_degradation_patterns(self, history: List[Dict]) -> List[str]:
        notes = [str(h.get("note","")) for h in history[-200:]]
        toks = [t.lower() for n in notes for t in TOKEN.findall(n)]
        alerts = []
        if len(set(toks)) <= max(20, len(toks)//20):
            alerts.append("Semantic collapse (low vocabulary)")
        # repetition
        pairs = Counter(tuple(toks[i:i+3]) for i in range(max(0,len(toks)-2)))
        if any(c > 10 for c in pairs.values()):
            alerts.append("Hypothesis fixation (repetitive patterns)")
        return alerts

    def compute_genuine_learning_rate(self, receipts: List[Dict]) -> float:
        # Compare compressed size trend over last windows (smaller → better structure)
        blobs = [str(r).encode("utf-8") for r in receipts[-500:]]
        if len(blobs) < 20:
            return 0.0
        sizes = []
        buf = deque([], maxlen=25)
        for b in blobs:
            buf.append(b)
            packed = zlib.compress(b"".join(buf), level=9)
            sizes.append(len(packed))
        if len(sizes) < 10:
            return 0.0
        # linear slope (last minus first) normalized
        slope = (sizes[-1]-sizes[0]) / max(1, len(sizes))
        rate = -slope / max(10.0, sum(sizes)/len(sizes))  # negative slope → positive learning
        return round(rate, 4)
