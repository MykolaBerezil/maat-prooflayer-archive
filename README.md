# MA'AT Runtime

**Complete implementation of the MA'AT (Measurement, Analysis, Adjudication, and Testing) Runtime system with recursive reactor, LLM integration, causal scaffolding, and learned gating policy.**

---

## Overview

MA'AT is a **bicameral AGI architecture** that implements rigorous hypothesis testing through dual hemispheres:

- **Right Hemisphere (R)**: Exploratory, generates novel hypotheses with looser acceptance thresholds
- **Left Hemisphere (L)**: Conservative, verifies and compresses accepted hypotheses with stricter thresholds

The system uses **triple-gate testing** (Bayesian, Coherence, MDL) to evaluate hypotheses and maintains **append-only cryptographic ledgers** for full auditability.

---

## Architecture

### Core Components

1. **Canonicalization & UKH** (`maat/core/`)
   - Deterministic JSON canonicalization with sorted keys and decimal formatting
   - Universal Knowledge Hash (UKH) using blake2b-256
   - Six AGL record types: Observation, Hypothesis, Test, Evidence, SlotDecision, Receipt

2. **Math Primitives** (`maat/mathx/`)
   - **Coherence**: FFT peak-to-mean ratio for detecting periodic patterns
   - **MDL**: Minimum Description Length for model compression evaluation

3. **Slot Gates** (`maat/slot/`)
   - Triple-gate testing: Bayesian (posterior mean), Coherence (FFT), MDL (compression)
   - Attention allocation metrics: novelty, coherence, risk, chaos
   - Decision logic: accept, reject, or defer

4. **Bicameral MAAT Engine** (`maat/engine/`)
   - R hemisphere: exploratory (looser thresholds)
   - L hemisphere: conservative (stricter thresholds)
   - Callosum transfer: R-accepted hypotheses automatically tested by L
   - Pluggable hypothesis generators (programmatic or LLM-based)

5. **Recursive Reactor** (`maat/reactor/`)
   - **Inner MA'AT**: Observes external world
   - **Outer MA'AT**: Observes inner's receipts (meta-cognition)
   - **Control Rods**: Four damping mechanisms (recursion, resource, reality, semantic)
   - **SCRAM**: Emergency shutdown on criticality/temperature/reality thresholds

6. **Hypothesis Generators** (`maat/engine/generator.py`)
   - **ProgrammaticGenerator**: Deterministic statistical hypotheses
   - **LLMAdapter**: Pluggable LLM integration with offline file emulation
   - **HybridGenerator**: Combines both with automatic fallback

7. **Causal DAG Scaffolding** (`maat/engine/causal.py`)
   - Directed Acyclic Graph for causal relationships
   - Cycle detection to maintain acyclicity
   - Edge weight learning from receipt outcomes
   - Hypothesis filtering by causal structure

8. **Learned Gating Policy** (`maat/engine/policy.py`)
   - Online threshold tuning targeting acceptance band (20-35% default)
   - Regret minimization (false accepts + false rejects)
   - Cooldown mechanism to prevent thrashing
   - Persists to `policy.json` with load/save

---

## Installation

### Prerequisites

- Python 3.11+
- NumPy (optional, for accelerated FFT)

### Setup

```bash
cd maat_project
export PYTHONPATH=$(pwd)
```

No additional dependencies required for core functionality. NumPy is optional for FFT acceleration.

---

## Usage

### Quick Start

Run the full system demo with all features:

```bash
python3 -m maat.cli.full_demo \
  --cycles 100 \
  --out ./out \
  --use-llm-file ./hypotheses.txt \
  --use-policy \
  --use-causal
```

### Command-Line Options

```
--out DIR              Output directory for ledgers (default: ./out)
--cycles N             Number of reactor cycles to run (default: 100)
--seed N               Random seed for determinism (default: 42)
--use-llm-file FILE    Path to hypotheses file for LLM emulation
--use-policy           Enable learned gating policy
--use-causal           Enable causal DAG scaffolding
--stress               Lower SCRAM thresholds for stress testing
--verbose              Detailed cycle-by-cycle output
```

### Simple Demo (Reactor Only)

```bash
python3 -m maat.cli.demo --cycles 50 --out ./out
```

---

## Testing

Run all tests:

```bash
cd maat_project
PYTHONPATH=$(pwd) python3 tests/test_canonical.py
PYTHONPATH=$(pwd) python3 tests/test_mathx.py
PYTHONPATH=$(pwd) python3 tests/test_slot.py
PYTHONPATH=$(pwd) python3 tests/test_engine.py
PYTHONPATH=$(pwd) python3 tests/test_reactor.py
```

All tests should pass with deterministic output.

---

## Output Files

After running the demo, the output directory contains:

### Ledgers (JSONL)

- `inner_observations.jsonl`: External observations processed by inner MA'AT
- `inner_R_evidence.jsonl`: Evidence from inner R-hemisphere testing
- `inner_R_decisions.jsonl`: Decisions from inner R-hemisphere gates
- `inner_R_receipts.jsonl`: Receipts from inner R-hemisphere
- `inner_L_*`: Same for inner L-hemisphere (if R accepts any hypotheses)
- `outer_observations.jsonl`: Meta-observations from inner receipts
- `outer_R_*`, `outer_L_*`: Same for outer MA'AT

### Reports (JSON)

- `policy.json`: Learned gating policy state
- `policy_report.json`: Policy history and statistics
- `causal_graph.json`: Causal DAG structure
- `causal_report.json`: Graph statistics

---

## AGL Record Schemas

### Observation

```json
{
  "spec": "AGL/1.0",
  "schema": "AGL/Observation",
  "id": "obs_<uuid>",
  "ts": "2024-01-01T12:00:00Z",
  "src": "sensor:temperature",
  "fields": {"value": "23.5", "unit": "celsius"},
  "meta": {},
  "ukh": "<blake2b-256>"
}
```

### Hypothesis

```json
{
  "spec": "AGL/1.0",
  "schema": "AGL/Hypothesis",
  "id": "hyp_<uuid>",
  "claim": "mean>23.5 implies stability",
  "hemi": "R",
  "from": ["obs_<uuid>"],
  "meta": {},
  "ukh": "<blake2b-256>"
}
```

### Evidence

```json
{
  "spec": "AGL/1.0",
  "schema": "AGL/Evidence",
  "id": "evid_<uuid>",
  "tst": "tst_<uuid>",
  "hyp": "hyp_<uuid>",
  "bayes": {
    "successes": 5,
    "failures": 3,
    "posterior": {"mean": 0.625}
  },
  "coherence": {"peak_mean": 12.5},
  "mdl": {"bits_delta": -15.2},
  "ukh": "<blake2b-256>"
}
```

### SlotDecision

```json
{
  "spec": "AGL/1.0",
  "schema": "AGL/SlotDecision",
  "id": "dec_<uuid>",
  "hyp": "hyp_<uuid>",
  "tst": "tst_<uuid>",
  "decision": "accept",
  "gates": {"bayes": 0.80, "coh": 7.5, "mdl": -8.0},
  "attention": {"nov": 0.5, "coh": 0.8, "risk": 0.2, "chaos": 0.3, "att": 0.65},
  "reason": ["posterior_mean=0.625 >= 0.80", "..."],
  "ukh": "<blake2b-256>"
}
```

### Receipt

```json
{
  "spec": "AGL/1.0",
  "schema": "AGL/Receipt",
  "id": "rec_<uuid>",
  "slot_id": "slot_R",
  "status": "accepted",
  "hyp": "hyp_<uuid>",
  "evid": "<evid_ukh>",
  "decision_ukh": "<dec_ukh>",
  "note": "hemi=R",
  "ukh": "<blake2b-256>"
}
```

---

## Triple-Gate Testing

Each hypothesis is evaluated against three gates:

1. **Bayesian Gate**: Posterior mean ≥ threshold (default R: 0.80, L: 0.95)
2. **Coherence Gate**: FFT peak-to-mean ≥ threshold (default R: 7.5, L: 8.5)
3. **MDL Gate**: Bits delta ≤ threshold (default R: -8.0, L: -16.0)

**Decision Logic:**
- **Accept**: All three gates pass
- **Defer**: At least one gate passes (Bayesian or Coherence)
- **Reject**: Neither Bayesian nor Coherence passes

---

## Control Rods

Four control rods moderate reactor behavior:

1. **Recursion Damper**: Reduces hypothesis generation count
2. **Resource Governor**: Limits computational resource usage
3. **Reality Anchor**: Maintains correlation with external observations
4. **Semantic Filter**: Filters low-quality hypotheses

**Auto-Adjustment:**
- High temperature → insert resource governor
- High pressure → insert recursion damper
- High criticality → insert multiple rods

---

## SCRAM Conditions

Emergency shutdown triggers when:

1. **Criticality** > 1.8 (outer/inner activity ratio)
2. **Temperature** > 0.95 (normalized cycle time)
3. **Reality Correlation** < 0.05 (external vs meta-series correlation)

When SCRAM triggers, all control rods are fully inserted and the reactor halts.

---

## Learned Gating Policy

The policy adapts gate thresholds online to:

1. Target acceptance band (20-35% default)
2. Minimize regret:
   - **False accepts**: Accepted but later MDL worsened
   - **False rejects**: Rejected but later coherence strong

**Update Rules:**
- Acceptance too low → loosen thresholds
- Acceptance too high → tighten thresholds
- High false accept regret → tighten
- High false reject regret → loosen

**Cooldown**: Minimum 10 cycles between updates (configurable)

---

## Causal DAG Scaffolding

The causal graph maintains a DAG over signals/features:

- **Nodes**: Signal names (e.g., "mean", "slope", "coherence")
- **Edges**: Causal relationships with weights [0, 1]
- **Cycle Detection**: Blocks edges that would create cycles

**Edge Weight Learning:**
- Hypothesis accepted → strengthen edges
- Hypothesis rejected → weaken edges
- Weight reaches 0 → remove edge

**Hypothesis Filtering:**
- `allow(inputs, target)` checks if hypothesis is allowed by DAG
- Blocked hypotheses are logged with reason

---

## Project Structure

```
maat_project/
├── maat/
│   ├── __init__.py
│   ├── core/
│   │   ├── canonical.py      # UKH, canonicalization, JSONL I/O
│   │   └── records.py         # AGL record factories
│   ├── mathx/
│   │   ├── coherence.py       # FFT peak-to-mean
│   │   └── mdl.py             # Minimum Description Length
│   ├── slot/
│   │   └── gates.py           # Triple-gate testing, attention
│   ├── engine/
│   │   ├── maat.py            # Bicameral MAAT engine
│   │   ├── generator.py       # Hypothesis generators
│   │   ├── causal.py          # Causal DAG scaffolding
│   │   └── policy.py          # Learned gating policy
│   ├── reactor/
│   │   └── reactor.py         # Recursive reactor, control rods, SCRAM
│   └── cli/
│       ├── demo.py            # Simple reactor demo
│       └── full_demo.py       # Full system demo
├── tests/
│   ├── test_canonical.py
│   ├── test_mathx.py
│   ├── test_slot.py
│   ├── test_engine.py
│   └── test_reactor.py
├── hypotheses.txt             # Sample LLM hypotheses file
└── README.md
```

---

## Key Features

✅ **Deterministic**: Fixed seed produces identical results  
✅ **Cryptographic Auditability**: All records have UKH  
✅ **Append-Only Ledgers**: JSONL format for immutability  
✅ **Triple-Gate Testing**: Bayesian, Coherence, MDL  
✅ **Bicameral Architecture**: R explores, L verifies  
✅ **Recursive Meta-Cognition**: Outer observes inner  
✅ **Control Rods & SCRAM**: Safe operation under stress  
✅ **LLM Integration**: Pluggable with offline emulation  
✅ **Causal DAG**: Hypothesis filtering by structure  
✅ **Learned Policy**: Adaptive threshold tuning  
✅ **Comprehensive Tests**: All components tested  

---

## Example Run

```bash
$ python3 -m maat.cli.full_demo --cycles 50 --use-policy --use-causal

MA'AT Full System Demo
============================================================
Features:
  - Recursive reactor: ✓
  - Learned policy: ✓
  - Causal DAG: ✓

Cycle 50: OK
  Criticality: 1.000
  Temperature: 0.004
  Pressure: 1.000
  Reality correlation: 0.800
  Policy thresholds:
    Bayes: 0.550 (adapted from 0.800)
    Coherence: 6.250 (adapted from 7.500)
    MDL: -5.500 (adapted from -8.000)
    Updates: 5

Final System State
============================================================
Saved policy to out/policy.json
Saved policy report to out/policy_report.json
Saved causal graph to out/causal_graph.json

Engine Statistics:
  Inner R: 50 total, 0 accept, 0.0% rate
  Outer R: 50 total, 0 accept, 0.0% rate

Demo complete!
All ledgers written to: out/
```

---

## License

This implementation follows the MA'AT specification from the original technical documentation.

---

## References

- Original MA'AT specification: `MA'ATRuntime—CompleteTechnicalDocumentation.md`
- AGL v1.0 schema definitions
- Triple-gate testing methodology
- Bicameral architecture principles

---

## Contact

For questions or issues, please refer to the original MA'AT documentation.


## License & Use

**Noncommercial use only.** Code is licensed under **PolyForm Noncommercial 1.0.0**; docs/data under **CC BY-NC 4.0**.

For commercial licensing, contact the repository owner.
