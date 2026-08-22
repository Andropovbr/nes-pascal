# Semantic Test Coverage Map

English | [Português (Brasil)](../pt-BR/compiler/test-coverage-map.md)

This document provides a comprehensive semantic coverage map across all 32 implemented subsystems in NES Pascal. It catalogs the current automated test protection across compiler phases, diagnostics, static assembly goldens, toolchain builds, Mesen emulator runtime verification, benchmark corpus measurement, and documentation/examples.

---

## 1. Subsystem Coverage Matrix

The matrix uses semantic verification tiers:
* **Strong:** Extensive dedicated unit/integration assertions and negative/boundary coverage.
* **Partial:** Tested indirectly or with basic checks, but lacks dedicated boundary/scenario coverage.
* **Missing:** No direct automated verification in this tier.
* **N/A:** Not applicable to the subsystem's architectural role.

| # | Subsystem | Lexer / Parser | Semantic Analysis | Diagnostics & Fixtures | Memory Layout | Backend ASM | Golden ASM | Toolchain (ca65/ld65) | Mesen Runtime | Benchmark Corpus | Notes |
| :- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| 1 | **Variables & scalar types** | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Strong | `byte`, `boolean`, `nes_color` |
| 2 | **Constants (`const`)** | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Inline immediate values |
| 3 | **Arithmetic (+, -)** | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Strong | 8-bit wrap, unary/binary |
| 4 | **Relational comparisons** | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Direct flag branching |
| 5 | **Boolean expressions** | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Strong | `not`, `and`, `or`, short-circuit |
| 6 | **Conditionals (`if`/`else`)** | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Nested branches |
| 7 | **Loops (`while`, `repeat`)** | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Condition-controlled |
| 8 | **Counting & loop control** | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Strong | `for`, `inc`, `dec`, `break`, `continue` |
| 9 | **Procedures** | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Parameterless, acyclic calls |
| 10 | **Procedure parameters** | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Strong | `byte`/`boolean` value params |
| 11 | **Definite assignment** | N/A | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Rejection of uninitialized reads |
| 12 | **Zero Page allocation** | N/A | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Promotion threshold & fallback |
| 13 | **Runtime memory layout** | N/A | N/A | Strong | Strong | Strong | Strong | Strong | Strong | Strong | 2 KiB physical reconciliation |
| 14 | **NMI & frame sync** | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Strong | `nes.wait_frame`, frame counter |
| 15 | **Frame callbacks** | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Strong | `nes.on_update`, `nes.on_vblank` |
| 16 | **Controller input** | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Dual-port polling, button queries |
| 17 | **CHR-ROM asset loading** | N/A | Strong | Strong | Strong | Strong | Missing | Strong | Strong | Missing | `--chr` validation (8 KiB exact) |
| 18 | **Nametable loading** | Strong | Strong | Strong | Strong | Strong | Missing | Strong | Strong | Missing | Full raw 1 KiB upload |
| 19 | **Runtime BG updates** | Strong | Strong | Strong | Strong | Strong | **Strong** | Strong | Strong | Strong | 4-write VBlank queue, tile shadow; golden: queue traversal, PPU write, cancel-lock, shadow confirm |
| 20 | **Palette management** | Strong | Strong | Strong | Strong | Strong | **Strong** | Strong | Strong | Strong | 32-byte shadow, VBlank uploader; golden: dirty-flag loop, triplet PPU write, $3F/$2006 latch |
| 21 | **Scrolling & PPU state** | Strong | Strong | **Strong** | Strong | Strong | Missing | Strong | Strong | Strong | Scroll staging, latch restore; type fixtures for both arg positions |
| 22 | **Basic hardware sprites** | Strong | Strong | Strong | Strong | Strong | Missing | Strong | Strong | Strong | 64-entry OAM shadow, NMI DMA |
| 23 | **Sprite management** | Strong | Strong | Strong | Strong | Strong | Missing | Strong | Strong | Strong | Static 64-slot pool reservation |
| 24 | **Metasprites** | Strong | Strong | Strong | Strong | Strong | **Strong** | Strong | Strong | Strong | Anchor geometry, flipping, clipping; golden: renderer loop, OAM shadow writes, inline DMA |
| 25 | **Sprite animation** | Strong | Strong | Strong | Strong | Strong | Missing | Strong | Strong | Strong | Sequences, timers, frame advance |
| 26 | **Builtin infrastructure** | Strong | Strong | Strong | Strong | Strong | Partial | Strong | Strong | Strong | Unified registry & validation |
| 27 | **Low-risk codegen opts** | N/A | N/A | N/A | Strong | Strong | Strong | Strong | Strong | Strong | Direct operands, flag branching |
| 28 | **Arrays** | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Fixed 1D, indexed access, boundaries |
| 29 | **Records** | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Nominal fixed layouts, typed fields, record arrays |
| 30 | **Expression temporary allocation** | N/A | N/A | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Scoped maximum-live pool, cache separation, exhaustion |
| 31 | **Functions** | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Typed returns, definite result, acyclic nested calls, call-safe temporaries |
| 32 | **Collision helpers** | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Half-open AABB, sprite/metasprite bounds, packed immutable map, wrap-safe edges |

---

## 2. Answers to Canonical Audit Questions

### 1. Which implemented subsystems have no Mesen runtime coverage?
* **CHR-ROM Asset Loading (`--chr`) — ✅ Resolved (P1):** `verify_chr_asset.lua` now reads all 8 192 PPU pattern-table bytes (`$0000–$1FFF`) via `emu.read(..., emu.memType.nesPpuDebug)` and asserts the complete deterministic pattern from `chr_asset.chr`, including the unique terminal marker (`$0A`) at offset `$1FFF`.
* *Note on pure compile-time primitives:* Standalone `arithmetic.nsp`, `boolean_expressions.nsp`, and `conditionals.nsp` do not have dedicated individual `.lua` scripts; however, their runtime behavior is thoroughly asserted transitively by `verify_low_risk_codegen.lua`, `verify_arrays.lua`, and `verify_counting.lua`.

### 2. Which hardware-facing features rely only on static/golden tests?
* **CHR-ROM embedding — ✅ Resolved (P1):** In addition to binary ROM validation, `verify_chr_asset.lua` now asserts the correct CHR pattern in the emulated PPU pattern table at runtime.
* All other hardware-facing features (Palettes, Nametables, VBlank Updates, Scrolling, Hardware Sprites, Metasprites, Animation, Collision Helpers, Controllers, NMI Callbacks, Frame Synchronization) possess dedicated, headless Mesen Lua behavioral tests.

### 3. Which features have Mesen coverage but weak semantic/diagnostic coverage?
* **Scrolling and PPU State — ✅ Resolved (P1):** Two dedicated negative fixtures (`invalid_set_scroll_x_type.nsp`, `invalid_set_scroll_y_type.nsp`) now explicitly assert that passing a `boolean` to the `x` or `y` argument of `nes.set_scroll` raises `E4004` (type mismatch) and that `E3046` (argument count) does not take precedence.

### 4. Which compiler features have no dedicated benchmark representation?
* `chr_asset` (standalone CHR embedding)
* `scrolling_ppu_state` (scroll staging & mirroring)
* `nametable_loading` (raw startup nametable transfer)
* `slow_update_callback` (lag-frame coalescing)
* `frame_synchronization` (standalone loop synchronization)
* `zero_page` / `memory_layout` (pure layout benchmarks, although all benchmarks report memory layouts)

### 5. Which examples are not exercised by toolchain or runtime tests?
* **None.** Every single example program in `examples/` (`minimal.nsp`, `arithmetic.nsp`, `boolean_expressions.nsp`, `conditionals.nsp`, `loops.nsp`, `counting.nsp`, `procedures.nsp`, `procedure_parameters.nsp`, `controller_input.nsp`, `sprite_support.nsp`, `metasprite_player.nsp`, `sprite_animation.nsp`, `palette_support.nsp`, `background_updates.nsp`, `frame_callbacks.nsp`, `frame_synchronization.nsp`, `gameplay_full_stack.nsp`, `nametable_loading.nsp`, `scrolling_ppu_state.nsp`, `slow_update_callback.nsp`, `zero_page.nsp`, `memory_layout.nsp`, `metasprite_clipping.nsp`, `arrays.nsp`, `enumerations.nsp`, `records.nsp`, `functions.nsp`, `chr_asset.nsp`, `collision_rectangles.nsp`, `collision_background.nsp`, `collision_helpers.nsp`) is actively compiled, assembled, and validated in `tests/test_integration.py` and/or `tools/measure_benchmarks.py`.

### 6. Which goldens protect broad output but lack focused assertions?
* `tests/golden/minimal.asm`, `tests/golden/memory_layout.asm`, `tests/golden/zero_page.asm`, and `tests/golden/frame_synchronization.asm` capture complete generated assembly files.
* Subsystems such as Metasprites, Sprite Animation, Background Updates, Palettes, and Scrolling rely on focused structural backend regex tests and Mesen integration tests rather than whole-file golden files.

### 7. Which tests depend primarily on internal implementation shape rather than observable behavior?
* Certain regex assertions in `tests/test_backend.py` check specific assembly comment formatting or temporary symbol names (`expression_temporary_0`). Behavior-oriented tests in `test_backend_optimizations.py`, `test_arrays.py`, `test_records.py`, and `test_integration.py` appropriately assert observable instruction sequences, memory allocations, and hardware state.

### 8. Are there any test files whose responsibilities have become overly broad?
* `tests/test_integration.py` currently houses three distinct concerns:
  1. Toolchain Integration Tests (`ca65`/`ld65` build validation, ROM headers, CLI parameters)
  2. Golden Assembly Regression Tests (comparing 15 `.asm` fixtures)
  3. Mesen Runtime Integration Tests (orchestrating 30 headless Mesen runs,
     including the dedicated collision-helper ROM)
  While well-structured (~800 lines), maintaining separation will be important as future language releases expand runtime testing.

### 9. Are there obvious test-name/history inconsistencies worth cleaning later?
* `test_parses_all_milestone_three_variable_types` was identified and renamed to `test_parses_scalar_and_color_variable_types`.
* Visual clipping example (`examples/metasprite_clipping.nsp`) vs headless unit fixture (`tests/fixtures/runtime/metasprite_clipping.nsp`) serve distinct purposes (visual demo vs fast headless validation) and are now clearly documented.

---

## 3. Gap Analysis

### High Priority (P1) — All Resolved
1. **✅ P1 — CHR-ROM Mesen runtime pattern table validation** *(resolved)*:
   * *Subsystem:* CHR-ROM Asset Loading (`--chr`)
   * *Added:* `tests/mesen/verify_chr_asset.lua` — reads all 8 192 PPU pattern-table bytes (`$0000–$1FFF`) via `emu.memType.nesPpuDebug` and verifies the deterministic pattern from `examples/assets/chr_asset.chr`, including the unique terminal byte `$0A` at `$1FFF`.
   * *Integrated:* `MesenIntegrationTests.test_chr_asset_is_visible_in_ppu_pattern_tables` in `tests/test_integration.py`.
   * *Matrix update:* Subsystem 17 — Mesen Runtime tier: **Missing → Strong**.

2. **✅ P1 — Focused negative diagnostic fixtures for `nes.set_scroll` argument types** *(resolved)*:
   * *Subsystem:* Scrolling & PPU State
   * *Added:* `tests/fixtures/diagnostics/invalid_set_scroll_x_type.nsp` and `invalid_set_scroll_y_type.nsp`.
   * *Added tests:* `test_boolean_x_argument_fixture_emits_type_diagnostic_not_argument_count` and `test_boolean_y_argument_fixture_emits_type_diagnostic_not_argument_count` in `tests/test_scrolling_ppu_state.py`, each asserting `E4004` and confirming `E3046` does not take precedence.
   * *Matrix update:* Subsystem 21 — Diagnostics tier: annotation updated to note both argument positions are now covered.

### Medium Priority (P2)
1. **✅ P2 — Add focused Golden Assembly fixtures for hardware subsystems** *(resolved for palettes, background updates, metasprites)*:
   * *Subsystems covered:* Palettes (subsystem 20), Runtime BG Updates (subsystem 19), Metasprites (subsystem 24).
   * *Golden files added:*
     - `tests/golden/palette_support.asm` — full-file golden for `examples/palette_support.nsp`; protects `runtime_upload_queued_palettes` dirty-flag loop, `runtime_upload_palette_triplet` PPU write sequence ($3F/$2006 latch, 3-byte shadow loop), NMI callsite order.
     - `tests/golden/background_updates.asm` — full-file golden from the stable `BackgroundUpdates` test fixture; protects `runtime_upload_queued_background` cancel-lock guard, 4-slot loop, PPU `$2006`/`$2007` writes, shadow confirmation, `runtime_queue_background_write` slot-find, overflow flag, atomic publication.
     - `tests/golden/metasprite_player.asm` — full-file golden for `examples/metasprite_player.nsp`; protects `runtime_metasprite_render` component iteration, OAM shadow writes, anchor arithmetic, clip checks, flip encoding, inline OAM DMA (`sta $4014`) in NMI, frame geometry tables.
   * *Tests added:* `test_palette_support_program_matches_golden_assembly`, `test_background_updates_program_matches_golden_assembly`, `test_metasprite_player_program_matches_golden_assembly` in `tests/test_backend.py::BackendGoldenTests`.
   * *Intentionally not frozen:* Sprite Animation (subsystem 25) and Scrolling (subsystem 21) golden assembly — their runtime paths are fully exercised by the existing Mesen integration tests and there is no current evidence that a golden snapshot would add non-redundant regression protection beyond what the Mesen and benchmark tests already provide. These remain as documented future-backlog items.
   * *Matrix updates:* Subsystems 19, 20, 24 — Golden Assembly tier: **Missing → Strong**.

2. **✅ P2 — Include `scrolling_ppu_state` in benchmark corpus** *(resolved)*:
   * *Subsystem:* Scrolling & PPU State
   * *Added:* `BenchmarkSpec("scrolling_ppu_state", "Scrolling and PPU State", "examples/scrolling_ppu_state.nsp")` in `tools/measure_benchmarks.py`.
   * *Focused test:* `ScrollingBenchmarkTests.test_scrolling_ppu_state_benchmark_reports_focused_resource_accounting` in `tests/test_scrolling_ppu_state.py` asserts stable PRG, instruction count, cycle estimate, ZP/RAM accounting, and runtime feature set.
   * *Matrix update:* Subsystem 21 — Benchmark Corpus tier: **Missing → Strong**.

3. **P2 — Split `tests/test_integration.py` into focused test suites**:
   * *Subsystem:* Test Infrastructure
   * *Missing Layer:* Test Architecture
   * *Why it matters:* Separates toolchain integration, golden comparisons, and Mesen runtime orchestration into clean modules (`test_toolchain.py`, `test_goldens.py`, `test_mesen_runtime.py`).
   * *Scope:* Medium (Non-functional test refactoring).

### Low Priority (P3)
1. **P3 — Normalize test docstrings and naming across legacy parser tests**:
   * *Subsystem:* Parser / Lexer Tests
   * *Missing Layer:* Test Maintenance
   * *Why it matters:* Ensures uniform docstrings across early test suites.
   * *Scope:* Small.

---

## 4. Prioritized Follow-up Backlog

* `[P1 ✅]` ~~Add Mesen PPU pattern validation test for CHR-ROM loading (`verify_chr_asset.lua`).~~ **Resolved** — `tests/mesen/verify_chr_asset.lua` validates all 8 192 PPU pattern-table bytes at runtime.
* `[P1 ✅]` ~~Add focused negative diagnostic fixture for invalid `nes.set_scroll` argument types.~~ **Resolved** — `invalid_set_scroll_x_type.nsp` and `invalid_set_scroll_y_type.nsp` fixtures with test assertions for `E4004` in both argument positions.
* `[P2 ✅]` ~~Add `scrolling_ppu_state` benchmark spec to `tools/measure_benchmarks.py`.~~ **Resolved** — `scrolling_ppu_state` is now in the benchmark corpus with a dedicated focused resource-accounting regression test.
* `[P2 ✅]` ~~Add focused golden assembly fixtures for hardware runtime routines (palettes, background queue, metasprite renderer).~~ **Resolved** — `tests/golden/palette_support.asm`, `tests/golden/background_updates.asm`, and `tests/golden/metasprite_player.asm` added with three focused `BackendGoldenTests` in `tests/test_backend.py`.
* `[P2]` Separate `tests/test_integration.py` into `test_toolchain.py`, `test_goldens.py`, and `test_mesen.py`.
* `[P3]` Clean up legacy test naming and docstring conventions.
