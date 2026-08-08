# Controller input

NES Pascal reads the standard controllers connected to ports 1 and 2. Input
is sampled by the main runtime outside NMI exactly once for each processed
frame. The frame counter remains the authoritative synchronization source.

## Button constants

The eight built-in `byte` constants use the same stable layout as the runtime
state bytes:

| Constant | Mask | Serial position |
| --- | --- | --- |
| `nes.button_a` | `$01` | 1 |
| `nes.button_b` | `$02` | 2 |
| `nes.button_select` | `$04` | 3 |
| `nes.button_start` | `$08` | 4 |
| `nes.button_up` | `$10` | 5 |
| `nes.button_down` | `$20` | 6 |
| `nes.button_left` | `$40` | 7 |
| `nes.button_right` | `$80` | 8 |

Simultaneous and opposing directions are stored exactly as the controller
reports them. The runtime does not filter combinations.

## Queries

Each query returns a canonical `boolean` value. The controller argument must
be the direct hexadecimal value `$01` or `$02`, or a declared compile-time
`byte` constant with one of those values. Dynamic controller indexes are not
supported.

```pascal
if nes.controller_down($01, nes.button_right) then
    inc(PlayerX);

if nes.controller_pressed($01, nes.button_start) then
    PlayerX := $78;

if nes.controller_released($01, nes.button_b) then
    PlayerTile := $01;
```

The second argument must be exactly one built-in button constant. Arbitrary
masks and button expressions are intentionally rejected.

- `nes.controller_down` is true while the current state contains the button.
- `nes.controller_pressed` is true when the bit is set in current state and
  clear in previous state.
- `nes.controller_released` is true when the bit is clear in current state and
  set in previous state.

Current and previous state are stable for the entire processed frame, so
repeated queries return consistent results. `pressed` and `released` describe
transitions between processed frames, not raw NMI events. Slow updates
coalesce missed frames and compare the newest poll with the last processed
poll rather than replaying an input backlog.

## Runtime order

For a registered update callback, the main runtime order is:

```text
wait until runtime_frame_counter differs from runtime_last_processed_frame
accept the newest pending frame
copy current controller states to previous states
latch and read ports $4016 and $4017
call the update callback
```

`nes.wait_frame` calls the same idempotent controller-update abstraction after
observing a new frame. `runtime_controller_polled_frame` prevents the ports
from being sampled twice if two runtime paths refer to the same processed
frame. A separate `runtime_controller_poll_valid` byte ensures that cleared
RAM is not mistaken for an already processed frame when the first accepted
counter value is `$00`. Controller polling is never called from NMI or a
VBlank callback.

## Hardware protocol and limitation

The internal reader writes `$01` and then `$00` to `$4016`, then reads eight
serial bits from `$4016` and `$4017` in parallel. The routine is isolated so a
future audio milestone can replace it without changing the Pascal API.

This first reader is not DMC-safe. DMC sample playback can delete controller
read cycles on NES hardware, so a repeated-read or another DMC-safe algorithm
must replace it before DMC audio is enabled.

## Controller example sprite

[`examples/controller_input.nsp`](../../examples/controller_input.nsp) uses a
fixed `nes.set_sprite_zero(x, y, tile, attributes)` helper solely to make the
controller milestone visible. The helper invalidates a five-byte staging
record, writes all four sprite fields, and publishes it. NMI commits only a
complete record to `runtime_oam_shadow` before OAM DMA.

This helper supports hardware sprite 0 only. It is not a sprite allocation,
management, animation, collision, or metasprite API. Its two 8x8 player tiles
are embedded in CHR-ROM only when the helper is used. New programs should use
the general [hardware sprite primitives](sprites.md); the fixed helper remains
for compatibility with this focused controller example.
