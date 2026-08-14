# Functions 0.5.12

Milestone 0.5.12 adds typed user functions on top of the scoped temporary
allocator introduced in 0.5.11. It does not add local variables, runtime stack
frames, recursion, aggregate returns, early returns, or optimizations.

## Implemented contract

- Declarations may be interleaved with procedures before the main block.
- Parameters and return values support `byte` and `boolean` only.
- Parameterless declarations omit a list; every call uses parentheses.
- Assigning the function name defines its result. Definite-assignment analysis
  requires a result on every path that reaches the epilogue.
- Function calls are resolved as value expressions and may be nested in
  arguments, arithmetic, comparisons, conditions, and short-circuit Boolean
  expressions.
- Direct, indirect, and mixed procedure/function recursion is rejected.

## ABI and memory ownership

Function parameters retain the procedure ABI: one deterministic static
regular-RAM byte per value parameter. Each function also owns one compiler
regular-RAM result byte in `FUNCTION_RESULTS`. The epilogue loads that byte into
the 6502 accumulator and returns with `RTS`:

```asm
function_Add:
    ; body assigns function_result_Add
    lda function_result_Add ; return value in A
    rts
```

There is no shared fixed return window and no Zero Page result reservation.
Programs without functions emit no result bytes, `FUNCTION_RESULTS` segment,
or function bodies. Ordinary `JSR` return addresses use the hardware stack;
the benchmark reports the maximum source-call depth and its two-byte-per-call
return-address peak separately from committed RAM.

Source-call depth is bounded at compile time so return addresses stay inside
the reserved 256-byte hardware stack: with two bytes per active `JSR` and ten
bytes reserved for runtime `JSR` frames and NMI headroom, the supported maximum
source-call depth is 123. Deeper acyclic chains are rejected with `E5007`;
recursion is rejected earlier with `E3014`.

The callable ABI treats `A`, `X`, `Y`, and processor flags as caller-clobbered;
there are no callee-saved registers. `A` contains the scalar result on return,
and loading the canonical Boolean result also leaves the zero flag valid for a
direct branch. The hardware stack pointer is balanced across each `JSR`/`RTS`;
compiler-managed expression temporaries and static parameter/result bytes are
the only preserved value locations promised by this milestone.

## Nested-call safety

The temporary analysis replays the complete acyclic source call graph. Each
callable receives a deterministic base equal to the maximum number of live
caller expression slots at its entry. Backend generation leases that prefix
while lowering the callable body, so callee temporaries cannot alias suspended
caller values.

Arguments evaluate left to right. When a later argument contains a function
call, an earlier result is leased in the expression pool until all arguments
are ready; only then is it copied into the callee's static parameter byte.
This also prevents a nested call to the same function from overwriting an
outer call's partially staged parameters.

Short-circuit Boolean order remains left to right. Binary arithmetic and
comparison nodes keep the established lowering rule: direct right operands
are consumed after the left side, while a right side requiring evaluation is
evaluated and preserved before the left side.

The focused pressure golden holds slot 0 in the main expression, enters
`Middle` at base 1, and enters `Leaf` at base 2; `Leaf` then leases slot 2 for
a verified peak of three simultaneously live bytes. The source-call depth is
two, so the corresponding return-address peak is four hardware-stack bytes.

| Static ABI component | Cost |
| --- | ---: |
| Per declared function result | 1 B regular RAM |
| Function epilogue (`LDA abs` + `RTS`) | 4 B PRG, 2 instructions |
| Call transfer (`JSR`) | 3 B PRG, 1 instruction |
| Active source return address | 2 B hardware stack |
| Suspended expression value | 1 scoped ZP byte while live |

Argument evaluation and result-body code are additional and depend on the
source. Nested calls add no fixed return window or software-frame overhead.

## Benchmark

The dedicated `functions` corpus entry compiles `examples/functions.nsp`,
including a function result passed directly to a procedure, and measures:

| Metric | Verified value |
| --- | ---: |
| PRG code / occupied | 365 B / 371 B |
| Instructions / estimated static base cycles | 158 / 560 |
| Expression tree depth / maximum live temporaries | 2 / 1 |
| Maximum source-call depth / JSR return-address peak | 2 / 4 B |
| Function result storage | 3 B regular compiler RAM |
| Regular runtime + user allocation | 11 B |
| Allocator-visible regular RAM free | 1,522 B |
| Allocator-visible Zero Page free | 142 B |
| Total allocator-visible free memory | 1,664 B |
| Compiler/runtime/user allocated or reserved | 25 B |
| Total committed/reserved CPU address space | 384 B |

All pre-existing benchmark PRG, instruction, cycle, RAM, Zero Page, and
temporary-pressure figures remain unchanged. In particular,
`gameplay_full_stack` remains 3,350 B PRG code, 3,356 B PRG occupied, expression
depth 1, zero live temporaries, 815 instructions, and 2,712 estimated static
base cycles.

## Regression coverage

`tests/test_functions.py` covers syntax, typed resolution, forward and nested
calls, definite results (including conditional short-circuit effects),
canonical diagnostics, recursion cycles, explicit memory ownership,
no-function zero cost, builtin interaction, three simultaneously live
temporary slots, and focused ABI goldens. `tests/fixtures/runtime/functions.nsp`
plus `tests/mesen/verify_functions.lua` checks nested static-parameter safety,
left-to-right arguments, right-first complex arithmetic, comparisons, Boolean
normalization, short-circuit side effects, procedure/function interaction, and
8-bit wraparound on an assembled ROM. Benchmark accounting has a focused
assertion for the three compiler-owned regular result bytes and exact 2 KiB
reconciliation.

Final local validation passed all 524 automated tests, including all 29
dedicated headless Mesen tests. The complete 21-program benchmark corpus and
every public example assembled and linked successfully.
