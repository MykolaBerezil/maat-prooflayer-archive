# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""
Hyperbolic embeddings for hierarchical causal DAGs using the Poincaré ball model.
Deterministic baseline: simple radial mapping by depth + evenly spaced angles.
"""
from __future__ import annotations
import math
from typing import Dict, Tuple, List

Vec = Tuple[float, float]

class HyperbolicCausalDAG:
    def __init__(self, edges: Dict[str, List[str]]):
        self.edges = edges
        self.parents = {c:p for p,cs in edges.items() for c in cs}
        self.root = next((n for n in edges if n not in self.parents), next(iter(edges), None))
        self.coords: Dict[str, Vec] = {}
        if self.root is not None:
            self._embed()

    def _children(self, n: str) -> List[str]:
        return self.edges.get(n, [])

    def _depth(self, n: str) -> int:
        d = 0
        while n in self.parents:
            d += 1
            n = self.parents[n]
        return d

    def _embed(self):
        # BFS; place nodes by depth, distribute angles per parent index.
        from collections import deque
        q, seen = deque([self.root]), set([self.root])
        idx: Dict[str,int] = {}
        while q:
            node = q.popleft()
            depth = self._depth(node)
            # radius in (0,1): deeper -> closer to unit boundary (tanh mapping)
            r = math.tanh((depth+1)/(depth+2))
            # position angle from sibling index
            parent = self.parents.get(node)
            if parent is None:
                angle = 0.0
            else:
                # assign stable index among siblings
                sibs = self._children(parent)
                if node not in idx:
                    idx[node] = sibs.index(node)
                k = max(1, len(sibs))
                angle = 2*math.pi*idx[node]/k
            self.coords[node] = (r*math.cos(angle), r*math.sin(angle))
            for c in self._children(node):
                if c not in seen:
                    seen.add(c); q.append(c)

    @staticmethod
    def _norm(u: Vec) -> float:
        return math.hypot(u[0], u[1])

    @staticmethod
    def poincare_distance(u: Vec, v: Vec) -> float:
        """d(u,v) = arcosh(1 + 2||u-v||^2 / ((1-||u||^2)(1-||v||^2)))"""
        ux, uy = u; vx, vy = v
        duv2 = (ux-vx)**2 + (uy-vy)**2
        nu = 1 - (ux*ux + uy*uy); nv = 1 - (vx*vx + vy*vy)
        nu = max(nu, 1e-12); nv = max(nv, 1e-12)
        arg = 1 + 2*duv2/(nu*nv)
        return math.acosh(max(arg, 1.0))

    def embed_in_poincare(self, node: str) -> Vec:
        return self.coords[node]

    def hyperbolic_distance(self, node1: str, node2: str) -> float:
        return self.poincare_distance(self.coords[node1], self.coords[node2])
