# Examples and Executable Documentation Audit

- **Branch:** `audit/examples-and-executable-docs`
- **Audit base:** `902856a` (head of `origin/main`)
- **Audit date:** 2026-08-14
- **Auditor role:** independent QA reviewer (not the original implementer)

This is a cross-cutting audit of the `examples/` corpus and the executable
claims carried by the documentation: example inventory, buildability,
language and NES/runtime feature coverage, doc-snippet classification, and
documentation-vs-implementation consistency for everything the docs present
as compilable or runnable.

Scope constraints honored: **no compiler semantics, parser, semantic rules,
backend, memory layout, runtime behavior, example, or test was changed.** The
modifications are this new audit document and a mechanical navigation fix that
adds the missing `gameplay_full_stack.nsp` entry to the building-and-running
example list (EN and PT-BR).

---

## 1. Scope and method

The audit covered:

- every source file in `examples/` (28 programs) and every bundled asset in
  `examples/assets/`;
- the canonical documentation under `docs/` (getting-started, language,
  runtime, reference, compiler) and `docs/pt-BR/`;
- the toolchain integration tests, Mesen runtime tests, golden Assembly
  fixtures, benchmark corpus, and CLI asset options that exercise examples;
- the `Makefile` validation targets and the GitHub Actions pipeline.

Verification performed:

1. Every positive example was compiled, assembled, and linked to a complete
   NROM image with `compile_source`, using the same `--chr`/`--nametable`/
   `--metasprite`/`--mirroring` options the tests and docs use.
2. Every `examples/*.nsp` reference in the docs was checked against the
   corpus, including asset files.
3. Pascal code fences across `docs/` were classified as complete programs,
   program-header fragments, partial-runnable illustrations, or
   expected-invalid diagnostic triggers, and the complete programs were
   compiled.
4. Documentation claims about compiler behavior were cross-checked against
   generated Assembly and runtime symbol output.
5. Local validation: full unit suite, Mesen runtime suite, and benchmark
   corpus.

Validation baseline: `python3 -m unittest discover -s tests` (**537 tests,
OK**), `MesenIntegrationTests` (**29 tests, OK**), `tools/measure_benchmarks.py`
(**21-benchmark corpus, OK**), and `make validate PYTHON=python3` (**OK**) are
all green before any change.

---

## 2. Example inventory

All 28 examples compile, assemble, and link into a valid 40,976-byte NROM
image (16-byte header, 32 KiB PRG, 8 KiB CHR, mapper 0). The rows below list
the asset options each program requires.

| Example | Language area | Asset options | Lines |
| --- | --- | --- | --- |
| `minimal` | minimal runtime | none | 17 |
| `arithmetic` | unary/binary byte arithmetic | none | 17 |
| `boolean_expressions` | comparisons, `and`/`or`/`not` | none | 29 |
| `conditionals` | `if`/`else` nesting | none | 27 |
| `loops` | `while`/`repeat`, `break`/`continue` | none | 32 |
| `counting` | `for`, `inc`/`dec`, wrap | none | 43 |
| `arrays` | fixed arrays, Boolean elements | none | 33 |
| `enumerations` | nominal game state, exact-type rules | none | 26 |
| `records` | fixed layouts, record arrays | none | 36 |
| `procedures` | forward resolution, nested calls | none | 44 |
| `procedure_parameters` | value params, argument copies | none | 35 |
| `functions` | typed returns, accumulator ABI | none | 34 |
| `memory_layout` | globals, params, expressions, for-loop cache | none | 39 |
| `zero_page` | ZP temporaries, promotion, fallback | none | 18 |
| `frame_synchronization` | NMI wait loop | none | 19 |
| `frame_callbacks` | `nes.on_update`/`nes.on_vblank` | none | 29 |
| `slow_update_callback` | pending-frame coalescing | none | 27 |
| `controller_input` | controller 1, sprite-0 staging | `--chr assets/game.chr` | 95 |
| `sprite_support` | OAM-shadow sprite API | `--chr assets/chr_asset.chr` | 19 |
| `metasprite_player` | metasprite movement, facing, bounds | `--chr assets/game.chr --metasprite assets/player_idle.json` | 76 |
| `metasprite_clipping` | edge clipping without coordinate wrap | `--chr assets/game.chr --metasprite assets/player_idle.json` | 123 |
| `sprite_animation` | consolidated animation manifest | `--chr assets/game.chr --metasprite assets/player_consolidated.json` | 83 |
| `chr_asset` | raw 8 KiB CHR-ROM asset | `--chr assets/chr_asset.chr` | 6 |
| `palette_support` | palette shadow + VBlank upload | `--chr assets/chr_asset.chr` | 19 |
| `nametable_loading` | raw 1 KiB nametable | `--chr assets/chr_asset.chr --nametable assets/nametable_loading.nam` | 8 |
| `background_updates` | tile/attribute writes, overflow | `--chr assets/chr_asset.chr --nametable assets/nametable_loading.nam` | 50 |
| `scrolling_ppu_state` | scroll pairs, mirroring | none (default `horizontal`; `--mirroring vertical` also valid) | 10 |
| `gameplay_full_stack` | combined RAM/background/metasprite pressure | `--chr assets/game.chr --nametable assets/nametable_loading.nam --metasprite assets/player_consolidated.json` | 85 |

Bundled assets (`examples/assets/`): `chr_asset.chr`, `game.chr`,
`nametable_loading.nam`, `player_idle.json`, `player_consolidated.json`.

---

## 3. Automated coverage matrix

Coverage is classified per example across the layers that exercise it:

- **Toolchain** — compiled+linked in `tests/test_integration.py`
  (`_assert_valid_nrom_image` or a dedicated `compile_source` build test);
- **Mesen** — executed headless in `tests/mesen/*.lua` via
  `MesenIntegrationTests`;
- **Golden** — full-file Assembly fixture in `tests/golden/*.asm`;
- **Benchmark** — measured in `tools/measure_benchmarks.py`.

| Example | Toolchain | Mesen | Golden | Benchmark |
| --- | :---: | :---: | :---: | :---: |
| `minimal` | ✅ | — | ✅ | ✅ |
| `arithmetic` | ✅ | —* | ✅ | ✅ |
| `boolean_expressions` | ✅ | —* | ✅ | ✅ |
| `conditionals` | ✅ | —* | ✅ | ✅ |
| `loops` | ✅ | ✅ | ✅ | ✅ |
| `counting` | ✅ | ✅ | ✅ | ✅ |
| `arrays` | ✅ | ✅ | ⚠ (fixture) | ✅ |
| `enumerations` | ✅ | ✅ | ✅ | ✅ |
| `records` | ✅ | ✅ | ✅ | ✅ |
| `procedures` | ✅ | ✅ | ✅ | ✅ |
| `procedure_parameters` | ✅ | ✅ | ✅ | ✅ |
| `functions` | ✅ | ✅ | ⚠ (fixture) | ✅ |
| `memory_layout` | ✅ | ✅ | ✅ | — |
| `zero_page` | ✅ | ✅ | ✅ | — |
| `frame_synchronization` | ✅ | ✅ | ✅ | — |
| `frame_callbacks` | ✅ | ✅ | ✅ | ✅ |
| `slow_update_callback` | ✅ | ✅ | — | — |
| `controller_input` | ✅ | ✅ | ✅ | ✅ |
| `sprite_support` | ✅ | ✅ | — | ✅ |
| `metasprite_player` | ✅† | ✅ | ✅ | ✅ |
| `metasprite_clipping` | ✅† | ✅ (2 scripts) | — | — |
| `sprite_animation` | ✅† | ✅ (2 scripts) | — | ✅ |
| `chr_asset` | ✅ | ✅ | — | — |
| `palette_support` | ✅ | ✅ | ✅ | ✅ |
| `nametable_loading` | ✅ | ✅ | — | — |
| `background_updates` | ✅ | ✅ | ✅ | ✅ |
| `scrolling_ppu_state` | ✅† | ✅ | — | ✅ |
| `gameplay_full_stack` | ✅ | — | — | ✅ |

\* `arithmetic`, `boolean_expressions`, and `conditionals` have no dedicated
`verify_*.lua` script; their runtime behavior is asserted transitively by
`verify_low_risk_codegen.lua`, `verify_arrays.lua`, and `verify_counting.lua`
(also documented in `test-coverage-map.md`, section 2, answer 1).

† `metasprite_player`, `metasprite_clipping`, `sprite_animation`, and
`scrolling_ppu_state` are exercised by Mesen scripts rather than
`_assert_valid_nrom_image`; they are still compiled and linked in the Mesen
tests, so all 28 examples are built somewhere.

`arrays` and `functions` use fixture-derived goldens
(`arrays-addressing.asm`, `functions_abi.asm`, `functions_temporary_pressure.asm`)
rather than a golden of the example itself.

**Mesen coverage gap (P3):** `gameplay_full_stack` is compiled, linked, and
benchmarked, but has no headless runtime script. Its individual subsystems
(background, metasprite animation, controller, palettes) each have runtime
coverage, so the gap is aggregate-pressure-only and low risk.

**Benchmark corpus gap (P3, already documented):** `chr_asset`,
`frame_synchronization`, `memory_layout`, `metasprite_clipping`,
`nametable_loading`, `slow_update_callback`, and `zero_page` are not in the
21-program benchmark corpus (see `test-coverage-map.md`, section 2, answer 4).

---

## 4. Documentation references to examples

Every example is referenced by at least one durable doc. No example is
orphaned. Reference counts (durable docs only, excluding historical milestone
audits):

| Example | Durable doc references |
| --- | --- |
| `minimal` | 12 |
| `functions` | 10 |
| `controller_input` | 8 |
| `counting` | 8 |
| `metasprite_player` | 8 |
| `sprite_animation` | 8 |
| `arithmetic` | 6 |
| `background_updates` | 6 |
| `boolean_expressions` | 6 |
| `conditionals` | 6 |
| `loops` | 6 |
| `memory_layout` | 6 |
| `nametable_loading` | 6 |
| `palette_support` | 6 |
| `procedure_parameters` | 6 |
| `procedures` | 6 |
| `records` | 6 |
| `sprite_support` | 6 |
| `arrays` | 4 |
| `chr_asset` | 4 |
| `enumerations` | 4 |
| `frame_callbacks` | 4 |
| `frame_synchronization` | 4 |
| `gameplay_full_stack` | 4 (compiler-section docs) |
| `metasprite_clipping` | 4 |
| `scrolling_ppu_state` | 4 |
| `slow_update_callback` | 4 |
| `zero_page` | 4 |

All relative doc links to examples and assets resolve (verified for EN and
PT-BR, including `../../../examples/...` paths from `docs/pt-BR/compiler/`).

---

## 5. Doc-snippet classification

176 Pascal code fences exist across `docs/`. Classification:

| Class | Count | Meaning |
| --- | ---: | --- |
| Fragment | 162 | Partial/illustrative code, not runnable standalone |
| Partial-runnable | 8 | Has `begin`/`end.` and `nes.run` but no `program` header or full declarations |
| Complete program | 4 | Full `program` headers; compilable |
| Program-header-only | 2 | Only a `program` header (diagnostic trigger context) |

The four complete programs are `docs/getting-started/first-program.md` and
`docs/language/program-structure.md` plus their two PT-BR mirrors. Both
distinct programs compile successfully with `compile_source`.

The eight partial-runnable snippets (background-loading, frame-callbacks,
procedures, and the semantic diagnostic guide, each in EN and PT-BR) are
intentional fragments that illustrate a body inside a larger program. None is
presented as a standalone buildable file; this is normal reference-doc
practice and not a defect.

---

## 6. Documentation-vs-implementation cross-check

The following doc claims were verified against actual compiler output:

| Claim | Source | Verdict |
| --- | --- | --- |
| Parameterless function calls with no arguments | `language/functions.md` | ✅ compiles; correct `jsr` |
| Nested function calls evaluate innermost-first | `language/functions.md` | ✅ `RightCall()` runs before `LeftCall()` in generated ASM |
| `nes_color` range and sprite constant types | `language/types.md` | ✅ exact-type and range rules verified |
| Enumerations require exact-type comparisons | `language/enumerations.md` | ✅ compiles; `E4004` for byte compare |
| Fixed-layout records and array-of-records addressing | `language/records.md` | ✅ compiles; scaled indexing in ASM |
| Arithmetic wrap and operator precedence | `language/expressions.md` | ✅ compiles; evaluation order verified |
| `inc`/`dec` wrap at `$00`/`$FF` | `language/increment-and-decrement.md` | ✅ compiles; endpoint behavior via counting example |
| `for` `downto`, exact endpoints | `language/loops.md` | ✅ compiles |
| `if`/`else` without dangling-else ambiguity | `language/conditionals.md` | ✅ compiles |
| Boolean short-circuit and `$00`/`$01` materialization | `language/expressions.md` | ✅ verified in generated ASM |
| `nes.wait_frame` NMI synchronization | `runtime/wait-frame.md` | ✅ runtime-verified (frame-synchronization example) |
| ZP promotion threshold and regular-RAM fallback | `runtime/cpu-memory.md` | ✅ promotion/fallback map behavior verified |
| Expression-temporary reservation and cache separation | `runtime/cpu-memory.md`, `compiler/expression-temporaries-0.5.11.md` | ✅ 0 reserved / 0 caches for simple programs; 1-byte cache for loop programs |

### Mismatches found (P2)

1. **`cpu-memory.md` memory-map excerpt is stale (P2).** The doc (lines
   191–208) presented a map excerpt for the `zero_page` "focused example" that
   showed a `Compiler caches` row of 1 byte at `$0010`, `Runtime data` of 0
   bytes at `$0200`, and the user variable at `$0200` with 1535 free bytes,
   and stated the example prints `Other compiler caches: 1 byte`. The current
   compiler emits, for `zero_page.nsp`:

   ```text
   $0010  $001F    16  Free      Recovered temporary Zero Page
   $0080  $00FF   128  User      Automatic Zero Page variables (2 used, 126 available)
   $0200  $0203     4  Runtime   Runtime data
   $0204  $0204     1  User      Regular user variables
   $0205  $07FF  1531  Free      General free RAM
   ```

   `Expression temporary reservation: 0 bytes` and `Other compiler caches: 0
   bytes` are printed for this example. The 1-byte cache and `$0011-$001F` free
   recovery appear only in the `memory_layout` example, and even there the
   runtime-data row is 4 bytes at `$0200-$0203`. The excerpt was therefore a
   blend that matched neither example. **Resolved by
   `chore/examples-docs-p2-hardening`:** `docs/runtime/cpu-memory.md` and its
   PT-BR mirror now present the regions table regenerated from the real
   `examples/zero_page.nsp` output, including the runtime-data row at
   `$0200-$0203`, the correct `0`-byte cache and `0`-byte temporary rows, the
   `$0205-$07FF` free region, and the matching
   `Expression temporary reservation: 0 bytes (maximum simultaneously live)` /
   `Other compiler caches: 0 bytes` lines. The prose now states the output
   comes from `examples/zero_page.nsp`.

2. **`game.nsp` and `assets/screen.tiles`/`assets/screen.attributes` do not
   exist (P2).** Three durable docs referenced a program and assets that are
   not in the repository:

   - `docs/getting-started/building-and-running.md:163` —
     `python -m nes_pascal.cli game.nsp -o build/game.nes --nametable-tiles assets/screen.tiles --nametable-attributes assets/screen.attributes`;
   - `docs/runtime/background-loading.md:37` — the same split-asset command;
   - `docs/runtime/scrolling-and-ppu-state.md:41` —
     `python -m nes_pascal.cli game.nsp -o build/game.nes --mirroring vertical`;
   - PT-BR mirrors at `docs/pt-BR/runtime/background-loading.md:37`,
     `docs/pt-BR/runtime/scrolling-and-ppu-state.md:43`, and
     `docs/pt-BR/getting-started/building-and-running.md:176`.

   There is no `examples/game.nsp`, no `assets/screen.tiles`, and no
   `assets/screen.attributes` anywhere in the repository (verified by
   filesystem search and git history). The `--nametable-tiles`/
   `--nametable-attributes` split options and `--mirroring vertical` are real
   and validated (the split form is tested at `tests/test_integration.py`
   `test_split_nametable_assets_build_as_one_complete_asset` and was probe
   compiled), but the commands shown could not be run as written.

   **Resolved by `chore/examples-docs-p2-hardening`:** the mirroring command
   in `docs/runtime/scrolling-and-ppu-state.md` (EN and PT-BR) now uses the
   real `examples/scrolling_ppu_state.nsp` program with `--mirroring vertical`
   and was probe-compiled. The split-asset commands in
   `docs/getting-started/building-and-running.md` and
   `docs/runtime/background-loading.md` (EN and PT-BR) were rewritten as
   clearly-marked illustrative placeholder commands (no real `.tiles`/
   `.attributes` assets exist in the repository, so none were invented), while
   the bundled `examples/nametable_loading.nsp` combined `--nametable`
   example remains the executable reference and the split options remain
   documented separately. The placeholder split command was probe-compiled
   with real derived assets to confirm the CLI form works.

3. **`gameplay_full_stack` is missing from the example command list (P3).**
   `docs/getting-started/building-and-running.md` lists every other example in
   its build command block and its description list, but not
   `gameplay_full_stack.nsp`. The example compiles, is in the benchmark
   corpus, and is the only full-stack (combined subsystem) example. **Fixed
   as part of this audit:** the command block and description list (EN and
   PT-BR) now include `gameplay_full_stack.nsp` with the flags used by its
   build and benchmark tests; the added command was probe-compiled
   successfully.

### Mismatches checked and confirmed correct

Earlier apparent mismatches (`nes.set_sprite_position`,
`nes.set_sprite_palette`) were audit-source errors, not doc defects: the
correct sprite API is `nes.sprite_set_position` / `nes.sprite_set_palette`,
and `nes.set_sprite_palette` with an out-of-range argument correctly emits
`E3034`. Doc claims were verified with the correct API names.

---

## 7. Diagnostic claims in executable docs

The documentation presents several expected-invalid examples as triggers for
specific diagnostics. These were probe-compiled and all matched their
documented codes and source locations:

- `E4002` (literals) at the documented column,
- `E4005` (unsupported parameter type) at the parameter position,
- `E4008`, `E4009`, `E4014`, `E4017` (arrays/enums) with documented contexts,
- `E3012` (loop control variable) with documented context,
- `E3057` (value builtin used as a statement) at the statement position,
- runtime-validation diagnostics `E6004`, `E6005`, `E6009`, `E6010` for
  CHR-size, background-asset, and mirroring misconfiguration.

No diagnostic doc example produced a different code than documented.

---

## 8. Navigation

- `docs/runtime/index.md` links every runtime page; `docs/language/index.md`
  links every language page.
- `docs/index.md` links all language pages and a curated runtime subset, and
  links the runtime index itself, so the 9 runtime pages not listed directly
  on the home page (background-loading, background-updates, cpu-memory,
  palettes, run, scrolling-and-ppu-state, set-background-color,
  vblank-cycle-budget, wait-frame) are still reachable in one click. Not a
  defect; the runtime index is the canonical listing.
- No broken internal doc links were found.

---

## 9. Quality and redundancy review

- The three metasprite examples are complementary, not redundant:
  `metasprite_player` demonstrates eight-direction movement, facing, and
  gameplay bounds; `metasprite_clipping` demonstrates partial clipping at each
  edge without coordinate wrap; `sprite_animation` demonstrates the
  consolidated manifest and animation timing. Each is a distinct runtime
  behavior and each has dedicated Mesen coverage.
- `memory_layout` and `zero_page` are intentionally distinct focused layout
  examples (cached-loop layout vs. promotion/fallback), both Mesen-verified.
- All examples are small (6–123 lines), focused, and serve as regression
  inputs for the tests they back.
- No example is stale or duplicated; no example was removed or modified.

---

## 10. Findings summary

| Severity | Count | Findings |
| --- | --- | --- |
| **P0** | 0 | No example fails to build; no doc presents a non-compiling complete program. |
| **P1** | 0 | No broken example, broken complete-program snippet, or runtime-defeating doc claim found. |
| **P2** | 2 | (1) `cpu-memory.md` memory-map excerpt was stale (did not match either focused example) — **resolved** by `chore/examples-docs-p2-hardening` (regenerated from real `zero_page` output, EN and PT-BR); (2) three docs referenced nonexistent `game.nsp` and `assets/screen.tiles`/`assets/screen.attributes` — **resolved** (mirroring now uses `scrolling_ppu_state.nsp`; split-asset commands are clearly-marked illustrative placeholders; EN and PT-BR). |
| **P3** | 2 | (1) `gameplay_full_stack` was missing from the building-and-running example list — **resolved** (EN and PT-BR updated); (2) `gameplay_full_stack` has no headless Mesen runtime script (aggregate-pressure only; subsystems covered individually). |

**No P0, P1, or P2 findings remain.** All three documentation findings
reported by this audit (two P2, one P3) have been resolved by
`chore/examples-docs-p2-hardening`; the only outstanding item is the P3
optional full-stack runtime script.

### Recommendations

**P2 backlog**
1. ~~Regenerate the `cpu-memory.md` map excerpt from real output (either
   `zero_page` or `memory_layout`), including the runtime-data row and the
   correct cache/free accounting.~~ **Resolved** by `chore/examples-docs-p2-hardening`
   using `examples/zero_page.nsp`.
2. ~~Fix the three `game.nsp` command examples to use real programs and assets.~~
   **Resolved** by `chore/examples-docs-p2-hardening`: mirroring uses
   `scrolling_ppu_state.nsp`; split-asset commands are clearly-marked
   illustrative placeholders (no `.tiles`/`.attributes` assets exist), with
   the combined `--nametable` example remaining executable.

**P3 backlog**
1. Optionally add a headless Mesen script for `gameplay_full_stack` that
   asserts the combined runtime state, for aggregate-pressure runtime
   protection.

---

## 11. Local validation results

- `python3 -m unittest discover -s tests`: **537 tests, OK**.
- `python3 -m unittest tests.test_integration.MesenIntegrationTests`:
  **29 tests, OK**.
- `python3 tools/measure_benchmarks.py`: **OK** (21-benchmark corpus).
- `make validate PYTHON=python3`: **OK** (test-all + benchmark + `make rom`).
- Independent probe compiles: 28/28 examples → valid NROM; 5 positive
  doc-snippet programs compiled; 15 diagnostic-trigger probes emitted the
  documented codes; split-asset and `--mirroring vertical` commands probe
  compiled.
- Note: `make validate` requires `PYTHON=python3` in this environment because
  the Makefile defaults to `python`; CI is unaffected.

## 12. GitHub Actions run

Pushed `audit/examples-and-executable-docs`. The authoritative CI pipeline
(`.github/workflows/ci.yml`) runs against the pushed branch:
`compiler-toolchain` (full unit suite + benchmark), `mesen-runtime`
(headless Mesen), and the aggregate `ci-gate` (fails unless both required jobs
succeed).

## 13. Final ci-gate

The pushed branch's CI run is triggered by the push. Per project policy this
audit does not claim remote CI success from this environment; the aggregate
`ci-gate` on the pushed branch is the authoritative confirmation.

**Follow-up hardening (`chore/examples-docs-p2-hardening`):** both P2 findings
and the P3 example-listing gap are resolved on a dedicated branch (see
sections 6 and 10). The follow-up branch runs the full `make test` and
`make validate` (`PYTHON=python3`) suites plus probe compiles of every changed
command, and verifies the final `ci-gate` on the authoritative pipeline before
merging.

---

## Conclusion

The example corpus is healthy: all 28 programs build to valid NROM images, all
28 are compiled by tests or Mesen, 23 have dedicated runtime scripts, and
every example is referenced in the documentation. The documentation carries no
non-compiling complete program. The audit originally reported two P2
documentation defects — a stale memory-map excerpt and three commands
referencing nonexistent files — plus a P3 example-listing gap. All three were
resolved by the follow-up branch `chore/examples-docs-p2-hardening`: the
memory-map excerpt now matches real `zero_page` output, the mirroring command
uses `scrolling_ppu_state.nsp`, and the split-asset commands are truthful
illustrative placeholders. **No P0, P1, or P2 findings remain.** The only
outstanding item is the optional P3 full-stack runtime script. No compiler,
example, or test changes were made.