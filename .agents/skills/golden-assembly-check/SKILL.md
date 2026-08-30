---
name: golden-assembly-check
description: Investigate and validate intended NES Pascal golden Assembly changes. Never normalize a golden diff without understanding it.
---

When generated Assembly differs:

1. Reproduce with the smallest relevant source fixture.
2. Diff old versus new Assembly.
3. Identify which source/compiler change caused each meaningful difference.
4. Verify language semantics and evaluation order are unchanged unless intentionally changed.
5. Check branch labels/ranges, temporaries, registers/runtime calls and memory references affected.
6. If the diff is expected, update the golden output only after the new output is justified.
7. Run the focused golden/backend tests.
8. For optimization-related diffs, use `compiler-benchmark` when the change could materially affect size/cycles/resources.

Report:
- reason for diff;
- representative changed sequence;
- semantic effect;
- whether golden was updated;
- tests run.

Unexpected diff = investigate, not auto-accept.
