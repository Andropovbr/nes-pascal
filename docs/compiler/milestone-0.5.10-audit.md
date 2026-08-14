# Milestone 0.5.10 — Records: Completeness and Quality Audit

English | [Português (Brasil)](../pt-BR/compiler/milestone-0.5.10-audit.md)

- **Branch:** `audit/0.5.10-validation`
- **Audit base commit:** `b9e4075` (merge of PR #21, `0.5.10-records`)
- **Milestone implementation commit:** `36534f7` ("Implement 0.5.10 records")
- **Audit date:** 2026-08-13
- **Auditor role:** independent QA reviewer (not the original implementer)

This document is an independent review artifact for milestone 0.5.10 (Records). It
is distinct from the implementation report
[`records-0.5.10.md`](records-0.5.10.md), which is the implementer's milestone
snapshot. This audit records evidence-based verification, coverage findings, and
a backlog for follow-up hardening.

---

## 1. Milestone requirements matrix

The contract is the Records section of `roadmap/0.md` (identifier `0.5.10`,
formerly Milestone 26). All eleven requirements were verified against concrete
repository evidence, not names or comments.

| # | Requirement | Status | Evidence |
| --- | --- | --- | --- |
| 1 | User-defined record types | **Verified** | `RecordTypeDeclaration` parsing (`nes_pascal/parser.py:143-186`), semantic resolution (`nes_pascal/semantic.py:_resolve_record_types`); tests `test_lexer_and_parser_preserve_named_record_structure`, `test_resolves_nominal_layout_and_typed_fields` (`tests/test_records.py`); example `examples/records.nsp`. |
| 2 | Byte fields | **Verified** | `RecordField` with `BuiltInType.BYTE`; field offsets asserted (`tests/test_records.py:106-109`); golden `tests/golden/records.asm` (`sta variable_Player`). |
| 3 | Boolean fields | **Verified** | `BuiltInType.BOOLEAN` field, canonical `$00`/`$01`; golden `records.asm` (`sta variable_Player + 2`, `lda #$01 ; true`); Mesen asserts `Enemies[0].Visible` at `$0207` (`tests/mesen/verify_records.lua`). |
| 4 | Enumeration fields | **Verified** | `EnumType` field; exact-type assignment rules (`test_enum_fields_reject_members_from_a_different_enum`); golden `cmp #$01`; Mesen asserts `Enemies[0].State` at `$0206`. |
| 5 | Record variables | **Verified** | `ResolvedVariable` with `RecordType`; contiguous regular RAM (`test_records_and_record_arrays_are_contiguous_regular_ram`); Mesen asserts `Player.X/Y/State/Visible` at `$0214-$0217`. |
| 6 | Record field access | **Verified** | `RecordFieldExpression` → `ResolvedRecordField` (`semantic.py`), `_load_record_field` (`backend_ca65.py:3057-3076`); golden reads; Mesen runtime reads. |
| 7 | Record field assignment | **Verified** | `RecordFieldAssignment` → `ResolvedRecordFieldAssignment`; direct and scaled-offset writes; golden writes; Mesen runtime writes. |
| 8 | Record arrays | **Verified** | `ArrayType` element `RecordType`; `_type_storage_size` (`memory_layout.py`); size-aware scaling (powers of two via `asl`, others via local repeated addition); `test_rejects_variable_scaled_offsets_beyond_one_byte`; Mesen `Enemies[1]` at `$0208-$020B`. |
| 9 | Calculate record sizes at compile time | **Verified** | `RecordType.size` = field count; size 4 asserted (`tests/test_records.py:105`); record arrays sized 16/32 bytes in layout test; memory map reports type names. |
| 10 | Generate field offsets | **Verified** | Zero-based `RecordField.offset`; offsets `[0,1,2,3]` asserted; golden `variable_Player + 1/2/3`; `_resolved_record_field_operand` folds `index * size + offset`. |
| 11 | Detect unsupported recursive record definitions | **Verified** | `E4023` for direct self-reference (`semantic.py:_resolve_record_types`); fixture `recursive_record_definition.nsp`; asserted in `test_record_diagnostic_fixtures_are_focused_and_stable`. Indirect (mutual) recursion is also rejected (`E4022`, unsupported nested field type). |

**Uncovered roadmap requirements:** none. All 11 requirements are implemented,
documented, and exercised by tests or fixtures.

---

## 2. Positive semantic coverage

### Normal / common cases (covered)
- Standalone record field reads and writes (`Player.X`, `Player.Y`, `Player.Active`, `Player.State`): golden + Mesen + unit tests.
- Record-array element access with constant and variable indexes: `Enemies[$00]`, `Enemies[$02]`, `Enemies[Index]` (golden, `test_indexed_write_preserves_index_before_evaluating_rhs`, Mesen).
- Enum and Boolean fields with exact type rules: `test_field_types_use_existing_strict_assignment_rules`, `test_enum_fields_reject_members_from_a_different_enum`.
- Field reads inside `if` conditions and comparisons: golden (`if Player.Active then`, `if Player.State = Moving then`); Mesen (`if Enemies[Index].State = Active then`).

### Boundary conditions (covered)
- Max legal scaled offset exactly `$FF` accepted; `$100` rejected (`test_rejects_variable_scaled_offsets_beyond_one_byte`, and probe-verified `array[$00..$3F]` size-4 → offset 255 accepted, `array[$00..$40]` → 259 rejected).
- Record with 256 fields accepted; 257 fields rejected (`E4024`) — probe-verified, but not in the automated suite (see P2-1).
- One-byte record never auto-promoted to Zero Page (`test_one_byte_record_is_never_automatically_promoted`).
- Empty record rejected (`E4024`) — probe-verified, not in the automated suite (see P2-1).
- Non-power-of-two record size uses local repeated addition (`test_non_power_of_two_record_size_uses_local_repeated_addition`).
- Large constant record-array index folds to a 16-bit ca65 address (`variable_Enemies + 960` for `Enemies[$F0]`) — probe-verified.

### Interactions (covered or probe-verified)
- Records × arithmetic: `Result := Result + Player.X` emits direct RHS operand `adc variable_Player` (probe-verified).
- Records × Boolean operators: `not`, `and` short-circuit with record fields (probe-verified).
- Records × comparisons: equality with immediate and field operands (golden, probe).
- Records × procedures: record field as `byte` argument (`Take(Player.X)`) — probe-verified, not in suite (see P3).
- Records × control flow: `for` loops over record arrays, `while`/`repeat` with field conditions — probe-verified, not in suite (see P3).
- Records × definite assignment: field write marks record assigned; read-before-assignment produces `E3008` for both standalone records and record arrays (unit/probe-verified; aggregate rule consistent with arrays).
- Records × callbacks: update callback reading a global record field; main-block requirement enforcement (probe-verified).
- Whole records rejected as values: assignment `E4025` (fixture), comparison `E4025` (probe-verified, see P2-2), scalar read `E4025`, whole-record builtin/procedure arguments (probe-verified).
- Arrays of enum remain rejected (`E4010`); record fields cannot be arrays or nested records (`E4022`).

### Cases only accidentally covered
- Record fields inside procedures and loops are not part of the automated suite; they work via the same resolution paths as the covered cases but lack focused regression tests (P3).

---

## 3. Diagnostic coverage matrix

| Invalid condition | Expected code | Existing test / fixture | Status |
| --- | --- | --- | --- |
| Duplicate record field | `E4019` | `tests/fixtures/diagnostics/duplicate_record_field.nsp` + `test_records.py` | Covered |
| Unknown record field (assignment) | `E4020` | `tests/fixtures/diagnostics/unknown_record_field.nsp` + `test_records.py` | Covered |
| Unknown record field (expression read) | `E4020` | no dedicated fixture (same code path as assignment) | P3 gap |
| Field access on scalar (assignment) | `E4021` | `tests/fixtures/diagnostics/field_access_on_non_record.nsp` + `test_records.py` | Covered |
| Field access on scalar (read) | `E4021` | no dedicated fixture (same code path) | P3 gap |
| Unsupported field type — array field | `E4022` | `tests/fixtures/diagnostics/unsupported_record_field_type.nsp` + `test_records.py` | Covered |
| Unsupported field type — nested/unknown record field | `E4022` | no fixture | P3 gap |
| Direct recursive record definition | `E4023` | `tests/fixtures/diagnostics/recursive_record_definition.nsp` + `test_records.py` | Covered |
| Empty record | `E4024` | `tests/fixtures/diagnostics/empty_record_definition.nsp` + `test_records.py` | **Resolved** |
| Record exceeding 256 fields | `E4024` | `tests/fixtures/diagnostics/oversized_record_definition.nsp` + `test_records.py` | **Resolved** |
| Variable record-array offset > `$FF` | `E4024` | `test_rejects_variable_scaled_offsets_beyond_one_byte` | Covered |
| Whole-record assignment | `E4025` | `tests/fixtures/diagnostics/invalid_record_usage.nsp` + `test_records.py` | Covered |
| Whole-record comparison | `E4025` | `tests/fixtures/diagnostics/whole_record_comparison.nsp` + `test_records.py` | **Resolved** |
| Whole record used as scalar | `E4025` | no fixture (probe-verified) | P3 gap |
| Unknown record type for a variable | `E4001` | `test_unknown_record_type_uses_the_existing_unknown_type_diagnostic` | Covered |
| Unknown record identifier (read) | `E3005` | no dedicated fixture (generic identifier path) | P3 gap |
| Record field read before assignment | `E3008` | no record-specific fixture (generic definite-assignment path) | P3 gap |
| Record type as procedure parameter type | `E4001` "Unknown type" | no test — misleading diagnostic (see P3-3) | P3 gap |

All eight new record diagnostic codes (`E4019`-`E4025`) are registered in the
catalog, documented in `docs/DIAGNOSTICS.md` and
`docs/reference/diagnostics/type-system.md`, and validated by
`test_diagnostic_catalog.py`.

Error paths implemented in code but never exercised by a test: whole record
used as scalar, and record type used as a parameter type. The two previously
unexercised P2 paths (empty record, record over 256 fields) and whole-record
comparison are now covered by the fixtures added in the hardening task below
(see [Resolved P2 findings](#resolved-p2-findings)).

---

## 4. Parser / semantic / backend layer coverage

| Layer | Evidence | Assessment |
| --- | --- | --- |
| Lexer | `TokenKind.RECORD` asserted via `tokenize("Entity = record X: byte; end;")` (`test_records.py`) | Covered |
| Parser | Record structure test, malformed-declaration tests (`E2102`), type-section ordering probes, assignment/expression DOT handling (`parser.py`) | Covered |
| AST | `RecordType`/`RecordField`/`RecordFieldExpression`/`RecordFieldAssignment` + resolved nodes; nominal-layout unit tests | Covered |
| Semantic | 17 unit tests, 9 focused fixtures, type-strictness tests, definite assignment, VBlank safety hooks, `_expression_type_hint` for comparisons | Covered |
| Memory layout | contiguous layout, record-array sizing, promotion exclusion, RAM exhaustion (`E5003`), temporary accounting, memory-map output | Covered |
| Backend | golden assembly, power-of-two and non-power-of-two scaling, indexed-write evaluation order, direct RHS operands, `_zero_flag_is_valid` for field loads | Covered |
| Runtime support | none required — no record runtime, descriptor, or helper emitted (asserted: `record_runtime`/`record_descriptor` absent; `runtime_features == ()`) | Covered |

---

## 5. Golden Assembly audit

`tests/golden/records.asm` is a focused partial golden covering the
`Index`/`Player`/`Enemies` statement core of the `records.nsp` codegen fixture:
direct and constant-index field writes, field reads, enum/Boolean branch code,
and variable-index scaled writes/reads (`asl` ×2, `adc #$01`, `tax`,
`lda ...,x`). It follows the established focused-golden convention used for
arrays (`arrays-addressing.asm`) and enumerations (`enumerations.asm`).

Classification: **required — exists.** The scaled-index addressing and direct
field operands are stability-critical lowering shapes and are adequately
protected. No additional full-file golden is warranted.

---

## 6. Toolchain validation

- `examples/records.nsp` compiles through NES Pascal → ca65 → ld65 → a valid
  NROM image (40976 bytes; header `NES`/`$1A`, 2 PRG banks, 1 CHR bank, mapper 0).
- Automated: `test_records_example_builds_valid_nrom_image`
  (`tests/test_integration.py`) validates header, mapper, banks, vectors, CHR
  size, and ROM size.
- Generated assembly inspected: field offsets (`variable_Player + 1/2/3`),
  scaled indexing (`variable_Enemies,x`), memory layout matches the Mesen
  expected addresses.

---

## 7. Mesen runtime coverage

`tests/mesen/verify_records.lua` runs `examples/records.nsp` in headless Mesen
and asserts concrete runtime memory:
- `Enemies[0].X/Y/State/Visible` at `$0204-$0207`,
- `Enemies[1].X/Y/State/Visible` at `$0208-$020B` (variable-index scaled write),
- `Player.X/Y/State/Visible` at `$0214-$0217`,
- `Index` at `$0080`, `Result` at `$0081`, `IsVisible` at `$0218`.

This is meaningful behavioral verification (fixed layout, scaled indexing,
enum/Boolean field storage, and a variable-index comparison branch), not a
ROM-boots-only check. Wired as
`test_records_preserve_fixed_layout_and_scaled_indexing`; passes locally.

---

## 8. Benchmark / resource coverage

- `records` benchmark added to the corpus (`tools/measure_benchmarks.py`) with
  exact metric assertions (`test_records_benchmark_reports_focused_resource_accounting`):
  PRG 389/395 B, 196 instructions, 605 static base cycles, tree depth 2,
  max live temporaries 0, record storage 20 B regular RAM, ZP promoted 2 B,
  runtime features none.
- Pre-existing 19 benchmark workloads retain prior metrics; verified against the
  `arrays-0.5.8.md` and `enumerations-0.5.9.md` documented baselines
  (PRG/instructions/cycles all unchanged).
- Record storage accounting (`_type_storage_size`) covers standalone records and
  arrays of records; no hidden ZP reservations; no runtime feature emission for
  programs without records.
- No performance thresholds or gates were introduced.

---

## 9. Documentation coverage

Checked: `docs/language/records.md`, `docs/compiler/records-0.5.10.md`,
`docs/reference/diagnostics/type-system.md`, `docs/DIAGNOSTICS.md`,
`docs/reference/unsupported-features.md`, `docs/language/{arrays,assignments,
expressions,program-structure,types,constants-and-variables}.md`,
`docs/language/index.md`, `docs/reference/index.md`, `docs/index.md`,
`docs/getting-started/building-and-running.md`, `README.md`, roadmap
`0.md` + `README.md`, and `docs/compiler/test-coverage-map.md` — each verified in
EN and maintained PT-BR.

- Roadmap state is correct: `0.5.10` marked Completed with all 11 items checked;
  index updated (next milestone `0.5.11`).
- EN/PT-BR synchronization verified (headers translated, diagnostics identifiers
  preserved, same sections/codes; PT-BR tracking list updated).
- Discrepancies found and disposition:
  - **Fixed during this audit:** `docs/reference/diagnostics/index.md` (EN and
    PT-BR) omitted the seven record diagnostics `E4019`-`E4025` from the
    per-code index, jumping `E4018` → `E5001`. This was a mechanical
    documentation inconsistency; rows added in both languages.
  - **Not fixed (reported):** `records-0.5.10.md` states "486 automated tests";
    the current suite is 490 (0 skipped in this environment). The figure is a
    stale point-in-time snapshot (P3).
  - **Historical by convention:** `arrays-0.5.8.md`, `enumerations-0.5.9.md`,
    and `optimization-audit-0.5.5.md` still list "arrays of records"/"records"
    as future work. These are point-in-time milestone reports and are retained
    as historical snapshots (P3 note).

---

## 10. Test coverage map

`docs/compiler/test-coverage-map.md` (EN/PT-BR) adds subsystem 29 "Records"
with Strong across all layers. This classification is defensible: focused tests,
nine diagnostic fixtures, a focused golden, a toolchain build test, a Mesen
runtime test, and a benchmark with exact metric assertions exist for every
layer. No map correction is warranted. The remaining weaknesses are the P3
fixture gaps in section 3, which do not change the layer classification.

---

## 11. Regression and interaction audit

- Full suite (491 tests) passes, including all pre-existing language, backend,
  memory, and runtime tests — no regression in covered behavior.
- Pre-existing benchmark metrics unchanged (verified against documented
  baselines) — no code-size, cycle, or memory regressions.
- Pre-existing examples, goldens, and Mesen scripts unaffected.
- Targeted interaction probes (records × enums, arrays, procedures, builtins,
  loops, callbacks, definite assignment, Boolean short-circuit, direct RHS
  operands, temporary usage in nested comparisons) all behave correctly.

---

## 12. Coverage gaps and findings

| Severity | Finding |
| --- | --- |
| P0 | None found. No correctness or semantic defect identified. |
| P1 | None. All documented milestone requirements are implemented and have focused regression protection. |
| P2-1 | No automated fixture/test for `E4024` empty-record and >256-field paths (only the variable-offset path is tested). Both are documented and probe-verified. **Resolved by the hardening task (see below).** |
| P2-2 | No automated fixture/test for whole-record comparison (`E4025`); only whole-record assignment is fixture-tested. Behavior probe-verified. **Resolved by the hardening task (see below).** |
| P3-1 | Diagnostics reference index omitted `E4019`-`E4025` (EN + PT-BR). **Fixed during this audit.** |
| P3-2 | `records-0.5.10.md` "486 automated tests" count is stale/unreproducible (current suite: 490). |
| P3-3 | A declared record used as a procedure parameter type reports `E4001` "Unknown type: Rec", which is misleading; enum parameter types get a dedicated `E3007` at parse time. No test exists. |
| P3-4 | Several implemented record error paths lack dedicated fixtures (unknown field read, field access on scalar read, whole record as scalar, record field read-before-assignment) — same code paths as covered cases; low incremental value. |
| P3-5 | Historical milestone docs (`arrays-0.5.8.md`, `enumerations-0.5.9.md`, `optimization-audit-0.5.5.md`) retain "records not yet supported" phrasing; accepted as historical snapshots. |

---

## Resolved P2 findings

Follow-up hardening task `chore/records-p2-diagnostic-hardening` closed P2-1 and
P2-2 with focused negative fixtures and assertions. No compiler, parser, AST,
semantic, backend, runtime, memory-layout, or diagnostic-definition behavior
changed; the fixtures and tests rely on the already-implemented checks.

| P2 finding | Fixture | Expected code | Assertion |
| --- | --- | --- | --- |
| Empty record layout rule | `tests/fixtures/diagnostics/empty_record_definition.nsp` | `E4024` | Added to `test_record_diagnostic_fixtures_are_focused_and_stable` (rejection + code + single occurrence) and to `test_record_layout_and_usage_fixtures_target_the_intended_rule` (message "Record Empty must declare at least one field.") |
| Record over 256 fields | `tests/fixtures/diagnostics/oversized_record_definition.nsp` (257 fields `F0`-`F256`) | `E4024` | Same assertions; message "Record Large exceeds the supported 256-byte layout." |
| Whole-record comparison | `tests/fixtures/diagnostics/whole_record_comparison.nsp` (`if A = B then`) | `E4025` | Same assertions; message "Whole-record comparison is not supported for type Position." |

- `oversized_record_definition.nsp` uses the smallest deterministic case that
  exceeds the legal maximum (257 fields); the legal maximum (256 fields) and the
  record-layout semantics are unchanged.
- `whole_record_comparison.nsp` assigns both record fields before comparing so
  the fixture reaches the whole-record-value restriction rather than an earlier
  definite-assignment diagnostic.
- The suite grew by one test method (17 Records tests now); full-suite count in
  section 13 is updated accordingly.

---

## 13. Local validation results

- `python3 -m unittest discover -s tests`: **491 tests, OK** (0 skipped), after
  the hardening task added one Records test method (490 before).
- `make test-mesen` (`MesenIntegrationTests`): **27 tests, OK**, including
  `test_records_preserve_fixed_layout_and_scaled_indexing`.
- `make validate` (test + benchmark + ROM): **OK**; `benchmark-report` generated
  and `build/minimal.nes` produced.
- Focused probes of untested code paths (empty record, 257-field record,
  whole-record comparison, forward enum field references, mutual recursion,
  nested comparisons with record temporaries, constant index > 255) all
  produced the expected diagnostics or correct assembly.

Note: `make validate` requires `PYTHON=python3` in this environment because the
Makefile defaults to `python`; CI is unaffected.

## 14. GitHub Actions run

Remote CI was not accessible from this environment (no `gh`/network). The
authoritative CI gate (`.github/workflows/ci.yml`: compiler job, Mesen job,
`ci-gate`) could not be re-verified remotely. Local evidence for the same jobs is
reported above; remote validation must be confirmed by a push/PR run.

## 15. Final ci-gate

Not verifiable remotely from this environment; local equivalent of every CI job
passed. This audit does not claim remote CI success. The milestone requirements
and the local evidence above are authoritative for this review.

---

## Recommendation

**READY WITH FOLLOW-UP HARDENING**

All eleven milestone 0.5.10 requirements are verified against concrete evidence
(implementation, tests, fixtures, golden, toolchain, Mesen, benchmark, docs).
The feature is layered across every compiler stage, has meaningful emulator
verification, and introduces no regression. No P0 or P1 findings exist. The
recommendation is driven by P2 test-coverage additions (empty/oversized record
layout diagnostics and whole-record comparison) and P3 documentation and
diagnostic polish, none of which block the milestone's acceptance criteria.