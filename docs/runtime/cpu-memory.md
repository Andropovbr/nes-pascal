# CPU memory

English | [Português (Brasil)](../pt-BR/runtime/cpu-memory.md)

NES Pascal models exactly 2,048 bytes of physical internal CPU RAM:
`$0000-$07FF`. Addresses `$0800-$1FFF` are hardware mirrors of that same RAM
and are never treated as additional storage.

## Default layout

| Range | Size | Owner | Purpose |
| --- | ---: | --- | --- |
| `$0000-$000F` | 16 bytes | Runtime | Mandatory Zero Page runtime reservation |
| from `$0010` | 0 to 16 bytes combined | Compiler | Maximum-live expression temporaries followed by cached `for` limits |
| through `$001F` | remaining bytes | Free | Recovered temporary capacity visible to the allocator |
| `$0020-$007F` | 96 bytes | Reserved | Stable space for future explicit Zero Page declarations |
| `$0080-$00FF` | 128 bytes | User | Optional automatic global-variable promotion |
| `$0100-$01FF` | 256 bytes | Reserved | 6502 hardware stack |
| `$0200-$02FF` | 0 or 256 bytes | Runtime | Page-aligned OAM shadow, linked by general or legacy sprite operations |
| from `$0200` without sprites, otherwise `$0300` | 0 or 5 bytes | Runtime | Legacy fixed sprite-0 staging record, allocated only when used |
| after earlier runtime blocks | 0, 65, or 66 bytes | Runtime | General sprite logical-Y table and one or two helper bytes |
| after earlier runtime blocks | `4N + 8` or `8N + 8` bytes | Runtime | Static or animation-enabled metasprite state plus shared renderer scratch |
| after earlier runtime blocks | 4 bytes | Runtime | Authoritative PPUCTRL, PPUMASK, and scroll state |
| after earlier runtime blocks | 0 or 41 bytes | Runtime | Palette shadow and atomic dirty flags, allocated only for runtime palette calls |
| after earlier runtime blocks | 0 or 960 bytes | Runtime | Confirmed tile shadow, linked only by `nes.get_tile` |
| after the optional tile shadow | 0 to 23 bytes | Runtime | Conditionally selected background queue, flags, and helper state |
| after regular runtime data | one byte per function | Compiler | Static function-result backing storage |
| after compiler result storage | remaining regular RAM | User/free | Non-promoted globals and all procedure/function parameters |

The Zero Page policy windows are fixed and non-overlapping. Runtime symbols,
measured expression slots, and compiler caches are mandatory when used. They
never borrow from optional promotion space.
The runtime owns `runtime_frame_counter` at `$0000` and
`runtime_frame_ready` at `$0001`. The update loop owns
`runtime_last_processed_frame` at `$0002`. Controller current, previous, and
poll-guard state occupy `$0003-$0008`. These runtime bytes cannot overlap
compiler storage. Within `$0010-$001F`, the compiler first places exactly the
maximum number of simultaneously live expression slots and then cached `for`
limits. The unused suffix is allocator-visible free Zero Page. Needing more
than 16 combined expression/cache bytes is a compilation error.

Expression slots use deterministic names (`expression_temporary_0`,
`expression_temporary_1`, and so on). Lowering explicitly acquires the lowest
free slot, keeps it leased while its value is needed, and releases it for later
expressions. Reservation is based on the whole program's measured peak, not
AST depth or expression count. A program with no such lifetime reserves zero
expression bytes. Cached `for_limit_*` values remain a separate accounting
category even though they share the same bounded Zero Page policy window.

Variable array and record-array writes continue to preserve their calculated
index on the 6502 hardware stack while evaluating the right-hand side. Those
stack bytes are hardware-stack use, not expression-temporary reservation.
Procedure, function, and builtin arguments are evaluated in their established order and
reuse the scoped pool only after earlier expression leases end.

Call scopes preserve all caller-owned leases. Any nested expression-producing
call must acquire a different slot until its caller releases the active value.
Function analysis applies this rule across the complete acyclic call graph.
Earlier argument values also receive temporary slots when a later argument can
call a function and overwrite static parameter storage. Each function has one
regular-RAM result byte and returns its value in `A`; no runtime stack frame or
fixed return area is reserved. Each active `JSR` uses only its normal two-byte
hardware-stack return address, reported by the benchmark call-depth metric.

General sprite operations conditionally link the page-aligned 256-byte OAM
shadow at `$0200-$02FF`. They reserve `runtime_sprite_logical_y` at
`$0300-$033F` and `runtime_sprite_value` at `$0340`.
`nes.sprite_set_position` conditionally adds
`runtime_sprite_secondary_value` at `$0341`; the four authoritative PPU state
bytes therefore begin at `$0341` or `$0342`. The logical-Y table lets hide/show
restore one position for each of 64 sprites. The legacy controller-example
helper instead reserves a five-byte staging record; when both APIs are used,
that record precedes the 65- or 66-byte general-sprite state.

Metasprite-only programs reserve `$0200-$02FF` for the shared OAM shadow. They
also reserve two two-byte indirect pointers at `$0009-$000C`, four regular-RAM
bytes per instance (X, Y, frame, flags), and eight shared regular-RAM scratch
bytes. One instance therefore uses 12 regular bytes plus four shared Zero Page
bytes; each additional instance adds four regular bytes. These blocks follow
any individual-sprite runtime state and precede palette/PPU/background state.
The statically owned component indexes and immutable geometry live in PRG-ROM,
not RAM.

When a program uses an animation operation or completion query, every
metasprite instance adds four regular-RAM bytes for animation ID, sequence
index, frame timer, and playback flags. The resulting regular-RAM cost is
`8N + 8`; the OAM shadow, shared scratch, and Zero Page pointers do not grow.
Programs limited to static frame selection retain `4N + 8` and omit all
animation state and routines.

Programs without individual sprite, metasprite, or OAM operations omit the OAM symbol, Assembly
segment, linker region, DMA code, and sprite state. Their regular runtime and
user allocation starts at `$0200`, making that 256-byte page available instead
of reserving it implicitly.

Function result bytes start immediately after all conditionally selected
regular runtime data and before regular user storage. They appear in the
`FUNCTION_RESULTS` linker segment and under `Compiler Symbols` in the generated
map. A program without functions omits the region, segment, symbols, and code.

Programs with runtime palette calls reserve a 32-byte palette shadow, four
background-palette flags, four sprite-palette flags, one universal-color flag,
and four PPU restoration bytes in regular runtime RAM. The restoration bytes
hold PPUCTRL, PPUMASK, scroll X, and scroll Y. This 45-byte block starts at
`$0200` without sprites, `$0305` after legacy fixed-sprite staging,
`$0341-$0342` after the general API, or `$0346-$0347` when both APIs are
linked. It uses no
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
page plus 65 bytes, or 66 with `nes.sprite_set_position`, leaving 188 down to
186 bytes; linking both leaves 183 down to 181 bytes. Automatic Zero Page
promotion space remains available independently. The shadow
remains the clearest implementation of confirmed random tile reads. Metatile
maps, modified-tile dictionaries, and compact read caches are deferred because
they would add lookup cost or runtime complexity.

VBlank callback validation rejects any reachable operation that uses shared
compiler expression slots or caches. The interrupt path therefore uses runtime-owned
Zero Page state plus callback variables, never main-context expression or
cached-loop storage.

The future explicit range prevents later source syntax for explicit Zero Page
variables from moving the automatic-promotion ABI. Explicit Zero Page syntax
is not implemented yet.

## Automatic promotion policy

Promotion is optional and conservative:

1. Only global variables are candidates. Procedure and function parameters always use
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
`build/zero_page.map`. The report separates maximum-live expression
reservation, compiler caches, policy reservation, recovered Zero Page,
optional promotion, and hardware reservation. It identifies every user symbol
as `Zero Page` or `Regular RAM`.

An excerpt for the focused example is:

```text
Start  End    Size  Owner     Region
$0000  $000F    16  Runtime   Zero Page runtime
$0010  ----      0  Compiler  Expression temporaries
$0010  $0010     1  Compiler  Compiler caches
$0011  $001F    15  Free      Recovered temporary Zero Page
$0020  $007F    96  Reserved  Future explicit Zero Page
$0080  $00FF   128  User      Automatic Zero Page variables (2 used, 126 available)
$0100  $01FF   256  Reserved  6502 hardware stack
$0200  ----      0  Runtime   Runtime data
$0200  $0200     1  User      Regular user variables
$0201  $07FF  1535  Free      General free RAM
```

The map also prints `Expression temporary reservation: 0 bytes` and
`Other compiler caches: 1 byte` for this example. The generated `.cfg`,
Assembly segments, and `.map` report all use the same
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
`runtime_sprite_logical_y`, and `runtime_sprite_value`.
`runtime_sprite_secondary_value` appears only with
`nes.sprite_set_position`. The five
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
