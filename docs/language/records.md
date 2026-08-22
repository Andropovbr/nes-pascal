# Records

English | [Português (Brasil)](../pt-BR/language/records.md)

NES Pascal supports named, fixed-layout record types for grouping static game
data. Records are nominal value types: two declarations remain different types
even when their fields have the same names and layout.

## Declaration and layout

Declare records in the optional `type` section:

```pascal
type
    EnemyState = (Inactive, Active, Dead);
    Enemy = record
        X: byte;
        Y: byte;
        State: EnemyState;
        Visible: boolean;
    end;
```

Fields retain declaration order and names are case-insensitive within their
record. Duplicate fields produce E4019. The supported field types are `byte`,
`boolean`, and a declared enumeration. Each consumes exactly one byte;
booleans remain canonical `$00`/`$01` bytes and are not bit-packed. There is no
alignment or padding, so the example has offsets `X +0`, `Y +1`, `State +2`,
`Visible +3`, and size 4 bytes.

Record fields may not themselves be records or arrays. Direct recursive
definitions produce E4023 instead of attempting an infinite layout. Empty
records and layouts above 256 bytes are also rejected.

## Variables and fields

```pascal
var
    Player: Enemy;
    Result: byte;

begin
    Player.X := $20;
    Player.State := Active;
    Player.Visible := true;
    Result := Player.X;
end.
```

A record variable is one contiguous regular-RAM allocation whose size is the
record size. It is never automatically promoted to Zero Page, even when the
record contains one field. Field reads and writes use the exact field type, so
a raw byte cannot be assigned to an enum or Boolean field. Unknown fields
produce E4020 and field access on a scalar produces E4021.

Standalone fields have compile-time-known addresses. The backend emits direct
ca65 operands such as `variable_Player + 2`; there is no pointer calculation,
descriptor, reflection table, implicit initialization object, heap allocation,
or record runtime routine.

Whole records are not general expression values. Whole-record assignment,
comparison, procedure/function arguments, and returns are rejected; operate on
individual fields instead. The predefined `nes_rect` record is accepted by the
collision builtins as a direct, nominally typed reference. This narrow builtin
contract does not add general record value semantics.

Definite-assignment analysis follows the existing aggregate rule used for
arrays: after one field is assigned, the record variable is considered
initialized as a whole. The program remains responsible for assigning every
field it later reads.

## Arrays of records

```pascal
var
    Enemies: array[$00..$07] of Enemy;
    Index: byte;

begin
    Enemies[$03].X := $40;
    Enemies[Index].State := Active;
end.
```

The existing fixed-array rules apply, but total storage accounts for record
size. Eight 4-byte `Enemy` elements occupy exactly 32 contiguous regular-RAM
bytes. No per-element descriptor or hidden Zero Page byte is emitted.

For a constant index, the compiler folds the complete offset:

```text
base + (index * record size) + field offset
```

For a variable index, the backend explicitly converts the logical index to a
byte offset. Power-of-two sizes use local `asl` instructions (`2`, `4`, and `8`
bytes require one, two, and three shifts). Other sizes use a small inline,
deterministic repeated-addition sequence. Indexed assignments evaluate the
index first and preserve the scaled field offset on the 6502 hardware stack
while evaluating the right-hand side.

Variable indexed access is accepted only when every possible scaled offset for
the selected field fits in `$00..$FF`. Larger record arrays remain usable with
compile-time constant indexes, but a variable access that could truncate the
offset produces E4024. As with byte arrays, variable indexes have no runtime
bounds check; programs must keep them inside the declared range.

## Current limitations

There are no anonymous, nested, dynamic, variant, packed, inherited, or
method-bearing records. Records cannot be parameters or return values, and
there are no references, pointers, constructors, destructors, whole-record
operators, runtime type information, or multidimensional arrays.
