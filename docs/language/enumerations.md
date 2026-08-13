# Enumerations

English | [Português (Brasil)](../pt-BR/language/enumerations.md)

NES Pascal supports small user-defined enumeration types for finite domains
such as game states. An enum is a nominal type: its one-byte representation
does not make it interchangeable with `byte` or another enum type.

## Declaration and members

Declare enums in the optional `type` section, before `const` and `var`:

```pascal
type
    GameState = (Title, Playing, Paused, GameOver);
```

Members are unqualified compile-time constants in the program namespace. They
receive byte values in declaration order: `Title` is `$00`, `Playing` is `$01`,
`Paused` is `$02`, and `GameOver` is `$03`. An enum contains from one through
256 members. Member names are case-insensitive and must be unique; they also
cannot collide with another program-level symbol.

## Variables, assignments, and comparisons

```pascal
var
    State: GameState;
    PreviousState: GameState;
    IsGameOver: boolean;

begin
    State := Title;
    PreviousState := State;

    if PreviousState <> Paused then
        State := GameOver;

    IsGameOver := State = GameOver;
end.
```

Enum variables occupy exactly one byte and follow ordinary deterministic global
allocation, including the existing optional Zero Page-promotion policy. Members
occupy no RAM, ROM, Zero Page, runtime table, or metadata.

Assignments, equality (`=`), and inequality (`<>`) require the exact same enum
type. `GameState`, `Direction`, and `byte` remain distinct even when their
underlying values match. Enum comparisons produce normal canonical booleans;
when used directly by `if`, the backend branches from the byte comparison.

There is no implicit conversion to or from `byte`, and hexadecimal or Boolean
literals cannot be assigned to an enum. Enum arithmetic, `inc`/`dec`, ordered
comparisons, explicit numeric member values, enum constants declared in `const`,
arrays of enums, enum procedure parameters, and runtime reflection are not
implemented.

Global declarations retain the project's existing zero-filled startup behavior.
That naturally corresponds to an enum's first member, but the compiler does not
emit enum-specific initialization code; programs must still satisfy normal
definite-assignment rules before reading a variable.
