---
name: diagnostic-check
description: Validate a new or changed NES Pascal compiler diagnostic as a stable public contract.
---

For each diagnostic:

1. Confirm the code belongs to the project's canonical namespace/range.
2. Confirm the code is not reused for a different meaning.
3. Confirm the correct compiler phase emits it.
4. Check message is specific/actionable and location is correct.
5. Add or update a focused negative fixture/test.
6. Verify the expected diagnostic is emitted.
7. Verify unrelated diagnostics are not emitted for the focused case when that matters.
8. Update the canonical diagnostic catalog/documentation.
9. Keep source identifier/syntax names unlocalized unless project policy explicitly says otherwise.

Do not change diagnostic numbering opportunistically.
