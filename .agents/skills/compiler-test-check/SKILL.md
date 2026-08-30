---
name: compiler-test-check
description: Choose and execute the smallest useful NES Pascal validation scope for a compiler change, escalating only when regression surface requires it.
---

Use this order.

1. Identify changed contract:
   - lexer/parser syntax;
   - AST;
   - semantic/type/name rules;
   - diagnostics;
   - backend/codegen;
   - memory layout;
   - runtime/hardware;
   - CLI/build.
2. Run the narrowest directly relevant unit/module tests first.
3. Add positive + negative + boundary coverage for new behavior when applicable.
4. If generated Assembly is an intentional contract, run/inspect golden coverage.
5. If ca65/ld65 compatibility is relevant, build a representative ROM (`make rom` or equivalent focused integration).
6. If real runtime behavior changed, use `nes-compiler-runtime-check`.
7. Escalate to broad/full local validation for shared parser/AST/semantic/backend/memory/runtime/build infrastructure or when focused failures suggest wider impact.
8. Before completing broad work, prefer `make validate`.
9. Do not claim CI unless remote CI was actually checked.

Report commands and outcome compactly.
