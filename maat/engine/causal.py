"""
Causal DAG scaffolding for hypothesis constraint and edge weight learning.
Maintains a directed acyclic graph over signals/features.
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


class CausalGraph:
    """
    Directed Acyclic Graph (DAG) for causal relationships between signals.
    Hypotheses are constrained by the current causal structure.
    """
    
    def __init__(self):
        """Initialize empty causal graph."""
        self.nodes: Set[str] = set()
        self.edges: Dict[Tuple[str, str], float] = {}  # (source, target) -> weight [0, 1]
        self.blocked_edges: Set[Tuple[str, str]] = set()  # Edges that would create cycles
    
    def add_node(self, name: str):
        """Add a node to the graph."""
        self.nodes.add(name)
    
    def add_edge(self, source: str, target: str, weight: float = 0.5):
        """
        Add or update an edge in the graph.
        
        Args:
            source: Source node name
            target: Target node name
            weight: Edge weight [0, 1]
        """
        # Ensure nodes exist
        self.add_node(source)
        self.add_node(target)
        
        # Check for cycles
        if self._would_create_cycle(source, target):
            self.blocked_edges.add((source, target))
            return False
        
        # Clamp weight to [0, 1]
        weight = max(0.0, min(1.0, weight))
        self.edges[(source, target)] = weight
        return True
    
    def _would_create_cycle(self, source: str, target: str) -> bool:
        """
        Check if adding edge (source -> target) would create a cycle.
        
        Args:
            source: Source node
            target: Target node
            
        Returns:
            True if edge would create cycle
        """
        # DFS from target to see if we can reach source
        visited = set()
        stack = [target]
        
        while stack:
            node = stack.pop()
            if node == source:
                return True
            
            if node in visited:
                continue
            visited.add(node)
            
            # Add all children of this node
            for (src, tgt), _ in self.edges.items():
                if src == node and tgt not in visited:
                    stack.append(tgt)
        
        return False
    
    def allow(self, inputs: List[str], target: str) -> bool:
        """
        Check if a hypothesis with given inputs->target is allowed by the DAG.
        
        Args:
            inputs: List of input signal names
            target: Target signal name
            
        Returns:
            True if hypothesis is allowed
        """
        # If nodes don't exist yet, allow (will be added)
        for inp in inputs:
            if inp not in self.nodes:
                return True
        if target not in self.nodes:
            return True
        
        # Check if all input->target edges are allowed
        for inp in inputs:
            if (inp, target) in self.blocked_edges:
                return False
            
            # Check if adding this edge would create a cycle
            if (inp, target) not in self.edges:
                if self._would_create_cycle(inp, target):
                    return False
        
        return True
    
    def update_from_receipt(self, receipt: Dict[str, Any], hyp: Dict[str, Any],
                           increase: float = 0.1, decrease: float = 0.05):
        """
        Update edge weights based on receipt outcome.
        
        Args:
            receipt: Receipt record
            hyp: Hypothesis record
            increase: Amount to increase weight for accepted hypotheses
            decrease: Amount to decrease weight for rejected hypotheses
        """
        # Extract inputs and target from hypothesis meta
        meta = hyp.get("meta", {})
        inputs = meta.get("inputs", [])
        target = meta.get("target", None)
        
        if not inputs or not target:
            # No causal structure specified, skip
            return
        
        status = receipt.get("status", "")
        
        # Update edge weights based on outcome
        for inp in inputs:
            edge = (inp, target)
            
            if status == "accepted":
                # Strengthen edge
                current = self.edges.get(edge, 0.5)
                new_weight = min(1.0, current + increase)
                self.add_edge(inp, target, new_weight)
            
            elif status == "rejected":
                # Weaken edge
                current = self.edges.get(edge, 0.5)
                new_weight = max(0.0, current - decrease)
                if new_weight > 0.0:
                    self.add_edge(inp, target, new_weight)
                else:
                    # Remove edge if weight reaches zero
                    if edge in self.edges:
                        del self.edges[edge]
    
    def prune(self, threshold: float = 0.1):
        """
        Remove edges with weight below threshold.
        
        Args:
            threshold: Minimum weight to keep edge
        """
        to_remove = []
        for edge, weight in self.edges.items():
            if weight < threshold:
                to_remove.append(edge)
        
        for edge in to_remove:
            del self.edges[edge]
    
    def top_k(self, k: int) -> List[Tuple[Tuple[str, str], float]]:
        """
        Get top k edges by weight.
        
        Args:
            k: Number of edges to return
            
        Returns:
            List of ((source, target), weight) tuples
        """
        sorted_edges = sorted(self.edges.items(), key=lambda x: x[1], reverse=True)
        return sorted_edges[:k]
    
    def to_dict(self) -> Dict[str, Any]:
        """Export graph to dictionary."""
        return {
            "nodes": list(self.nodes),
            "edges": [
                {"source": src, "target": tgt, "weight": weight}
                for (src, tgt), weight in self.edges.items()
            ],
            "blocked_edges": [
                {"source": src, "target": tgt}
                for (src, tgt) in self.blocked_edges
            ]
        }
    
    def from_dict(self, data: Dict[str, Any]):
        """Import graph from dictionary."""
        self.nodes = set(data.get("nodes", []))
        
        self.edges = {}
        for edge in data.get("edges", []):
            src = edge["source"]
            tgt = edge["target"]
            weight = edge["weight"]
            self.edges[(src, tgt)] = weight
        
        self.blocked_edges = set()
        for edge in data.get("blocked_edges", []):
            src = edge["source"]
            tgt = edge["target"]
            self.blocked_edges.add((src, tgt))
    
    def save(self, path: Path):
        """Save graph to JSON file."""
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    def load(self, path: Path):
        """Load graph from JSON file."""
        if path.exists():
            with open(path, 'r') as f:
                data = json.load(f)
                self.from_dict(data)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics."""
        return {
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "blocked_edge_count": len(self.blocked_edges),
            "avg_weight": sum(self.edges.values()) / len(self.edges) if self.edges else 0.0,
            "max_weight": max(self.edges.values()) if self.edges else 0.0,
            "min_weight": min(self.edges.values()) if self.edges else 0.0
        }

