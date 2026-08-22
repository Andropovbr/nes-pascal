# Collision helpers

English | [Português (Brasil)](../pt-BR/runtime/collision-helpers.md)

NES Pascal provides query-only collision primitives for byte-sized,
single-screen gameplay. They do not move objects, resolve penetration, register
entities, or maintain a collision world.

## Rectangle representation and edge rules

`nes_rect` is a predefined ordinary record, implemented by the same fixed
layout machinery as user records:

```pascal
var
    PlayerBounds: nes_rect;

begin
    PlayerBounds.X := $20;
    PlayerBounds.Y := $30;
    PlayerBounds.Width := $08;
    PlayerBounds.Height := $08;
end;
```

Its fields are four consecutive `byte` values at offsets X `+0`, Y `+1`,
Width `+2`, and Height `+3`. A `nes_rect` is regular static RAM; it has no
descriptor, heap object, pointer, or hidden per-entity state. Collision APIs
accept standalone `nes_rect` variables directly and do not accept a
structurally similar user record.

Bounds are unsigned and half-open: `[X, X + Width)` by
`[Y, Y + Height)`. A point on the left or top edge is inside; a point equal to
the right or bottom edge is outside. Two rectangles that only touch at an edge
do not overlap. Width or Height zero always means no collision.

The runtime checks logical ends with the 6502 carry. An end exactly equal to
256 is valid, so X `$F8` with Width `$08` can contain `$FF`. An end greater
than 256 is invalid and the predicate returns `false`; for example X `$FA`
with Width `$10` never wraps into a rectangle at the left edge. Bounds helpers
produce a zero-area rectangle when their requested result would wrap.

## Point and rectangle predicates

```pascal
Inside := nes.point_in_rect(PointX, PointY, PlayerBounds);
Overlap := nes.collides(PlayerBounds, EnemyBounds);
```

Signatures are:

```text
nes.point_in_rect(x: byte, y: byte, rectangle: nes_rect): boolean
nes.collides(left: nes_rect, right: nes_rect): boolean
```

Both return canonical `$00`/`$01` Boolean values. The point helper validates
the box and compares unsigned distances from its top-left. `nes.collides`
validates both boxes and tests whether the later start on each axis lies
strictly before the earlier rectangle's end. This distance form locks the
half-open edge rule without relying on wrapped byte addition.

Calls are safe inside functions and short-circuit Boolean expressions. Scalar
arguments are evaluated through the established builtin/function call scopes;
rectangle arguments are direct addresses and add no expression temporary.
When an earlier scalar argument must survive a later user-function call, the
compiler leases the normal scoped expression pool so a nested collision query
cannot overwrite the outer call's staged input.
Collision queries may run in main code, functions, procedures, and the update
callback. They are rejected on a VBlank callback path because main code can be
interrupted while the helpers use their shared runtime scratch.

## Sprite bounds

```pascal
nes.sprite_bounds(PlayerSprite, $01, $02, $06, $05, PlayerBounds);
```

The signature is:

```text
nes.sprite_bounds(
    value: sprite,
    offset_x: byte,
    offset_y: byte,
    width: byte,
    height: byte,
    output: nes_rect
)
```

Offsets are unsigned additions to the sprite position. `$00, $00, $08, $08`
describes the complete 8-by-8 sprite; the example creates a smaller box. The
helper reads X from the existing OAM shadow and raw OAM Y from the existing
hide/show cache, so it does not duplicate position state. Visibility does not
enable or disable collision. Individual-sprite flip bits do not transform the
explicit collision offsets; the collision box remains anchored to the
position passed to the sprite API. Sprite coordinates retain the low-level raw
OAM Y convention documented under [Hardware sprites](sprites.md).

## Metasprite bounds and metadata

```pascal
nes.metasprite_bounds(Player, PlayerBounds);
```

The output uses the current instance position, frame, and whole-metasprite
flip flags. No component scan occurs at runtime. The importer computes the
fallback box once from the minimum and maximum extents of actual 8-by-8 frame
components. Empty frames produce a zero-area box.

One frame may instead declare an immutable anchor-relative collision box:

```json
"collision_box": {
  "x": 1,
  "y": 2,
  "width": 6,
  "height": 5
}
```

`x` and `y` are signed metadata offsets, while width and height are 1..255.
Both the original and flipped offsets must fit signed 8-bit representation.
Horizontal flip transforms X offset to `-x-width`; vertical flip transforms Y
offset to `-y-height`. This mirrors asymmetric custom boxes around the same
logical anchor/pivot as component geometry. The four resolved bytes are added
to PRG frame metadata only when `nes.metasprite_bounds` is linked; no duplicate
geometry is stored per instance.

Older metadata without `collision_box` remains valid and uses visual component
bounds. Malformed dimensions, values, or flip-unsafe offsets produce E6016.

## Background collision map

`nes.background_collision(x, y)` accepts screen pixel coordinates. X `$00` to
`$FF` selects tile columns 0..31. Y `$00` to `$EF` selects tile rows 0..29;
Y `$F0` to `$FF` returns `false`. The current model is nametable 0 on one
static 256-by-240 screen; it is not a scrolling world-coordinate API.

Configure a map with `--collision-map`. The UTF-8 text file has exactly 30
rows of 32 characters:

```text
11111111111111111111111111111111
10000000000000000000000000000001
...
11111111111111111111111111111111
```

`0` means passable and `1` means solid. The compiler validates row count,
width, and every value, then packs the 960 logical flags row-major and
least-significant-bit first into 120 immutable PRG-ROM bytes. Runtime indexing
uses four packed bytes per row, so positions such as tile index 641 do not
truncate even though the logical 32-by-30 tile index exceeds 255. A two-byte
Zero Page pointer performs carry-aware ROM address addition across page
boundaries. The query returns a canonical Boolean.

This data path is independent of `nes.get_tile` and does not link the 960-byte
confirmed background shadow. `nes.set_tile` changes visual background data but
does not mutate or synchronize the collision map. The map remains static, and
scrolling/world collision is outside this milestone.

## Costs and feature selection

All collision builtins are ordinary declarative registry entries. Programs
that call none of them emit zero collision code, RAM, Zero Page, and ROM data.

| Used collision path | Collision-specific regular RAM | Collision-specific ZP symbols | Collision-map PRG data |
| --- | ---: | ---: | ---: |
| point/rect, rect/rect, or bounds | 10 B shared scratch | 2 B pointer | 0 B |
| background lookup only | 2 B pixel/index scratch | 2 B pointer | 120 B map + 8 B mask table |

Sprite and metasprite bounds also require their already documented sprite
runtime state and OAM shadow. The two pointer bytes live inside the existing
16-byte runtime Zero Page policy partition and are emitted as symbols only
when a collision helper is used.

See [`examples/collision_helpers.nsp`](../../examples/collision_helpers.nsp)
for one focused program using every public path.
