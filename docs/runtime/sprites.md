# Hardware sprites

English | [Português (Brasil)](..\pt-BR\runtime\sprites.md)

NES Pascal exposes the NES's 64 hardware OAM entries as individually managed
hardware sprites. One `sprite` value identifies exactly one four-byte OAM
entry; it is not a game entity or a multi-tile metasprite. Use the separate
[metasprite API](metasprites.md) for compiled multi-component objects. There is
no automatic animation, collision, sorting, flickering, or
8-sprites-per-scanline mitigation yet.

## Sprite indexes

The built-in `sprite` type occupies one byte but is distinct from `byte`.
Its valid range is `$00..$3F`, selecting hardware sprites 0 through 63.

```pascal
const
    PlayerSprite: sprite = $00;

var
    EnemySprite: sprite;
```

There is no implicit conversion between `sprite` and `byte`. Direct
hexadecimal literals are accepted where a sprite argument is expected and are
checked against the 64-entry limit. `sprite` procedure parameters are not yet
supported.

## Static allocation and ownership

`nes.sprite_create()` is a compile-time reservation expression:

```pascal
PlayerSprite := nes.sprite_create();
EnemySprite := nes.sprite_create();
```

Each syntactically distinct call site owns one hardware sprite for the whole
program. The compiler processes sites in source order and assigns the lowest
unreserved OAM index. Repeated execution of the same site, including a site in
a loop or repeatedly called procedure, produces the same index; it is not a
runtime allocation. Conditional sites reserve their slot whether or not the
branch executes. There is no runtime bitmap, free list, `destroy`, or reuse.

Explicit ownership is established by `sprite` constants, direct sprite
literal assignments, direct literal/constant sprite API arguments, and the
legacy sprite-zero helper. These indexes are reserved before automatic
allocation, regardless of their source order. Multiple explicit references
may intentionally alias one hardware sprite, but `sprite_create()` never
selects an explicitly owned or previously created slot.

The resolved program records each reserved OAM index as
`individual_explicit`, `individual_created`, or `metasprite_component`. This
metadata costs no runtime RAM. Metasprite creation allocates components only
from the unreserved complement of that same 64-entry table, so individual
sprites and metasprites cannot collide.

If a creation site would exceed the remaining capacity, compilation stops
with E3050. The same diagnostic reports a metasprite whose maximum frame does
not fit. Allocation never wraps, aliases, overwrites another owner, truncates
a metasprite, or returns a sentinel. `nes.sprite_create()` takes no arguments
and E3049 reports an invalid argument list.

## OAM layout and API

Each hardware sprite occupies four bytes in the runtime OAM shadow:

| Offset | Meaning |
| ---: | --- |
| 0 | Y coordinate |
| 1 | Tile index |
| 2 | Attributes |
| 3 | X coordinate |

The public operations are:

```pascal
nes.sprite_set_x(PlayerSprite, $78);
nes.sprite_set_y(PlayerSprite, $70);
nes.sprite_set_position(PlayerSprite, $78, $70);
nes.sprite_set_tile(PlayerSprite, $01);
nes.sprite_set_palette(PlayerSprite, $02);
nes.sprite_set_attributes(PlayerSprite, $00);
nes.sprite_hide(PlayerSprite);
nes.sprite_show(PlayerSprite);
nes.sprite_set_flip_horizontal(PlayerSprite, true);
nes.sprite_set_flip_vertical(PlayerSprite, false);
nes.sprite_set_behind_background(PlayerSprite, false);
```

X, Y, tile, and raw attributes are `byte` values. The flip, priority, and
visibility helpers operate independently. A compile-time sprite palette above
3 produces E3048. A dynamic `byte` palette outside `0..3` is ignored at
runtime, leaving the existing attributes unchanged.

This individual-sprite API exposes the hardware OAM Y byte directly. The PPU
draws the first sprite row on the scanline after that value, and `$FF` is used
as the hidden sentinel. No logical-screen `Y - 1` conversion is performed.
The higher-level [metasprite API](metasprites.md) instead accepts a logical
screen anchor and converts each visible component with
`OAM Y = component logical top - 1`.

`nes.sprite_set_position(sprite, x, y)` is equivalent to the separate X and Y
setters. For a dynamic sprite value, its OAM offset is calculated once before
both coordinates are written. The operation also updates the runtime's cached
OAM Y without implicitly showing a hidden sprite.

## Attribute byte

The runtime follows the NES OAM attribute format:

| Bits | Meaning |
| --- | --- |
| 0-1 | Sprite palette, 0 through 3 |
| 2-4 | Unused hardware bits; retained by property helpers |
| 5 | Behind-background priority |
| 6 | Horizontal flip |
| 7 | Vertical flip |

`nes.sprite_set_attributes` replaces the complete byte. The palette, flip,
and priority helpers perform read-modify-write operations and preserve every
unrelated bit.

## Visibility

All 64 sprites start hidden. Initialization writes `$FF` to every OAM-shadow Y
byte before NMI or rendering can expose RAM contents.

`nes.sprite_hide` saves the current visible raw OAM Y byte in a runtime-owned
64-byte cache, then writes `$FF` to OAM. Repeated hide calls preserve the saved
value. `nes.sprite_show` restores that byte. Calling `nes.sprite_set_y` while
hidden updates the cache but keeps the sprite
hidden; a later show uses the new value. The extra 64 bytes keep hide/show
deterministic without introducing a larger sprite object model.

## DMA and execution context

When any sprite operation is linked, the runtime reserves the page-aligned
`$0200-$02FF` OAM shadow. Early in every NMI, after frame bookkeeping and
before palette/background uploads or the user VBlank callback, it resets
`$2003` to zero and writes page `$02` to `$4014`. This copies all 256 bytes to
PPU OAM during VBlank. User code never writes PPU OAM directly.

Sprite setters update CPU RAM and are intended for initialization, ordinary
main code, or `nes.on_update`. They are rejected from the user VBlank callback
because NMI owns DMA and the sprite helper scratch state is not reentrant.
Changes made by an update callback are visible after the next NMI upload.

See [CPU memory](cpu-memory.md) for exact allocations and
[VBlank cycle budget](vblank-cycle-budget.md) for DMA cost.
