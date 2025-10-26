#!/usr/bin/env python3
import sys, pathlib
ROOT = pathlib.Path(".").resolve()
bad = []
for p in ROOT.rglob("*.py"):
    txt = p.read_text(encoding="utf-8", errors="ignore")
    if "SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0" not in txt:
        bad.append(str(p))
if bad:
    print("Missing SPDX in:")
    for b in bad: print(" -", b)
    sys.exit(1)
print("All .py files contain SPDX header.")
