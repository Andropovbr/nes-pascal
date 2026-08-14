# Diagnostic Catalog and Error-Message Consistency Audit

- **Branch:** `audit/diagnostic-consistency`
- **Audit base:** `77b81a2` (head of `chore/documentation-navigation-cleanup`)
- **Audit date:** 2026-08-14
- **Auditor role:** independent QA reviewer (not the original implementer)

This is a cross-cutting consistency audit of the compiler diagnostic system:
catalog completeness, automated coverage, message quality, error precedence,
EN/PT-BR documentation parity, fixture hygiene, and source-location usefulness.

Scope constraints honored: **no compiler semantics, parser, semantic rules,
backend, memory layout, or runtime behavior were changed.** One mechanical
index correction and one new audit document are the only modifications.

---

## 1. Scope and method

The audit verified every diagnostic code against the following evidence:

- `nes_pascal/diagnostics.py` — `DiagnosticCode` enum and `DIAGNOSTIC_CATALOG`;
- every `DiagnosticCode` reference in `nes_pascal/*.py` (emit/raise sites,
  including helper functions such as `Lexer._error`, `Parser._error`,
  `SemanticAnalyzer._error`, `memory_layout._raise_error`,
  `metasprite_assets._error`, `cli.ToolchainError`, and the builtin-registry
  `count_code` parameters);
- `docs/DIAGNOSTICS.md` and `docs/pt-BR/DIAGNOSTICS.md` (machine-checked compat
  index);
- `docs/reference/diagnostics/*.md` and `docs/pt-BR/reference/diagnostics/*.md`
  (per-code detail pages and index);
- `tests/test_diagnostic_catalog.py`, `tests/test_diagnostic_precedence.py`;
- all fixtures in `tests/fixtures/diagnostics/`;
- focused diagnostic assertions across the full `tests/` tree;
- targeted probe compilation for precedence and message-quality checks.

Validation baseline: `make test` (529 tests, OK) and `make validate`
(`PYTHON=python3`; full suite + 21-benchmark corpus + `make rom`) both green
before any change.

---

## 2. Catalog completeness

| Metric | Result |
| --- | --- |
| Total codes in `DiagnosticCode` / `DIAGNOSTIC_CATALOG` | **118** |
| Codes defined but never emitted | **0** |
| Emitted codes missing from the catalog | **0** |
| Documented but nonexistent codes | **0** |
| Duplicate codes | **0** |
| Codes outside their category range | **0** |
| Codes missing from EN docs (`docs/DIAGNOSTICS.md` + reference index + detail pages) | **0** |
| Codes missing from PT-BR docs | **0** |

Every catalog code has at least one reachable emit/raise site. No raw `EXXXX`
string is constructed outside `diagnostics.py`; the only non-`CompilerError`
emissions are the driver-level `E5001`/`E5002`/`E6001` messages built by
`cli.py` (`ToolchainError`/`OSError` handlers), which still resolve through
`DiagnosticCode` members. `tests/test_diagnostic_catalog.py` (code uniqueness,
catalog/code identity, category ranges, `docs/DIAGNOSTICS.md` parity) passes.

### Catalog-vs-docs title mismatches (P3)

The machine catalog and the human-facing docs disagree on four titles. The
docs (index + category page, EN + PT-BR) are internally consistent; in each
case the `diagnostics.py` catalog title is the outlier.

| Code | Catalog title (`diagnostics.py`) | Docs title (index + category page) | Notes |
| --- | --- | --- | --- |
| E3015 | Runtime command inside callable | Runtime command inside procedure | **Fixed** in both indexes to "callable" / "rotina"; `semantic.md` heading already matched the catalog. |
| E4024 | Record layout overflow | Invalid record layout or indexed offset | Catalog title is narrower than the diagnostic's actual scope (empty record, >256-byte layout, and variable record-array indexed offset beyond `$FF`). Docs are more accurate. |
| E6011 | Metasprite metadata not found | Metasprite asset not found | Enum member is `METASPRITE_ASSET_NOT_FOUND`; docs use "asset". |
| E6012 | Metasprite metadata read failure | Metasprite asset read failure | Enum member is `METASPRITE_ASSET_READ_FAILURE`; docs use "asset". |

No catalog source change was made: `DIAGNOSTIC_CATALOG` titles are consumed
only by `test_diagnostic_catalog.py`, which checks codes and categories but
not titles, so aligning them is a docs-only decision that should be made with
the catalog author. Recommendation: update the catalog titles for E4024,
E6011, and E6012 to match the enum names and the documented scope.

---

## 3. Automated coverage matrix

Coverage strength per code, classifying each as:

- **Strong** — a focused test (fixture wired into a test, or an inline
  source case) asserts the exact diagnostic code, usually with message or
  location.
- **Partial** — asserted but only through a generic/indirect mechanism, or a
  code asserted via message without a stable code assertion.
- **Missing** — no automated protection found anywhere in the suite.
- **Not Applicable** — no such classification needed; every code is reachable
  and 112 of 118 have direct regression protection.

### Codes with **no** automated protection (Missing)

| Code | Trigger | Notes |
| --- | --- | --- |
| E1002 | `$` not followed by a hex digit | Lexer code path has no test; only the happy path (`$21`) and `E1000` are covered. |
| E3002 | a second `nes.run` statement | No test compiles `nes.run; nes.run;`. |
| E5001 | ca65/ld65 absent from `PATH` | CLI/toolchain driver path never exercised; `test_integration.py` skips without the tools. |
| E5002 | ca65/ld65 returns a nonzero status | No test mocks `subprocess`/tool failure. |
| E6001 | `OSError` while reading source / writing output | CLI `main()` error path never exercised. |
| E6012 | metasprite metadata file exists but is unreadable (`OSError`/`UnicodeError`) | Analogous CHR path (`E6003`) is covered in `test_assets.py` via `patch.object(Path, "read_bytes", ...)`; the metasprite path has no equivalent. |

### Codes whose coverage is meaningful but not a dedicated fixture (Partial)

- E3057 / E3058 — asserted by focused inline cases in `test_builtins.py`
  (`test_generic_argument_count_and_context_diagnostics_are_stable`), but the
  dedicated fixtures `invalid_builtin_context.nsp` and
  `invalid_builtin_argument_count.nsp` are **orphaned** (see section 6).
- E3017, E3010, E3012, E3016, E3017, and the function codes E3059–E3063,
  E4026 — asserted inline in `test_semantic.py`/`test_functions.py`; stable,
  but the fixtures that carry the same names are only partially reused.
- E3050 — asserted in `test_sprite_management.py` (inline capacity cases) and
  indirectly in `test_metasprites.py`; the `sprite_capacity_exhausted.nsp`
  fixture is used in the sprite-management suite.

### Codes with dedicated-fixture protection (Strong, non-exhaustive)

Metasprite codes (E3051–E3055, E4009) via
`test_metasprites.test_every_language_diagnostic_fixture_emits_only_its_expected_code`;
callback codes (E3018–E3025) via `test_callbacks.py`; records (E4019–E4025)
via `test_records.py`; enums (E4015–E4018) via `test_enumerations.py`; arrays
(E4010–E4014) via `test_arrays.py`; memory codes (E5003–E5007) via
`test_memory_layout.py`; and the precedence battery in
`test_diagnostic_precedence.py`.

**Conclusion:** 112 of 118 codes have direct regression protection. The six
Missing codes (E1002, E3002, E5001, E5002, E6001, E6012) are the audit's main
coverage gap.

---

## 4. Message quality

Messages are generally precise, include the offending identifier/literal/type,
and carry suggestion text. Cases worth reporting (nothing was rewritten):

| Finding | Severity | Detail |
| --- | --- | --- |
| Bare procedure name in an expression reports `E3005` "Unknown identifier" | P2 | `Value := Work;` (missing `()`) reports `Unknown identifier: Work` although `Work` is a declared procedure. The `E3062` path only triggers for `Work()`. The message is accurate for a value lookup but misleading because the name is declared. Already reported for functions as P3-4 in `milestone-0.5.12-audit.md`; the procedure analog was re-confirmed. |
| Function registered as a callback reports `E3018` "Unknown callback procedure" | P2 | `nes.on_update(F);` where `F` is a declared function reports `Unknown callback procedure: F`. Rejection is correct; the wording does not explain that functions cannot be callbacks. Already reported as P3-3 in `milestone-0.5.12-audit.md`. |
| `E3063` shadows call-site errors | P3 | A function with a partially undefined result plus a wrong call-site argument count or type reports `E3063` (body analysis precedes call validation) instead of `E3060`/`E4004`. Both are real errors; the call-site error is usually what the user is fixing. No precedence change was made during this audit. |
| `E3016`/`E3060` "expects 1 argument(s)" | P3 | Singular/plural rendering (`argument(s)`) is awkward for a count of 1. Consistent with the documented example output, so left unchanged. |
| `E3022` suggestion "…before `nes.run;`." | P3 | The suggestion text ends with a trailing `;.` (`nes.run;.`). Understandable but grammatically odd. |

---

## 5. Diagnostic precedence

The existing `test_diagnostic_precedence.py` battery covers: assignment type
errors (E4004) vs background-color requirement (E3003); literal-kind errors
(E4004) vs literal-range errors (E4002); uninitialized reads (E3008); runtime
placement errors (E3009/E3011/E3015); loop control (E3010/E3012); unknown
procedure (E3013); recursion (E3014); procedure argument count (E3016) vs
type (E4004); unsupported parameter type (E4005); and the "valid semantics do
not mask the final requirement" trio (E3003, E3001).

Probe-verified ordering (no changes made):

| Scenario | Winner | Assessment |
| --- | --- | --- |
| Procedure call with too many args and wrong arg types | E3016 (count) | Correct |
| Function call with too many args and wrong arg types | E3060 (count) | Correct |
| Function with undefined result **and** wrong call-site args/types | E3063 (body) | Shadows E3060/E4004; see section 4 |
| Array indexed by a `boolean` constant | E4011 (index type) | Correct |
| Array indexed by out-of-range constant | E4012 (bounds) | Correct |
| Scalar indexed | E4013 (usage) | Correct |
| Record field access on non-record | E4021 | Correct |
| Unknown field on a known record | E4020 | Correct |
| Enum compared with a `byte` operand | E4004 (operand types) before E4017 | Correct |
| Value builtin misused as a statement | E3057 (context) before count errors | Correct |
| Malformed `nes.metasprite_create()` with OAM exhausted | E3053 (args) before E3050 | Sensible |
| Valid metasprite creation with OAM exhausted | E3050 (capacity) | Correct |
| `if Counter then nes.run` (type error + runtime placement) | E4004 (condition type) before E3009 | Correct |
| `for` body modifies control variable and reads an unknown name | E3012 before E3005 | Sensible |
| Program-level final checks (E3003 background color, E3001 run, E3037 duplicate load) | Run after statement analysis | Correct |

**Precedence gap:** no regression test currently locks the "function with a
partially undefined result plus an invalid call site" ordering (E3063 before
E3060/E4004). If that ordering is intentional, a focused assertion should
document it; the only existing probe is manual.

---

## 6. Fixture hygiene

Inspected all 102 files in `tests/fixtures/diagnostics/`.

- **Orphan fixtures (2):** `invalid_builtin_context.nsp` and
  `invalid_builtin_argument_count.nsp` are not referenced by name in any test.
  The diagnostics they exercise (E3057, E3058) are asserted inline in
  `test_builtins.py`, so no coverage is lost, but the fixtures are dead files.
- **Asset-dependent metasprite fixtures:** `invalid_metasprite_import.nsp`,
  `duplicate_metasprite_import.nsp`, `invalid_metasprite_create.nsp`,
  `metasprite_argument_count.nsp`, `incompatible_metasprite_frame.nsp`,
  `invalid_metasprite_value.nsp`, and `invalid_metasprite_animation.nsp` all
  require a configured `--metasprite` asset. Compiled standalone they emit
  `E3051` ("asset not configured"), not the code their filenames imply. They
  are correctly wired with assets in `test_metasprites.py` /
  `test_sprite_animation.py`, so this is documentation precision, not a test
  defect. The docs trigger lines for E3053, E3054, E3056, and E4009 do not
  mention that the fixture requires asset configuration (E3052 and E3055 do).
- **Constrained-layout fixtures:** `user_ram_exhausted.nsp` and
  `temporary_ram_exhausted.nsp` produce no diagnostic at default settings; the
  docs and tests use them with a deliberately constrained internal layout.
  Documented and wired in `test_memory_layout.py`.
- **No duplicated fixtures** were found.
- **No fixture currently fails with a different code than its filename
  implies** when compiled in the way the corresponding test compiles it.

---

## 7. Source-location correctness

- Lexer (E1000/E1002), parser (E2101/E2102), and semantic diagnostics use
  precise line/column positions with correct source-line highlighting;
  verified against the caret assertions in `test_diagnostic_precedence.py`.
- E5003 (`USER_RAM_EXHAUSTED`) correctly uses the variable declaration
  position (`memory_layout.py` passes `variable.position`).
- **E5004** (`TEMPORARY_RAM_EXHAUSTED`) and **E5007**
  (`HARDWARE_STACK_CALL_DEPTH_EXHAUSTED`) emit at `1:1`. This is documented
  behavior; however, the position of the deepest expression (E5004) and the
  deepest call site (E5007) are not present in the
  `TemporaryRequirements` model, so a more precise location would require a
  model change (out of scope). Observation only.
- E5005/E5006 are internal-configuration diagnostics and correctly use `1:1`.
- E6011–E6018 (asset/metasprite driver diagnostics) emit at source `1:1`;
  JSON-internal detail is carried in the message, and E6013 includes the
  metadata line/column. Acceptable for driver-level errors.

---

## 8. EN/PT-BR parity

- `docs/DIAGNOSTICS.md` vs `docs/pt-BR/DIAGNOSTICS.md`: identical 118-code set
  (machine-verified by the catalog test).
- `docs/reference/diagnostics/index.md` vs PT-BR: identical 118 codes, links,
  and category labels.
- All six detail pages (lexical, syntax, semantic, type-system,
  code-generation, runtime-validation) in PT-BR have the same 118 headings as
  EN (verified by heading extraction).
- The PT-BR index mirrored the EN index's E3015 title inconsistency; both were
  corrected together (E3015 → "callable" / "rotina").
- No other EN/PT-BR divergence was found at the code, link, category, or
  heading level. Translation content itself was not rewritten.

---

## 9. Findings summary

| Severity | Count | Findings |
| --- | --- | --- |
| **P0** | 0 | No wrong code, compiler crash, or diagnostic corruption found. |
| **P1** | 0 | No important missing or misleading user-facing diagnostic behavior that requires a code change. |
| **P2** | 3 | (1) `E3005` for a bare procedure/function name in an expression is misleading ("Unknown identifier" for a declared name); (2) `E3018` for a function registered as a callback says "Unknown callback procedure" for a declared name; (3) missing regression protection for E1002, E3002, E5001, E5002, E6001, E6012 (six codes with zero automated coverage). |
| **P3** | 8 | (1) Catalog/doc title mismatches for E4024, E6011, E6012; (2) E3015 index inconsistency (fixed); (3) E3063 shadows E3060/E4004 — ordering undocumented; (4) orphan fixtures `invalid_builtin_context.nsp`, `invalid_builtin_argument_count.nsp`; (5) docs triggers for E3053/E3054/E3056/E4009 omit the required `--metasprite` configuration; (6) `E3016`/`E3060` "1 argument(s)" grammar; (7) `E3022` suggestion "before nes.run;." punctuation; (8) E5004/E5007 `1:1` positions lack model support for a more precise location. |

### Recommendation

The diagnostic system is structurally healthy: the catalog, category ranges,
documentation index, and PT-BR set are internally consistent and machine
checked; 112 of 118 codes have direct regression protection; and no P0/P1
defect exists. The backlog below is for follow-up hardening, not a gate.

**P2 backlog**
1. Add focused negative coverage for E1002 (lexer) and E3002 (duplicate
   `nes.run`).
2. Add CLI/driver-level tests for E5001 (missing toolchain), E5002 (tool
   failure), and E6001 (file access failure), e.g. by mocking
   `shutil.which`/`subprocess.run`/`Path`.
3. Add a metasprite read-failure test for E6012 (mirror the `E6003`
   `patch.object(Path, "read_bytes", ...)` pattern in `test_assets.py`).
4. Consider wording improvements for the E3005 bare-name path and the E3018
   function-as-callback path.

**P3 backlog**
1. Align catalog titles for E4024, E6011, E6012 with the enum names and the
   documented scope.
2. Wire or delete the two orphan builtin fixtures.
3. Update the E3053/E3054/E3056/E4009 docs triggers to mention required
   `--metasprite` configuration.
4. Add a precedence assertion documenting E3063-before-E3060/E4004 (or adjust
   if unintended).
5. Minor message polish (E3016/E3060 pluralization, E3022 suggestion
   punctuation).

---

## 10. Local validation results

- `python3 -m unittest tests.test_diagnostic_catalog tests.test_diagnostic_precedence`: **21 tests, OK**.
- `make test` (`PYTHON=python3`): **529 tests, OK** (0 failures, 0 skips).
- `make validate` (`PYTHON=python3`, `MESEN_PATH=/opt/mesen/Mesen`): **OK** —
  full suite, 21-benchmark corpus assembled/linked, `build/minimal.nes`
  produced.
- Independent precedence and message probes: 25+ scenarios compiled with
  expected codes and locations (see sections 4 and 5).
- Note: `make validate` requires `PYTHON=python3` in this environment because
  the Makefile defaults to `python`; CI is unaffected.

## 11. GitHub Actions run

Pushed `audit/diagnostic-consistency`. The authoritative CI pipeline
(`.github/workflows/ci.yml`) runs against the pushed branch:
`compiler-toolchain` (full unit suite + benchmark), `mesen-runtime`
(headless Mesen), and the aggregate `ci-gate` (fails unless both required jobs
succeed).

## 12. Final ci-gate

To be recorded after the pushed branch's CI completes (see the commit message
and the CI run for the final status). Local validation (section 10) is fully
green; the remote gate is the authoritative confirmation.

---

## Conclusion

The diagnostic catalog is consistent and complete at the code level, fully
documented in both languages, and protected by regression tests for 112 of 118
codes. No P0 or P1 defect exists. The remaining findings are documentation
polish and a focused set of missing regression tests for six low-traffic code
paths (E1002, E3002, E5001, E5002, E6001, E6012), none of which change
compiler semantics.
