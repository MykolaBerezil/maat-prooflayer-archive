#!/usr/bin/env python3
import sys, pathlib
ROOT = pathlib.Path(".").resolve()
SPDX = "# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0\n"
touched = []
for p in ROOT.rglob("*.py"):
    txt = p.read_text(encoding="utf-8", errors="ignore")
    if "SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0" in txt:
        continue
    lines = txt.splitlines(True)
    # Insert SPDX as first non-shebang line
    if lines and lines[0].startswith("#!"):
        lines = [lines[0], SPDX] + lines[1:]
    else:
        lines = [SPDX] + lines
    p.write_text("".join(lines), encoding="utf-8")
    touched.append(str(p))
print("Injected SPDX into", len(touched), "files")
for t in sorted(touched)[:30]:
    print(" -", t)
