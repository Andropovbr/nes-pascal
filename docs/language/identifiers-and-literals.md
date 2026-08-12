# Identifiers and literals

English | [Português (Brasil)](../pt-BR/language/identifiers-and-literals.md)

## Identifiers

Identifiers:

- begin with a letter;
- may contain letters, digits, and `_`;
- are case-insensitive;
- preserve their original spelling for diagnostics.

Constants, variables, and procedures share one case-insensitive namespace.

## Hexadecimal literals

Hexadecimal values use the `$` prefix:

```pascal
$00
$21
$FF
```

Hexadecimal literals initialize `nes_color` and `byte` values. Boolean values
use the `true` and `false` keywords.

The valid numeric range depends on the expected type. See
[Built-in types](types.md).
