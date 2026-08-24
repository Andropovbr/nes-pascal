# Random Number Generation Implementation and Measurements (0.5.14)

English | [Português (Brasil)](../pt-BR/compiler/random-number-generation-0.5.14.md)

Milestone 0.5.14 adds a feature-gated 16-bit Galois LFSR and three declarative
builtins: `nes.seed_random`, `nes.random_byte`, and `nes.random_range`.
Descriptors select `RuntimeFeature.RANDOM` and, only for bounded calls,
`RuntimeFeature.RANDOM_RANGE`; no parser or backend public-name special case was
added.

The frozen step is `(state >> 1) xor $B400` when the old low bit is one. It has
a validated maximal 65,535-state nonzero period. Calls step first and return the
new low byte. Nonzero public seed `$SS` expands to `$SSSS`; seed zero normalizes
to `$ACE1`. Cleared state zero is an inactive auto-seed marker. The first call
mixes one coherent frame/controller snapshot into state and never automatically
reseeds afterward.

Inclusive bounded generation computes a low rejection cutoff `256 mod span`,
rejects the incomplete tail, and reduces accepted bytes by repeated subtraction.
It has variable runtime cost and adds no generic division/modulo subsystem.
Reversed dynamic bounds and singleton bounds return the minimum without
advancing; reversed constants produce `E3064`.

## Benchmark

| Metric | `random_numbers` |
| --- | ---: |
| PRG code / occupied | 417 / 423 B |
| Instructions | 193 |
| Estimated static base cycles | 659 |
| Runtime regular RAM | 8 B total; 4 B RNG |
| Runtime RNG ZP | 0 B |
| Function result RAM | 1 B |
| User RAM | 3 B |
| Max live expression temporaries | 0 |
| Source call depth | 1 |

The benchmark includes one seeded byte, one non-power-of-two range, one
power-of-two range in a Function, and the shared runtime routines. Static cycle
estimation counts emitted instructions once and does not represent rejection
retries, average latency, or worst-case runtime latency.

All pre-existing benchmarks retain their exact 0.5.13 PRG, instruction, static
cycle, RAM, ZP, and temporary-pressure metrics. A minimal ROM has no random
symbols, routines, state, or scratch.

Pure tests validate the complete LFSR cycle, frozen vectors, zero-seed mapping,
and uniform accepted-domain mappings for spans 3, 5, 6, 7, 10, 100, and 255.
Golden fragments cover state, seeding, stepping, and bounded reduction. Two
headless Mesen ROMs cover the exact 16-byte sequence, all boundary policies,
Functions, argument/arithmetic order, short-circuiting, zero normalization, and
controlled delayed frame/controller automatic seeding.

## Deliberately deferred

Cryptographic randomness, hardware entropy, public 16-bit values, distributions,
shuffle/choice helpers, weighted tables, independent streams, RNG objects,
noise, and general division/modulo remain outside this milestone.
