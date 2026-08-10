# Metasprites

English | [Português (Brasil)](..\pt-BR\runtime\metasprites.md)

A metasprite is one logical object composed of an arbitrary list of 8-by-8 NES
hardware sprites. A `metasprite` value identifies the logical instance; it is
not an OAM index, and component indexes are never exposed to source code.
Metasprites and individually managed [`sprite` values](sprites.md) write the
same OAM shadow and share the same physical limit of 64 hardware sprites.

## Import and creation

PNG2CHR Studio metadata is configured at build time and imported by its root
`name`:

```text
python -m nes_pascal.cli examples/metasprite_player.nsp -o build/metasprite_player.nes --chr assets/game.chr --metasprite assets/player_idle.json
```

```pascal
var
    Player: metasprite;

begin
    nes.import_metasprite(player);
    Player := nes.metasprite_create(player.idle_0);
end;
```

`--metasprite` is repeatable. Relative JSON and CHR paths are resolved from the
Pascal source directory. `nes.import_metasprite` is a compile-time top-level
statement and must precede `nes.run`. It does not open a file on the NES.
Frame symbols use `<asset>.<animation>_<zero-based-frame>`, so the six attached
idle frames are `player.idle_0` through `player.idle_5`.

Each syntactically distinct `nes.metasprite_create(frame)` site is one
persistent static instance. Creation starts hidden with the selected frame and
zeroed position. There is no heap, destruction, or runtime name lookup.

## Public API

```pascal
nes.metasprite_set_position(Player, X, Y);
nes.metasprite_set_frame(Player, player.idle_2);
nes.metasprite_set_animation(Player, player.idle);
nes.metasprite_restart_animation(Player);
nes.metasprite_set_flip_horizontal(Player, true);
nes.metasprite_set_flip_vertical(Player, false);
nes.metasprite_hide(Player);
nes.metasprite_show(Player);
```

Position takes two `byte` values, flip setters take `boolean`, and frame
selection requires a symbolic frame from the instance's creation asset.
Changing a frame preserves position, visibility, and whole-object flips. If
the new frame has fewer components, the unused reserved entries remain hidden.
Changing position or frame while hidden does not show the instance.
E3055 rejects a cross-asset frame when the instance identity is directly known
at compilation. Because ordinary `metasprite` variables are opaque one-byte
identities, the runtime also checks asset IDs and safely ignores an
incompatible dynamic pairing instead of reading beyond reserved capacity.

Animation selection, automatic timing, looping, one-shot completion, restart,
and the interaction with manual frame selection are documented in
[Sprite animation](sprite-animation.md).

## Supported metadata

The compiler accepts PNG2CHR Studio `png2chr-studio-animation` metadata version
2. It validates the required object/array structure, 8-by-8 source tile size,
frame dimensions, metadata origin, component count, signed coordinates, tile
range, attribute byte, palette bits, flip booleans, 256-tile declared
capacity, and 8 KiB NROM CHR declaration.

Every frame is stored as a component list. Layouts may be rectangular, sparse,
asymmetric, or use negative origin-relative offsets. Repeated and
non-contiguous CHR indexes remain unchanged. Only entries in each frame's
`sprites` array consume OAM, so omitted/transparent source tiles do not.
Component order is preserved.

There is one immutable frame representation. Manual frame selection and
[sprite animation](sprite-animation.md) reference the same frame IDs and the
same component lists; animation state never creates a second geometry,
pivot, flip, or clipping path.

PNG2CHR Studio version 2 defines root `origin` as the configured logical anchor
in source-frame pixel coordinates. It subtracts that anchor during export, so
every `animations[].frames[].sprites[].x/y` value is already a signed offset
from the anchor. NES Pascal consumes those offsets directly; it does not
subtract `origin` again.

Tooling fields such as source image coordinates, source tile row/column,
reuse labels, and conversion statistics stay in the compiler only. Animation
durations and loop policy become compact immutable PRG tables. Tile graphics
remain solely in CHR-ROM; they are not copied into PRG.

The metadata currently declares a tile capacity and final tile count but does
not unambiguously identify which 4 KiB NES pattern table the indexes target.
NES Pascal uses the configured NROM CHR bank and validates the one-byte sprite
tile range, but it cannot prove that a differently named JSON and CHR file came
from the same export. A future PNG2CHR Studio contract should add an explicit
pattern-table/bank identity and preferably a CHR content hash. The attached
metadata names `player.chr` while the supplied compatible file is `game.chr`;
the compiler therefore does not treat the tooling output filename as identity.

## Frame origin, logical anchor, and position

Source-frame coordinates use the image frame's top-left as `(0, 0)`. Frame
`width` and `height` describe that source extent and are retained for
compile-time representation and future bounding-box work. They do not imply a
rectangular component grid and are not copied to runtime RAM.

The root metadata `origin` selects one point in that source coordinate system
as both the logical anchor and whole-metasprite flip pivot. PNG2CHR Studio
exports a source cell at `(source_x, source_y)` as:

```text
component.x = source_x - origin.x
component.y = source_y - origin.y
```

NES Pascal stores `component.x/y` unchanged as signed `dx/dy`.
`nes.metasprite_set_position(M, x, y)` places the anchor at logical screen
coordinate `(x, y)`, so logical X/Y always identify the same object point
regardless of frame or flip state. An origin of `(0, 0)` deliberately uses the
source frame's top-left as the anchor. An origin inside or outside a frame can
represent character feet, ship centers, asymmetric effects, or hinge-like
objects.

The source-frame origin, logical anchor, and flip pivot are distinct concepts,
but version 2 needs only one declared `origin`: source-frame `(0, 0)` is fixed,
while the configured `origin` is both anchor and pivot. A separate `pivot`
field is unnecessary unless a future asset format needs flipping around a
point different from the logical position.

### Compatibility with initial 0.5.3 assets

PNG2CHR Studio already used the contract above when it emitted schema version
2. The initial NES Pascal 0.5.3 importer incorrectly treated `sprites[].x/y`
as source coordinates and subtracted `origin` a second time. This was invisible
for `(0, 0)` assets but wrong for every nonzero anchor. The importer now follows
the producer's existing contract; there is no schema change and no compatibility
mode for the incorrect double subtraction.

Existing `(0, 0)` metadata remains deterministic and keeps its top-left,
hinge-like flip behavior. NES Pascal never guesses a center from frame width or
height. To center a 24-by-24 frame, re-export with `origin: {"x": 12, "y": 12}`;
the corresponding component offsets become `-12`, `-4`, and `4`. Changing only
`origin` without re-exporting the component offsets does not satisfy the format
contract. The bundled player fixture was reanchored this way.

## Whole-metasprite flipping

Flipping mirrors each 8-by-8 component around the logical anchor, not around a
rectangle inferred from width/height. For logical coordinate `L` and signed
top-left offset `d`, placement is:

```text
not flipped: component_top_left = L + d
flipped:     component_top_left = L - d - 8
```

Equivalently, the flipped offset is `d' = -d - 8`. The extra 8 accounts for
the component width or height. Horizontal flip XORs OAM attribute bit 6;
vertical flip XORs bit 7. XOR preserves unrelated palette and priority bits
and correctly combines a whole-object flip with a component already flipped
by the asset.

A centered pivot preserves the corresponding visible bounding range while
mirroring asymmetric placement and tile orientation inside it. A deliberately
non-centered pivot keeps logical X/Y stable but can move the visible bounding
range, which is the intended door-hinge behavior. The runtime does not alter
logical X/Y in either case.

## OAM ownership and cost

The compiler determines the largest component count among every frame in an
instance's asset and reserves that many free entries. Individual explicit
reservations are processed first, then `nes.sprite_create()` sites, then
metasprite creation sites in source order. Metasprite entries may be
non-contiguous and are recorded as `metasprite_component` owners. The resolved
instance privately maps component positions to those OAM indexes.

If the shared total would exceed 64, E3050 stops compilation. Allocation never
wraps, overwrites another owner, truncates a frame, or returns an invalid
sentinel. This fixed maximum lets automatic animations switch between
differently sized frames without runtime OAM allocation.

Each instance uses four mutable regular-RAM bytes: logical X, logical Y,
selected frame ID, and visibility/flip flags. Metasprite support also links
eight shared regular-RAM scratch bytes and two shared two-byte Zero Page
pointers. Immutable PRG tables contain:

- low/high frame pointers and one asset ID per frame;
- for each frame, one component count followed by four bytes per component:
  signed X offset, signed Y offset, tile, attributes;
- low/high slot-table pointers and one asset ID per instance;
- for each instance, one reserved-slot count followed by its internal OAM
  indexes.

Width, height, and origin do not occupy ROM table bytes because the exported
component offsets already encode the anchor-relative geometry.

Programs using [sprite animation](sprite-animation.md) add four mutable bytes
per instance and compact animation sequence tables in PRG-ROM. Programs that
use only static frame operations retain the costs above and do not link the
animation state or routines.

## Visibility, clipping, and NES Y

Showing renders every active component from current state. Hiding writes
`$FF` to the Y byte of every owned slot. Rendering a shorter frame hides the
remaining slots.

Coordinate addition is signed and checked before writing OAM. A component is
shown only when the entire 8-by-8 tile is representable: X top-left `0..248`
and logical Y top `1..232`. Anything beyond the left, right, top, or bottom
boundary is hidden as a whole hardware sprite; arithmetic never wraps it to
the opposite edge. Both positive and negative offset paths recheck the final
right/bottom limits. Pixel-level clipping is not implemented.

Metasprite Y is a logical screen top coordinate. For a visible component the
runtime writes `OAM Y = logical top - 1` exactly once, matching the NES sprite
Y convention. Logical top 0 would encode as `$FF`, which this runtime reserves
as the hidden sentinel, so that component is clipped.

This differs intentionally from the low-level individual-sprite API:
`nes.sprite_set_y` accepts and stores the raw OAM Y byte without subtracting
one, while metasprite positioning accepts a logical screen anchor and performs
the conversion per component. Existing individual-sprite Y and hide/show
behavior remains unchanged.

Metasprite layout work runs in initialization, main code, or `nes.on_update`,
never in NMI. NMI continues to upload the complete page-aligned shadow through
one OAM DMA.

## Hardware scanline limit

The 64-entry OAM capacity is not the only sprite limit. The NES PPU renders at
most eight hardware sprites on one scanline. A wide metasprite, or several
objects sharing scanlines, may exhibit sprite dropout even when total OAM
ownership is valid. NES Pascal does not sort sprites, rotate OAM priority,
balance scanlines, or implement flicker mitigation. Animation does not change
this hardware limit.
