# Expressions

English | [Português (Brasil)](..\pt-BR\language\expressions.md)

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

Constant declarations are literal-only; their initializers cannot contain
arithmetic expressions.

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

The operators `not`, `and`, and `or` accept only `boolean` operands and produce
a normalized `boolean` result:

```pascal
Ready := Enabled and not Paused;
InRange := (Counter >= Minimum) and (Counter <= Maximum);
```

`and` and `or` evaluate from left to right and short-circuit. The right operand
of `and` is skipped when the left operand is `false`; the right operand of `or`
is skipped when the left operand is `true`.

The controller queries `nes.controller_down`, `nes.controller_pressed`, and
`nes.controller_released` are built-in boolean expressions. They accept a
compile-time controller index and exactly one `nes.button_*` constant. See
[Controller input](../runtime/controller-input.md) for frame-transition
semantics and the complete button list.

## Precedence

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
