# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
from maat.reactor.health import SystemHealthMonitor

def test_health_metrics_minimal():
    """Test health monitor computes diversity metrics."""
    mon = SystemHealthMonitor()
    receipts = [{"note": "Accepted: trend continuation"}, {"note": "Rejected: paradox"}]
    d = mon.compute_diversity_metrics(receipts)
    assert d["vocab_size"] >= 2
    assert d["token_count"] >= 2
    print(f"✓ Health monitor test passed: {d}")

if __name__ == "__main__":
    test_health_metrics_minimal()
