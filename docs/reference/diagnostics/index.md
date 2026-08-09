# Compiler diagnostics

Diagnostic codes are part of the compiler's public API. Once retired, a code
must never be assigned to a different diagnostic. Future diagnostics must use
the range reserved for their category.

## Diagnostic code ranges

| Range | Category | Details |
| --- | --- | --- |
| E1000-E1999 | Lexical Analysis | [Lexical diagnostics](lexical.md) |
| E2000-E2999 | Parser / Syntax | [Syntax diagnostics](syntax.md) |
| E3000-E3999 | Semantic Analysis | [Semantic diagnostics](semantic.md) |
| E4000-E4999 | Type System | [Type-system diagnostics](type-system.md) |
| E5000-E5999 | Code Generation | [Code-generation diagnostics](code-generation.md) |
| E6000-E6999 | Runtime Validation | [Runtime-validation diagnostics](runtime-validation.md) |
| W1000-W1999 | Warnings | Reserved; no warnings are emitted |
| I1000-I1999 | Informational Messages | Reserved; no informational messages are emitted |

## Diagnostic index

| Code | Category | Description |
| --- | --- | --- |
| [E1000](lexical.md) | Lexical Analysis | Unexpected character |
| [E1002](lexical.md) | Lexical Analysis | Malformed hexadecimal literal |
| [E2101](syntax.md) | Parser / Syntax | Unknown command |
| [E2102](syntax.md) | Parser / Syntax | Invalid syntax |
| [E3001](semantic.md) | Semantic Analysis | Missing `nes.run` |
| [E3002](semantic.md) | Semantic Analysis | Statement after `nes.run` |
| [E3003](semantic.md) | Semantic Analysis | Invalid background-color call count |
| [E3004](semantic.md) | Semantic Analysis | Duplicate symbol |
| [E3005](semantic.md) | Semantic Analysis | Unknown identifier |
| [E3006](semantic.md) | Semantic Analysis | Assignment to constant |
| [E3007](semantic.md) | Semantic Analysis | Unknown assignment target |
| [E3008](semantic.md) | Semantic Analysis | Variable read before assignment |
| [E3009](semantic.md) | Semantic Analysis | Runtime command inside conditional |
| [E3010](semantic.md) | Semantic Analysis | Loop control outside loop |
| [E3011](semantic.md) | Semantic Analysis | Runtime command inside loop |
| [E3012](semantic.md) | Semantic Analysis | For control variable modification |
| [E3013](semantic.md) | Semantic Analysis | Unknown procedure |
| [E3014](semantic.md) | Semantic Analysis | Recursive procedure call |
| [E3015](semantic.md) | Semantic Analysis | Runtime command inside procedure |
| [E3016](semantic.md) | Semantic Analysis | Incorrect procedure argument count |
| [E3017](semantic.md) | Semantic Analysis | Frame wait before runtime start |
| [E3018](semantic.md) | Semantic Analysis | Unknown callback procedure |
| [E3019](semantic.md) | Semantic Analysis | Invalid callback signature |
| [E3020](semantic.md) | Semantic Analysis | Duplicate update callback |
| [E3021](semantic.md) | Semantic Analysis | Duplicate VBlank callback |
| [E3022](semantic.md) | Semantic Analysis | Invalid callback registration context |
| [E3023](semantic.md) | Semantic Analysis | VBlank-unsafe operation |
| [E3024](semantic.md) | Semantic Analysis | Invalid callback call graph |
| [E3025](semantic.md) | Semantic Analysis | Conflicting callback registration |
| [E3026](semantic.md) | Semantic Analysis | Invalid controller index |
| [E3027](semantic.md) | Semantic Analysis | Dynamic controller index |
| [E3028](semantic.md) | Semantic Analysis | Invalid controller button |
| [E3029](semantic.md) | Semantic Analysis | Invalid controller argument count |
| [E3030](semantic.md) | Semantic Analysis | Invalid sprite-zero argument count |
| [E3031](semantic.md) | Semantic Analysis | Invalid background palette index |
| [E3032](semantic.md) | Semantic Analysis | Invalid sprite palette index |
| [E3033](semantic.md) | Semantic Analysis | Invalid palette color index |
| [E3034](semantic.md) | Semantic Analysis | Invalid palette argument count |
| [E3035](semantic.md) | Semantic Analysis | Invalid background-load argument count |
| [E3036](semantic.md) | Semantic Analysis | Background load after runtime start |
| [E3037](semantic.md) | Semantic Analysis | Duplicate background load |
| [E3038](semantic.md) | Semantic Analysis | Invalid set-tile argument count |
| [E3039](semantic.md) | Semantic Analysis | Invalid get-tile argument count |
| [E3040](semantic.md) | Semantic Analysis | Invalid set-attribute argument count |
| [E3041](semantic.md) | Semantic Analysis | Invalid clear-background-updates argument count |
| [E3042](semantic.md) | Semantic Analysis | Invalid tile coordinate |
| [E3043](semantic.md) | Semantic Analysis | Invalid attribute coordinate |
| [E3044](semantic.md) | Semantic Analysis | Invalid background-overflow query argument count |
| [E3045](semantic.md) | Semantic Analysis | Invalid background-overflow clear argument count |
| [E3046](semantic.md) | Semantic Analysis | Invalid set-scroll argument count |
| [E3047](semantic.md) | Semantic Analysis | Invalid sprite API argument count |
| [E3048](semantic.md) | Semantic Analysis | Invalid hardware sprite palette |
| [E3049](semantic.md) | Semantic Analysis | Invalid sprite-create argument count |
| [E3050](semantic.md) | Semantic Analysis | OAM hardware-sprite capacity exhausted |
| [E3051](semantic.md) | Semantic Analysis | Invalid metasprite import |
| [E3052](semantic.md) | Semantic Analysis | Duplicate metasprite import |
| [E3053](semantic.md) | Semantic Analysis | Invalid metasprite creation |
| [E3054](semantic.md) | Semantic Analysis | Invalid metasprite API argument count |
| [E3055](semantic.md) | Semantic Analysis | Incompatible metasprite frame |
| [E4001](type-system.md) | Type System | Unknown type |
| [E4002](type-system.md) | Type System | Invalid `nes_color` value |
| [E4003](type-system.md) | Type System | Invalid `byte` value |
| [E4004](type-system.md) | Type System | Incompatible types |
| [E4005](type-system.md) | Type System | Unsupported parameter type |
| [E4006](type-system.md) | Type System | Invalid controller argument type |
| [E4007](type-system.md) | Type System | Invalid palette argument type |
| [E4008](type-system.md) | Type System | Invalid `sprite` value |
| [E4009](type-system.md) | Type System | Invalid `metasprite` value |
| [E5001](code-generation.md) | Code Generation | Missing toolchain |
| [E5002](code-generation.md) | Code Generation | Toolchain failure |
| [E5003](code-generation.md) | Code Generation | User RAM exhausted |
| [E5004](code-generation.md) | Code Generation | Temporary RAM exhausted |
| [E5005](code-generation.md) | Code Generation | Invalid memory layout |
| [E5006](code-generation.md) | Code Generation | RAM segment overflow |
| [E6001](runtime-validation.md) | Runtime Validation | File access failure |
| [E6002](runtime-validation.md) | Runtime Validation | CHR-ROM asset not found |
| [E6003](runtime-validation.md) | Runtime Validation | CHR-ROM asset read failure |
| [E6004](runtime-validation.md) | Runtime Validation | Invalid CHR-ROM size |
| [E6005](runtime-validation.md) | Runtime Validation | Invalid background asset configuration |
| [E6006](runtime-validation.md) | Runtime Validation | Background asset not found |
| [E6007](runtime-validation.md) | Runtime Validation | Background asset read failure |
| [E6008](runtime-validation.md) | Runtime Validation | Invalid background asset size |
| [E6009](runtime-validation.md) | Runtime Validation | Background asset required |
| [E6010](runtime-validation.md) | Runtime Validation | Invalid mirroring configuration |
| [E6011](runtime-validation.md) | Runtime Validation | Metasprite asset not found |
| [E6012](runtime-validation.md) | Runtime Validation | Metasprite asset read failure |
| [E6013](runtime-validation.md) | Runtime Validation | Malformed metasprite JSON metadata |
| [E6014](runtime-validation.md) | Runtime Validation | Unsupported metasprite metadata format |
| [E6015](runtime-validation.md) | Runtime Validation | Unsupported metasprite metadata version |
| [E6016](runtime-validation.md) | Runtime Validation | Invalid metasprite metadata |
| [E6017](runtime-validation.md) | Runtime Validation | Incompatible metasprite CHR data |
| [E6018](runtime-validation.md) | Runtime Validation | Invalid metasprite asset configuration |

## Warnings

The W1000-W1999 range is reserved for future non-fatal compiler warnings. The
compiler currently emits no warnings.

## Informational messages

The I1000-I1999 range is reserved for future informational diagnostics. The
compiler currently emits no informational messages.
