# Expression Temporary Allocation (0.5.11)

> Milestone [0.5.12](functions-0.5.12.md) now extends this scoped model across
> the complete acyclic procedure/function call graph.

English | [Português (Brasil)](../pt-BR/compiler/expression-temporaries-0.5.11.md)

Milestone 0.5.11 replaces the unconditional 16-byte, AST-depth expression
temporary model with deterministic compile-time allocation based on the actual
maximum number of simultaneously live values. It changes compiler storage, not
NES Pascal syntax or arithmetic semantics. Functions remain unimplemented.

## Scoped pool and lifetime model

`TemporaryPool` leases the lowest available numbered slot, records the current
and maximum live counts, and requires an explicit release. The backend and the
pre-layout analysis use the same acquire/use/release rules:

1. Evaluate the established right operand first when direct 0.5.7 lowering is
   not legal.
2. Acquire a slot only after that result exists in `A`.
3. Store the result and keep the slot leased while evaluating the left operand.
4. Consume the stored byte, then release the slot.

Sequential expressions therefore reuse `expression_temporary_0` instead of
accumulating storage. A left-nested expression can keep slots 0, 1, 2, and so
on live concurrently without aliasing. The emitter is bounded by the count
reserved by memory analysis and asserts that its observed peak exactly matches
that reservation.

Direct immediates, direct safe memory operands, branch-oriented Boolean
lowering, and local zero-test elimination from 0.5.7 remain unchanged. Byte
arithmetic still uses 6502 `ADC`/`SBC` behavior and wraps modulo 256.

## Calls, indexes, and separate storage categories

Call scopes retain every caller-owned lease. Nested lowering receives the same
pool and can only acquire an unleased slot. Current builtin value calls already
exercise this boundary. Future function-call analysis must extend the same
rule across the call graph and assign non-overlapping slots for every active
caller/callee chain. This is a compile-time caller-owned model; this milestone
does not add runtime frames, return values, or Functions.

Procedure arguments keep their existing left-to-right staging: each argument
is fully evaluated and stored in its parameter before the next starts. Builtin
arguments retain their emitter-defined order. Current source expressions do
not expose a function-like user side effect strong enough for a runtime order
oracle, so focused assembly tests additionally lock the existing right-first
complex-expression sequence.

Variable array and record-array writes still save their calculated index on
the 6502 hardware stack while evaluating the right-hand side. That stack use is
separate from Zero Page expression slots. Nested reads such as
`Values[Indexes[I]]`, scaled record indexes, indexed writes, procedure
arguments, and builtin arguments all use the same scoped expression pool.

Compiler storage is reported in separate categories:

- expression temporaries: the exact maximum-live count;
- compiler caches: currently `for_limit_*` bytes, counted independently;
- runtime Zero Page symbols;
- promoted user Zero Page variables;
- hardware stack reservation.

The combined expression/cache policy capacity remains 16 bytes at
`$0010-$001F`. Actual symbols occupy the prefix; the unused suffix is emitted
as `Recovered temporary Zero Page` and becomes allocator-visible free memory.
The future-explicit window remains `$0020-$007F`, and automatic promotion
remains `$0080-$00FF`, so existing user Zero Page addresses do not move.

If expression slots plus compiler caches exceed 16 bytes, compilation fails
with `E5004`. The diagnostic states the combined requirement, its expression
and cache components, and the available capacity. It never wraps slot indexes,
aliases a live value, borrows optional promotion space, or silently spills.

## Focused validation

The dedicated fixture proves all of these cases in one deterministic layout:

| Case | Peak expression slots | Result |
| --- | ---: | --- |
| direct arithmetic / simple programs | 0 | no `expression_temporary_0`; 16 ZP bytes recovered |
| `Values[I] + Values[J]` | 1 | slot 0 only |
| `(Values[I] + Values[J]) + Values[K]` | 2 | slots 0 and 1 do not alias |
| `((Values[I] + Values[J]) + Values[K]) + Values[L]` | 3 | slots 0, 1, and 2; later statements reuse them |
| nested comparison | 2 | arithmetic result and comparison operand remain distinct |
| 18-term left-nested indexed sum | 17 | deterministic `E5004` against the 16-byte capacity |

The runtime regression checks three-deep arithmetic, `$F0 + $20 = $10`
wraparound, sequential reuse, nested array indexes, indexed array writes,
record-array reads and writes, nested comparison materialization, and two
procedure argument expressions. The focused golden records every temporary
declaration and use, protecting deterministic identity and reuse.

## 0.5.5 fixed-window comparison

`Legacy fixed temp window` is the old 16-byte combined temporary/cache window.
`New expression` is only the expression reservation; caches are shown
separately. `Net ZP saved` subtracts caches that still remain required.

| Benchmark | Legacy fixed temp window | Actual max live | New expression | Other caches | Net ZP saved | Old ZP alloc./reserved | New ZP alloc./reserved | Old ZP free | New ZP free |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `minimal` | 16 B | 0 | 0 B | 0 B | 16 B | 25 B | 9 B | 128 B | 144 B |
| `arithmetic` | 16 B | 0 | 0 B | 0 B | 16 B | 25 B | 9 B | 128 B | 144 B |
| `boolean_expressions` | 16 B | 0 | 0 B | 0 B | 16 B | 26 B | 10 B | 127 B | 143 B |
| `conditionals` | 16 B | 0 | 0 B | 0 B | 16 B | 27 B | 11 B | 126 B | 142 B |
| `loops` | 16 B | 0 | 0 B | 0 B | 16 B | 28 B | 12 B | 125 B | 141 B |
| `counting` | 16 B | 0 | 0 B | 6 B | 10 B | 28 B | 18 B | 125 B | 135 B |
| `procedures` | 16 B | 0 | 0 B | 0 B | 16 B | 28 B | 12 B | 125 B | 141 B |
| `procedure_parameters` | 16 B | 0 | 0 B | 0 B | 16 B | 27 B | 11 B | 126 B | 142 B |
| `controller_input` | 16 B | 0 | 0 B | 0 B | 16 B | 30 B | 14 B | 123 B | 139 B |
| `sprite_support` | 16 B | 0 | 0 B | 0 B | 16 B | 26 B | 10 B | 127 B | 143 B |
| `metasprite_player` | 16 B | 0 | 0 B | 0 B | 16 B | 34 B | 18 B | 123 B | 139 B |
| `sprite_animation` | 16 B | 0 | 0 B | 0 B | 16 B | 34 B | 18 B | 123 B | 139 B |
| `palette_support` | 16 B | 0 | 0 B | 0 B | 16 B | 25 B | 9 B | 128 B | 144 B |
| `background_updates` | 16 B | 0 | 0 B | 0 B | 16 B | 25 B | 9 B | 128 B | 144 B |
| `frame_callbacks` | 16 B | 0 | 0 B | 0 B | 16 B | 25 B | 9 B | 128 B | 144 B |
| `scrolling_ppu_state` | 16 B | 0 | 0 B | 0 B | 16 B | 25 B | 9 B | 128 B | 144 B |
| `arrays` | 16 B | 1 | 1 B | 2 B | 13 B | 28 B | 15 B | 125 B | 138 B |
| `enumerations` | 16 B | 0 | 0 B | 0 B | 16 B | 26 B | 10 B | 127 B | 143 B |
| `records` | 16 B | 0 | 0 B | 0 B | 16 B | 27 B | 11 B | 126 B | 142 B |
| `gameplay_full_stack` | 16 B | 0 | 0 B | 0 B | 16 B | 33 B | 17 B | 124 B | 140 B |

Across the 20-program corpus, the per-program savings total 311 bytes as a
comparative aggregate. Nineteen benchmarks now reserve zero expression bytes;
`arrays` reserves one. `counting` retains six loop-cache bytes and `arrays`
retains two; those bytes are not mislabeled as expression temporaries. The
deepest benchmark demand is one, while the focused regression proves a natural
three-slot source pattern and the exhaustion fixture proves deeper handling.

## Code-generation regression check

The allocation change modifies data reservation and map reporting only. Every
benchmark retained its pre-change PRG code/occupied size, instruction count,
and estimated static cycles. Representative values are:

| Benchmark | PRG code/occupied | Instructions | Estimated static cycles |
| --- | ---: | ---: | ---: |
| `minimal` | 239/245 B | 108 | 367 |
| `counting` | 488/494 B | 216 | 700 |
| `arrays` | 382/388 B | 182 | 569 |
| `records` | 389/395 B | 196 | 605 |
| `gameplay_full_stack` | 3,350/3,356 B | 815 | 2,712 |

For `gameplay_full_stack`, current accounting is 17 bytes allocated/reserved by
compiler/runtime/user in ZP, 1,004 bytes of regular runtime/user RAM, a 256-byte
OAM shadow, 256 bytes reserved by the hardware stack, 99 ZP bytes unavailable
by policy, and 416 allocator-visible free bytes (140 ZP + 276 regular). Thus
1,277 bytes are allocated/reserved by compiler/runtime/user and 1,632 bytes of
CPU address space are committed/reserved. These categories plus free memory
reconcile exactly to the NES's 2,048 bytes.

## Verification

Local validation passed 475 non-Mesen automated tests and all 28 dedicated
headless Mesen tests. The complete 20-program benchmark suite assembled and
linked, every public example built through the toolchain integration suite,
Python byte-compilation succeeded, and `git diff --check` reported no errors.

## Deliberately deferred

Functions, return values, stack frames, spilling, a general register allocator,
CFG/SSA/dataflow infrastructure, and expression reordering remain deferred.
