# NES Pascal

NES Pascal is a prototype of a compiled, strongly typed language inspired by
Pascal and specialized for Nintendo Entertainment System games. The current
milestone supports strongly typed constants, variables, and assignments using
the one-byte `nes_color`, `byte`, and `boolean` types, plus byte arithmetic.
It generates ca65 Assembly for an NROM-256 image.

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

## Compilation

Compile the minimal example with:

```text
python -m nes_pascal.cli examples/minimal.nsp -o build/minimal.nes
```

Compile the arithmetic example with:

```text
python -m nes_pascal.cli examples/arithmetic.nsp -o build/arithmetic.nes
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
- `semantic.py` validates declarations, resolves references, checks exact
  assignment types, and rejects reads before assignment;
- `backend_ca65.py` generates readable, commented Assembly from resolved
  values and allocates variables in regular CPU RAM;
- `cli.py` writes Assembly and coordinates ca65 and ld65;
- `nrom.cfg` defines the 32 KiB PRG and 8 KiB CHR NROM layout.

Ordinary source errors are displayed without a stack trace and include an
error code, file, line, column, source excerpt, and correction hint.
See the complete [diagnostics reference](docs/DIAGNOSTICS.md) for stable codes,
examples, and suggested fixes.

## Current limitations

- only `program`, optional `const` and `var` sections, assignment,
  `nes.set_background_color`, and `nes.run` are supported;
- `nes_color`, `byte`, and `boolean` are the only built-in types;
- `nes_color` and `byte` initializers use hexadecimal literals, while
  `boolean` uses `true` or `false`;
- constants cannot refer to other constants;
- arithmetic is limited to `byte` operands with unary `+` and `-`, binary `+`
  and `-`, and parentheses;
- variables use regular RAM; zero-page allocation is not implemented;
- there are no multiplication, division, comparisons, boolean expressions,
  procedures, sprites, controller input, audio, runtime strings, recursion,
  or optimizations;
- only NTSC NES, mapper 0, 32 KiB PRG-ROM, and 8 KiB CHR-ROM are supported;
- CHR-ROM is empty, and the backend does not provide a game engine.
