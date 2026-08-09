# `nes.run`

`nes.run` completes initialization and starts the frame-synchronized runtime
phase:

```pascal
nes.run;
```

It must:

- appear exactly once;
- remain outside conditionals, loops, and procedures.

The runtime waits for VBlank and enables NMI, background rendering, sprite
rendering, and both leftmost-eight-pixel rendering bits through compiler-owned
PPUCTRL and PPUMASK shadows. The normal enabled PPUMASK state therefore adds
`$1E` while preserving unrelated shadow bits. Content at X positions `$00..$07`
is visible by default; no public masking configuration is currently provided.
Scroll shadows retain their
zero-filled `($00, $00)` defaults unless [`nes.set_scroll`](scrolling-and-ppu-state.md)
stages a new pair. Runtime-owned state and initialization PPU writes are
complete before NMI is enabled.

When present, [`nes.load_background()`](background-loading.md) performs its
complete 1 KiB PPU upload earlier in the initialization sequence with
rendering disabled. `nes.run` remains the single point that enables rendering
after all initialization uploads finish.

Statements after `nes.run` execute on the main thread. A loop can call
[`nes.wait_frame`](wait-frame.md) to advance once per NMI. Existing programs
that end with `nes.run` remain valid: the compiler emits an implicit stable
idle loop after the main block when no update callback is registered.
Palette calls after `nes.run` stage atomically published values in runtime RAM;
the NMI uploader consumes them before any user VBlank callback.

When [`nes.on_update`](frame-callbacks.md) registers a callback, the implicit
loop records one persistent initial frame baseline, waits until the volatile
counter differs, stores the newest observed value, calls the update procedure
once with direct `JSR`, and repeats. A frame that arrives during a slow update
therefore remains pending and is processed immediately after the callback
returns. Backlogs are coalesced to the newest frame rather than replayed.
Before each accepted callback, the main runtime updates both controller ports
once. Update logic remains in normal main context. A separately registered
VBlank callback runs in NMI.
