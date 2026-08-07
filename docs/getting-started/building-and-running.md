# Building and running programs

## Compilation

Compile the minimal example with:

```text
python -m nes_pascal.cli examples/minimal.nsp -o build/minimal.nes
```

The repository also contains focused examples for each implemented language
area:

```text
python -m nes_pascal.cli examples/arithmetic.nsp -o build/arithmetic.nes
python -m nes_pascal.cli examples/boolean_expressions.nsp -o build/boolean_expressions.nes
python -m nes_pascal.cli examples/conditionals.nsp -o build/conditionals.nes
python -m nes_pascal.cli examples/loops.nsp -o build/loops.nes
python -m nes_pascal.cli examples/counting.nsp -o build/counting.nes
python -m nes_pascal.cli examples/procedures.nsp -o build/procedures.nes
python -m nes_pascal.cli examples/procedure_parameters.nsp -o build/procedure_parameters.nes
python -m nes_pascal.cli examples/memory_layout.nsp -o build/memory_layout.nes
python -m nes_pascal.cli examples/zero_page.nsp -o build/zero_page.nes
python -m nes_pascal.cli examples/frame_synchronization.nsp -o build/frame_synchronization.nes
python -m nes_pascal.cli examples/frame_callbacks.nsp -o build/frame_callbacks.nes
python -m nes_pascal.cli examples/slow_update_callback.nsp -o build/slow_update_callback.nes
python -m nes_pascal.cli examples/controller_input.nsp -o build/controller_input.nes
python -m nes_pascal.cli examples/chr_asset.nsp -o build/chr_asset.nes --chr assets/chr_asset.chr
python -m nes_pascal.cli examples/palette_support.nsp -o build/palette_support.nes --chr assets/chr_asset.chr
python -m nes_pascal.cli examples/nametable_loading.nsp -o build/nametable_loading.nes --chr assets/chr_asset.chr --nametable assets/nametable_loading.nam
python -m nes_pascal.cli examples/background_updates.nsp -o build/background_updates.nes --chr assets/chr_asset.chr --nametable assets/nametable_loading.nam
python -m nes_pascal.cli examples/scrolling_ppu_state.nsp -o build/scrolling_ppu_state.nes --mirroring horizontal
```

The examples demonstrate:

- `arithmetic.nsp`: unary and binary byte arithmetic;
- `boolean_expressions.nsp`: comparisons and Boolean operators;
- `conditionals.nsp`: simple, compound, and nested branches;
- `loops.nsp`: counting, nested control flow, `break`, and `continue`;
- `counting.nsp`: wrapping `inc` and `dec`, ascending and descending `for`
  loops, exact `$00` and `$FF` endpoints, and nested loops;
- `procedures.nsp`: forward procedure resolution, nested calls, shared global
  state, `JSR`/`RTS`, and a conditional inside a procedure;
- `procedure_parameters.nsp`: typed value parameters, left-to-right argument
  copies, mutable local parameter values, and nested parameterized calls;
- `scrolling_ppu_state.nsp`: one fixed nonzero scroll pair, a palette update,
  and restoration to the default `($00, $00)` pair;
- `memory_layout.nsp`: globals, procedure parameters, expressions, and a
  for-loop allocated through the deterministic runtime memory layout;
- `zero_page.nsp`: mandatory Zero Page temporaries, promoted globals, and a
  non-promoted regular-RAM fallback variable;
- `frame_synchronization.nsp`: runtime startup followed by a three-frame
  main-thread loop synchronized with `nes.wait_frame`.
- `frame_callbacks.nsp`: one main-thread update counter and one NMI VBlank
  counter, including a transitively validated VBlank-safe helper.
- `slow_update_callback.nsp`: a deliberately long update that crosses NMIs and
  demonstrates pending-frame coalescing without nested callbacks.
- `controller_input.nsp`: controller 1 movement, held A speed, B press/release
  appearance, Start reset, Select mode toggle, safe sprite-0 staging, OAM DMA,
  and two small embedded CHR tiles.
- `chr_asset.nsp`: inclusion of one project-relative raw CHR-ROM asset.
- `palette_support.nsp`: custom CHR data, initialized background and sprite
  palettes, then a safely queued full and individual palette update.
- `nametable_loading.nsp`: one project-relative raw 1 KiB nametable uploaded
  completely, including its attribute table, before rendering starts.
- `background_updates.nsp`: bounded and repeated tile writes, confirmed-shadow
  reads, rejected tile and attribute overflow, pending cancellation, explicit
  overflow clearing, and one raw attribute update after runtime starts.

The loop, counting, and procedure-parameter examples select background color
`$21` only when their expected final states are reached.

The `Makefile` shortcut builds the minimal program:

```text
make rom
```

Generated ROMs use the format described in
[Target platform](../runtime/target-platform.md).

Each command also writes a generated ld65 configuration beside the ROM using
the `.cfg` suffix and a human-readable CPU RAM report using `.map`. The map
lists reserved, runtime, compiler, user, and free regions plus the address of
every source variable and value parameter. See [CPU memory](../runtime/cpu-memory.md).

## CHR-ROM assets

Configure one raw CHR-ROM file with `--chr`:

```text
python -m nes_pascal.cli examples/chr_asset.nsp -o build/chr_asset.nes --chr assets/chr_asset.chr
```

Relative paths are resolved from the directory containing the `.nsp` source,
not from the compiler process working directory. `.` and `..` components and
platform-native separators are supported; absolute paths remain valid. NROM
currently requires exactly 8192 bytes (8 KiB). A missing, unreadable, or
incorrectly sized configured file stops compilation with a diagnostic. When
`--chr` is omitted, the compiler generates an empty 8 KiB CHR-ROM (except for
the existing fixed sprite-0 demonstration, which retains its internal tiles).

## Nametable assets

Programs using `nes.load_background();` configure either one raw 1024-byte
file or a 960-byte tile map plus a 64-byte attribute table:

```text
python -m nes_pascal.cli examples/nametable_loading.nsp -o build/nametable_loading.nes --chr assets/chr_asset.chr --nametable assets/nametable_loading.nam
python -m nes_pascal.cli game.nsp -o build/game.nes --nametable-tiles assets/screen.tiles --nametable-attributes assets/screen.attributes
```

The options are mutually exclusive forms. Split options must appear together.
Paths follow the same source-relative and normalized rules as `--chr`. See
[Background loading](../runtime/background-loading.md) for the raw layout,
initialization behavior, and current single-screen limits.

After `nes.run`, use `nes.set_tile`, `nes.get_tile`, `nes.set_attribute`,
`nes.clear_background_updates`, `nes.background_updates_overflowed`, and
`nes.clear_background_update_overflow` as described in
[Runtime background updates](../runtime/background-updates.md). At most four
tile or attribute bytes are uploaded during each VBlank.

## Running in Mesen

1. Generate `build/minimal.nes`.
2. Open Mesen.
3. Select **File > Open** and choose `build/minimal.nes`.
4. The display should remain stable with universal background color `$21`.

## Cleaning generated files

Remove build artifacts with:

```text
make clean
```
