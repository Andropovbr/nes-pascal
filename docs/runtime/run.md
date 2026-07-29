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
idle loop after the main block.

`nes.run` does not move user logic into NMI. Frame callbacks remain
unsupported.
