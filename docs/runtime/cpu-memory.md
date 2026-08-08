# CPU memory

NES Pascal models exactly 2,048 bytes of physical internal CPU RAM:
`$0000-$07FF`. Addresses `$0800-$1FFF` are hardware mirrors of that same RAM
and are never treated as additional storage.

## Default layout

| Range | Size | Owner | Purpose |
| --- | ---: | --- | --- |
| `$0000-$000F` | 16 bytes | Runtime | Mandatory Zero Page runtime reservation |
| `$0010-$001F` | 16 bytes | Compiler | Mandatory expression and cached for-limit temporaries |
| `$0020-$007F` | 96 bytes | Reserved | Stable space for future explicit Zero Page declarations |
| `$0080-$00FF` | 128 bytes | User | Optional automatic global-variable promotion |
| `$0100-$01FF` | 256 bytes | Reserved | 6502 hardware stack |
| `$0200-$02FF` | 0 or 256 bytes | Runtime | Page-aligned OAM shadow, linked by general or legacy sprite operations |
| from `$0200` without sprites, otherwise `$0300` | 0 or 5 bytes | Runtime | Legacy fixed sprite-0 staging record, allocated only when used |
| after earlier runtime blocks | 0 or 65 bytes | Runtime | General sprite logical-Y table and one helper byte |
| after earlier runtime blocks | 4 bytes | Runtime | Authoritative PPUCTRL, PPUMASK, and scroll state |
| after earlier runtime blocks | 0 or 41 bytes | Runtime | Palette shadow and atomic dirty flags, allocated only for runtime palette calls |
| after earlier runtime blocks | 0 or 960 bytes | Runtime | Confirmed tile shadow, linked only by `nes.get_tile` |
| after the optional tile shadow | 0 to 23 bytes | Runtime | Conditionally selected background queue, flags, and helper state |
| from `$0200` without sprites, otherwise `$0300` | up to 1,536 or 1,280 bytes | User/free | Non-promoted globals and all procedure parameters |

The Zero Page partitions are fixed and non-overlapping. Runtime and compiler
allocations are mandatory. They never borrow from optional promotion space.
The runtime owns `runtime_frame_counter` at `$0000` and
`runtime_frame_ready` at `$0001`. The update loop owns
`runtime_last_processed_frame` at `$0002`. Controller current, previous, and
poll-guard state occupy `$0003-$0008`. These runtime bytes cannot overlap
compiler storage. The compiler places reusable expression slots and cached
`for` limits in `$0010-$001F`. Needing more than 16 temporary bytes is a
compilation error.

General sprite operations conditionally link the page-aligned 256-byte OAM
shadow at `$0200-$02FF`. They reserve `runtime_sprite_logical_y` at
`$0300-$033F` and `runtime_sprite_value` at `$0340`; the four authoritative PPU
state bytes then occupy `$0341-$0344`. The logical-Y table lets hide/show
restore one position for each of 64 sprites. The legacy controller-example
helper instead reserves a five-byte staging record; when both APIs are used,
that record precedes the 65-byte general-sprite state.

Programs without sprite or OAM operations omit the OAM symbol, Assembly
segment, linker region, DMA code, and sprite state. Their regular runtime and
user allocation starts at `$0200`, making that 256-byte page available instead
of reserving it implicitly.

Programs with runtime palette calls reserve a 32-byte palette shadow, four
background-palette flags, four sprite-palette flags, one universal-color flag,
and four PPU restoration bytes in regular runtime RAM. The restoration bytes
hold PPUCTRL, PPUMASK, scroll X, and scroll Y. This 45-byte block starts at
`$0200` without sprites, `$0305` after legacy fixed-sprite staging, `$0341`
after the general API, or `$0346` when both APIs are linked. It uses no
additional Zero Page. User RAM begins immediately after the conditionally
allocated runtime blocks.

Every program reserves four regular-RAM bytes for the authoritative PPUCTRL,
PPUMASK, horizontal-scroll, and vertical-scroll shadows. A program that calls
`nes.set_scroll` reserves three additional bytes for an atomically published
pending pair. Programs without that call retain the zero scroll defaults and
omit the staging record.

Tile-only writes reserve 16 bytes for four ready/address/value arrays, one
sticky overflow flag, five helper bytes, and four PPU state restoration bytes:
26 bytes total. Attribute-only writes omit the two tile-index helpers and need
24 bytes. `nes.clear_background_updates()` conditionally adds the
one-byte cancellation lock; overflow-only APIs need only the sticky flag. The
960-byte confirmed
32-by-30 tile shadow is added only when `nes.get_tile()` is used. Queue plus
shadow therefore reserves 986 bytes without cancellation and, without sprites,
starts user RAM at `$05DA`. Adding cancellation raises that to 987 bytes and
starts user RAM at `$05DB`. A
`get_tile`-only program needs the shadow, four tile-index helper bytes, and the
four PPU state bytes, for 968 bytes total.

With runtime palette support, the palette and queue share the four PPU state
bytes. Palette, queue, and shadow reserve 1,027 bytes without cancellation or
1,028 bytes with it, leaving 509 or 508 regular RAM bytes when no sprite helper
is used. Legacy fixed-sprite support reserves the 256-byte OAM page and five
scalar bytes, leaving 248 or 247 bytes. The general sprite API reserves that
page plus 65 bytes, leaving 188 or 187 bytes; linking both leaves 183 or 182
bytes. Automatic Zero Page promotion space remains available independently. The shadow
remains the clearest implementation of confirmed random tile reads. Metatile
maps, modified-tile dictionaries, and compact read caches are deferred because
they would add lookup cost or runtime complexity.

VBlank callback validation rejects any reachable operation that uses those
shared compiler temporaries. The interrupt path therefore uses runtime-owned
Zero Page state plus callback variables, never main-context expression or
cached-loop storage.

The future explicit range prevents later source syntax for explicit Zero Page
variables from moving the automatic-promotion ABI. Explicit Zero Page syntax
is not implemented yet.

## Automatic promotion policy

Promotion is optional and conservative:

1. Only global variables are candidates. Procedure parameters always use
   regular RAM.
2. The compiler counts static source operations that read or write each
   global. It does not estimate loop iterations or procedure call frequency.
3. A global becomes eligible after at least three source references.
4. Eligible globals are considered strictly in declaration order. They are
   not ranked by frequency.
5. Each eligible one-byte global uses the next address from `$0080` upward.
6. If the automatic range is full, remaining variables fall back to regular
   RAM without an error, symbol change, or semantic change.

All current built-in types occupy one byte and may be promoted. The policy
does not perform lifetime analysis, storage overlays, call-graph analysis,
dynamic profiling, or advanced hotness estimation.

ca65 segments are marked `zeropage`, so instructions referencing promoted
globals or compiler temporaries use Zero Page opcodes. Regular variables keep
absolute addressing.

## Generated memory map

For an output named `build/zero_page.nes`, the compiler writes
`build/zero_page.map`. The report separates mandatory reservations from
optional promotion and identifies every user symbol as `Zero Page` or
`Regular RAM`.

An excerpt for the focused example is:

```text
Start  End    Size  Owner     Region
$0000  $000F    16  Runtime   Zero Page runtime
$0010  $001F    16  Compiler  Zero Page temporaries (1 used, 15 reserved)
$0020  $007F    96  Reserved  Future explicit Zero Page
$0080  $00FF   128  User      Automatic Zero Page variables (2 used, 126 available)
$0100  $01FF   256  Reserved  6502 hardware stack
$0200  ----      0  Runtime   Runtime data
$0200  $0200     1  User      Regular user variables
$0201  $07FF  1535  Free      General free RAM
```

The generated `.cfg`, Assembly segments, and `.map` report all use the same
validated layout object, so their address calculations cannot drift.

The runtime-symbol table also reports:

```text
$0000       1  runtime_frame_counter  volatile 8-bit NMI frame counter
$0001       1  runtime_frame_ready    best-effort advisory frame-ready latch
$0002       1  runtime_last_processed_frame  persistent update-loop baseline
$0003       1  runtime_controller_1_current  controller 1 current state
$0004       1  runtime_controller_1_previous controller 1 previous state
$0005       1  runtime_controller_2_current  controller 2 current state
$0006       1  runtime_controller_2_previous controller 2 previous state
$0007       1  runtime_controller_polled_frame most recently polled frame
$0008       1  runtime_controller_poll_valid distinguishes initial RAM from frame zero
```

When general sprite support is present, the regions table adds the OAM shadow
at `$0200-$02FF`, and the runtime-symbol table reports `runtime_oam_shadow`,
`runtime_sprite_logical_y`, and `runtime_sprite_value`. The five
`runtime_sprite_zero_*` symbols are additionally reported only for the legacy
fixed sprite-0 compatibility helper.

When runtime palette support is present, the table also reports
`runtime_palette_shadow`, `runtime_palette_background_0_dirty` through
`runtime_palette_background_3_dirty`, `runtime_palette_sprite_0_dirty` through
`runtime_palette_sprite_3_dirty`, `runtime_palette_universal_dirty`,
`runtime_ppuctrl_shadow`, `runtime_scroll_x_shadow`, and
`runtime_scroll_y_shadow`.

When `nes.get_tile` is present, the table reports
`runtime_background_shadow`. When queued updates are present, it reports the
four-element `runtime_background_queue_ready`,
`runtime_background_queue_high`, `runtime_background_queue_low`, and
`runtime_background_queue_value` arrays. Writers and overflow APIs add
`runtime_background_queue_overflow`; cancellation adds
`runtime_background_queue_cancel_lock`. Coordinate, value, and tile-index
helpers are reported only for entry points that use them. The PPU
restoration symbols are allocated for palette or background uploads and shared
when both features are present.
