# Unsupported features

This page lists important limits of the currently implemented language,
runtime, and target. Planned work is tracked in the
[project roadmap](../../roadmap/README.md); an unchecked roadmap item is not part of
the supported language.

## Language limitations

- `nes_color`, `byte`, `boolean`, `sprite`, and `metasprite` are the only
  built-in types.
- `type` declarations and user-defined types are not supported.
- Constants cannot refer to other constants, and constant initializers cannot
  contain expressions.
- Type inference and implicit conversions are not supported.
- Arithmetic is limited to `byte` operands with unary `+` and `-`, binary `+`
  and `-`, and parentheses.
- Multiplication and division are not supported.
- Equality and inequality require matching types; ordered comparisons are
  limited to `byte`.
- Boolean expressions support only `not`, `and`, and `or`.
- `case`, arrays, records, general functions, runtime strings, and inline
  Assembly are not supported. A small fixed set of built-in query expressions
  and the statically resolved `nes.sprite_create()` and
  `nes.metasprite_create(frame)` intrinsics are supported.
- Procedure parameters are limited to `byte` and `boolean` values. There are
  no reference parameters, default values, return values, or general local
  variables.
- Procedure calls may be nested but cannot be recursive.
- Dynamic memory and object orientation are not supported.

## Statement and execution limitations

- Statements are limited to assignment, `inc` and `dec`, `if`/`else`,
  supported loops, `break`, `continue`, procedure calls,
  the palette APIs, `nes.load_background`, `nes.set_background_color`,
  `nes.set_scroll`, the `nes.sprite_*` hardware sprite primitives, compile-time
  `nes.import_metasprite`, and the `nes.metasprite_*` primitives,
  `nes.run`, `nes.wait_frame`,
  `nes.on_update`, `nes.on_vblank`, and the fixed controller-example
  `nes.set_sprite_zero` helper.
- Conditional branches and loop bodies may contain supported statements, but
  `nes.run` and callback registration remain top-level only. Palette calls in
  runtime control flow or procedures are staged for VBlank.
- Frame-synchronized loops and update callbacks run on the main thread. NMI
  may invoke only one statically registered, transitively validated VBlank
  callback.
- `for` supports only `byte` control variables and bounds. A control variable
  cannot be modified inside its loop body.

## Runtime and target limitations

- Automatic Zero Page promotion is limited to the deterministic global-variable
  policy. Explicit Zero Page declarations are not implemented.
- Only NTSC NES, mapper 0, 32 KiB PRG-ROM, and 8 KiB CHR-ROM are supported.
- One raw, exactly 8 KiB CHR-ROM file is supported. CHR-RAM, multiple files or
  banks, graphics conversion, compression, and runtime CHR updates are not.
- One raw 1 KiB nametable for nametable 0 is supported during initialization,
  either combined or as 960 tile bytes plus 64 attribute bytes, followed by at
  most four queued tile or raw attribute-byte updates per frame. Multiple
  screens, generated nametables, alternate nametable selection, scrolling
  gameplay systems, and streaming are not supported. One fixed scroll pair
  can be staged with `nes.set_scroll`.
- Standard controllers 1 and 2 are supported without remapping, Four Score,
  expansion devices, buffering, combos, turbo, or DMC-safe repeated reads.
- Hardware sprite primitives support all 64 OAM entries, individual fields,
  palette/flip/priority attributes, deterministic hide/show, static individual
  allocation, and NMI OAM DMA. Metasprites support statically owned arbitrary
  component layouts, manual frame selection, whole-object position,
  visibility, flip, and hardware-sprite clipping. Runtime creation/destruction,
  automatic animation/timing, collision, sprite multiplexing/flickering,
  sorting, and scanline-overflow mitigation are not supported.
  `nes.set_sprite_zero` remains a legacy compatibility helper.
- Callback registration is static. There is only one callback of each kind,
  with no parameters, return values, priorities, lists, removal, indirect
  calls, IRQ callbacks, or user-owned interrupt handlers.
- There is no generic PPU command queue. Runtime palette changes use one fixed
  shadow and bounded VBlank uploader; other rendering-time PPU writes remain
  unsupported.
- The compiler does not provide a game engine or a general optimization pass;
  Zero Page promotion is a fixed allocation policy, not a hotness optimizer.
