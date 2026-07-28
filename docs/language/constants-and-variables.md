# Constants and variables

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

Constant initializers are literal-only. They cannot refer to other constants
or contain arithmetic expressions.

## Variables

Variable declarations appear after the optional `const` section and before
procedure declarations and the main block:

```pascal
var
    BackgroundColor: nes_color;
    Counter: byte;
    Enabled: boolean;
```

Each declaration contains exactly one identifier and an explicit built-in
type. Storage is deterministic. A global referenced by at least three source
operations is eligible for automatic Zero Page promotion in declaration
order. If optional promotion space is unavailable, it falls back to regular
RAM without changing its symbol or behavior. Other globals and every procedure
value parameter use regular RAM. The compiler reports an error before linking
if mandatory temporaries or regular RAM are exhausted. See the
[CPU memory reference](../runtime/cpu-memory.md).

## Names and duplicate declarations

Constant, variable, and procedure names share one case-insensitive namespace.
Duplicate declarations are errors. Original spelling is retained for
diagnostics.

Procedure parameters use a local namespace. Their names must be unique within
the declaration and cannot shadow a global symbol. Different procedures may
reuse the same parameter name.

Variables receive values through [assignments](assignments.md) or other
supported update statements; a declaration does not initialize its variable.
