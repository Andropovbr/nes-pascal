# Milestone 0.5.5: Compiler Architecture and Code Generation Audit

> Historical baseline: milestone 0.5.11 replaced the fixed AST-depth model
> identified here with exact maximum-live scoped allocation. See
> [Expression Temporary Allocation (0.5.11)](expression-temporaries-0.5.11.md).

English | [Português (Brasil)](../pt-BR/compiler/optimization-audit-0.5.5.md)

This document establishes the official architecture, code generation, and resource consumption baseline for the **NES Pascal** compiler as of milestone **0.5.5**.

It evaluates the compiler's current state, measures generated 6502 code across an expanded 16-benchmark suite, analyzes technical debt and architectural risks, assesses optimization opportunities, reconciles the NMI/VBlank cycle budget with runtime specifications, and defines a prioritized sequence of follow-up milestones.

---

## 1. Executive Summary

NES Pascal has reached a maturity level where compiled programs execute as realistic, multi-system arcade games on the NES (exercising controller input, frame callbacks, OAM DMA, metasprites, pivot flipping, clipping, sprite animation, and background updates).

### Key Audit Conclusions

1. **Deterministic and Working Pipeline:**
   The compiler pipeline (Lexer -> Parser -> AST -> Semantic Analysis -> Memory Layout -> ca65 Backend -> ld65 Linker) is stable, deterministic, and passes all 408 automated tests (including 21 Mesen emulator behavioral integration tests).

2. **Builtin / Intrinsic Scalability Is the Immediate Priority:**
   The current compiler uses 21 dedicated AST node families (~40 individual AST/ResolvedAST classes) to model `nes.*` hardware routines. With upcoming releases adding APU audio, music, SFX, collisions, timers, HUD, and a standard library, continuing this pattern will cause rapidly increasing cross-phase boilerplate replicated across 5 compiler modules. A unified `BuiltinCall` / `ResolvedBuiltinCall` registry is a **critical prerequisite before Release 0.6 (Audio)**.

3. **Expression Temporary Allocation Is a Correctness Prerequisite for Functions:**
   Expression temporaries are currently allocated by static AST depth (`expression_temporary_{depth}`) with an unconditional 16-byte reservation in Zero Page. Across all 16 benchmarks, the actual maximum number of simultaneously live expression temporaries is **at most 2**. Evaluating nested function calls inside expressions (`Foo(A + Bar(B + C))`) will alias and corrupt outer expression temporaries under the current depth-reset scheme. Scoped compile-time temporary pooling is an essential **correctness prerequisite before Functions**.

4. **Cumulative RAM Pressure Is Dominated by Feature-Conditional Shadows:**
   The newly added full-stack gameplay benchmark (`gameplay_full_stack`) combines animated metasprites, controller polling, OAM DMA, and background tile updates. Compiler/runtime/user storage allocates or reserves **1,293 bytes** (~63.1%) of the 2,048-byte physical RAM: 33 bytes in Zero Page, 1,004 bytes in regular runtime/user RAM, and a 256-byte OAM shadow. Including the 256-byte hardware stack page and 99 bytes unavailable under the current Zero Page policy, **1,648 bytes** (~80.5%) of CPU address space are committed or reserved, leaving 400 bytes visible to the allocator. The 960-byte tile shadow dominates regular runtime/user RAM (95.6%) but remains strictly feature-conditional and is omitted for write-only background updates.

5. **Code Generation Inefficiencies Are Dominated by Four Measured Patterns:**
   - **Constant Immediates in Temporaries:** Binary arithmetic (`+`, `-`) and comparisons (`=`, `<`, etc.) unconditionally store right-hand operands into Zero Page temporaries even when the operand is a compile-time immediate `#$XX` or a direct memory variable.
   - **Boolean Value Materialization:** Conditions in `if`, `while`, `repeat`, and `for` materialize Boolean results as `$00` or `$01` in the accumulator, perform a redundant `CMP #$00`, and then branch, instead of branching directly on processor status flags (`BEQ`, `BNE`, `BCC`, `BCS`). In `gameplay_full_stack`, this accounts for **28 Boolean materializations** and **11 redundant `CMP #$00`** instructions.
   - **Redundant `CMP #$00`:** Instructions like `LDA`, `TAX`, `INX`, `DEX`, `AND`, `ORA`, and `EOR` already set CPU Zero (`Z`) and Negative (`N`) flags, making trailing zero tests redundant.
   - **RAM Staging in Calling Conventions:** Internal runtime routines pass arguments via fixed RAM scratch locations (`runtime_metasprite_offset_x`, `runtime_sprite_value`) where CPU registers (`A`, `X`, `Y`) could carry 2–3 parameters directly.

6. **NMI / VBlank Budget Reconciled with Explicit Safety Margins:**
   Theoretical NTSC VBlank provides 2,273 CPU cycles. The combined worst-case runtime NMI work (OAM DMA + all 25 palette bytes dirty + 4 confirmed tile writes + scroll commit + latch restore) consumes **~1,779 CPU cycles** (~78.3% of VBlank). The remaining **~494 cycles** before safety margin yields a **recommended safe user callback budget of ~250–300 CPU cycles** in worst-case frames, and **~1,200–1,400 cycles** in typical frames.

7. **Linear 6502 IR Is Medium Migration Risk; Heavy IRs Are Premature:**
   The 6502 architecture (8-bit, 3 registers, 256-byte Zero Page) does not benefit from complex graph-coloring register allocators or multi-level SSA IRs. A lightweight **Linear 6502 IR** with structured instructions and basic peephole passes provides high ROI, but its backend migration represents a **Medium risk** that should follow an incremental 4-phase migration strategy.

---

## 2. Compiler Pipeline Today

```text
Source Code (.nsp)
       |
       v
  [ lexer.py ]           --> Tokens
       |
       v
  [ parser.py ]          --> Untyped AST (ast.py)
       |
       v
 [ semantic.py ]         --> Scope resolution, strict typing, definite assignment
       |
       v
[ memory_layout.py ]     --> Feature detection, Zero Page promotion, ld65 .cfg, CPU .map
       |
       v
[ backend_ca65.py ]      --> Assembly code generation (list[str]), iNES header, runtime routines
       |
       v
  [ ca65 & ld65 ]        --> Assembled object (.o) and final ROM (.nes)
```

---

## 3. Benchmark Corpus

The audit evaluated 16 deterministic programs representing specific compiler subsystems, isolated feature workloads, and a combined full-stack gameplay scenario:

| Benchmark | Source File | Primary Characteristics |
| :--- | :--- | :--- |
| `minimal` | [`examples/minimal.nsp`](../../examples/minimal.nsp) | Minimal runtime baseline, PPU color, `nes.run` |
| `arithmetic` | [`examples/arithmetic.nsp`](../../examples/arithmetic.nsp) | Unary negation, binary addition/subtraction, 8-bit wraparound |
| `boolean_expressions` | [`examples/boolean_expressions.nsp`](../../examples/boolean_expressions.nsp) | Equality, relational comparisons, `not`, `and`, `or` |
| `conditionals` | [`examples/conditionals.nsp`](../../examples/conditionals.nsp) | `if`/`else` branches, nested conditionals |
| `loops` | [`examples/loops.nsp`](../../examples/loops.nsp) | `while`, `repeat`/`until`, `break`, `continue` |
| `counting` | [`examples/counting.nsp`](../../examples/counting.nsp) | `inc`, `dec`, ascending/descending `for` loops |
| `procedures` | [`examples/procedures.nsp`](../../examples/procedures.nsp) | Parameterless procedures, acyclic calls |
| `procedure_parameters` | [`examples/procedure_parameters.nsp`](../../examples/procedure_parameters.nsp) | `byte` and `boolean` value parameters in procedure RAM slots |
| `controller_input` | [`examples/controller_input.nsp`](../../examples/controller_input.nsp) | Dual controller polling, `down`/`pressed`/`released` state, sprite 0 |
| `sprite_support` | [`examples/sprite_support.nsp`](../../examples/sprite_support.nsp) | 64-entry OAM shadow, positioning, palettes, flipping, visibility |
| `metasprite_player` | [`examples/metasprite_player.nsp`](../../examples/metasprite_player.nsp) | Multi-component metasprite positioning, flipping, manual frames |
| `sprite_animation` | [`examples/sprite_animation.nsp`](../../examples/sprite_animation.nsp) | Animated player: timer, looping/one-shot, frame advancement, facing |
| `palette_support` | [`examples/palette_support.nsp`](../../examples/palette_support.nsp) | Full 32-byte palette updates, VBlank palette queue |
| `background_updates` | [`examples/background_updates.nsp`](../../examples/background_updates.nsp) | VBlank tile/attribute update queue, 960-byte tile shadow |
| `frame_callbacks` | [`examples/frame_callbacks.nsp`](../../examples/frame_callbacks.nsp) | Deterministic main-thread update loop and NMI synchronization |
| `gameplay_full_stack` | [`examples/gameplay_full_stack.nsp`](../../examples/gameplay_full_stack.nsp) | **Combined full-stack benchmark**: animated metasprite, controller input, OAM DMA, background updates, tile shadow read, user state |

---

## 4. Measurement Methodology

Measurements are collected deterministically using [`tools/measure_benchmarks.py`](../../tools/measure_benchmarks.py):
1. **PRG-ROM Occupied Bytes:** Extracted directly from `ld65` link map segment tables (`CODE` + `VECTORS`), distinguishing actual byte footprint from the 32 KiB padded NROM image.
2. **CPU RAM Accounting:** Extracted from the compiler's deterministic `ProgramMemoryLayout` and `.map` symbol tables. Measurements separately report compiler/runtime/user allocation, compiler-policy reservation, hardware stack reservation, and allocator-visible free Zero Page and regular RAM. An arithmetic invariant verifies that committed/reserved and allocator-visible bytes reconcile to the NES's 2,048-byte physical RAM.
3. **Expression Tree Depth:** Calculated as the maximum height of operator subtrees (0 for leaf literals/variables).
4. **Max Live Expression Temporaries:** Calculated based on the compiler's right-first recursive lowering order. Indicates the maximum number of `expression_temporary_X` bytes simultaneously required at any single evaluation point (0 = no temporaries used; 1 = only `temp_0`; 2 = `temp_0` and `temp_1` simultaneously live).
5. **Assembly Pattern Frequency:** Parsed from generated `.asm` files using regex matchers to count redundant stores, boolean materializations, redundant comparisons, and roundtrips.
6. **Cycle Estimates:** Calculated using standard Ricoh 2A03 instruction cycle tables accounting for addressing modes, branch penalties, and DMA overhead.

---

## 5. Baseline Resource Results

### CPU RAM Accounting

`ZP Alloc./Reserved` combines used runtime symbols, the fixed 16-byte compiler
temporary reservation, and promoted user variables. `ZP Temp Required` reports
the temporary symbols actually generated. `ZP Policy Reserved` covers address
space unavailable by compiler policy but not consumed by the program. The
hardware stack column reserves its address page; it does not claim that all 256
bytes contain live stack data.

| Benchmark | ZP Alloc./Reserved | ZP Temp Required | Regular Runtime/User | OAM Shadow | Non-ZP Allocated | Stack Reserved | ZP Policy Reserved | Regular Allocator Free | ZP Allocator Free | Total Allocator Free | Compiler/Runtime/User Alloc./Reserved | Total Committed/Reserved |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `minimal` | 25 B | 0 B | 7 B | 0 B | 7 B | 256 B | 103 B | 1,529 B | 128 B | 1,657 B | 32 B | 391 B |
| `arithmetic` | 25 B | 2 B | 7 B | 0 B | 7 B | 256 B | 103 B | 1,529 B | 128 B | 1,657 B | 32 B | 391 B |
| `boolean_expressions` | 26 B | 1 B | 12 B | 0 B | 12 B | 256 B | 103 B | 1,524 B | 127 B | 1,651 B | 38 B | 397 B |
| `conditionals` | 27 B | 1 B | 5 B | 0 B | 5 B | 256 B | 103 B | 1,531 B | 126 B | 1,657 B | 32 B | 391 B |
| `loops` | 28 B | 1 B | 4 B | 0 B | 4 B | 256 B | 103 B | 1,532 B | 125 B | 1,657 B | 32 B | 391 B |
| `counting` | 28 B | 7 B | 9 B | 0 B | 9 B | 256 B | 103 B | 1,527 B | 125 B | 1,652 B | 37 B | 396 B |
| `procedures` | 28 B | 1 B | 4 B | 0 B | 4 B | 256 B | 103 B | 1,532 B | 125 B | 1,657 B | 32 B | 391 B |
| `procedure_parameters` | 27 B | 1 B | 11 B | 0 B | 11 B | 256 B | 103 B | 1,525 B | 126 B | 1,651 B | 38 B | 397 B |
| `controller_input` | 30 B | 1 B | 9 B | 256 B | 265 B | 256 B | 103 B | 1,271 B | 123 B | 1,394 B | 295 B | 654 B |
| `sprite_support` | 26 B | 0 B | 70 B | 256 B | 326 B | 256 B | 103 B | 1,210 B | 127 B | 1,337 B | 352 B | 711 B |
| `metasprite_player` | 34 B | 1 B | 16 B | 256 B | 272 B | 256 B | 99 B | 1,264 B | 123 B | 1,387 B | 306 B | 661 B |
| `sprite_animation` | 34 B | 1 B | 20 B | 256 B | 276 B | 256 B | 99 B | 1,260 B | 123 B | 1,383 B | 310 B | 665 B |
| `palette_support` | 25 B | 0 B | 50 B | 256 B | 306 B | 256 B | 103 B | 1,230 B | 128 B | 1,358 B | 331 B | 690 B |
| `background_updates` | 25 B | 0 B | 995 B | 0 B | 995 B | 256 B | 103 B | 541 B | 128 B | 669 B | 1,020 B | 1,379 B |
| `frame_callbacks` | 25 B | 0 B | 6 B | 0 B | 6 B | 256 B | 103 B | 1,530 B | 128 B | 1,658 B | 31 B | 390 B |
| `gameplay_full_stack` | 33 B | 1 B | 1,004 B | 256 B | 1,260 B | 256 B | 99 B | 276 B | 124 B | 400 B | 1,293 B | 1,648 B |

### Code and Expression Footprint

| Benchmark | Category | PRG Code | PRG Occupied | Tree Depth | Max Live Temps | Instructions |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `minimal` | Minimal Runtime | 239 B | 245 B | 0 | 0 | 108 |
| `arithmetic` | Arithmetic | 259 B | 265 B | 3 | 2 | 119 |
| `boolean_expressions` | Boolean Expressions | 416 B | 422 B | 2 | 1 | 187 |
| `conditionals` | Conditionals | 303 B | 309 B | 1 | 1 | 138 |
| `loops` | Loops (while/repeat) | 404 B | 410 B | 1 | 1 | 187 |
| `counting` | Counting & for-loops | 533 B | 539 B | 2 | 2 | 237 |
| `procedures` | Procedures | 330 B | 336 B | 2 | 2 | 153 |
| `procedure_parameters` | Procedure Parameters | 366 B | 372 B | 2 | 1 | 163 |
| `controller_input` | Controller Input | 889 B | 895 B | 1 | 1 | 404 |
| `sprite_support` | Individual Sprites | 583 B | 589 B | 0 | 0 | 273 |
| `metasprite_player` | Metasprites | 1,437 B | 1,443 B | 1 | 1 | 551 |
| `sprite_animation` | Sprite Animation | 2,007 B | 2,013 B | 1 | 1 | 675 |
| `palette_support` | Palettes | 812 B | 818 B | 0 | 0 | 342 |
| `background_updates` | Background Updates | 2,166 B | 2,172 B | 1 | 1 | 522 |
| `frame_callbacks` | Frame Callbacks | 272 B | 278 B | 0 | 0 | 124 |
| `gameplay_full_stack` | Full-Stack Gameplay | 3,478 B | 3,484 B | 1 | 1 | 874 |

---

## 6. Generated Assembly Findings & Inefficient Patterns

### Pattern Frequency Across Benchmarks

| Benchmark | Redundant Temp Stores | Boolean Materializations ($00/$01) | Redundant `CMP #$00` | `STA`->`LDA` Roundtrips | Total Instructions |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `minimal` | 0 | 1 | 0 | 0 | 108 |
| `arithmetic` | 2 | 0 | 0 | 0 | 119 |
| `boolean_expressions` | 6 | 18 | 5 | 0 | 187 |
| `conditionals` | 2 | 4 | 2 | 1 | 138 |
| `loops` | 8 | 10 | 5 | 0 | 187 |
| `counting` | 3 | 6 | 3 | 0 | 237 |
| `procedures` | 2 | 6 | 3 | 0 | 153 |
| `procedure_parameters` | 2 | 5 | 4 | 1 | 163 |
| `controller_input` | 8 | 29 | 18 | 0 | 404 |
| `sprite_support` | 0 | 3 | 0 | 0 | 273 |
| `metasprite_player` | 4 | 28 | 14 | 2 | 551 |
| `sprite_animation` | 4 | 31 | 13 | 1 | 675 |
| `palette_support` | 0 | 0 | 0 | 0 | 342 |
| `background_updates` | 0 | 0 | 0 | 1 | 522 |
| `frame_callbacks` | 0 | 0 | 0 | 0 | 124 |
| `gameplay_full_stack` | 4 | 28 | 11 | 0 | 874 |

### Recurring Inefficiencies Detailed

#### 1. Intermediate Storage of Immediate Constants and Variables
* **Source:** `Counter := Counter + $01;` or `if Counter > $10 then`
* **Generated Assembly Today:**
  ```asm
  lda #$01
  sta expression_temporary_0
  lda variable_Counter
  clc
  adc expression_temporary_0
  ```
* **Optimal Direct Assembly:**
  ```asm
  lda variable_Counter
  clc
  adc #$01
  ```
* **Impact:** Adds 2 instructions (5 bytes, 5 cycles) per simple binary operation.
* **Fix Location:** Backend expression lowering ([`backend_ca65.py`](../../nes_pascal/backend_ca65.py)).

#### 2. Boolean Materialization Before Branching
* **Source:** `if Counter <= Limit then`
* **Generated Assembly Today:**
  ```asm
      lda #$10
      sta expression_temporary_0
      lda variable_Counter
      cmp expression_temporary_0
      bcc @comparison_true_0
      beq @comparison_true_0
  @comparison_false_1:
      lda #$00              ; false
      jmp @comparison_end_2
  @comparison_true_0:
      lda #$01              ; true
  @comparison_end_2:
      cmp #$00
      bne @if_then_3
      jmp @if_else_5
  ```
* **Optimal Direct Assembly:**
  ```asm
      lda variable_Counter
      cmp variable_Limit
      beq @if_then_3
      bcc @if_then_3
      jmp @if_else_5
  ```
* **Critical Distinction:** When a Boolean is consumed strictly as control flow (`if`, `while`, `repeat`), branching directly on CPU flags is optimal. When a Boolean is stored as a first-class value (`Flag := A < B;`), materializing canonical `$00` / `$01` bytes remains strictly necessary.
* **Impact:** Eliminates ~7 instructions (~14 bytes, ~16 cycles) per conditional branch.
* **Fix Location:** Backend condition lowering ([`backend_ca65.py`](../../nes_pascal/backend_ca65.py)).

#### 3. Redundant `CMP #$00`
* **Source:** Variable loads or boolean operations followed by zero tests.
* **Observation:** `LDA`, `TAX`, `INX`, `DEX`, `AND`, `ORA`, and `EOR` already set the Zero (`Z`) and Negative (`N`) flags on 6502.
* **Impact:** Eliminates 2 bytes and 2 cycles per test.
* **Fix Location:** Backend lowering or peephole optimization pass.

---

## 7. Expression and Temporary Allocation Findings

### Expression Tree Depth vs. Live Temporaries
- `Max Expression Tree Depth` reflects AST height.
- `Max Live Expression Temporaries` reflects the actual peak memory requirement of simultaneously live temporaries during lowering.
- **Measured Result:** Across all 16 benchmarks, the peak simultaneous temporary requirement is **at most 2** (`temp_0` and `temp_1`).
- **Static Reservation:** [`memory_layout.py`](../../nes_pascal/memory_layout.py#L112) unconditionally allocates 16 Zero Page bytes (`$0010`–`$001F`) for every program, wasting 14 to 16 bytes of scarce Zero Page space in simple programs.

### Correctness Risk: Nested Function Calls
Consider the future expression:
```pascal
Result := CalculateDamage(Base + GetModifier(EnemyType));
```
- Outer expression `Base + ...` stores `Base` into `expression_temporary_0`.
- Evaluating the argument `GetModifier(...)` enters a new expression scope.
- If the inner expression resets depth to 0, it will overwrite `expression_temporary_0`.
- When `GetModifier` returns, the outer addition resumes with corrupted operand data.

### Conclusion and Recommendations
- **Arrays (Milestone 0.5.8):** Indexed expressions (`Arr[Index + $01] := Val + $02`) increase temporary pressure but do not introduce arbitrary call nesting.
- **Functions:** Scoped compile-time temporary pooling / liveness is a **hard correctness prerequisite before Functions**.
- **Recommendation:** Separate temporary allocation into its own prerequisite milestone prior to Functions.

---

## 8. RAM Footprint Breakdown & Full-Stack Pressure

### Full-Stack Gameplay Benchmark (`gameplay_full_stack`)
The benchmark's compiler/runtime/user footprint is **1,293 bytes**: 33 bytes
allocated or reserved in Zero Page, 1,004 bytes of regular runtime/user data,
and the 256-byte OAM shadow. The memory policy also keeps 99 Zero Page bytes
unavailable to the allocator, and the hardware reserves `$0100-$01FF` for the
6502 stack. The stack figure describes address-space reservation, not 256 bytes
of live stack contents.

```text
$0000-$000C  Zero Page runtime symbols                         13 B allocated
$000D-$000F  Unused fixed runtime partition                     3 B policy-reserved
$0010-$0010  Generated expression temporary                     1 B required
$0011-$001F  Unused fixed temporary reservation                15 B compiler-reserved
$0020-$007F  Future explicit Zero Page                         96 B policy-reserved
$0080-$0083  Promoted user variables                            4 B allocated
$0084-$00FF  Automatic-promotion capacity                     124 B allocator-visible free

$0100-$01FF  6502 hardware stack page                         256 B hardware-reserved
$0200-$02FF  OAM shadow                                       256 B allocated

$0300-$030F  Metasprite and animation state                    16 B allocated
$0310-$0313  PPUCTRL, PPUMASK, and scroll shadows               4 B allocated
$0314-$06D3  Background tile shadow                           960 B allocated
$06D4-$06E9  Background VBlank queue and helper state          22 B allocated
$06EA-$06EB  Regular user variables                             2 B allocated
$06EC-$07FF  General regular RAM                              276 B allocator-visible free
```

The reconciled aggregates are:

| Accounting category | Bytes | Meaning |
| :--- | ---: | :--- |
| Zero Page allocated/reserved by the benchmark | 33 | 13 runtime-symbol bytes + 16 compiler temporary bytes + 4 promoted user bytes |
| Regular runtime/user allocated | 1,004 | 1,002 runtime bytes + 2 regular user bytes |
| OAM shadow allocated | 256 | Feature-conditional DMA source page |
| Compiler/runtime/user allocated or reserved | 1,293 | Zero Page benchmark footprint + regular runtime/user + OAM |
| Hardware stack page reserved | 256 | Address space reserved; dynamic occupancy is not measured |
| Zero Page policy-reserved/unavailable | 99 | 96 future-explicit bytes + 3 unused fixed-runtime bytes |
| Total committed/reserved address space | 1,648 | Compiler/runtime/user + hardware stack + policy reservation |
| Allocator-visible regular RAM free | 276 | `$06EC-$07FF` |
| Allocator-visible Zero Page free | 124 | `$0084-$00FF` |
| Total allocator-visible free | 400 | 2,048 - 1,648 |

The 96-byte `Future explicit Zero Page` region is a compiler memory-policy
reservation. It is neither current program consumption nor available to the
normal allocator. Likewise, only one byte of the 16-byte temporary partition
has a generated symbol in this benchmark, although the entire partition is
reserved for compiler temporaries.

### Background-Shadow RAM Finding
- The 960-byte tile shadow is linked **only when `nes.get_tile()` is called**.
- A representative write-only program using `nes.set_tile` and
  `nes.set_attribute` links 26 regular runtime bytes and no OAM shadow. It
  retains **1,510 regular bytes** plus **128 Zero Page bytes**, or **1,638
  allocator-visible free bytes** in total.
- The 960-byte buffer is an intentional architectural cost of providing confirmed PPU tile readback; it is not technical debt, but a feature-conditional capability.

---

## 9. Reconciled NMI / VBlank Cycle Budget

### Hardware Limits & Timing Components
NTSC NES provides **2,273 CPU cycles** per VBlank window. Standard Ricoh 2A03 component costs from [`docs/runtime/vblank-cycle-budget.md`](../runtime/vblank-cycle-budget.md):

| NMI Component | Cost (CPU Cycles) | Condition / State |
| :--- | :---: | :--- |
| Hardware entry, register save, frame bookkeeping, restore, `RTI` | 52 | Unconditional fixed cost |
| Final PPU state restoration (`$2002`, `$2000`, `$2005`x2, `$2001`) | 36 | Unconditional fixed cost |
| OAM DMA transfer (`$2003` reset + `$4014` page DMA) | 525–526 | When sprites/metasprites linked |
| Palette upload routine | 75 to 784 | 75 (clean) / 784 (all 25 bytes dirty) |
| Background update queue scan | 67 to 335 | 67 (clean) / 203 (4 writes) / 335 (4 confirmed tiles) |
| Scroll pair commit | 7 to 28 | 7 (no pair) / 28 (pair pending) |
| Cancellation lock check | 6 | When `nes.clear_background_updates` linked |
| Empty callback dispatch (`JSR` + `RTS`) | 12 | When `nes.on_vblank` registered |

### Worst-Case vs. Typical Scenarios

```text
Worst-Case Frame (OAM DMA + 25 Dirty Colors + 4 Confirmed Tile Writes + Scroll Commit):
  52 (Entry/Exit) + 36 (PPU) + 526 (OAM) + 784 (Palette) + 335 (BG) + 28 (Scroll) + 6 (Lock) + 12 (Hook)
  = 1,779 CPU cycles (~78.3% of VBlank window)

Estimated Remaining Budget before Safety Margin:
  2,273 - 1,779 = 494 CPU cycles

Recommended Safety Margin (Interrupt jitter, DMA parity, page-crossing branches):
  ~200 CPU cycles

Recommended Safe User Callback Budget:
  - Worst-Case Burst Frame: ~250 to 300 CPU cycles
  - Typical Gameplay Frame (OAM DMA only, clean palette/queue): ~1,200 to 1,400 CPU cycles
```

All game logic, controller polling (~241 cycles), and metasprite rendering (~550 cycles) execute safely outside VBlank on the main thread.

---

## 10. Builtin / Intrinsic Scalability Assessment

### Current Architecture
Currently, 21 distinct runtime operations are modeled with dedicated AST node pairs across 5 compiler modules:
- AST classes in [`nes_pascal/ast.py`](../../nes_pascal/ast.py) (~40 classes).
- Parser statement/expression dispatch in [`nes_pascal/parser.py`](../../nes_pascal/parser.py).
- Semantic verification in [`nes_pascal/semantic.py`](../../nes_pascal/semantic.py).
- Resource detection in [`nes_pascal/memory_layout.py`](../../nes_pascal/memory_layout.py).
- Code generation dispatch in [`nes_pascal/backend_ca65.py`](../../nes_pascal/backend_ca65.py).

### Upcoming Roadmap Expansion
Releases 0.6 and 0.7 plan 25+ new runtime operations (APU tones, SFX, music, collisions, HUD, timers, math). Continuing dedicated AST node modeling represents linear per-builtin growth replicated across multiple compiler phases.

### Recommendation
- Introduce a unified `BuiltinCall` / `ResolvedBuiltinCall` node and a declarative **Builtin Registry** specifying:
  `name`, `parameter_types`, `return_type`, `runtime_feature_dependency`, and `codegen_handler`.
- Structurally special constructs should remain specialized (`nes.run`, `nes.on_update`, `nes.on_vblank`, `nes.import_metasprite`, `nes.load_background`).
- **Timing:** Must be implemented as the immediate architectural priority before Release 0.6 (Audio).

---

## 11. Backend Representation & Linear 6502 IR Assessment

### Risk Reassessment
- **Migration Risk: Medium.** While the conceptual instruction classes (`Instruction`, `Operand`, `Label`, `Directive`, `Comment`) are simple, converting the entire backend requires preserving byte-for-byte golden assembly equivalence, label scoping, and directive serialization.
- **Recommended Incremental Migration Strategy:**
  1. *Phase 1:* Define structured `Instruction`, `Label`, `Directive`, `Comment`, and `RawAssembly` classes.
  2. *Phase 2:* Implement linear instruction emission for standard program statements and expressions, ensuring byte-for-byte ca65 text serialization.
  3. *Phase 3:* Keep legacy runtime subroutines (NMI, PPU stabilization, metasprite renderer) encapsulated via the `RawAssembly` escape hatch.
  4. *Phase 4:* Gradually migrate runtime routines to structured instructions only when optimization, register tracking, or cycle analysis benefits justify it.

---

## 12. Technical Debt Dependency Matrix

| Finding / Technical Debt | Severity | Impact Area | Category | Blocks / Complicates | Recommended Timing |
| :--- | :---: | :--- | :--- | :--- | :--- |
| **Dedicated AST nodes for intrinsics** | **High** | Maintainability | Architecture / Scalability | Release 0.6 Audio & Release 0.7 Stdlib | **Immediate Priority (Before Release 0.6)** |
| **AST-depth expression temporaries** | **High** | Correctness | Hard Correctness Block | Functions (Nested expression calls) | **Prerequisite before Functions** |
| **Direct Boolean materialization in control flow** | **Medium** | Code Size & Cycles | Performance Opportunity | Conditional branches & loop overhead | **Low-Risk Codegen Milestone** |
| **Intermediate temporary stores for constants** | **Medium** | Code Size & Cycles | Performance Opportunity | Binary arithmetic & comparison lowering | **Low-Risk Codegen Milestone** |
| **Text-only (`list[str]`) ASM backend** | **Medium** | Optimization | Maintainability / Tooling | Systematic peephole & register tracking | **In Milestone 0.7.9** |
| **RAM staging in calling conventions** | **Low-Med** | CPU Cycles | Performance Opportunity | Internal runtime efficiency | **In Milestone 0.7.9** |
| **Single-unit global symbol table** | **Medium** | Scope / Modules | Architectural Scope | Language Modules (0.7.8) | **In Milestone 0.7.8** |

---

## 13. Prioritized Risk / Benefit Matrix

| Opportunity / Refactoring | Expected Benefit | Risk Level | Primary Benefit Type | Scope |
| :--- | :---: | :---: | :--- | :--- |
| **Builtin / Intrinsic Registry** | **Large** | Low-Medium | Scalability & Maintainability | Architectural |
| **Scoped Expression Temporary Pool** | **Large** | Medium | Correctness (Function calls) | Local |
| **Low-Risk Codegen Improvements** | **Moderate** | Low | PRG-ROM size & CPU cycles | Local |
| **Linear 6502 IR & Peephole Pass** | **Moderate** | Medium | Maintainability & Optimization | Local |
| **Register-based Calling Conventions** | **Small-Mod** | Low | CPU cycles & RAM scratch | Local |

---

## 14. Revised Follow-up Milestone Recommendations

Based on empirical measurements, the recommended progression is:

1. **`Builtin / Intrinsic Infrastructure`:**
   Implement unified `BuiltinCall` / `ResolvedBuiltinCall` registry before expanding APIs.
2. **`Low-Risk Code Generation Improvements`:**
   Implement direct immediate operands (`ADC #$XX`), direct variable operands (`ADC var`), direct Boolean branch emission for control flow, and redundant `CMP #$00` removal without requiring the full Linear IR.
3. **`Arrays`:**
   Implement fixed-size global arrays with indexed addressing.
4. **`Enumerations`:**
   Add user-defined enumeration types.
5. **`Records`:**
   Add user-defined record types with compile-time field offsets.
6. **`Expression Temporary Allocation`:**
   Implement compile-time temporary liveness pooling to guarantee call safety for nested expressions.
7. **`Functions`:**
   Implement function declarations and calls on top of safe temporary allocation.
8. **`Structured 6502 Emitter & Baseline Optimizations` (0.7.9):**
   Implement Linear 6502 IR, peephole passes, and systematic optimizations.

---

## 15. Test Results

- **Automated Unit & Integration Test Suite:** 408 passed (0 failures, 0 errors in 28.2s).
- **Mesen Emulator Behavioral Suite:** All 21 emulator integration tests passed.
- **Full-Stack Benchmark Verification:** [`examples/gameplay_full_stack.nsp`](../../examples/gameplay_full_stack.nsp) verified for compilation, RAM layout, and valid NROM header generation.
- **ROM Stability:** No regressions in any existing example or ROM binary output.
