# CPU memory

NES Pascal models exactly 2,048 bytes of physical internal CPU RAM:
`$0000-$07FF`. Addresses `$0800-$1FFF` are hardware mirrors of that same RAM
and are never treated as additional allocatable storage.

## Default layout

| Range | Size | Owner | Purpose |
| --- | ---: | --- | --- |
| `$0000-$00FF` | 256 bytes | Reserved | Zero Page, reserved for milestone 0.3.2 |
| `$0100-$01FF` | 256 bytes | Reserved | 6502 hardware stack |
| `$0200-$02FF` | 256 bytes | Runtime | Page-aligned OAM shadow, symbol `runtime_oam_shadow` |
| `$0300` | 0 bytes | Runtime | Scalar runtime data; currently empty |
| `$0300-$030F` | 16 bytes | Compiler | Reusable expression and cached for-limit temporaries |
| `$0310-$07FF` | 1,264 bytes | User/free | Globals followed by procedure value-parameter slots |

The OAM shadow always occupies one complete page so a future sprite runtime
can use the NES OAM DMA mechanism without changing its address. User code
cannot allocate it directly.

The 16-byte compiler pool is reserved even when a program uses fewer
temporaries. Expression slots are reused by evaluation depth. For-loop final
values use deterministic slots in the same pool. A program that needs more
than 16 compiler slots is rejected before Assembly is emitted.

Globals are allocated in source declaration order. Procedure value-parameter
slots follow, in procedure and parameter declaration order. Every currently
implemented type occupies one byte. With no user symbols, 1,264 bytes are
available; each global or parameter reduces that total by one. Allocation
never wraps or enters `$0800-$1FFF`.

Zero Page remains fully reserved. Zero Page allocation and addressing are
deferred to milestone 0.3.2.

## Generated memory map

For an output named `build/memory_layout.nes`, the compiler writes
`build/memory_layout.map`. Its region table gives start, end, size, owner, and
temporary-pool usage. Summary lines show reserved-or-used and free totals.
Separate symbol tables list user, runtime, and compiler allocations.

An excerpt looks like this:

```text
NES Pascal CPU Memory Map
=========================

Physical CPU RAM: $0000-$07FF (2048 bytes)

Start  End    Size  Owner     Region
$0000  $00FF   256  Reserved  Zero Page
$0100  $01FF   256  Reserved  6502 hardware stack
$0200  $02FF   256  Runtime   OAM shadow
$0300  ----      0  Runtime   Runtime data
$0300  $030F    16  Compiler  Expression temporaries (2 used, 14 available)
$0310  $0317     8  User      User variables
$0318  $07FF  1256  Free      Free RAM
```

The generated `.cfg` file uses the same layout object, so the Assembly
segments, linker regions, and reported addresses cannot drift independently.
