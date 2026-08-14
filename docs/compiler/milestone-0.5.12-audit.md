# Milestone 0.5.12 — Functions: Completeness and Quality Audit

- **Branch:** `audit/0.5.12-validation`
- **Audit base commit:** `40313d5` (merge of PR #26, `0.5.12-functions`)
- **Milestone implementation commit:** `1c8f88d` ("Implement 0.5.12 functions")
- **Audit date:** 2026-08-14
- **Auditor role:** independent QA reviewer (not the original implementer)

This document is an independent review artifact for milestone 0.5.12 (Functions).
It is distinct from the implementation report
[`functions-0.5.12.md`](functions-0.5.12.md), which is the implementer's
milestone snapshot. This audit records evidence-based verification, coverage
findings, and a backlog for follow-up hardening.

---

## 1. Milestone requirements matrix

The contract is the Functions section of `roadmap/0.md` (identifier `0.5.12`).
All twelve requirements were verified against concrete repository evidence, not
names or comments.

| # | Requirement | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Function declarations | **Verified** | `function` grammar in `parser.py` (typed name, optional parameter list, optional return type); declarations accepted between `var` and the main block; `test_parser_represents_typed_function_and_explicit_call`, `test_parser_rejects_malformed_function_declarations`; declarations interleaved with procedures. |
| 2 | Function calls | **Verified** | `FunctionCall` AST node and `ResolvedFunctionCall`; every call requires parentheses, including parameterless calls; `test_forward_calls_resolve_in_callee_first_order`; nested calls in arguments/arithmetic/comparisons/conditions verified in runtime fixtures and probes. |
| 3 | `byte` return values | **Verified** | `function_result_<name>` regular-RAM backing byte; epilogue `lda function_result_<name>` + `rts`; `test_return_storage_is_regular_ram_and_absent_without_functions`; golden ABI; Mesen runtime (nested arithmetic results `$06/$31/$66/$F3`). |
| 4 | `boolean` return values | **Verified** | Canonical `$00`/`$01` materialization; accumulator carries the result; the final `lda` leaves the Z flag valid so caller short-circuit branches directly; `test_boolean_function_is_valid_in_short_circuit_expression`; probe and Mesen short-circuit verification. |
| 5 | Function parameters | **Verified** | `byte`/`boolean` value parameters using the static regular-RAM procedure ABI (`parameter_<name>` symbols); type validation via `E4005`; probe-verified rejection of enum and `color` parameter types. |
| 6 | Return type validation | **Verified** | Only `byte`/`boolean` returns; `E4026` for any other type (`tests/fixtures/diagnostics/unsupported_function_return_type.nsp`); wrong result literals rejected with `E4004` (`wrong_boolean_function_result.nsp`, `wrong_byte_function_result.nsp`). |
| 7 | Function calls inside expressions | **Verified** | Calls resolve as value expressions in arithmetic, comparisons, array indexes, record field writes, `if`/`while`/`for` conditions, `nes.*` arguments, and short-circuit operands; verified at unit, golden, and Mesen-runtime layers. |
| 8 | Define return-value storage or calling convention | **Verified** | Documented ABI in `docs/language/functions.md` and `functions-0.5.12.md`: static regular-RAM result byte per function, result returned in `A`, `A`/`X`/`Y`/flags caller-clobbered, hardware-stack return addresses, no runtime frame; golden `tests/golden/functions_abi.asm`. |
| 9 | Preserve outer expression temporaries across nested function calls | **Verified** | `callable_bases` in `TemporaryRequirements`; codegen pre-acquires each callee's base prefix so callee body temporaries sit above caller-live slots; `_generate_call_arguments` leases earlier argument results across later call-containing arguments; analysis and codegen agree; pressure golden (`Leaf` at base 2, peak 3 live bytes). |
| 10 | Support nested function-call expressions on top of the scoped temporary allocator | **Verified** | Nested calls reuse the 0.5.11 scoped pool without aliasing; 4-deep probe (`max_call_depth` 4, 3 live caller temps) verified via Mesen; nested call chains with sibling stacking verified. |
| 11 | Define evaluation order when function calls appear in larger expressions | **Verified** | Documented and verified: arguments left-to-right; `and`/`or` left-to-right short-circuit (skipped operands do not execute); binary arithmetic/comparison keeps right-operand-first when the right side requires evaluation (`LeftCall() - RightCall()` runs `RightCall()` first). Matches pre-existing lowering rules; no regression. |
| 12 | Reject direct and indirect recursion involving functions | **Verified** | `E3014` for direct (`recursive_function_call.nsp`), indirect (`recursive_function_call_indirect.nsp`), and mixed procedure/function cycles (`recursive_callable_mixed.nsp`); `test_direct_indirect_and_mixed_recursion_are_rejected`; probe confirmed a cycle is rejected even when the recursive function is unreachable from the main block. |

**Uncovered roadmap requirements:** none. All 12 requirements are implemented,
documented, and exercised by tests, fixtures, goldens, or benchmarks.

---

## 2. Positive semantic coverage

### Normal / common cases (covered)
- Single function returning a literal: canonical `lda function_result_X; rts` epilogue.
- Parameterised functions: static `parameter_*` RAM staging, left-to-right argument copy.
- Nested calls `F() + G() + H()`: right-first complex-operand lowering, per-call base offsets (`function_G` base 1, `function_F` base 2 with two live caller slots), pool=2.
- Boolean functions in short-circuit `if F() and G() then`: Z-flag path without `cmp #$00`, side-effect order left-to-right (Mesen-verified).
- Procedure/function interaction: procedures called from function bodies; function results passed directly to procedures (`examples/functions.nsp`).
- For-loops inside function bodies: `for_limit_*` cache, body evaluation per iteration, `jsr` per call (Mesen-verified `Sum($05)=$0F`).
- While-loops with function calls in the condition (Mesen-verified).

### Boundary conditions (covered)
- Result must be assigned on every path: loop-body-only assignment, conditional-only assignment, and read-before-assignment all emit `E3063` (probe-verified); both-branches-definite passes (unit test).
- Short-circuit `and`/`or` right-hand assignments are *not* definite, left-hand assignments remain definite (unit tests).
- 4-level call chain with `max_call_depth` 4 (Mesen-verified `$04`); 4-deep nested arguments with 3 simultaneously live temporaries (Mesen-verified `$0E`).
- Function used as a frame callback is rejected (probe); callback registration inside a function body is rejected.
- Parameter/result type boundaries: `enum`/`color` parameters → `E4005`; `enum`/`sprite` returns → `E4026`; byte↔boolean argument mismatches → `E4004`.
- Callable names share the global namespace with variables/procedures (`test_callable_names_share_the_existing_global_namespace`); a parameter shadowing the function name → `E3004`.

### Interactions (covered)
- Arrays × functions: `Values[Index()] := Value()` preserves the index on the hardware stack and re-reads it after the value expression (Mesen-verified).
- Records × functions: record-array field writes using function-call index and value (Mesen-verified `Positions[1].X=$07, .Y=$0E`).
- Builtins × functions: `nes.get_tile($00, Y())` stages X via `pha`/`pla` around the `jsr` (assembly-verified); `nes.set_background_color(F())` argument call (fixture).
- For-loops × functions: initial/final evaluated once into `for_limit_*`; function calls in body and final value; `for_limit` caches are always allocated after all expression temporaries, so callee body temporaries (bounded by `expression_temporaries`) can never alias a live `for_limit_*` byte.
- `nes.run`-required structure unchanged; function-bearing programs still satisfy single `set_background_color` validation.
- 8-bit wraparound inside function bodies (Mesen-verified).

### Cases only indirectly covered
- Function argument *type* mismatch (`E4004`) has no dedicated negative fixture, only an in-process unit assertion (`test_function_diagnostics_cover_call_and_type_errors`) and a CLI probe (P3-1).
- Maximum call depth near the 256-byte hardware-stack limit has no compile-time guard (P2-1).

---

## 3. Diagnostic coverage matrix

| Invalid condition | Expected code | Existing test / fixture | Status |
| --- | --- | --- | --- |
| Unknown function name | `E3059` | `tests/fixtures/diagnostics/unknown_function.nsp` + unit case `Missing()` | Covered |
| Wrong argument count | `E3060` | `tests/fixtures/diagnostics/function_argument_count.nsp` + unit case `One()` | Covered |
| Function used as statement | `E3061` | `tests/fixtures/diagnostics/function_used_as_statement.nsp` + unit case | Covered |
| Procedure used as expression | `E3062` | `tests/fixtures/diagnostics/procedure_used_as_expression.nsp` + unit case `Value := Work()` | Covered |
| Result read before assigned / not on every path | `E3063` | `tests/fixtures/diagnostics/undefined_function_result.nsp` + unit definite-assignment tests | Covered |
| Wrong result type / argument type | `E4004` | `wrong_byte_function_result.nsp`, `wrong_boolean_function_result.nsp` (result); argument type only unit-tested (`Enabled($01)`) | Covered (result); P3-1 (argument) |
| Unsupported return type | `E4026` | `tests/fixtures/diagnostics/unsupported_function_return_type.nsp` | Covered |
| Unsupported parameter type | `E4005` | pre-existing parameter fixtures exercised for enum/`color` via probes; enum-specific fixture `enum_procedure_parameter.nsp` | Covered |
| Direct / indirect / mixed recursion | `E3014` | `recursive_function_call.nsp`, `recursive_function_call_indirect.nsp`, `recursive_callable_mixed.nsp` | Covered |
| Function registered as frame callback | `E3018` | probe-verified only; function is declared yet reported "Unknown callback procedure" (P3-3) | P3-3 |
| Function called without parentheses | `E3005` | probe-verified; "Unknown identifier" (P3-4) | P3-4 |
| Bare statement call with wrong arg count | `E3061` before `E3060` | `function_used_as_statement.nsp` (correct count); wrong-count statement probe reports `E3061` (by design, P3-5) | P3-5 |

All six new function-specific diagnostics (`E3059`–`E3063`, `E4026`) are
registered in the canonical catalog (`docs/DIAGNOSTICS.md`,
`docs/reference/diagnostics/index.md`, `semantic.md`/`type-system.md`, and the
maintained PT-BR counterparts), validated by the diagnostic-catalog test, and
have focused negative fixtures. Messages are specific and actionable with
suggestion text.

---

## 4. Parser / semantic / backend layer coverage

| Layer | Evidence | Assessment |
| --- | --- | --- |
| Lexer / Parser | `function` keyword, optional parameter list, optional `: type`, `begin/end` body; statement-level `F(...)` parsed as a procedure call so `E3061` fires; `test_parser_represents_typed_function_and_explicit_call`, `test_parser_rejects_malformed_function_declarations` | Covered |
| Semantic | `FunctionDeclaration`/`FunctionCall` resolution, `ResolvedFunction`, `ResolvedFunctionCall`, `ResolvedFunctionResultAssignment`; definite-result analysis with short-circuit-aware path rules; recursion-cycle detection; shared global namespace; function/callback placement rules | Covered |
| AST | `FunctionDeclaration`, `FunctionCall`, `ResolvedFunction*` nodes; dedicated types; catalog of resolved nodes updated | Covered |
| Memory layout | `function_result_*` regular-RAM symbols in `FUNCTION_RESULTS`; zero cost when no functions (`test_return_storage_is_regular_ram_and_absent_without_functions`, benchmark identity); parameters reuse the procedure static-RAM ABI | Covered |
| Backend | `codegen_analysis.py` computes `callable_bases` + `max_call_depth`; `backend_ca65.py` pre-acquires base slots, leases argument results across call-containing arguments, emits `lda function_result_X; rts` epilogue; `_zero_flag_is_valid` enables direct Z branching for boolean results; analysis and codegen lease behavior agree (probe-verified across 20+ scenarios) | Covered |
| Runtime support | No new runtime code; hardware stack reserved in full for `JSR`/`RTS` return addresses; benchmarks unchanged | Covered |

---

## 5. Golden Assembly audit

`tests/golden/functions_abi.asm` records the return-ABI contract: epilogue
`lda function_result_X` / `rts`, caller `jsr`, and result staging.

`tests/golden/functions_temporary_pressure.asm` is the critical
temporary-safety golden: the caller holds `expression_temporary_0`,
`function_Middle` acquires `expression_temporary_1` (base 1), and `function_Leaf`
acquires `expression_temporary_2` (base 2) — a verified peak of three
simultaneously live bytes at source call depth two (four hardware-stack bytes).
This is exactly the boundary the milestone must not regress.

Classification: **required — exists.** The focused-golden convention is
followed; no full-file golden is warranted for Functions.

---

## 6. Toolchain validation

- The complete 21-benchmark corpus (20 pre-existing + `functions`) assembles and
  links through ca65/ld65 (`make benchmark`, `make validate`).
- `make rom` produces `build/minimal.nes` (valid NROM).
- The runtime fixture `tests/fixtures/runtime/functions.nsp` compiles to a ROM,
  assembles, links, and runs under headless Mesen (see section 7).
- All public examples, including `examples/functions.nsp`, compile, assemble,
  and link (validated in `tests/test_integration.py` and the benchmark corpus).
- No linker-configuration regression: `FUNCTION_RESULTS` sits after other
  compiler result storage in regular RAM; functionless programs omit the
  segment, symbols, and bodies entirely.

---

## 7. Mesen runtime coverage

`tests/mesen/verify_functions.lua` runs `tests/fixtures/runtime/functions.nsp`
and asserts concrete runtime memory: nested static-parameter safety,
left-to-right arguments, right-first complex arithmetic, comparisons, Boolean
normalization, short-circuit side effects, procedure/function interaction, and
8-bit wraparound. It is wired as
`test_functions_preserve_nested_static_parameters_and_short_circuits`; all 29
`MesenIntegrationTests` pass locally.

The independent probe battery adds runtime verification beyond the shipped
fixture (each address cross-checked against its memory map):
- `probe_stress.nsp` — nested calls with mixed return values (`A1=$06, A2=$31,
  A3=$66, B1=$F3`, 11 `Mark` calls in documented order).
- `probe_for.nsp` — for-loop inside a function (`Sum($05)=$0F`, `Index=$06`).
- `probe_record_func.nsp` — record-array field writes with function-call index
  and value (`Positions[1].X=$07, .Y=$0E`).
- `probe_depth.nsp` — 4-level call chain (`max_call_depth` 4, result `$04`).
- `probe_deep_temp.nsp` — 4-deep nested arguments, 3 live temporaries
  (`$0E`).
- `probe_while_calls.nsp` — while condition with function calls
  (`Result=$02`, `Counter=$03`).

This is behavioral verification of call-safe temporaries, evaluation order, and
nested parameter safety, not a ROM-boots-only check.

---

## 8. Benchmark / resource coverage

- The dedicated `functions` corpus entry compiles `examples/functions.nsp` and
  measures the documented ABI costs: 365 B PRG code / 371 B occupied, 158
  instructions, 560 estimated static base cycles, expression depth 2, maximum
  live temporaries 1, source call depth 2 (4 B JSR return-address peak), 3 B
  function-result regular RAM. All figures match the implementer report.
- **No-function zero cost (independently verified):** the full benchmark report
  was regenerated at the pre-0.5.12 commit (`e077216`) and at `1c8f88d`, and the
  two were compared. All 20 pre-existing benchmarks are **identical** in PRG
  code/occupied bytes, expression tree depth, maximum live temporaries,
  instruction count, estimated static cycles, and every RAM accounting column
  (including Zero Page and regular RAM); the only new result bytes in the corpus
  are the `functions` benchmark's 3 B. A program without functions emits no
  result bytes, `FUNCTION_RESULTS` segment, or function bodies.
- `test_benchmark_accounting.py` reconciles every category to the 2,048-byte NES
  CPU address space, including the three compiler-owned function result bytes
  and exact 2 KiB reconciliation.
- `for_limit_*` caches, expression temporaries, and function results are
  reported as distinct categories; nothing is mislabeled.

---

## 9. Documentation coverage

Checked: `docs/language/functions.md`, `docs/pt-BR/language/functions.md`,
`docs/runtime/cpu-memory.md`, `docs/pt-BR/runtime/cpu-memory.md`,
`docs/reference/unsupported-features.md`,
`docs/reference/diagnostics/{index,semantic,type-system}.md` + PT-BR,
`docs/compiler/functions-0.5.12.md`, `docs/compiler/test-coverage-map.md` +
PT-BR, `docs/index.md`, `docs/DIAGNOSTICS.md`, `docs/getting-started/*`,
roadmap `0.md` + `README.md`, README, and `docs/reference/compiler-pipeline.md`.

- Roadmap state is correct: `0.5.12` marked Completed with all 12 items
  checked; index updated (last completed `0.5.12`, next milestone `0.5.13`
  Collision Helpers).
- Language reference (EN + PT-BR) accurately documents declarations,
  left-to-right arguments, right-first complex operands, short-circuit
  preservation, the static-RAM ABI, caller-clobbered registers, the full
  hardware-stack reservation, `E3014` cycle rejection, and the absence of
  locals/frames/recursion/aggregate returns.
- Diagnostic indexes and detail pages (EN + PT-BR) register all new codes.
- Discrepancies found and disposition:
  - **Not fixed (reported):** `docs/pt-BR/compiler/functions-0.5.12.md` does
    not exist, while every prior milestone design doc (`optimization-audit-0.5.5`,
    `low-risk-codegen-0.5.7`, `arrays-0.5.8`, `enumerations-0.5.9`,
    `records-0.5.10`, `expression-temporaries-0.5.11`) has a maintained PT-BR
    translation. All user-facing 0.5.12 docs are translated; only this
    compiler-internal design snapshot is missing (P3-2).
  - **Accurate, verified:** the "524 automated tests" and "all 29 dedicated
    headless Mesen tests" claims in `functions-0.5.12.md` equal the live suite.

---

## 10. Test coverage map

`docs/compiler/test-coverage-map.md` (EN/PT-BR) adds subsystem 31 "Functions"
with Strong across every applicable tier (Semantic, Memory Layout, Backend ASM,
Golden ASM, Toolchain, Mesen Runtime, Benchmark Corpus) and N/A for Lexer/Parser
(grammar is exercised via unit tests but the coverage map marks it N/A per the
established convention). This classification is defensible: focused unit tests
for all 12 requirements, negative fixtures for every new diagnostic, a focused
ABI golden plus a temporary-pressure golden, toolchain assembly/linking of the
21-benchmark corpus, a Mesen runtime test, and exact benchmark accounting exist
for every applicable tier. No map correction is warranted.

---

## 11. Regression and interaction audit

- Full suite: **524 tests, OK** (0 skipped, 0 failures), including all
  pre-existing language, backend, memory, golden, and runtime tests, and all 29
  `MesenIntegrationTests`.
- Pre/post-0.5.12 benchmark comparison (section 8): all 20 pre-existing
  benchmarks byte-identical in every metric — no size, instruction, cycle, RAM,
  Zero Page, or temporary-pressure regression.
- Evaluation order, Boolean materialization, short-circuit lowering, indexed
  writes, and `for` loop lowering are unchanged for function-free programs.
- Targeted interaction probes: nested args, array/record indexes with calls,
  builtin arguments with calls, for/while/if conditions with calls, deep call
  chains, deep temp nesting, parameter/result type rejection, namespace
  collisions, recursion (including unreachable), callback misuse, and
  bare-statement calls.
- Pre-existing examples, goldens, and Mesen scripts unaffected.

---

## 12. Coverage gaps and findings

| Severity | Finding |
| --- | --- |
| P0 | None found. No correctness or semantic defect identified in the implemented, documented scope. |
| P1 | None. All 12 documented milestone requirements are implemented and have focused regression protection. |
| P2-1 | **No compile-time guard on maximum source-call depth vs the 256-byte hardware stack.** A 130-function chain (each body calling the next) compiles successfully with `max_call_depth = 130`; at runtime the JSR return addresses exceed 256 bytes, wrap the stack pointer, and silently corrupt state. Nested-call *expression* chains are naturally bounded by the 17-temp `E5004` limit, but sequential call chains are not. Reachable, silent, and undocumented; the design doc reserves the full stack and reports depth, but nothing rejects depth > 128. |
| P3-1 | Function argument *type* mismatch (`E4004`) has no dedicated negative fixture; only an in-process unit assertion (`Enabled($01)`) and CLI probes. Same code path as the pre-existing `E4004`; low incremental value. |
| P3-2 | `docs/pt-BR/compiler/functions-0.5.12.md` missing; breaks the per-milestone PT-BR design-doc pattern (all prior milestone design docs are translated). All user-facing 0.5.12 docs are translated. |
| P3-3 | A function registered as a frame callback (`nes.on_update(SomeFunction)`) is rejected with `E3018` "Unknown callback procedure: SomeFunction" although the function is declared; the rejection is correct, but the message does not explain that functions cannot be callbacks. |
| P3-4 | A function called without parentheses (`Value := CurrentScore;`) reports `E3005` "Unknown identifier: CurrentScore"; accurate but does not suggest the required `()`. |
| P3-5 | A bare statement call with the wrong argument count (`F($01, $02);`) reports `E3061` (function used as a statement) rather than `E3060` (argument count). By design — statement-level calls parse as procedure calls; the primary error surfaces first. |

---

## 13. Local validation results

- `make validate` (`PYTHON=python3`, `MESEN_PATH=/opt/mesen/Mesen`): **OK** —
  full suite **524 tests, OK** (0 skipped), 21-benchmark corpus assembled and
  linked, `build/minimal.nes` produced.
- `python3 -m unittest tests.test_integration.MesenIntegrationTests`: **29
  tests, OK**.
- Independent probes (compiler CLI + headless Mesen `--testRunner`): nested
  args, array/record indexed calls, for/while/if conditions, 4-level and
  4-deep-temp nesting, callback/type/namespace misuse — all behaved as
  documented.
- Determinism: repeated compilation produces byte-identical Assembly; benchmark
  reports regenerated deterministically across runs.
- Note: `make validate` requires `PYTHON=python3` in this environment because
  the Makefile defaults to `python`; CI is unaffected.

## 14. GitHub Actions run

Pushed `audit/0.5.12-validation`. The authoritative CI pipeline
(`.github/workflows/ci.yml`) ran against the pushed branch. The final
validation run (after the record-keeping commit `a5add38`) is GitHub Actions
run `31772718704` (run number 56, event `push`, head `a5add38`).

- `compiler-toolchain` job: **completed / success**
- `mesen-runtime` job: **completed / success**
- `ci-gate` job: **completed / success**

## 15. Final ci-gate

The aggregated `ci-gate` job **passed** for the pushed branch, confirming the
compiler-toolchain and Mesen runtime jobs and the overall gate remotely. Local
evidence (section 13) agrees with the remote result.

---

## Recommendation

All twelve milestone 0.5.12 requirements are verified against concrete evidence
(implementation, unit tests, negative fixtures, two focused goldens, toolchain
assembly/linking, 29 headless Mesen runs, and exact benchmark accounting). The
feature is layered correctly across parser, semantic, memory layout, and
backend; analysis and codegen agree on temporary liveness, so call-safety
divergence would be a loud compile-time failure rather than silent corruption.
Evaluation order, Boolean materialization, short-circuit lowering, and all
size/cycle invariants are preserved (pre/post benchmark identity across the
corpus). No P0 or P1 findings exist. The single P2 item is a hardening boundary
(maximum source-call depth has no compile-time guard against the 256-byte
hardware stack); the P3 items are documentation polish and minor diagnostic
wording. None block the milestone's acceptance criteria.

**READY WITH FOLLOW-UP HARDENING**
