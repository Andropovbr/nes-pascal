# Milestone 0.5.11 — Expression Temporary Allocation: Completeness and Quality Audit

- **Branch:** `audit/0.5.11-validation`
- **Audit base commit:** `9640da8` (merge of PR #24, `0.5.11-expression-temporaries`)
- **Milestone implementation commit:** `ea3e17d` ("Implement 0.5.11 expression temporary allocation")
- **Audit date:** 2026-08-14
- **Auditor role:** independent QA reviewer (not the original implementer)

This document is an independent review artifact for milestone 0.5.11 (Expression
Temporary Allocation). It is distinct from the implementation report
[`expression-temporaries-0.5.11.md`](expression-temporaries-0.5.11.md), which is
the implementer's milestone snapshot. This audit records evidence-based
verification, coverage findings, and a backlog for follow-up hardening.

---

## 1. Milestone requirements matrix

The contract is the Expression Temporary Allocation section of `roadmap/0.md`
(identifier `0.5.11`). All twenty requirements were verified against concrete
repository evidence, not names or comments.

| # | Requirement | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Replace unconditional 16-byte expression-temporary reservation with a compile-time-derived requirement | **Verified** | `analyze_program_temporaries` (`nes_pascal/codegen_analysis.py`) computes `expression_temporary_bytes`; `memory_layout.py` sizes the linker region to the measured total. `arithmetic`/`minimal` now reserve 0 expression bytes (benchmark report, `make validate`). |
| 2 | Define a scoped compiler-managed temporary pool | **Verified** | `TemporaryPool`/`TemporarySlot` with `call_scope` (`codegen_analysis.py`); acquire-lowest-free-slot, explicit release; unit tests `test_lowest_slot_reuse_and_call_scope_are_deterministic`, `test_pool_exhaustion_never_reuses_a_live_slot` (`tests/test_expression_temporaries.py`). |
| 3 | Track temporary acquisition and release during expression lowering | **Verified** | `acquire`/`release` calls in `_load_binary_expression`, `_comparison_setup`, and the `for` decrement path (`nes_pascal/backend_ca65.py`); the emitter asserts its observed peak exactly matches the reservation. |
| 4 | Calculate maximum simultaneously live expression temporaries for the compiled program | **Verified** | `expression_temporary_requirement` per statement, max across the program; asserted against emission peak in `generate()`; probe battery (right-first lowering, sibling-stacking, left-nested chains) reproduced exact maxima including a 17-slot chain. |
| 5 | Allocate only the required number of expression temporaries | **Verified** | Linker region equals the measured total; 19 of 20 benchmarks reserve zero expression bytes, `arrays` reserves one; `test_zero_temp_program_reserves_and_emits_no_expression_slot`. |
| 6 | Preserve Zero Page placement for temporaries while capacity is available | **Verified** | Expression slots remain at the `$0010-$001F` policy prefix; `ZP_TEMP`/`ZP_TEMP_FREE` regions; user addresses unchanged (future explicit `$0020-$007F`, automatic promotion `$0080-$00FF`); `test_runtime_temporary_and_user_regions_are_deterministic`. |
| 7 | Detect temporary-pool exhaustion deterministically | **Verified** | `E5004` at compile time; `tests/fixtures/diagnostics/temporary_ram_exhausted.nsp` (18-term chain, 17 temps) emits `E5004 ... requires 17 bytes (17 expression temporaries and 0 compiler caches), but only 16 bytes are available.`; asserted in `tests/test_memory_layout.py:230-247`; boundary probe: 17 terms (16 temps) accepted, 18 terms (17 temps) rejected. |
| 8 | Support nested expression trees without accidental aliasing | **Verified** | Lowest-free-slot lease with explicit release; 2- and 3-deep nested chains keep slots 0/1, 0/1/2 distinct; `test_one_two_and_deeper_requirements_match_actual_liveness`, `test_sequential_deep_expressions_reuse_three_slots`; focused golden `tests/golden/expression-temporaries.asm`. |
| 9 | Support array-index expressions without corrupting surrounding expression state | **Verified** | Nested reads `Values[Indexes[I]]`, scaled record indexes, indexed writes; indexed writes still save the index on the 6502 hardware stack while evaluating the RHS; Mesen runtime asserts indexed writes/reads; `test_arrays_records_procedure_arguments_and_builtins_share_one_pool`. |
| 10 | Preserve procedure-call argument evaluation semantics | **Verified** | Left-to-right argument staging retained; pre/post-0.5.11 instruction streams byte-identical for `procedure_parameters`/`procedures` benchmarks; focused assembly assertions in the expression-temporaries fixture. |
| 11 | Define save/restore or non-aliasing behavior required across future nested function calls | **Verified** | `call_scope` preserves every caller-owned lease; nested lowering can only acquire an unleased slot; builtin value calls already exercise the boundary; documented forward contract for Functions. Runtime frames and save/restore are deliberately deferred (0.5.12). |
| 12 | Make the temporary model call-safe before Functions are enabled | **Verified** | Pool + `call_scope` is structurally non-aliasing across call boundaries; builtin argument lowering exercises it; `test_lowest_slot_reuse_and_call_scope_are_deterministic`. No Functions syntax introduced. |
| 13 | Preserve deterministic memory maps | **Verified** | `test_linker_configuration_and_memory_map_are_reproducible`, `test_temporary_symbol_allocation_is_deterministic`; byte-identical regeneration across repeated compilations. |
| 14 | Report expression-temporary reservation in memory diagnostics | **Verified** | Memory map prints `Expression temporary reservation: N bytes (maximum simultaneously live)`, separate `Compiler caches`, and `Recovered temporary Zero Page` lines; verified against `memory_layout.nsp`/`counting.nsp` maps. |
| 15 | Add tests for zero-, one-, two-, and deeper-temporary requirements | **Verified** | `test_zero_temp_program_reserves_and_emits_no_expression_slot`, `test_one_two_and_deeper_requirements_match_actual_liveness`, `test_sequential_deep_expressions_reuse_three_slots`. |
| 16 | Add tests proving simple programs no longer reserve unused expression-temporary bytes | **Verified** | `test_zero_temp_program_reserves_and_emits_no_expression_slot`; `arithmetic`/`minimal` reserve 0 bytes and emit no `expression_temporary_0`. |
| 17 | Add tests for nested array/index expressions | **Verified** | Runtime fixture `tests/fixtures/runtime/expression_temporaries.nsp` (nested `Values[Indexes[I]]`, indexed writes, record-array reads/writes) + Mesen script `tests/mesen/verify_expression_temporaries.lua` + focused golden. |
| 18 | Add regression tests for expression evaluation order and 8-bit wraparound | **Verified** | Runtime fixture asserts `$F0 + $20 = $10` wraparound, sequential slot reuse, nested comparison materialization; pre/post instruction-stream identity across the corpus proves order preservation. |
| 19 | Compare Zero Page usage with the 0.5.5 baseline | **Verified** | `expression-temporaries-0.5.11.md` "0.5.5 fixed-window comparison" table (legacy window, max live, new expression, caches, net ZP saved per benchmark; 311-byte comparative aggregate); `optimization-audit-0.5.5.md` historical note preserves the baseline. Spot-checked against live benchmark output. |
| 20 | Do not implement Functions in this milestone | **Verified** | No function syntax/parsing/return values; roadmap marks 0.5.11 Completed and 0.5.12 Functions Planned; `docs/compiler/expression-temporaries-0.5.11.md` defers Functions explicitly. |

**Uncovered roadmap requirements:** none. All 20 requirements are implemented,
documented, and exercised by tests, fixtures, goldens, or benchmarks.

---

## 2. Positive semantic coverage

### Normal / common cases (covered)
- Direct arithmetic and simple programs: 0 temps, 16 ZP bytes recovered (unit + benchmark).
- Two- and three-operand expressions: peak 1 and 2 slots; four-operand nested chain: peak 3 (fixture table and focused golden).
- Sequential statements reuse `expression_temporary_0`; later statements reuse all slots.
- Comparison materialization keeps the arithmetic result and comparison operand distinct (peak 2).

### Boundary conditions (covered)
- Exact capacity: 17 terms (16 temps) accepted; 18 terms (17 temps) `E5004` (probe-verified).
- 16 terms + 1 cache byte accepted; 17 terms + 1 cache byte `E5004` (probe-verified).
- 0 temps + 16 cache bytes accepted; 0 temps + 17 cache bytes `E5004` (probe-verified).
- Mandatory temps never borrow optional promotion space (`test_zero_page.py:100`, `counting.nsp` at 5-byte limit).
- Zero-size `ZP_TEMP` linker region accepted by ld65 (all benchmarks and minimal ROM link).
- Zero-size `ZP_TEMP` with zero-size `ZP_TEMP_FREE` (exact 16-byte saturation) accepted.

### Interactions (covered)
- Arrays × expressions: `Values[Index] + Values[Index]` chains (fixture, boundary probes).
- Nested indexes: `Values[Indexes[I]]` (fixture, Mesen).
- Records: record-array reads and writes inside expressions (fixture, Mesen).
- Procedure arguments: two argument expressions evaluated and staged (fixture, Mesen).
- Builtin value arguments: `nes.set_background_color($21)` (fixture).
- `for` loops: `for_limit_*` caches separate accounting category sharing the same window (benchmark report; counting/arrays keep caches, never mislabeled).
- 8-bit wraparound: `$F0 + $20 = $10` (Mesen).
- Short-circuit Boolean lowering and direct flag comparisons unchanged (benchmark instruction identity).

### Cases only indirectly covered
- Exact 16-byte saturation of combined temps+caches has no dedicated unit test, only probe verification (P3-1).

---

## 3. Diagnostic coverage matrix

| Invalid condition | Expected code | Existing test / fixture | Status |
| --- | --- | --- | --- |
| Expression temporaries + caches exceed 16 bytes | `E5004` | `tests/fixtures/diagnostics/temporary_ram_exhausted.nsp` + `tests/test_memory_layout.py:230-247` | Covered |
| Mandatory storage borrows optional promotion space | `E5004` | `tests/test_zero_page.py:100` (`counting.nsp` at 5-byte limit) | Covered |
| Combined requirement and components stated | `E5004` message | asserted: "requires 17 bytes (17 expression temporaries and 0 compiler caches), but only 16 bytes are available." | Covered |
| Pool exhaustion never reuses a live slot | `TemporaryPoolExhausted` | `test_pool_exhaustion_never_reuses_a_live_slot` (unit) | Covered |
| Emitter peak mismatch vs. reservation | internal assert | `generate()` assertion, exercised by the focused fixture and benchmark corpus | Covered |
| Programmatic saturation edge (temps+caches exactly 16; 17) | `E5004` boundary | probe-verified at the CLI boundary | P3-1 gap (unit) |

`E5004` is registered in the catalog, documented in `docs/DIAGNOSTICS.md` and
`docs/reference/diagnostics/code-generation.md`, and validated by
`test_diagnostic_catalog.py`. The diagnostic message itself is precise, states
the combined requirement and its components, and never wraps, aliases, borrows
promotion space, or silently spills.

**Documentation defect (P3-2):** the `E5004` "Expected compiler output" example
in `docs/reference/diagnostics/code-generation.md` (EN and PT-BR) shows the
pre-0.5.11 message text ("Expression and loop code requires 17 temporary
bytes...") instead of the actual emitted message ("Compiler-managed Zero Page
storage requires 17 bytes (17 expression temporaries and 0 compiler caches),
but only 16 bytes are available."). The catalog tests validate code presence and
uniqueness only, not the example's message text.

---

## 4. Parser / semantic / backend layer coverage

| Layer | Evidence | Assessment |
| --- | --- | --- |
| Lexer / Parser | No syntax change; no new tokens or grammar | N/A (correctly N/A in coverage map) |
| Semantic | No source-language semantics changed; no new resolved node types | N/A (correctly N/A in coverage map) |
| AST | Unchanged; temporary model is compiler-internal | N/A (correctly N/A in coverage map) |
| Memory layout | `memory_layout.py` sizing, `ZP_TEMP`/`ZP_TEMP_FREE` linker regions, E5004 raise site, memory-map reporting; deterministic region/symbol tests | Covered |
| Backend | `codegen_analysis.py` pre-layout analysis + `backend_ca65.py` scoped acquisition; 7 focused unit tests; golden | Covered |
| Runtime support | none required — no runtime changes, no descriptor/helper emitted | Covered |

---

## 5. Golden Assembly audit

`tests/golden/expression-temporaries.asm` is a focused partial golden recording
every expression-temporary declaration and use: slot 0/1/2 declarations,
acquire/store/consume/release sequences, sequential reuse, nested array indexes,
indexed writes, record-array access, comparison materialization, and procedure
argument staging. It follows the established focused-golden convention.

Classification: **required — exists.** It protects the deterministic identity,
reuse, and ordering contract, which is the stability-critical surface of this
milestone. No additional full-file golden is warranted.

---

## 6. Toolchain validation

- The complete 20-benchmark corpus assembles and links through ca65/ld65 with
  the new variable-size `ZP_TEMP` region, including the zero-size and
  exact-saturation cases (`make validate`).
- `make rom` produces `build/minimal.nes` (valid NROM) under the new layout.
- The expression-temporaries runtime fixture compiles to a ROM and runs under
  headless Mesen (see section 7).
- No linker-configuration regression: `ZP_TEMP_FREE` is ordered between
  `ZP_TEMP` and the explicit window, and all regions remain non-overlapping and
  within Zero Page bounds.

---

## 7. Mesen runtime coverage

`tests/mesen/verify_expression_temporaries.lua` runs the expression-temporaries
fixture and asserts concrete runtime memory:
- three-deep arithmetic result,
- `$F0 + $20 = $10` wraparound,
- sequential slot reuse,
- nested `Values[Indexes[I]]` reads,
- indexed array writes,
- record-array reads and writes,
- nested comparison materialization,
- two procedure argument expressions.

Fixture addresses were independently cross-checked against the actual memory
map (expression temporaries `$0217-$0219` region contents, index `$020A`,
record result `$0215`, arrays base `$0210`, result `$0216`) and all matched.
Wired as `test_expression_temporaries_preserve_nested_runtime_values`; all 28
`MesenIntegrationTests` pass locally. This is behavioral verification, not a
ROM-boots-only check.

---

## 8. Benchmark / resource coverage

- `test_benchmark_accounting.py` reconciles every category to the 2,048-byte
  NES CPU address space for the corpus; `make benchmark` report regenerates
  byte-identically (verified with `md5sum` across two runs).
- Expression temporaries are reported as their own category; `for_limit_*`
  caches are separate and never mislabeled as expression temporaries
  (`counting` keeps 6, `arrays` keeps 2).
- **Code-quality invariants preserved:** pre-0.5.11 vs. post-0.5.11 generated
  Assembly is byte-identical for all 20 benchmarks except a single comment
  change on the `expression_temporary_0` declaration ("reusable" →
  "scoped reusable"). PRG code/occupied size, instruction counts, and estimated
  static cycles are unchanged; only data reservation and map reporting differ.
- 19 benchmarks now reserve zero expression bytes; `arrays` reserves one. Net
  ZP savings vs. the legacy 16-byte window are documented per benchmark
  (311-byte comparative aggregate) and match live measurements.
- No new performance thresholds or gates were introduced.

---

## 9. Documentation coverage

Checked: `docs/compiler/expression-temporaries-0.5.11.md`,
`docs/runtime/cpu-memory.md`, `docs/reference/diagnostics/code-generation.md`,
`docs/DIAGNOSTICS.md`, `docs/compiler/test-coverage-map.md`, `docs/index.md`,
README, roadmap `0.md` + `README.md`, plus the historical notes added to
`arrays-0.5.8.md`, `low-risk-codegen-0.5.7.md`, `optimization-audit-0.5.5.md`,
and `records-0.5.10.md` — each verified in EN and maintained PT-BR.

- Roadmap state is correct: `0.5.11` marked Completed with all 20 items
  checked; index updated (last completed `0.5.11`, next milestone `0.5.12`
  Functions).
- EN/PT-BR synchronization verified (headers, same sections/codes, diagnostic
  identifiers preserved; PT-BR index and coverage map updated; Mesen count
  27→28 in both).
- Historical notes in the 0.5.5/0.5.7/0.5.8/0.5.10 reports are accurate
  (verified against live benchmark output: `arrays` 1 expression + 2 cache
  bytes = 13 recovered; `records` 0 bytes = 16 recovered).
- Discrepancies found and disposition:
  - **Not fixed (reported):** the `E5004` example message in
    `code-generation.md` (EN + PT-BR) is stale (P3-2).
  - **Not fixed (reported):** "Recovered temporary Zero Page" is described as
    "allocator-visible free memory"; it is free in the linker configuration and
    reported Free in the map, but no compiler allocator currently places data
    there. This is forward-looking wording, not an error (P3-3, informational).
  - **Accurate, verified:** the "475 non-Mesen automated tests and all 28
    dedicated headless Mesen tests" claim equals the current 503-test suite
    (475 + 28); not stale.

---

## 10. Test coverage map

`docs/compiler/test-coverage-map.md` (EN/PT-BR) adds subsystem 30 "Expression
temporary allocation" with Strong across Diagnostics & Fixtures, Memory Layout,
Backend ASM, Golden ASM, Toolchain, Mesen Runtime, and Benchmark Corpus, and
N/A for Lexer/Parser/Semantic. This classification is defensible: focused unit
tests, an exhaustion fixture, a focused golden, toolchain assembly/linking of
the corpus, a Mesen runtime test, and exact benchmark accounting exist for every
applicable tier. No map correction is warranted.

---

## 11. Regression and interaction audit

- Full suite: **503 tests, OK** (475 non-Mesen + 28 Mesen), no skips, no
  failures — including all pre-existing language, backend, memory, golden, and
  runtime tests.
- Pre/post-0.5.11 generated Assembly byte-identical across all 20 benchmarks
  (modulo one comment) — no instruction, size, or cycle regression, and
  expression evaluation order is preserved for every corpus shape.
- `make validate` (test-all + benchmark + rom): **OK**.
- Targeted interaction probes: 17/18-term capacity boundaries, temps+caches
  combined boundaries, zero-size and saturated regions, peak-liveness battery
  across all statement/expression shapes, E5004 message text and position
  (`1:1`), and fixture-address vs. memory-map cross-check.
- Pre-existing examples, goldens, and Mesen scripts unaffected.

---

## 12. Coverage gaps and findings

| Severity | Finding |
| --- | --- |
| P0 | None found. No correctness or semantic defect identified. |
| P1 | None. All 20 documented milestone requirements are implemented and have focused regression protection. |
| P2 | None. Capacity boundaries, pool-exhaustion, promotion-no-borrow, and accounting invariants are all covered by tests or fixtures. |
| P3-1 | No automated unit test for the exact combined (temps + caches) saturation boundary; verified by CLI probes only. Same code path as the fixture; low incremental value. |
| P3-2 | `docs/reference/diagnostics/code-generation.md` `E5004` "Expected compiler output" shows the pre-0.5.11 message text (EN and PT-BR). |
| P3-3 | "Recovered temporary Zero Page ... allocator-visible free memory" wording is forward-looking; no allocator currently places data in the recovered suffix (informational). |

---

## 13. Local validation results

- `make test-all` (`PYTHON=python3`, `MESEN_PATH=/opt/mesen/Mesen`): **503
  tests, OK** (0 skipped), including `test_expression_temporaries` (7),
  `test_benchmark_accounting`, `test_memory_layout`, and all 28
  `MesenIntegrationTests`.
- `make benchmark`: **OK**; report regenerated byte-identically across runs;
  accounting reconciles to 2,048 bytes.
- `make rom`: **OK**; `build/minimal.nes` produced.
- `make validate` (test + benchmark + rom): **OK**.
- Pre/post Assembly diff across 20 benchmarks: byte-identical except one
  comment; PRG/instructions/cycles unchanged.
- Determinism: repeated compilation produces byte-identical Assembly and
  identical benchmark reports.
- Note: `make validate` requires `PYTHON=python3` in this environment because
  the Makefile defaults to `python`; CI is unaffected.

## 14. GitHub Actions run

Pushed `audit/0.5.11-validation` (`ab557e2`). The authoritative CI pipeline
(`.github/workflows/ci.yml`) ran against the pushed branch: GitHub Actions run
`31767587223` (run number 50, event `push`, head `ab557e2`).

- `compiler-toolchain` job: **completed / success**
- `mesen-runtime` job: **completed / success**
- `ci-gate` job: **completed / success**

## 15. Final ci-gate

The aggregated `ci-gate` job **passed** for the pushed branch, confirming the
compiler-toolchain and Mesen runtime jobs and the overall gate remotely. Local
evidence (section 13) agrees with the remote result.

---

## Recommendation

**READY**

All twenty milestone 0.5.11 requirements are verified against concrete evidence
(implementation, unit tests, exhaustion fixture, focused golden, toolchain
assembly/linking, Mesen runtime, benchmark accounting, documentation). The
feature is layered correctly across analysis, memory layout, and backend; the
emitter asserts exact agreement with the pre-layout analysis, so analysis/emission
divergence is a loud compile-time failure rather than silent corruption.
Evaluation order, Boolean materialization, short-circuit lowering, and all
code-size/cycle invariants are preserved (byte-identical streams across the
corpus). No P0, P1, or P2 findings exist. The remaining P3 items are
documentation polish and one boundary-test nicety, none of which block the
milestone's acceptance criteria.
