# Built-in types

NES Pascal provides four built-in types. Each occupies one byte, but the
types are distinct and are not implicitly converted.

## `nes_color`

`nes_color` occupies one byte and represents an NES palette value. Its allowed
range is `$00..$3F`.

The same range is enforced for scalar assignments, universal background-color
calls, full background and sprite palettes, and individual palette colors.
Values are never wrapped or masked into range.

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

## `byte`

`byte` occupies one byte and accepts hexadecimal values from `$00` through
`$FF`.

```pascal
const
    Maximum: byte = $FF;
```

A larger value produces E4003.

## `boolean`

`boolean` occupies one byte. `false` is represented by zero and `true` by one.
No hexadecimal-to-boolean conversion is allowed.

```pascal
const
    RenderingEnabled: boolean = true;
```

Assignments and operator operands must obey the exact type rules described in
[Assignments](assignments.md) and [Expressions](expressions.md).

## `sprite`

`sprite` is a strongly typed hardware OAM index. It occupies one byte, but its
allowed values are `$00..$3F`, selecting the NES's 64 hardware sprites.

```pascal
const
    PlayerSprite: sprite = $00;
```

A value above `$3F` produces E4008. `sprite` is not implicitly interchangeable
with `byte`, does not support arithmetic or `inc`/`dec`, and is passed directly
to the [hardware sprite API](../runtime/sprites.md).

Procedure value parameters currently support only `byte` and `boolean`.
`nes_color` and `sprite` remain valid for constants and global variables but
produce E4005 when used as a parameter type.
