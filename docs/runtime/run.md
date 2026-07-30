# `nes.run`

`nes.run` completes initialization and starts the frame-synchronized runtime
phase:

```pascal
nes.run;
```

It must:

- appear exactly once;
- remain outside conditionals, loops, and procedures.

The runtime waits for VBlank, restores the supported scroll state, enables NMI,
and enables background rendering. Runtime-owned state and initialization PPU
writes are complete before NMI is enabled.

Statements after `nes.run` execute on the main thread. A loop can call
[`nes.wait_frame`](wait-frame.md) to advance once per NMI. Existing programs
that end with `nes.run` remain valid: the compiler emits an implicit stable
idle loop after the main block when no update callback is registered.

When [`nes.on_update`](frame-callbacks.md) registers a callback, the implicit
loop records one persistent initial frame baseline, waits until the volatile
counter differs, stores the newest observed value, calls the update procedure
once with direct `JSR`, and repeats. A frame that arrives during a slow update
therefore remains pending and is processed immediately after the callback
returns. Backlogs are coalesced to the newest frame rather than replayed.
Update logic remains in normal main context. A separately registered VBlank
callback runs in NMI.
