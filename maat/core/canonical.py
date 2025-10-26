# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""
Canonical JSON serialization and Universal Knowledge Hash (UKH) computation.
Ensures deterministic, tamper-evident receipts.
"""
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List


def _decimal_string(x: float) -> str:
    """
    Format float as decimal string with 15 decimal places, stripping trailing zeros.
    Ensures deterministic float representation.
    """
    s = f"{x:.15f}"
    s = s.rstrip("0").rstrip(".")
    return s if s else "0"


def _canon_value(v: Any) -> Any:
    """Recursively canonicalize a value for deterministic serialization."""
    if isinstance(v, float):
        return _decimal_string(v)
    if isinstance(v, dict):
        return _canon_dict(v)
    if isinstance(v, list):
        return [_canon_value(x) for x in v]
    if isinstance(v, (bool, int, str)) or v is None:
        return v
    # Fallback for unexpected types
    return str(v)


def _canon_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    """Canonicalize dictionary by sorting keys and canonicalizing values."""
    return {k: _canon_value(d[k]) for k in sorted(d.keys())}


def canonical_json(obj: Dict[str, Any], exclude_ukh: bool = True) -> str:
    """
    Serialize object to canonical JSON string.
    
    Args:
        obj: Dictionary to serialize
        exclude_ukh: If True, exclude 'ukh' field from serialization
        
    Returns:
        Canonical JSON string with sorted keys and no whitespace
    """
    if exclude_ukh and 'ukh' in obj:
        obj = {k: v for k, v in obj.items() if k != 'ukh'}
    return json.dumps(_canon_dict(obj), ensure_ascii=False, separators=(',', ':'), sort_keys=True)


def compute_ukh(obj: Dict[str, Any]) -> str:
    """
    Compute Universal Knowledge Hash (UKH) using blake2b-256.
    
    Args:
        obj: Dictionary to hash
        
    Returns:
        64-character hexadecimal hash string
    """
    data = canonical_json(obj, exclude_ukh=True).encode("utf-8")
    return hashlib.blake2b(data, digest_size=32).hexdigest()


def add_ukh(obj: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add UKH field to object in-place.
    
    Args:
        obj: Dictionary to add UKH to
        
    Returns:
        The same object with 'ukh' field added
    """
    obj["ukh"] = compute_ukh(obj)
    return obj


def append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    """
    Append object to JSONL file with automatic UKH computation.
    
    Args:
        path: Path to JSONL file
        obj: Dictionary to append
    """
    if "ukh" not in obj:
        add_ukh(obj)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(canonical_json(obj, exclude_ukh=False) + "\n")


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    """
    Read all records from JSONL file.
    
    Args:
        path: Path to JSONL file
        
    Returns:
        List of dictionaries
    """
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

