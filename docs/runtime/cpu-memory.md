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
| `$0200-$02FF` | 256 bytes | Runtime | Page-aligned OAM shadow, symbol `runtime_oam_shadow` |
| `$0300` | 0 bytes | Runtime | Scalar regular-RAM runtime data; currently empty |
| `$0300-$07FF` | 1,280 bytes | User/free | Non-promoted globals and all procedure parameters |

The Zero Page partitions are fixed and non-overlapping. Runtime and compiler
allocations are mandatory. They never borrow from optional promotion space.
The runtime owns `runtime_frame_counter` at `$0000` and
`runtime_frame_ready` at `$0001`. The update loop owns
`runtime_last_processed_frame` at `$0002`. These runtime bytes cannot overlap
compiler storage. The compiler places reusable expression slots and cached
`for` limits in `$0010-$001F`. Needing more than 16 temporary bytes is a
compilation error.

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
$0200  $02FF   256  Runtime   OAM shadow
$0300  ----      0  Runtime   Runtime data
$0300  $0300     1  User      Regular user variables
$0301  $07FF  1279  Free      General free RAM
```

The generated `.cfg`, Assembly segments, and `.map` report all use the same
validated layout object, so their address calculations cannot drift.

The runtime-symbol table also reports:

```text
$0000       1  runtime_frame_counter  volatile 8-bit NMI frame counter
$0001       1  runtime_frame_ready    best-effort advisory frame-ready latch
$0002       1  runtime_last_processed_frame  persistent update-loop baseline
```
