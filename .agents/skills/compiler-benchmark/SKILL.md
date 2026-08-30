---
name: compiler-benchmark
description: Compare NES Pascal code-generation/resource effects using the repository benchmark corpus and generated evidence.
---

Use when backend/lowering/memory changes may materially affect generated output.

1. Establish baseline from the unchanged implementation/known report when available.
2. Use stable benchmark programs; do not repurpose historical baseline sources.
3. Run the repository benchmark entry point (`make benchmark` / `tools/measure_benchmarks.py`).
4. Compare only metrics the tooling actually produces.
5. Relevant metrics may include:
   - PRG-ROM size;
   - instruction count;
   - estimated/static cycles;
   - Zero Page;
   - RAM;
   - temporary pressure.
6. Inspect representative Assembly when a metric changes unexpectedly.
7. Do not report guessed improvements as measured.
8. If baseline cannot be reproduced, state that limitation.

Output a compact before/after table or bullet list and explain only meaningful deltas.
