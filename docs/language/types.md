# Built-in types

NES Pascal provides three built-in types. Each occupies one byte, but the
types are distinct and are not implicitly converted.

## `nes_color`

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
