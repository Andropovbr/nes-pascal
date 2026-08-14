# Built-in types

English | [Português (Brasil)](../pt-BR/language/types.md)

NES Pascal provides five built-in types. Each occupies one byte, but the
types are distinct and are not implicitly converted. It also supports
[user-defined enumerations](enumerations.md), which are nominal one-byte types,
and named [records](records.md), which are nominal fixed-layout aggregate types.

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
var
    PlayerSprite: sprite;

begin
    PlayerSprite := nes.sprite_create();
end;
```

A value above `$3F` produces E4008. `sprite` is not implicitly interchangeable
with `byte`, does not support arithmetic or `inc`/`dec`, and is passed directly
to the [hardware sprite API](../runtime/sprites.md). `nes.sprite_create()`
produces a statically reserved `sprite` value; it is not a general function or
runtime object allocation.

## `metasprite`

`metasprite` is an opaque one-byte identity for a statically created logical
object composed of several hardware sprites. It is not an OAM index and no
hexadecimal literal can be converted to it.

```pascal
var
    Player: metasprite;

begin
    nes.import_metasprite(player);
    Player := nes.metasprite_create(player.idle_0);
end;
```

Each creation site has a stable identity and statically owned component slots.
The type supports assignment and the [metasprite API](../runtime/metasprites.md),
but not arithmetic, comparisons, `inc`, `dec`, constants, or procedure
parameters. E4009 rejects numeric values in a metasprite context.

Imported frame and animation names are internal compile-time symbol kinds, not
user-declarable built-in types. Frame symbols select creation/manual frames;
animation symbols are accepted only by the
[sprite-animation API](../runtime/sprite-animation.md). Neither can be stored
in a variable or synthesized from a byte.

Procedure value parameters currently support only `byte` and `boolean`.
`nes_color`, `sprite`, and `metasprite` remain valid global types but produce
E4005 when used as a parameter type. `nes_color` and `sprite` also support
typed constants; `metasprite` identities come only from creation sites.
