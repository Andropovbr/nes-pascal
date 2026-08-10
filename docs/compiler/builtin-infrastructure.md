# Builtin / Intrinsic Infrastructure

English | [Português (Brasil)](..\pt-BR\compiler\builtin-infrastructure.md)

Milestone 0.5.6 gives ordinary `nes.*` calls one compile-time pipeline:

```text
source call
  -> BuiltinCall(public name, arguments, source position)
  -> registry lookup and signature validation
  -> optional semantic hook
  -> ResolvedBuiltinCall(BuiltinId, resolved arguments)
  -> descriptor runtime dependencies
  -> BackendEmitter dispatch
  -> direct ca65 code
```

This infrastructure exists only in the compiler. Generated ROMs contain no
builtin lookup table, dynamic dispatch, or additional runtime indirection.

## Registry and resolved identity

`nes_pascal/builtins.py` contains a static, immutable registry indexed both by
the public name and by `BuiltinId`. Each `BuiltinDescriptor` records:

- public name and stable identity;
- statement or value kind;
- parameter types and optional return type;
- semantic hook identity;
- runtime-feature dependencies, including dependencies that apply only to
  queued palette writes;
- backend emitter identity;
- argument-count diagnostic and correction text;
- the exceptional bare-statement syntax used by `nes.wait_frame`.

The parser does not construct operation-specific node families. It preserves
the qualified name, arguments, and call location in `BuiltinCall`. Semantic
analysis resolves that name exactly once and stores `BuiltinId` in
`ResolvedBuiltinCall`; memory layout and code generation never parse the public
name again.

Generic signature validation checks context, argument count, and exact types.
The `SemanticHook` cases retain checks that cannot be expressed by a type tuple,
including controller constants, palette/index limits, background coordinate
limits, static sprite allocation, symbolic metasprite frames and animations,
and cross-asset ownership.

Memory feature detection recursively collects `RuntimeFeature` values from
resolved descriptors. An unused registry entry costs no RAM or code. In
particular, `nes.get_tile()` requests the 960-byte confirmed background shadow,
while write-only tile and attribute operations do not. Sprite and metasprite
descriptors request OAM support only when used.

The ca65 backend uses centralized `BackendEmitter` maps for statement and value
builtins. Group helpers still express hardware-specific sequences, but dispatch
is based on the resolved emitter identity rather than AST classes or public-name
string matching.

## Construct inventory

| Classification | Existing constructs | Representation |
| --- | --- | --- |
| Ordinary background statements | `nes.set_background_color`, `nes.set_tile`, `nes.set_attribute`, `nes.clear_background_updates`, `nes.clear_background_update_overflow` | `BuiltinCall` / `ResolvedBuiltinCall` |
| Ordinary palette statements | `nes.set_background_palette`, `nes.set_sprite_palette`, `nes.set_background_palette_color`, `nes.set_sprite_palette_color` | `BuiltinCall` / `ResolvedBuiltinCall` |
| Ordinary frame/scroll statements | `nes.wait_frame`, `nes.set_scroll` | `BuiltinCall` / `ResolvedBuiltinCall` |
| Ordinary sprite statements | `nes.set_sprite_zero`, `nes.sprite_set_position`, `nes.sprite_set_x`, `nes.sprite_set_y`, `nes.sprite_set_tile`, `nes.sprite_set_palette`, `nes.sprite_set_attributes`, `nes.sprite_hide`, `nes.sprite_show`, `nes.sprite_set_flip_horizontal`, `nes.sprite_set_flip_vertical`, `nes.sprite_set_behind_background` | `BuiltinCall` / `ResolvedBuiltinCall` |
| Ordinary metasprite/animation statements | `nes.metasprite_set_position`, `nes.metasprite_set_frame`, `nes.metasprite_set_animation`, `nes.metasprite_restart_animation`, `nes.metasprite_hide`, `nes.metasprite_show`, `nes.metasprite_set_flip_horizontal`, `nes.metasprite_set_flip_vertical` | `BuiltinCall` / `ResolvedBuiltinCall` |
| Ordinary value builtins | `nes.controller_down`, `nes.controller_pressed`, `nes.controller_released`, `nes.sprite_create`, `nes.metasprite_create`, `nes.metasprite_animation_finished`, `nes.get_tile`, `nes.background_updates_overflowed` | `BuiltinCall` / `ResolvedBuiltinCall` |
| Compile-time asset construct | `nes.import_metasprite` | Specialized: validates configured asset identity and contributes no runtime call |
| Compile-time background asset construct | `nes.load_background` | Specialized: coordinates configured nametable data and pre-render program order |
| Callback/program-structure constructs | `nes.on_update`, `nes.on_vblank` | Specialized: register procedure identities and validate call graphs |
| Runtime-start program structure | `nes.run` | Specialized: unique top-level phase boundary, not an ordinary call |

Qualified controller button names such as `nes.button_a` through
`nes.button_right` are typed compile-time constants, not callable builtins.

## Adding an ordinary builtin

An ordinary future API should require only:

1. one registry descriptor with a new `BuiltinId`, signature,
   `RuntimeFeature` dependencies, and `BackendEmitter`;
2. an existing generic semantic path, or one focused `SemanticHook` when the
   signature cannot express a compile-time constraint;
3. a backend emitter helper or an intentional entry in an existing grouped
   emitter;
4. positive, negative, feature-isolation, and generated-behavior tests;
5. synchronized language/API documentation.

Do not add a new parsed AST class, resolved AST class, parser branch family, or
memory-layout `isinstance` case for an ordinary builtin. Keep a construct
specialized only when it changes program structure, compiler asset
configuration, or callback topology.

## Refactor size and compatibility

The migration replaced 18 ordinary parsed node classes and 17 ordinary
resolved node classes with one parsed and one resolved class. It also removed
the controller, sprite-operation, metasprite-operation, and AST palette-kind
dispatch enums from `ast.py`.

The 0.5.5 benchmark corpus remains the compatibility baseline. The following
representative results are identical before and after the refactor:

| Benchmark | PRG occupied | Instructions | ZP allocated/reserved | Non-ZP allocated | Representative linked features |
| --- | ---: | ---: | ---: | ---: | --- |
| `minimal` | 245 -> 245 B | 108 -> 108 | 25 -> 25 B | 7 -> 7 B | minimal runtime only |
| `controller_input` | 895 -> 895 B | 404 -> 404 | 30 -> 30 B | 265 -> 265 B | controller query, legacy sprite zero, OAM |
| `sprite_support` | 589 -> 589 B | 273 -> 273 | 26 -> 26 B | 326 -> 326 B | sprite API and OAM |
| `metasprite_player` | 1,443 -> 1,443 B | 551 -> 551 | 34 -> 34 B | 272 -> 272 B | metasprite API, controller query, OAM |
| `sprite_animation` | 2,013 -> 2,013 B | 675 -> 675 | 34 -> 34 B | 276 -> 276 B | metasprite animation and OAM |
| `background_updates` | 2,172 -> 2,172 B | 522 -> 522 | 25 -> 25 B | 995 -> 995 B | queue, overflow state, confirmed tile shadow |
| `gameplay_full_stack` | 3,484 -> 3,484 B | 874 -> 874 | 33 -> 33 B | 1,260 -> 1,260 B | combined controller, palette, scroll, OAM, animation, and background features |

Here, Zero Page means benchmark-allocated or compiler-reserved Zero Page;
non-ZP includes regular runtime/user allocation plus any OAM shadow. The full
accounting definitions remain in the 0.5.5 optimization audit.
