# Runtime background updates

English | [Português (Brasil)](../pt-BR/runtime/background-updates.md)

Milestone 0.4.4 provides bounded updates to nametable 0 after rendering starts.
All coordinates and values are `byte` expressions:

```pascal
nes.set_tile($0F, $0E, $03);
Tile := nes.get_tile($0F, $0E);
nes.set_attribute($03, $03, $E4);
```

`nes.set_tile(x, y, tile)` accepts tile coordinates `x = 0..31` and
`y = 0..29`. It queues the corresponding PPU write. When NMI writes the byte
to the PPU, it also updates the optional 960-byte confirmed tile shadow.
`nes.get_tile(x, y)` reads this shadow and therefore returns the value confirmed
in the PPU, not a value merely waiting in the queue.

`nes.set_attribute(x, y, value)` accepts hardware attribute-table coordinates
`x = 0..7` and `y = 0..7`. The value is a raw NES attribute byte for the
selected 4-by-4-tile region; the compiler does not encode palette quadrants.
Attributes have no separate RAM shadow.

Direct literal or constant coordinates outside these ranges are compile-time
errors. Other coordinate expressions are checked at runtime: out-of-range tile
or attribute writes do nothing, and an out-of-range `nes.get_tile` returns
`$00`.

## Four writes per frame

The runtime owns four fixed queue slots. Each successful `nes.set_tile` or
`nes.set_attribute` occupies one slot until the next NMI consumes it. NMI scans
all four slots and writes at most four bytes through `$2007` per frame. A slot's
ready flag is published only after its address and value are complete.

When all four slots are occupied, a later write is dropped and
`runtime_background_queue_overflow` becomes `$01`. A rejected tile or attribute
write changes neither PPU memory nor the confirmed tile shadow. Existing queue
entries are never overwritten. Once NMI frees the slots, later calls can be
accepted even while the sticky overflow flag remains set.

`nes.background_updates_overflowed()` returns a `boolean` view of that sticky
flag. `nes.clear_background_update_overflow()` resets only the flag and does not
affect queued writes.

`nes.clear_background_updates()` discards every write that has not yet been
consumed. It does not clear the overflow flag and does not change the confirmed
tile shadow or PPU memory. If NMI has already consumed a write, that confirmed
write cannot be cancelled.

When the program calls `nes.clear_background_updates()`, the compiler links a
one-byte cancellation lock checked once at the beginning of the bounded NMI
uploader. The store that acquires this lock is the race boundary. If NMI
passes the check first, it completes that whole bounded upload before main code
resumes, and cancellation then removes only writes still pending afterward. If
main code acquires the lock first, an intervening NMI skips the whole queue;
main code clears all four ready flags and then releases the lock. NMI can
therefore never observe a sequentially half-cleared queue. Tile and attribute
writes use the same protocol, and the independent sticky overflow flag is not
touched.

Repeated writes to one address occupy separate slots and are uploaded in queue
order. Before that NMI, `nes.get_tile()` still returns the previously confirmed
value. After NMI, it returns the last write processed for that tile.

## Initialization and PPU state

The 960-byte shadow is linked only when `nes.get_tile()` appears in the program.
When the program calls [`nes.load_background()`](background-loading.md), its
initial upload copies the first 960 asset bytes into that shadow. Without a
configured background, generated RESET code zeroes both nametable 0 and the
shadow while rendering and NMI are disabled. Thus the first `get_tile` result
always represents the compiler-established PPU state.

Write-only background programs omit the shadow. A tile-only program reserves
26 bytes: 22 bytes for queue state and helpers plus four shared PPU
restoration bytes. Attribute-only writes need 24 bytes because they do not use
the two tile-index helpers. The cancellation lock adds one byte only when
`nes.clear_background_updates()` is present. A program combining tile writes
with `nes.get_tile()` reserves 986 bytes without cancellation or 987 bytes with
it. A
`get_tile`-only program reserves 968 bytes and does not install the NMI queue
uploader. Programs using only the overflow inspection/clear APIs reserve only
the one-byte sticky flag. The generated `.map` identifies each conditional
block.

The backend also emits only the public background helpers referenced by the
program. Tile-only, attribute-only, and read-only programs therefore omit the
other entry points. The shared queue publisher, uploader, and tile-index helper
remain present whenever a retained public entry point calls them; this is
explicit dependency selection, not a general dead-code optimizer.

The background uploader runs before the optional user VBlank callback. One
shared NMI epilogue then restores PPUCTRL, scroll X/Y, and PPUMASK after all
runtime and user VBlank work. Background operations and `nes.get_tile` are not permitted on
a VBlank callback path because NMI owns queue consumption.

Background updates support only nametable 0, one-byte writes, and raw attribute
entries. They do not add multiple nametables, a generic PPU queue, or streaming.
