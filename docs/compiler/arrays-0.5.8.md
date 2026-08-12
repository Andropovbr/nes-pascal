# Array Implementation and Measurements (0.5.8)

English | [Português (Brasil)](../pt-BR/compiler/arrays-0.5.8.md)

Milestone 0.5.8 adds fixed-size global arrays as a compiler language construct,
not as a runtime subsystem. `ArrayType` retains element type, lower and upper
bounds, element count, and total one-byte-element size. Resolved array reads and
writes remain explicit through semantic analysis, memory layout, temporary
analysis, and ca65 emission.

## Lowering and memory model

- Arrays use `array[$00..$NN] of byte|boolean`; only lower bound `$00` is
  supported.
- Arrays are allocated contiguously in declaration order in regular user RAM.
  They are deliberately excluded from automatic Zero Page promotion.
- Constant indexes become static symbol offsets. Variable indexes are evaluated
  into `X` and use absolute indexed addressing.
- An indexed assignment evaluates the index first, preserves it temporarily on
  the hardware stack, evaluates the value, and then stores through `,x`. No
  fixed compiler symbol or array runtime state is introduced.
- An array element used by Boolean control flow feeds the 0.5.7 branch-oriented
  lowering directly. Stored Boolean elements remain canonical `$00`/`$01`.
- Compile-time-known indexes are folded and checked. Variable indexes have no
  runtime bounds check or metadata cost.

## Array benchmark

The new `arrays` workload fills byte and Boolean arrays in loops, reads and
writes constant and variable indexes, performs indexed arithmetic, and branches
on Boolean elements.

| Metric | Result |
| --- | ---: |
| PRG code | 382 B |
| PRG occupied | 388 B |
| Instructions | 182 |
| Estimated static base cycles | 569 |
| Expression tree depth | 2 |
| Maximum live expression temporaries | 1 |
| Fixed temporary pool reservation | 16 B |
| Temporaries/cache actually required | 3 B |
| Array element storage | 16 B regular RAM |
| Other regular runtime/user storage | 4 B |
| Automatically promoted scalar storage | 3 B ZP |
| ZP benchmark allocated/reserved | 28 B |
| ZP allocator-visible free | 125 B |
| Regular allocator-visible free | 1,516 B |
| Runtime features | None |

The three required temporary/cache bytes are one reusable expression byte for
`Sum + Values[Index]` and two existing `for_limit_*` bytes. Array indexing
itself adds no fixed or actual Zero Page temporary. Constant-only indexing
requires no index temporary.

`Estimated static base cycles` uses the deterministic benchmark convention:
each emitted instruction is counted once at its base Ricoh 2A03 cost, branches
are not taken, and loop counts, page crossing, interrupts, and DMA are excluded.

## Pre-existing corpus regression check

The complete 16-program 0.5.5/0.5.7 corpus was measured before and after array
support. Every listed metric is identical; no-array programs emit no array
runtime, descriptor, metadata, RAM, or Zero Page state.

| Benchmark | PRG code/occupied B | Instructions | Est. cycles | Live temps | ZP temp required | Non-ZP allocated |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `minimal` | 239/245 | 108 | 367 | 0 | 0 B | 7 B |
| `arithmetic` | 251/257 | 115 | 383 | 0 | 0 B | 7 B |
| `boolean_expressions` | 382/388 | 170 | 525 | 0 | 0 B | 12 B |
| `conditionals` | 282/288 | 128 | 415 | 0 | 0 B | 5 B |
| `loops` | 317/323 | 146 | 460 | 0 | 0 B | 4 B |
| `counting` | 488/494 | 216 | 700 | 0 | 6 B | 9 B |
| `procedures` | 289/295 | 134 | 466 | 0 | 0 B | 4 B |
| `procedure_parameters` | 350/356 | 155 | 524 | 0 | 0 B | 11 B |
| `controller_input` | 704/710 | 318 | 945 | 0 | 0 B | 265 B |
| `sprite_support` | 583/589 | 273 | 911 | 0 | 0 B | 326 B |
| `metasprite_player` | 1,303/1,309 | 489 | 1,599 | 0 | 0 B | 272 B |
| `sprite_animation` | 1,875/1,881 | 614 | 2,035 | 0 | 0 B | 276 B |
| `palette_support` | 812/818 | 342 | 1,106 | 0 | 0 B | 306 B |
| `background_updates` | 2,166/2,172 | 522 | 1,773 | 1 | 0 B | 995 B |
| `frame_callbacks` | 272/278 | 124 | 438 | 0 | 0 B | 6 B |
| `gameplay_full_stack` | 3,350/3,356 | 815 | 2,712 | 1 | 0 B | 1,260 B |

## Deliberately deferred

Runtime bounds checking, non-zero lower bounds, array parameters/returns,
multidimensional and dynamic arrays, bit packing, arrays of records, pointer
semantics, a generic runtime array system, and temporary allocator redesign
remain outside this milestone.
