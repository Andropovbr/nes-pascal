# Enumeration Implementation and Measurements (0.5.9)

English | [Português (Brasil)](../pt-BR/compiler/enumerations-0.5.9.md)

Milestone 0.5.9 adds user-defined, nominal, byte-sized enumeration types.
`EnumType` preserves type identity, ordered member names, and their deterministic
underlying byte values through semantic analysis. Enum members become typed
compile-time immediates; there is no runtime enum subsystem.

## Lowering and storage

- The only syntax is `type Name = (Member, ...);`; members are unqualified.
- The first member is `$00`, followed by sequential byte values through `$FF`.
- Variables use one ordinary scalar byte and are eligible for the existing
  promotion policy. Members, type declarations, descriptors, and tables consume
  no RAM, ROM, or Zero Page.
- Nominal type identity remains intact until ca65 lowering. Cross-enum and
  enum/scalar assignments or equality comparisons are rejected.
- Equality and inequality use the direct-immediate/direct-memory machinery from
  0.5.7. A branch-only comparison does not materialize a Boolean result.

Representative lowering for `if State = Playing then` is:

```asm
    lda variable_State
    cmp #$01
    beq @if_then_0
```

## Enumeration benchmark

The `enumerations` workload performs title, playing, pause, and game-over state
transitions, enum copies, equality, inequality, stored Boolean results, and a
branch-only comparison.

| Metric | Result |
| --- | ---: |
| PRG code | 275 B |
| PRG occupied | 281 B |
| Instructions | 125 |
| Estimated static base cycles | 408 |
| Expression tree depth | 1 |
| Maximum live expression temporaries | 0 |
| Temporaries actually required | 0 B |
| Enum user storage | 3 B (1 B promoted ZP, 2 B regular RAM) |
| ZP benchmark allocated/reserved | 26 B |
| ZP allocator-visible free | 127 B |
| Regular allocator-visible free | 1,530 B |
| Runtime features | None |

The 17 pre-existing workloads (`minimal` through `arrays` and
`gameplay_full_stack`) remain byte-for-byte identical in all reported benchmark
metrics. Programs without an enum declaration add no enum code, runtime state,
RAM, Zero Page, ROM metadata, or descriptors.

## Deliberately deferred

Enum arithmetic, `inc`/`dec`, ordering, explicit numeric values, bit flags,
sets, arrays of enums, procedure enum parameters, enum constants in `const`,
reflection, serialization, records, and runtime metadata remain outside this
milestone.
