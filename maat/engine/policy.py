# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""
Learned gating policy for adaptive threshold tuning.
Adjusts gate thresholds online to hit target acceptance band and minimize regret.
"""
import json
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class PolicyMetrics:
    """Metrics for policy evaluation."""
    acceptance_rate: float = 0.0
    regret_false_accept: float = 0.0  # Accepted but later MDL worsened
    regret_false_reject: float = 0.0  # Rejected but later coherence strong
    total_decisions: int = 0


@dataclass
class GateThresholds:
    """Gate threshold values."""
    bayes: float = 0.80
    coh: float = 7.5
    mdl: float = -8.0


class LearnedGatesPolicy:
    """
    Online policy for learning gate thresholds.
    Targets an acceptance band and minimizes regret.
    """
    
    def __init__(self, target_accept_min: float = 0.20, target_accept_max: float = 0.35,
                 learning_rate: float = 0.05, cooldown: int = 10):
        """
        Initialize learned gating policy.
        
        Args:
            target_accept_min: Minimum target acceptance rate
            target_accept_max: Maximum target acceptance rate
            learning_rate: Learning rate for threshold updates
            cooldown: Minimum cycles between threshold updates
        """
        self.target_accept_min = target_accept_min
        self.target_accept_max = target_accept_max
        self.learning_rate = learning_rate
        self.cooldown = cooldown
        
        # Current thresholds (R hemisphere defaults)
        self.thresholds = GateThresholds(bayes=0.80, coh=7.5, mdl=-8.0)
        
        # History tracking
        self.history: deque = deque(maxlen=100)  # Rolling window of recent metrics
        self.update_count = 0
        self.cycles_since_update = 0
        
        # Regret tracking
        self.accepted_hyps: deque = deque(maxlen=50)  # Recently accepted hypotheses
        self.rejected_hyps: deque = deque(maxlen=50)  # Recently rejected hypotheses
    
    def step(self, metrics: Dict[str, Any]) -> GateThresholds:
        """
        Update thresholds based on recent metrics.
        
        Args:
            metrics: Dictionary with keys:
                - 'acceptance_rate': Current acceptance rate
                - 'recent_decisions': List of recent decision records
                - 'recent_evidence': List of recent evidence records
                
        Returns:
            Updated gate thresholds
        """
        self.cycles_since_update += 1
        
        # Extract metrics
        accept_rate = metrics.get('acceptance_rate', 0.0)
        recent_decisions = metrics.get('recent_decisions', [])
        recent_evidence = metrics.get('recent_evidence', [])
        
        # Track accepted/rejected hypotheses
        for dec in recent_decisions:
            if dec.get('decision') == 'accept':
                self.accepted_hyps.append(dec.get('hyp'))
            elif dec.get('decision') == 'reject':
                self.rejected_hyps.append(dec.get('hyp'))
        
        # Compute regret
        regret_false_accept = self._compute_false_accept_regret(recent_evidence)
        regret_false_reject = self._compute_false_reject_regret(recent_evidence)
        
        # Record history
        self.history.append({
            'acceptance_rate': accept_rate,
            'regret_false_accept': regret_false_accept,
            'regret_false_reject': regret_false_reject,
            'thresholds': {
                'bayes': self.thresholds.bayes,
                'coh': self.thresholds.coh,
                'mdl': self.thresholds.mdl
            }
        })
        
        # Only update if cooldown has passed
        if self.cycles_since_update < self.cooldown:
            return self.thresholds
        
        # Determine if we need to adjust thresholds
        if accept_rate < self.target_accept_min:
            # Acceptance rate too low: loosen thresholds
            self._loosen_thresholds()
            self.update_count += 1
            self.cycles_since_update = 0
        
        elif accept_rate > self.target_accept_max:
            # Acceptance rate too high: tighten thresholds
            self._tighten_thresholds()
            self.update_count += 1
            self.cycles_since_update = 0
        
        # Adjust based on regret
        if regret_false_accept > 0.3:
            # Too many false accepts: tighten
            self._tighten_thresholds(factor=0.5)
            self.update_count += 1
            self.cycles_since_update = 0
        
        if regret_false_reject > 0.3:
            # Too many false rejects: loosen
            self._loosen_thresholds(factor=0.5)
            self.update_count += 1
            self.cycles_since_update = 0
        
        return self.thresholds
    
    def _loosen_thresholds(self, factor: float = 1.0):
        """Loosen thresholds to increase acceptance rate."""
        delta = self.learning_rate * factor
        
        # Decrease Bayesian threshold
        self.thresholds.bayes = max(0.5, self.thresholds.bayes - delta)
        
        # Decrease coherence threshold
        self.thresholds.coh = max(3.0, self.thresholds.coh - delta * 5.0)
        
        # Increase MDL threshold (less negative = looser)
        self.thresholds.mdl = min(-2.0, self.thresholds.mdl + delta * 10.0)
    
    def _tighten_thresholds(self, factor: float = 1.0):
        """Tighten thresholds to decrease acceptance rate."""
        delta = self.learning_rate * factor
        
        # Increase Bayesian threshold
        self.thresholds.bayes = min(0.98, self.thresholds.bayes + delta)
        
        # Increase coherence threshold
        self.thresholds.coh = min(15.0, self.thresholds.coh + delta * 5.0)
        
        # Decrease MDL threshold (more negative = tighter)
        self.thresholds.mdl = max(-20.0, self.thresholds.mdl - delta * 10.0)
    
    def _compute_false_accept_regret(self, recent_evidence: List[Dict]) -> float:
        """
        Compute regret from false accepts (accepted but later MDL worsened).
        
        Args:
            recent_evidence: List of recent evidence records
            
        Returns:
            Regret score [0, 1]
        """
        if not self.accepted_hyps or not recent_evidence:
            return 0.0
        
        # Check if accepted hypotheses later showed poor MDL
        poor_mdl_count = 0
        for evid in recent_evidence:
            hyp_id = evid.get('hyp')
            if hyp_id in self.accepted_hyps:
                mdl_bits = float(evid.get('mdl', {}).get('bits_delta', 0))
                if mdl_bits > 0:  # Positive MDL = poor compression
                    poor_mdl_count += 1
        
        return poor_mdl_count / len(self.accepted_hyps) if self.accepted_hyps else 0.0
    
    def _compute_false_reject_regret(self, recent_evidence: List[Dict]) -> float:
        """
        Compute regret from false rejects (rejected but later coherence strong).
        
        Args:
            recent_evidence: List of recent evidence records
            
        Returns:
            Regret score [0, 1]
        """
        if not self.rejected_hyps or not recent_evidence:
            return 0.0
        
        # Check if rejected hypotheses later showed strong coherence
        strong_coh_count = 0
        for evid in recent_evidence:
            hyp_id = evid.get('hyp')
            if hyp_id in self.rejected_hyps:
                coh = float(evid.get('coherence', {}).get('peak_mean', 0))
                if coh > 10.0:  # Strong coherence
                    strong_coh_count += 1
        
        return strong_coh_count / len(self.rejected_hyps) if self.rejected_hyps else 0.0
    
    def get_thresholds_dict(self) -> Dict[str, float]:
        """Get current thresholds as dictionary."""
        return {
            'bayes': self.thresholds.bayes,
            'coh': self.thresholds.coh,
            'mdl': self.thresholds.mdl
        }
    
    def get_report(self) -> Dict[str, Any]:
        """Generate policy report."""
        recent_history = list(self.history)[-20:]  # Last 20 entries
        
        return {
            'current_thresholds': self.get_thresholds_dict(),
            'update_count': self.update_count,
            'cycles_since_update': self.cycles_since_update,
            'target_band': [self.target_accept_min, self.target_accept_max],
            'recent_history': recent_history,
            'stats': {
                'avg_acceptance_rate': sum(h['acceptance_rate'] for h in recent_history) / len(recent_history) if recent_history else 0.0,
                'avg_regret_false_accept': sum(h['regret_false_accept'] for h in recent_history) / len(recent_history) if recent_history else 0.0,
                'avg_regret_false_reject': sum(h['regret_false_reject'] for h in recent_history) / len(recent_history) if recent_history else 0.0
            }
        }
    
    def save(self, path: Path):
        """Save policy state to JSON."""
        data = {
            'thresholds': self.get_thresholds_dict(),
            'update_count': self.update_count,
            'cycles_since_update': self.cycles_since_update,
            'target_band': [self.target_accept_min, self.target_accept_max],
            'learning_rate': self.learning_rate,
            'cooldown': self.cooldown
        }
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load(self, path: Path):
        """Load policy state from JSON."""
        if not path.exists():
            return
        
        with open(path, 'r') as f:
            data = json.load(f)
        
        self.thresholds.bayes = data['thresholds']['bayes']
        self.thresholds.coh = data['thresholds']['coh']
        self.thresholds.mdl = data['thresholds']['mdl']
        self.update_count = data.get('update_count', 0)
        self.cycles_since_update = data.get('cycles_since_update', 0)
        self.target_accept_min = data['target_band'][0]
        self.target_accept_max = data['target_band'][1]
        self.learning_rate = data.get('learning_rate', 0.05)
        self.cooldown = data.get('cooldown', 10)

