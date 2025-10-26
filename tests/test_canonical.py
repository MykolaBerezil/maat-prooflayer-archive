"""
Tests for canonical JSON serialization and UKH computation.
"""
import json
import tempfile
from pathlib import Path

from maat.core.canonical import (
    _decimal_string, canonical_json, compute_ukh, add_ukh, append_jsonl, read_jsonl
)
from maat.core.records import AGL_Observation


def test_decimal_string():
    """Test deterministic float formatting."""
    assert _decimal_string(1.0) == "1"
    assert _decimal_string(0.5) == "0.5"
    assert _decimal_string(0.123456789012345) == "0.123456789012345"
    assert _decimal_string(1.100000000000000) == "1.1"
    assert _decimal_string(0.0) == "0"


def test_canonical_json_deterministic():
    """Test that canonical JSON is deterministic."""
    obj1 = {"b": 2, "a": 1, "c": 3.14159}
    obj2 = {"c": 3.14159, "a": 1, "b": 2}
    
    json1 = canonical_json(obj1)
    json2 = canonical_json(obj2)
    
    assert json1 == json2
    assert "ukh" not in json1


def test_ukh_deterministic():
    """Test that UKH is deterministic for same content."""
    obj1 = {"spec": "AGL/1.0", "value": 1.5, "name": "test"}
    obj2 = {"name": "test", "spec": "AGL/1.0", "value": 1.5}
    
    ukh1 = compute_ukh(obj1)
    ukh2 = compute_ukh(obj2)
    
    assert ukh1 == ukh2
    assert len(ukh1) == 64  # blake2b-256 produces 64 hex chars


def test_ukh_different_for_different_content():
    """Test that UKH changes with content."""
    obj1 = {"value": 1.5}
    obj2 = {"value": 1.6}
    
    ukh1 = compute_ukh(obj1)
    ukh2 = compute_ukh(obj2)
    
    assert ukh1 != ukh2


def test_add_ukh():
    """Test adding UKH to object."""
    obj = {"spec": "AGL/1.0", "value": 42}
    result = add_ukh(obj)
    
    assert "ukh" in result
    assert result is obj  # Modified in place
    assert len(result["ukh"]) == 64


def test_ukh_excludes_itself():
    """Test that UKH computation excludes the ukh field."""
    obj = {"value": 1}
    ukh1 = compute_ukh(obj)
    
    obj["ukh"] = "fake_hash"
    ukh2 = compute_ukh(obj)
    
    assert ukh1 == ukh2  # UKH should be same regardless of ukh field


def test_jsonl_roundtrip():
    """Test writing and reading JSONL."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.jsonl"
        
        obj1 = {"id": 1, "value": 1.5}
        obj2 = {"id": 2, "value": 2.5}
        
        append_jsonl(path, obj1)
        append_jsonl(path, obj2)
        
        records = read_jsonl(path)
        
        assert len(records) == 2
        assert records[0]["id"] == 1
        assert records[1]["id"] == 2
        assert "ukh" in records[0]
        assert "ukh" in records[1]


def test_observation_ukh_deterministic():
    """Test that Observation records produce deterministic UKH."""
    obs1 = AGL_Observation("test:source", {"x": [1.0, 2.0, 3.0]}, {"note": "test"})
    obs2 = AGL_Observation("test:source", {"x": [1.0, 2.0, 3.0]}, {"note": "test"})
    
    # Different timestamps, so different UKH
    assert obs1["ts"] != obs2["ts"]
    
    # But if we set same timestamp and ID, UKH should match
    obs1["ts"] = "2024-01-01T00:00:00Z"
    obs1["id"] = "obs_test123"
    obs2["ts"] = "2024-01-01T00:00:00Z"
    obs2["id"] = "obs_test123"
    
    ukh1 = compute_ukh(obs1)
    ukh2 = compute_ukh(obs2)
    
    assert ukh1 == ukh2


def test_canonical_json_no_whitespace():
    """Test that canonical JSON has no whitespace."""
    obj = {"a": 1, "b": 2}
    result = canonical_json(obj)
    
    assert " " not in result
    assert "\n" not in result
    assert "\t" not in result


def test_canonical_json_sorted_keys():
    """Test that keys are sorted."""
    obj = {"z": 1, "a": 2, "m": 3}
    result = canonical_json(obj)
    
    # Parse back to check order
    parsed = json.loads(result)
    keys = list(parsed.keys())
    assert keys == ["a", "m", "z"]


if __name__ == "__main__":
    # Run all tests
    test_decimal_string()
    test_canonical_json_deterministic()
    test_ukh_deterministic()
    test_ukh_different_for_different_content()
    test_add_ukh()
    test_ukh_excludes_itself()
    test_jsonl_roundtrip()
    test_observation_ukh_deterministic()
    test_canonical_json_no_whitespace()
    test_canonical_json_sorted_keys()
    print("All tests passed!")

