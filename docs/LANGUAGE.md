# NES Pascal language

## Status

This specification describes only the currently implemented subset. The syntax
is inspired by Pascal, but the language is not intended to be compatible with
Pascal or Free Pascal.

## Minimal program structure

A program contains:

1. the `program` keyword;
2. a program name;
3. a semicolon;
4. an optional `const` section;
5. an optional `var` section;
6. a block beginning with `begin`;
7. a sequence of statements;
8. the `end` keyword;
9. a final period.

Example:

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

## Identifiers

Identifiers:

- begin with a letter;
- may contain letters, digits, and `_`;
- are case-insensitive in the current prototype;
- preserve their original spelling for diagnostics.

## Hexadecimal literals

Hexadecimal values use the `$` prefix:

```pascal
$00
$21
$FF
```

Hexadecimal literals initialize `nes_color` and `byte` values. Boolean values
use the `true` and `false` keywords.

## Constants

A constant declaration has this grammar:

```text
Identifier : Type = Literal ;
```

Declarations appear in a `const` section between the program header and the
main block:

```pascal
const
    BackgroundColor: nes_color = $21;
```

Every constant requires an explicit type. `nes_color` and `byte` constants use
hexadecimal initializers; `boolean` constants use `true` or `false`. There is
no type inference.
Constant names are resolved case-insensitively, and duplicate declarations are
errors.

## Built-in types

### `nes_color`

`nes_color` occupies one byte and represents an NES palette value. Its allowed
range is `$00..$3F`.

Valid:

```pascal
const
    BackgroundColor: nes_color = $21;
```

Invalid:

```pascal
const
    BackgroundColor: nes_color = $80;
```

Expected diagnostic:

```text
E4002 path/to/source.nsp:4:34

Value $80 is not valid for type nes_color.

Allowed range: $00..$3F.
```

### `byte`

`byte` occupies one byte and accepts hexadecimal values from `$00` through
`$FF`.

```pascal
const
    Maximum: byte = $FF;
```

A larger value produces `E4003`.

### `boolean`

`boolean` occupies one byte. `false` is represented by zero and `true` by one.
No hexadecimal-to-boolean conversion is allowed.

```pascal
const
    RenderingEnabled: boolean = true;
```

## Variables

Variable declarations appear after the optional `const` section and before
`begin`:

```pascal
var
    BackgroundColor: nes_color;
    Counter: byte;
    Enabled: boolean;
```

Each declaration contains exactly one identifier and an explicit built-in
type. Variable and constant names share one case-insensitive namespace.
Variables are allocated as one-byte values in regular CPU RAM. Zero-page
allocation is not part of this milestone.

## Assignment

Assignment uses `:=`:

```pascal
BackgroundColor := $21;
Counter := $FF;
Enabled := true;
```

The right-hand side may be:

- a hexadecimal literal;
- `true` or `false`;
- a constant reference;
- a previously assigned variable reference;
- a `byte` arithmetic expression.

Both sides must have exactly the same type. There are no implicit conversions.
Reading a variable before an earlier assignment is a compilation error.
Constants cannot be assignment targets.

Assignment diagnostics preserve the earliest primary error:

- E4002 reports a `nes_color` value outside `$00..$3F`;
- E4004 reports incompatible source and target types, including hexadecimal
  literals assigned to `boolean`;
- E3008 reports a variable read before assignment.

Whole-program checks such as E3003 run only after statement-level semantic
analysis succeeds. See [DIAGNOSTICS.md](DIAGNOSTICS.md) for the complete
diagnostic reference and examples.

## Arithmetic expressions

Arithmetic is defined only for `byte` values. Operands may be hexadecimal
literals, `byte` constants, previously assigned `byte` variables, or nested
arithmetic expressions.

Supported operators:

- unary `+`, which leaves the value unchanged;
- unary `-`, which computes the two's-complement negation;
- binary `+`;
- binary `-`.

Parentheses group expressions. Unary operators bind more tightly than binary
operators. Binary `+` and `-` have equal precedence and associate from left to
right:

```pascal
Counter := $08 - $03 + $01;
Result := -(Counter + Step);
```

All results wrap modulo 256. For example, `$FF + $01` produces `$00`, and
`$00 - $01` produces `$FF`. This behavior directly reflects one-byte 6502
arithmetic.

Arithmetic expressions always have type `byte`. They cannot be assigned to
`nes_color` or `boolean`, and those types cannot be used as operands. The
compiler reports E4004 for these incompatible uses.

Constant declarations remain literal-only in this milestone; their
initializers cannot contain arithmetic expressions.

## Initial commands

### `nes.set_background_color`

Sets the universal NES background palette color.

Syntax with a constant reference:

```pascal
nes.set_background_color(BackgroundColor);
```

Direct hexadecimal literals remain supported:

```pascal
nes.set_background_color($21);
```

The argument must resolve to a valid `nes_color`. It may also be a previously
assigned `nes_color` variable:

```pascal
BackgroundColor := $21;
nes.set_background_color(BackgroundColor);
```

### `nes.run`

Completes initial configuration and keeps the program running.

```pascal
nes.run;
```

In the current milestone it:

- must appear exactly once;
- must be the final command in the block;
- causes commands after it to be rejected.

## Unsupported features

The current milestone does not support:

- `type` declarations;
- procedures;
- functions;
- user-defined parameters;
- multiplication or division;
- comparisons or boolean expressions;
- type inference;
- implicit conversions;
- `if`, `while`, `for`, or `case`;
- arrays or records;
- inline Assembly;
- sprites, controller input, or audio.

These features must be added only in explicitly requested milestones.
