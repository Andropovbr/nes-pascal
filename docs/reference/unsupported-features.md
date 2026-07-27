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
  not supported.
- Procedures have no parameters, return values, or local variables.
- Procedure calls may be nested but cannot be recursive.
- Dynamic memory and object orientation are not supported.

## Statement and execution limitations

- Statements are limited to assignment, `inc` and `dec`, `if`/`else`,
  supported loops, `break`, `continue`, procedure calls,
  `nes.set_background_color`, and `nes.run`.
- Conditional branches and loop bodies may contain supported statements, but
  NES runtime commands remain top-level only.
- `while`, `repeat`/`until`, and `for` loops execute only during initialization
  before `nes.run`; they are not frame-based gameplay loops.
- `for` supports only `byte` control variables and bounds. A control variable
  cannot be modified inside its loop body.

## Runtime and target limitations

- Variables use regular CPU RAM; zero-page allocation is not implemented.
- Only NTSC NES, mapper 0, 32 KiB PRG-ROM, and 8 KiB CHR-ROM are supported.
- CHR-ROM is empty.
- Sprites, controller input, audio, graphics assets, and frame callbacks are
  not supported.
- The compiler does not provide a game engine or a general optimization pass.
