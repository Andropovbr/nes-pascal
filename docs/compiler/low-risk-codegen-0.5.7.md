# Low-Risk Code Generation Improvements

> Historical note: the fixed reservation described below was replaced by the
> exact scoped pool in [milestone 0.5.11](expression-temporaries-0.5.11.md).

English | [Português (Brasil)](../pt-BR/compiler/low-risk-codegen-0.5.7.md)

Milestone 0.5.7 adds a small set of local ca65 lowering decisions. It is not a
general optimizer: the backend still emits readable Assembly directly, without
an Assembly-text rewrite pass, instruction IR, control-flow graph, or global
register/flag tracking.

## Implemented rules

The backend now:

- emits `ADC #value` and `SBC #value` when the right arithmetic operand is a
  compile-time byte value;
- emits `ADC variable`, `SBC variable`, and `CMP variable` for stable variable
  operands when evaluating the left side has no runtime side effects;
- emits `CMP #value` for immediate comparison operands;
- keeps the original right-first temporary path when direct consumption could
  make evaluation order observable;
- lowers Boolean expressions used by `if`, `while`, and `repeat` directly to
  branches;
- preserves canonical `$00`/`$01` materialization when a Boolean is stored or
  otherwise used as data;
- uses the flags produced by a proven final `LDA`, Boolean materialization, or
  supported builtin query instead of adding `CMP #$00`;
- lowers controller-query conditions through the existing `BuiltinId` backend
  path without bypassing the builtin registry;
- preserves short-circuit evaluation for `and`, `or`, and `not`;
- keeps potentially distant paths behind absolute `JMP` instructions. Relative
  branches target only nearby labels or trampolines.

The fixed 16-byte Zero Page temporary reservation is unchanged. Only generated
temporary symbols and actual temporary use can decrease. Runtime ABIs, calling
conventions, builtin descriptors, memory regions, and public language semantics
are unchanged.

## Representative Assembly

An immediate arithmetic operand no longer passes through Zero Page:

```asm
; before
lda #$01
sta expression_temporary_0
lda variable_Counter
clc
adc expression_temporary_0

; after
lda variable_Counter
clc
adc #$01
```

A stable variable can be consumed directly:

```asm
; before
lda variable_Right
sta expression_temporary_0
lda variable_Left
sec
sbc expression_temporary_0

; after
lda variable_Left
sec
sbc variable_Right
```

A comparison used only for control flow no longer materializes a Boolean:

```asm
; before
lda #$08
sta expression_temporary_0
lda variable_Counter
cmp expression_temporary_0
bcc @comparison_true
lda #$00
jmp @comparison_end
@comparison_true:
lda #$01
@comparison_end:
cmp #$00
bne @if_then
jmp @if_else

; after
lda variable_Counter
cmp #$08
bcc @if_then
jmp @if_else       ; long-branch-safe false path
```

The same comparison still produces canonical data for an assignment:

```asm
lda variable_Counter
cmp #$08
bcc @comparison_true
lda #$00              ; false
jmp @comparison_end
@comparison_true:
lda #$01              ; true
@comparison_end:
sta variable_Flag
```

## Benchmark method

The unchanged 16-program corpus from milestone 0.5.5 was measured immediately
before and after the backend change with `tools/measure_benchmarks.py`.

PRG sizes and instruction counts are measured from generated output. `Estimated
static cycles` is deliberately narrower than runtime timing: it counts every
emitted instruction once at its base Ricoh 2A03 cost, treats branches as not
taken, and excludes dynamic loop counts, page crossing, interrupts, and DMA.
It is useful for deterministic before/after comparison, not for frame-budget
prediction.

| Benchmark | PRG code B (delta) | PRG occupied B | Instructions | Estimated static cycles | Live temps | ZP temp/cache bytes | Non-ZP B |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `minimal` | 239 -> 239 (0, 0.0%) | 245 -> 245 | 108 -> 108 (0, 0.0%) | 367 -> 367 (0, 0.0%) | 0 -> 0 | 0 -> 0 | 7 -> 7 |
| `arithmetic` | 259 -> 251 (-8, -3.1%) | 265 -> 257 | 119 -> 115 (-4, -3.4%) | 395 -> 383 (-12, -3.0%) | 2 -> 0 | 2 -> 0 | 7 -> 7 |
| `boolean_expressions` | 416 -> 382 (-34, -8.2%) | 422 -> 388 | 187 -> 170 (-17, -9.1%) | 571 -> 525 (-46, -8.1%) | 1 -> 0 | 1 -> 0 | 12 -> 12 |
| `conditionals` | 303 -> 282 (-21, -6.9%) | 309 -> 288 | 138 -> 128 (-10, -7.2%) | 440 -> 415 (-25, -5.7%) | 1 -> 0 | 1 -> 0 | 5 -> 5 |
| `loops` | 404 -> 317 (-87, -21.5%) | 410 -> 323 | 187 -> 146 (-41, -21.9%) | 563 -> 460 (-103, -18.3%) | 1 -> 0 | 1 -> 0 | 4 -> 4 |
| `counting` | 533 -> 488 (-45, -8.4%) | 539 -> 494 | 237 -> 216 (-21, -8.9%) | 751 -> 700 (-51, -6.8%) | 2 -> 0 | 7 -> 6 | 9 -> 9 |
| `procedures` | 330 -> 289 (-41, -12.4%) | 336 -> 295 | 153 -> 134 (-19, -12.4%) | 511 -> 466 (-45, -8.8%) | 2 -> 0 | 1 -> 0 | 4 -> 4 |
| `procedure_parameters` | 366 -> 350 (-16, -4.4%) | 372 -> 356 | 163 -> 155 (-8, -4.9%) | 544 -> 524 (-20, -3.7%) | 1 -> 0 | 1 -> 0 | 11 -> 11 |
| `controller_input` | 889 -> 704 (-185, -20.8%) | 895 -> 710 | 404 -> 318 (-86, -21.3%) | 1146 -> 945 (-201, -17.5%) | 1 -> 0 | 1 -> 0 | 265 -> 265 |
| `sprite_support` | 583 -> 583 (0, 0.0%) | 589 -> 589 | 273 -> 273 (0, 0.0%) | 911 -> 911 (0, 0.0%) | 0 -> 0 | 0 -> 0 | 326 -> 326 |
| `metasprite_player` | 1437 -> 1303 (-134, -9.3%) | 1443 -> 1309 | 551 -> 489 (-62, -11.3%) | 1741 -> 1599 (-142, -8.2%) | 1 -> 0 | 1 -> 0 | 272 -> 272 |
| `sprite_animation` | 2007 -> 1875 (-132, -6.6%) | 2013 -> 1881 | 675 -> 614 (-61, -9.0%) | 2175 -> 2035 (-140, -6.4%) | 1 -> 0 | 1 -> 0 | 276 -> 276 |
| `palette_support` | 812 -> 812 (0, 0.0%) | 818 -> 818 | 342 -> 342 (0, 0.0%) | 1106 -> 1106 (0, 0.0%) | 0 -> 0 | 0 -> 0 | 306 -> 306 |
| `background_updates` | 2166 -> 2166 (0, 0.0%) | 2172 -> 2172 | 522 -> 522 (0, 0.0%) | 1773 -> 1773 (0, 0.0%) | 1 -> 1 | 0 -> 0 | 995 -> 995 |
| `frame_callbacks` | 272 -> 272 (0, 0.0%) | 278 -> 278 | 124 -> 124 (0, 0.0%) | 438 -> 438 (0, 0.0%) | 0 -> 0 | 0 -> 0 | 6 -> 6 |
| `gameplay_full_stack` | 3478 -> 3350 (-128, -3.7%) | 3484 -> 3356 | 874 -> 815 (-59, -6.8%) | 2848 -> 2712 (-136, -4.8%) | 1 -> 1 | 1 -> 0 | 1260 -> 1260 |

All non-ZP allocation, fixed Zero Page reservation, promoted-variable layout,
allocator-visible free memory, and runtime-feature selection remained unchanged.
The generated compiler temporary/cache symbol count decreased where direct
operands made symbols unnecessary; `counting` still needs six `for_limit_*`
cache bytes.

`minimal`, `sprite_support`, `palette_support`, `background_updates`, and
`frame_callbacks` are unchanged because their generated source paths do not
contain the optimized arithmetic/comparison branch patterns. Feature isolation
also remains unchanged: controller, OAM, metasprite animation, palette queue,
background shadow, and callback routines are emitted under the same conditions
as before.

| Representative benchmark | Registry runtime features before and after |
| --- | --- |
| `minimal` | None |
| `controller_input` | `CONTROLLER_QUERY`, `LEGACY_SPRITE_ZERO` |
| `sprite_support` | `SPRITE_API`, `SPRITE_SET_POSITION` |
| `metasprite_player` | `CONTROLLER_QUERY`, `METASPRITE_API` |
| `sprite_animation` | `CONTROLLER_QUERY`, `METASPRITE_ANIMATION`, `METASPRITE_API` |
| `background_updates` | `BACKGROUND_CLEAR_OVERFLOW`, `BACKGROUND_CLEAR_UPDATES`, `BACKGROUND_GET_TILE`, `BACKGROUND_INSPECT_OVERFLOW`, `BACKGROUND_SET_ATTRIBUTE`, `BACKGROUND_SET_TILE` |
| `gameplay_full_stack` | `BACKGROUND_GET_TILE`, `BACKGROUND_SET_ATTRIBUTE`, `BACKGROUND_SET_TILE`, `CONTROLLER_QUERY`, `METASPRITE_ANIMATION`, `METASPRITE_API` |

## Deliberately deferred

This milestone does not implement accumulator tracking across expressions,
cross-basic-block flag reasoning, dead-store or reload elimination, a general
peephole pass, CFG/SSA, structured 6502 IR, register allocation, runtime ABI
changes, or temporary-pool redesign. Complex or potentially side-effecting
operands continue through the conservative temporary path.
