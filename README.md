# NES Pascal

NES Pascal is a prototype of a compiled, strongly typed language inspired by
Pascal and specialized for Nintendo Entertainment System games. The current
milestone supports strongly typed constants, variables, and assignments using
the one-byte `nes_color`, `byte`, and `boolean` types, plus byte arithmetic.
It also supports comparisons and short-circuit Boolean expressions. It
supports structured `if`/`else` statements and generates ca65 Assembly for an
NROM-256 image. Basic control flow also includes `while`, `repeat`/`until`,
`for`, `break`, and `continue`. Dedicated `inc` and `dec` operations provide
predictable one-byte counter updates. Parameterless procedures support
forward and nested acyclic calls.

## Prerequisites

- Python 3.11 or newer;
- GNU Make, optional for the `Makefile` shortcuts;
- [cc65](https://cc65.github.io/), with `ca65` and `ld65` on `PATH`;
- an NES emulator such as Mesen to run the ROM.

The compiler has no runtime Python dependencies outside the standard library.

## Installation

The compiler can run directly from the repository root. An editable
installation is optional:

```text
python -m pip install -e .
```

## Supported source

The minimal example exercises every built-in type:

```pascal
program Minimal;

const
    DefaultBackgroundColor: nes_color = $21;

var
    BackgroundColor: nes_color;
    FrameCounter: byte;
    RenderingEnabled: boolean;

begin
    BackgroundColor := DefaultBackgroundColor;
    FrameCounter := $00;
    RenderingEnabled := true;
    nes.set_background_color(BackgroundColor);
    nes.run;
end.
```

All types occupy one byte:

- `nes_color` accepts `$00..$3F`;
- `byte` accepts `$00..$FF`;
- `boolean` accepts only `false` and `true`.

Constants and variables require explicit types. Assignment uses `:=`, requires
an exact type match, and does not perform implicit conversion. Variables must
be assigned before they are read.

Arithmetic expressions are available only for `byte`. Binary `+` and `-` are
left-associative, unary `+` and `-` are supported, and parentheses control
grouping. Results wrap modulo 256, matching the one-byte 6502 operations.
There are no implicit conversions to or from `nes_color` or `boolean`.

See `examples/arithmetic.nsp` for a focused arithmetic example.

Comparisons produce `boolean` values. `=` and `<>` require operands of exactly
the same type, while `<`, `>`, `<=`, and `>=` accept only `byte`. Boolean
expressions use `not`, `and`, and `or`; the binary operators use
short-circuit evaluation.

See `examples/boolean_expressions.nsp` for all comparison and Boolean
operators.

Conditional statements accept a single statement or a compound `begin`/`end`
branch. Conditions must be `boolean`, `else` is optional, and conditionals may
be nested. Definite-assignment analysis follows both control-flow paths.

See `examples/conditionals.nsp` for simple, compound, and nested branches.

`while` and `repeat` loops require `boolean` conditions and may be nested.
`break` exits the nearest loop, while `continue` starts its next condition
check. Loop bodies may be single statements or structured statement
sequences.

The practical `examples/loops.nsp` program counts to a target, exercises
`break` and `continue`, counts back down with `repeat`/`until`, and selects
background color `$21` when the expected state is reached.

The `examples/counting.nsp` program demonstrates wrapping `inc`/`dec`
operations, ascending and descending `for` loops, exact `$00`/`$FF`
endpoints, and nested loops. It selects background color `$21` only when all
expected counter values are reached.

The `examples/procedures.nsp` program demonstrates forward procedure
resolution, nested calls, shared global state, `JSR`/`RTS`, and a conditional
inside a procedure.

## Compilation

Compile the minimal example with:

```text
python -m nes_pascal.cli examples/minimal.nsp -o build/minimal.nes
```

Compile the arithmetic example with:

```text
python -m nes_pascal.cli examples/arithmetic.nsp -o build/arithmetic.nes
```

Compile the Boolean-expression example with:

```text
python -m nes_pascal.cli examples/boolean_expressions.nsp -o build/boolean_expressions.nes
```

Compile the conditional example with:

```text
python -m nes_pascal.cli examples/conditionals.nsp -o build/conditionals.nes
```

Compile the practical loop example with:

```text
python -m nes_pascal.cli examples/loops.nsp -o build/loops.nes
```

Compile the counting example with:

```text
python -m nes_pascal.cli examples/counting.nsp -o build/counting.nes
```

Compile the procedure example with:

```text
python -m nes_pascal.cli examples/procedures.nsp -o build/procedures.nes
```

Or use:

```text
make rom
```

The command generates `build/minimal.asm`, the intermediate
`build/minimal.o`, and `build/minimal.nes`. The image has an iNES header,
32 KiB of PRG-ROM, and 8 KiB of empty CHR-ROM.

## Tests

Run the complete suite with:

```text
python -m unittest discover -s tests -v
```

Or:

```text
make test
```

The integration test assembles and links the ROM, then validates its header,
mapper, banks, vectors, CHR data, and final size. It is skipped with an
explicit message when `ca65` or `ld65` is unavailable.

To include the optional headless Mesen behavior test, point `MESEN_PATH` to
the emulator executable before running the suite. The test compiles
the behavior examples, executes their ROMs, and verifies final variables and
the universal background color:

```powershell
$env:MESEN_PATH = "C:\path\to\Mesen.exe"
python -m unittest discover -s tests -v
```

The test is skipped clearly when Mesen or the cc65 toolchain is unavailable.

Remove build artifacts with:

```text
make clean
```

## Running in Mesen

1. Generate `build/minimal.nes`.
2. Open Mesen.
3. Select **File > Open** and choose `build/minimal.nes`.
4. The display should remain stable with universal background color `$21`.

## Architecture

The pipeline is deliberately separated:

```text
.nsp source
  -> lexer
  -> parser
  -> AST
  -> semantic validation, name resolution, and type checking
  -> resolved AST
  -> ca65 backend
  -> ca65
  -> ld65
  -> ROM
```

- `lexer.py` produces tokens with line and column information;
- `parser.py` validates grammar and builds the parsed AST in `ast.py`;
- `semantic.py` validates declarations, resolves references and procedure
  calls, checks exact types, and enforces interprocedural definite assignment;
- `backend_ca65.py` generates readable, commented Assembly from resolved
  values and allocates variables in regular CPU RAM;
- `cli.py` writes Assembly and coordinates ca65 and ld65;
- `nrom.cfg` defines the 32 KiB PRG and 8 KiB CHR NROM layout.

Ordinary source errors are displayed without a stack trace and include an
error code, file, line, column, source excerpt, and correction hint.
See the complete [diagnostics reference](docs/DIAGNOSTICS.md) for stable codes,
examples, and suggested fixes.

## Current limitations

- statements are limited to assignment, `inc`/`dec`, `if`/`else`, basic
  loops, `break`/`continue`, `nes.set_background_color`, and `nes.run`;
- `nes_color`, `byte`, and `boolean` are the only built-in types;
- `nes_color` and `byte` initializers use hexadecimal literals, while
  `boolean` uses `true` or `false`;
- constants cannot refer to other constants;
- arithmetic is limited to `byte` operands with unary `+` and `-`, binary `+`
  and `-`, and parentheses;
- equality and inequality require matching types; ordered comparisons are
  limited to `byte`;
- Boolean expressions support only `not`, `and`, and `or`;
- conditional branches support assignments and nested conditionals; NES
  runtime commands remain top-level only;
- loops support `while`, `repeat`/`until`, `break`, and `continue`, but execute
  only during initialization before `nes.run`;
- `for` supports only `byte` control variables and bounds; its control
  variable cannot be changed inside the body;
- procedures have no parameters, return values, or local variables;
- procedure calls may be nested but cannot be recursive;
- variables use regular RAM; zero-page allocation is not implemented;
- there is no multiplication, division, functions, sprites, controller input,
  audio, runtime strings, recursion, or general optimization pass;
- only NTSC NES, mapper 0, 32 KiB PRG-ROM, and 8 KiB CHR-ROM are supported;
- CHR-ROM is empty, and the backend does not provide a game engine.
