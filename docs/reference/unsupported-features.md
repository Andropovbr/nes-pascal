# Unsupported features

This page lists important limits of the currently implemented language,
runtime, and target. Planned work is tracked in the
[project roadmap](../../roadmap/README.md); an unchecked roadmap item is not part of
the supported language.

## Language limitations

- `nes_color`, `byte`, and `boolean` are the only built-in types.
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
- `case`, arrays, records, functions, runtime strings, and inline Assembly are
  not supported. The three fixed controller query intrinsics are the only
  function-shaped expressions.
- Procedure parameters are limited to `byte` and `boolean` values. There are
  no reference parameters, default values, return values, or general local
  variables.
- Procedure calls may be nested but cannot be recursive.
- Dynamic memory and object orientation are not supported.

## Statement and execution limitations

- Statements are limited to assignment, `inc` and `dec`, `if`/`else`,
  supported loops, `break`, `continue`, procedure calls,
  `nes.set_background_color`, `nes.run`, `nes.wait_frame`, `nes.on_update`,
  `nes.on_vblank`, and the fixed controller-example `nes.set_sprite_zero`
  helper.
- Conditional branches and loop bodies may contain supported statements, but
  NES initialization commands remain top-level only. `nes.wait_frame` is the
  sole runtime command allowed in main-block control flow.
- Frame-synchronized loops and update callbacks run on the main thread. NMI
  may invoke only one statically registered, transitively validated VBlank
  callback.
- `for` supports only `byte` control variables and bounds. A control variable
  cannot be modified inside its loop body.

## Runtime and target limitations

- Automatic Zero Page promotion is limited to the deterministic global-variable
  policy. Explicit Zero Page declarations are not implemented.
- Only NTSC NES, mapper 0, 32 KiB PRG-ROM, and 8 KiB CHR-ROM are supported.
- CHR-ROM remains empty unless the fixed sprite-0 demonstration helper is
  used; that helper embeds two internal 8x8 player tiles.
- Standard controllers 1 and 2 are supported without remapping, Four Score,
  expansion devices, buffering, combos, turbo, or DMC-safe repeated reads.
- General sprites, audio, and user-provided graphics assets are not supported.
  `nes.set_sprite_zero` stages hardware sprite 0 only and is not a sprite API.
- Callback registration is static. There is only one callback of each kind,
  with no parameters, return values, priorities, lists, removal, indirect
  calls, IRQ callbacks, or user-owned interrupt handlers.
- There is no generic PPU command queue. The current runtime exposes no
  rendering-time PPU write command; initialization palette writes remain
  restricted to the rendering-disabled phase.
- The compiler does not provide a game engine or a general optimization pass;
  Zero Page promotion is a fixed allocation policy, not a hotness optimizer.
