# Semantic Test Coverage Map

English | [Português (Brasil)](../pt-BR/compiler/test-coverage-map.md)

This document provides a comprehensive semantic coverage map across all 28 implemented subsystems in NES Pascal. It catalogs the current automated test protection across compiler phases, diagnostics, static assembly goldens, toolchain builds, Mesen emulator runtime verification, benchmark corpus measurement, and documentation/examples.

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
| 17 | **CHR-ROM asset loading** | N/A | Strong | Strong | Strong | Strong | Missing | Strong | Missing | Missing | `--chr` validation (8 KiB exact) |
| 18 | **Nametable loading** | Strong | Strong | Strong | Strong | Strong | Missing | Strong | Strong | Missing | Full raw 1 KiB upload |
| 19 | **Runtime BG updates** | Strong | Strong | Strong | Strong | Strong | Missing | Strong | Strong | Strong | 4-write VBlank queue, tile shadow |
| 20 | **Palette management** | Strong | Strong | Strong | Strong | Strong | Missing | Strong | Strong | Strong | 32-byte shadow, VBlank uploader |
| 21 | **Scrolling & PPU state** | Strong | Strong | Strong | Strong | Strong | Missing | Strong | Strong | Missing | Scroll staging, latch restore |
| 22 | **Basic hardware sprites** | Strong | Strong | Strong | Strong | Strong | Missing | Strong | Strong | Strong | 64-entry OAM shadow, NMI DMA |
| 23 | **Sprite management** | Strong | Strong | Strong | Strong | Strong | Missing | Strong | Strong | Strong | Static 64-slot pool reservation |
| 24 | **Metasprites** | Strong | Strong | Strong | Strong | Strong | Missing | Strong | Strong | Strong | Anchor geometry, flipping, clipping |
| 25 | **Sprite animation** | Strong | Strong | Strong | Strong | Strong | Missing | Strong | Strong | Strong | Sequences, timers, frame advance |
| 26 | **Builtin infrastructure** | Strong | Strong | Strong | Strong | Strong | Partial | Strong | Strong | Strong | Unified registry & validation |
| 27 | **Low-risk codegen opts** | N/A | N/A | N/A | Strong | Strong | Strong | Strong | Strong | Strong | Direct operands, flag branching |
| 28 | **Arrays** | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Strong | Fixed 1D, indexed access, boundaries |

---

## 2. Answers to Canonical Audit Questions

### 1. Which implemented subsystems have no Mesen runtime coverage?
* **CHR-ROM Asset Loading (`--chr`):** Verified statically through binary comparison and ld65 segment inspection in `test_assets.py`, but has no active emulator script checking visual CHR pattern tile output.
* *Note on pure compile-time primitives:* Standalone `arithmetic.nsp`, `boolean_expressions.nsp`, and `conditionals.nsp` do not have dedicated individual `.lua` scripts; however, their runtime behavior is thoroughly asserted transitively by `verify_low_risk_codegen.lua`, `verify_arrays.lua`, and `verify_counting.lua`.

### 2. Which hardware-facing features rely only on static/golden tests?
* **CHR-ROM embedding:** Checked by file size validation, linker configuration generation, and raw binary ROM slicing, but without runtime PPU tile pattern assertions in Mesen.
* All other hardware-facing features (Palettes, Nametables, VBlank Updates, Scrolling, Hardware Sprites, Metasprites, Animation, Controllers, NMI Callbacks, Frame Synchronization) possess dedicated, headless Mesen Lua behavioral tests.

### 3. Which features have Mesen coverage but weak semantic/diagnostic coverage?
* **Scrolling and PPU State:** Possesses complete runtime verification (`verify_scrolling_ppu_state.lua`), but only a single negative diagnostic fixture (`invalid_set_scroll_argument_count.nsp`). Additional argument type checks are handled by general builtin validation.

### 4. Which compiler features have no dedicated benchmark representation?
* `chr_asset` (standalone CHR embedding)
* `scrolling_ppu_state` (scroll staging & mirroring)
* `nametable_loading` (raw startup nametable transfer)
* `slow_update_callback` (lag-frame coalescing)
* `frame_synchronization` (standalone loop synchronization)
* `zero_page` / `memory_layout` (pure layout benchmarks, although all benchmarks report memory layouts)

### 5. Which examples are not exercised by toolchain or runtime tests?
* **None.** Every single example program in `examples/` (`minimal.nsp`, `arithmetic.nsp`, `boolean_expressions.nsp`, `conditionals.nsp`, `loops.nsp`, `counting.nsp`, `procedures.nsp`, `procedure_parameters.nsp`, `controller_input.nsp`, `sprite_support.nsp`, `metasprite_player.nsp`, `sprite_animation.nsp`, `palette_support.nsp`, `background_updates.nsp`, `frame_callbacks.nsp`, `frame_synchronization.nsp`, `gameplay_full_stack.nsp`, `nametable_loading.nsp`, `scrolling_ppu_state.nsp`, `slow_update_callback.nsp`, `zero_page.nsp`, `memory_layout.nsp`, `metasprite_clipping.nsp`, `arrays.nsp`, `chr_asset.nsp`) is actively compiled, assembled, and validated in `tests/test_integration.py` and/or `tools/measure_benchmarks.py`.

### 6. Which goldens protect broad output but lack focused assertions?
* `tests/golden/minimal.asm`, `tests/golden/memory_layout.asm`, `tests/golden/zero_page.asm`, and `tests/golden/frame_synchronization.asm` capture complete generated assembly files.
* Subsystems such as Metasprites, Sprite Animation, Background Updates, Palettes, and Scrolling rely on focused structural backend regex tests and Mesen integration tests rather than whole-file golden files.

### 7. Which tests depend primarily on internal implementation shape rather than observable behavior?
* Certain regex assertions in `tests/test_backend.py` check specific assembly comment formatting or temporary symbol names (`expression_temporary_0`). Behavior-oriented tests in `test_backend_optimizations.py`, `test_arrays.py`, and `test_integration.py` appropriately assert observable instruction sequences, memory allocations, and hardware state.

### 8. Are there any test files whose responsibilities have become overly broad?
* `tests/test_integration.py` currently houses three distinct concerns:
  1. Toolchain Integration Tests (`ca65`/`ld65` build validation, ROM headers, CLI parameters)
  2. Golden Assembly Regression Tests (comparing 15 `.asm` fixtures)
  3. Mesen Runtime Integration Tests (orchestrating 24 headless Mesen test runs)
  While well-structured (~800 lines), maintaining separation will be important as future language releases expand runtime testing.

### 9. Are there obvious test-name/history inconsistencies worth cleaning later?
* `test_parses_all_milestone_three_variable_types` was identified and renamed to `test_parses_scalar_and_color_variable_types`.
* Visual clipping example (`examples/metasprite_clipping.nsp`) vs headless unit fixture (`tests/fixtures/runtime/metasprite_clipping.nsp`) serve distinct purposes (visual demo vs fast headless validation) and are now clearly documented.

---

## 3. Gap Analysis

### High Priority (P1)
1. **P1 — Add dedicated Mesen runtime test for standalone CHR-ROM pattern validation**:
   * *Subsystem:* CHR-ROM Asset Loading (`--chr`)
   * *Missing Layer:* Mesen Runtime Emulation
   * *Why it matters:* CHR data integrity is verified at ROM binary level, but runtime verification of PPU pattern table visibility (`$0000-$1FFF`) ensures emulator compatibility.
   * *Suggested Test:* Mesen Lua script reading PPU pattern table memory after reset.
   * *Scope:* Small (1 Lua verification script + integration test method).

2. **P1 — Expand negative diagnostic fixtures for `nes.set_scroll` argument types**:
   * *Subsystem:* Scrolling & PPU State
   * *Missing Layer:* Diagnostic fixtures
   * *Why it matters:* Rejection of invalid types (e.g. `boolean` passed to `nes.set_scroll`) should be covered by a focused negative fixture in `tests/fixtures/diagnostics/`.
   * *Scope:* Small (1 negative `.nsp` fixture + diagnostic test assertion).

### Medium Priority (P2)
1. **P2 — Add focused Golden Assembly fixtures for hardware subsystems**:
   * *Subsystems:* Metasprites, Sprite Animation, Palettes, Background Updates, Scrolling
   * *Missing Layer:* Golden Assembly
   * *Why it matters:* While protected by backend regex tests and Mesen runtime checks, focused golden snippets prevent unexpected assembly emitter regressions.
   * *Scope:* Medium (5 focused `.asm` goldens).

2. **P2 — Include `scrolling_ppu_state` in benchmark corpus**:
   * *Subsystem:* Scrolling & PPU State
   * *Missing Layer:* Benchmark / Resource Measurement
   * *Why it matters:* Measures static cycle and PRG footprint impact of scroll staging and PPU restoration.
   * *Scope:* Small (Add entry to `tools/measure_benchmarks.py`).

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

* `[P1]` Add Mesen PPU pattern validation test for CHR-ROM loading (`verify_chr_asset.lua`).
* `[P1]` Add focused negative diagnostic fixture for invalid `nes.set_scroll` argument types.
* `[P2]` Add focused golden assembly fixtures for hardware runtime routines (palettes, background queue, metasprite renderer).
* `[P2]` Add `scrolling_ppu_state` benchmark spec to `tools/measure_benchmarks.py`.
* `[P2]` Separate `tests/test_integration.py` into `test_toolchain.py`, `test_goldens.py`, and `test_mesen.py`.
* `[P3]` Clean up legacy test naming and docstring conventions.
