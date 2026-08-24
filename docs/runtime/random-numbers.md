# Random Numbers

English | [Português (Brasil)](../pt-BR/runtime/random-numbers.md)

NES Pascal provides a small deterministic gameplay PRNG. It is suitable for
enemy behavior, spawn selection, loot, visual variation, and procedural game
choices. It is **not cryptographically secure** and is not an entropy source.

## API

```pascal
nes.seed_random($2A);
Value := nes.random_byte();
EnemyX := nes.random_range($08, $F7);
```

- `nes.seed_random(seed: byte)` selects a reproducible stream. A nonzero seed
  `$SS` maps to internal state `$SSSS`; `$00` maps to canonical state `$ACE1`.
- `nes.random_byte(): byte` advances the state exactly once and returns the low
  byte of the new state.
- `nes.random_range(minimum: byte, maximum: byte): byte` uses inclusive
  `[minimum, maximum]` bounds. Equal bounds return that byte without advancing.
  A dynamic minimum greater than the maximum returns the minimum without
  advancing; constant reversed bounds are rejected with `E3064`. `$00..$FF`
  advances once and returns an ordinary random byte.

The generator is a right-shifting 16-bit Galois LFSR with XOR mask `$B400`.
Every nonzero state belongs to one cycle of 65,535 states. The all-zero state is
absorbing for this algorithm, so it is never activated. Cleared RAM `$0000`
instead means “automatic seed pending”; the first random call replaces it with
a nonzero timing-derived state before stepping.

The algorithm, seed mapping, step-before-output convention, and resulting byte
sequence are a compatibility contract. Seed `$2A` begins `$15, $8A, $45, $A2,
$D1, $E8, $74, $BA, ...`. A future algorithm change must be explicitly
documented rather than silently changing replays, tests, or debugging runs.

## Automatic and deterministic seeding

Without `nes.seed_random`, the first random call snapshots the 8-bit NMI frame
counter. If controller query APIs are already linked, it also XORs the current
states of controllers 1 and 2. The mixed byte is XORed with `$E1` for the low
state and `$AC` for the high state, which guarantees a nonzero pair. This is a
small timing variation mechanism: pressing Start on a different frame tends to
select a different stream, but it is not true entropy.

Automatic mixing happens once, immediately before the first random step. Later
frames and controller input do not reseed an active stream. Calling
`nes.seed_random` first installs a nonzero state, so automatic mixing is skipped
and identical seed + call order produces identical output across builds and
emulator runs. No ROM address, code layout, uninitialized RAM, or host timing is
used.

## Bounded reduction and timing

For a span `N`, bounded generation rejects source bytes below `256 mod N`, then
reduces the remaining equally sized domain by repeated subtraction. This avoids
the lower-residue bias of `random_byte() mod N` without introducing public or
general-purpose division/modulo support. Spans that divide 256 have cutoff zero
and never reject; the full 256-byte span has a direct path.

Rejection sampling has variable execution time. A correct full-period nonzero
state eventually accepts for every valid span, but code with a strict frame
budget should account for retries. The helper uses two regular-RAM scratch bytes
for span and cutoff.

## Calls, callbacks, and memory

Random calls are stateful and are never duplicated, removed, or reordered.
Function arguments and Boolean short-circuiting keep their documented
left-to-right behavior. Complex arithmetic keeps NES Pascal's established
lowering order: a non-direct right operand is evaluated before the left one.
A skipped Boolean operand does not advance the PRNG.

Random calls are rejected on VBlank callback paths with `E3023`; main and NMI
must not race on mutable PRNG state or range scratch. Use them in initialization,
main code, Functions, or the update callback.

Programs without RNG calls emit zero RNG code and allocate zero RNG RAM/ZP.
`random_byte` or `seed_random` allocates exactly 2 regular-RAM state bytes and
zero RNG ZP bytes. Linking `random_range` adds 2 regular-RAM scratch bytes. The
compiler-managed `TemporaryPool` is used only when the surrounding expression
normally requires it; the runtime has no RNG-specific expression pool or heap.

See [the random-numbers example](../../examples/random_numbers.nsp).
