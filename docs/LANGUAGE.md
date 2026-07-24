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

## Comparisons

Every comparison produces a normalized `boolean` value: `$00` for `false` or
`$01` for `true`.

Equality and inequality use `=` and `<>`. Both operands must have exactly the
same type. They support `byte`, `nes_color`, and `boolean`:

```pascal
Equal := Counter = Limit;
Different := BackgroundColor <> $0F;
SameState := Enabled = true;
```

Ordered comparisons use `<`, `>`, `<=`, and `>=`. They accept only `byte`
operands and use unsigned one-byte ordering:

```pascal
BelowLimit := Counter < Limit;
AtLeastOne := Counter >= $01;
```

Comparing different types or using `nes_color` or `boolean` with an ordered
operator produces E4004.

## Boolean expressions

The operators `not`, `and`, and `or` accept only `boolean` operands and
produce a normalized `boolean` result:

```pascal
Ready := Enabled and not Paused;
InRange := (Counter >= Minimum) and (Counter <= Maximum);
```

`and` and `or` evaluate from left to right and short-circuit. The right
operand of `and` is skipped when the left operand is `false`; the right
operand of `or` is skipped when the left operand is `true`.

Expression precedence, from highest to lowest, is:

1. parentheses;
2. unary `+`, unary `-`, and `not`;
3. binary `+` and `-`;
4. comparisons;
5. `and`;
6. `or`.

Use parentheses to negate a comparison:

```pascal
Different := not (Counter = Limit);
```

## Conditional statements

An `if` condition must have type `boolean`. A conditional may contain one
statement:

```pascal
if Enabled then
    Counter := $01;
```

The optional `else` branch follows Pascal semicolon placement. There is no
semicolon between the final statement of the `then` branch and `else`; one
semicolon terminates the complete conditional:

```pascal
if Enabled then
    Counter := $01
else
    Counter := $02;
```

Use `begin` and `end` for a branch containing multiple statements:

```pascal
if Enabled then
begin
    Counter := Counter + $01;
    Ready := true;
end
else
begin
    Counter := $00;
    Ready := false;
end;
```

Conditionals may be nested. An `else` without an enclosing branch block
belongs to the nearest unmatched `if`.

Definite-assignment analysis follows control flow. A variable assigned in both
branches of an `if/else` is assigned afterward. An assignment made only in
the `then` branch, or in an `if` without `else`, is not guaranteed afterward.

`nes.set_background_color` and `nes.run` are initialization commands and must
remain in the top-level program block. Placing either command inside a
conditional produces E3009.

The backend emits a nearby relative branch followed by an absolute `JMP`.
This keeps conditional branches valid even when a branch body exceeds the
6502 relative-branch range.

## Loops

### `while`

`while` checks a `boolean` condition before each iteration:

```pascal
while Counter < Limit do
    Counter := Counter + $01;
```

A compound body uses `begin` and `end`:

```pascal
while Running do
begin
    Counter := Counter + $01;
    Running := Counter < Limit;
end;
```

### `repeat` / `until`

`repeat` executes its body before checking its `boolean` condition, so the
body runs at least once:

```pascal
repeat
    Counter := Counter - $01;
until Counter = $00;
```

### Loop control

`break` exits the nearest enclosing loop. `continue` transfers control to the
nearest loop's next condition check:

```pascal
while Counter < Limit do
begin
    Counter := Counter + $01;
    if Counter = SkipValue then
        continue;
    if Counter = StopValue then
        break;
end;
```

Using either statement outside a loop produces E3010. Loops may be nested;
`break` and `continue` always target the innermost loop.

Definite-assignment analysis is intentionally conservative. Assignments made
only inside a loop are not considered guaranteed after the loop because a
`while` body may not execute and loop control may skip statements. Assign
values before entering a loop when they are needed afterward or in a
`repeat` condition.

NES initialization commands cannot be placed inside loops. Doing so produces
E3011. Current loops execute only during startup before `nes.run`; they are
not frame-based loops and cannot yet implement timed gameplay behavior.

The backend uses absolute jumps for loop back edges and exits, with relative
branches targeting only nearby labels. Large and nested loop bodies therefore
do not depend on the 6502 relative-branch range.

## Increment and decrement operations

`inc` and `dec` update an initialized `byte` variable. The one-argument forms
add or subtract one:

```pascal
inc(Counter);
dec(Counter);
```

An optional `byte` expression specifies the amount:

```pascal
inc(Counter, Step);
dec(Counter, Step + $01);
```

Updates wrap modulo 256, like other `byte` arithmetic. Incrementing `$FF`
produces `$00`; decrementing `$00` produces `$FF`. The one-argument forms
generate the 6502 `INC` and `DEC` instructions directly. The target must
already be assigned because an update reads its previous value.

## `for` loops

An ascending `for` loop includes both bounds:

```pascal
for Index := $00 to $03 do
    inc(Total);
```

A descending loop uses `downto`:

```pascal
for Index := $03 downto $00 do
begin
    inc(Total, $02);
end;
```

The control variable, initial expression, and final expression must all have
type `byte`. The compiler assigns the initial value before evaluating and
caching the final value. The final expression is evaluated exactly once.
The body may be a single statement or a `begin`/`end` block, and `for` loops
may be nested.

The control variable is definitely assigned after the loop, even when the
initial range is empty, because initialization occurs before the first range
check. A non-empty loop that completes normally leaves it at the final value;
an empty range leaves it at the initialized value. Assigning the control
variable, applying `inc` or `dec` to it, or reusing it as a nested loop's
control variable produces E3012.

`break` exits a `for` loop. `continue` advances to its next value. Endpoint
checks occur before increment or decrement, so `$FF` for `to` and `$00` for
`downto` terminate without wrapping into another iteration. The backend uses
nearby relative branches and absolute jumps so large bodies remain valid.

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
- type inference;
- implicit conversions;
- `case`;
- arrays or records;
- inline Assembly;
- sprites, controller input, or audio.

These features must be added only in explicitly requested milestones.
