# `nes.wait_frame`

`nes.wait_frame` blocks the main thread until the runtime-owned NMI frame
counter changes:

```pascal
nes.run;
while Running do
begin
    nes.wait_frame;
    inc(Frames);
end;
```

The command must execute after the unconditional top-level `nes.run` call. It
may appear in main-block loops and conditionals. It cannot appear inside a
procedure in this milestone; doing so produces E3015. Executing it before
`nes.run` would wait forever because NMI is still disabled, so the compiler
reports E3017.

## Synchronization contract

The NMI handler increments `runtime_frame_counter`, an 8-bit volatile counter,
once per NMI. `nes.wait_frame` samples that byte and waits until its value
changes. The counter wraps modulo 256 and remains the authoritative signal;
the separate `runtime_frame_ready` byte is a best-effort advisory latch only.
NMI sets the latch and a completed main-thread wait clears it, but races are
allowed because no synchronization decision reads it.

NMI preserves A, X, Y, processor status through the interrupt protocol, and
stack balance. It may call the one statically registered and validated
VBlank callback after frame bookkeeping. It does not run update logic or
process a generic PPU command queue.

After observing the new counter value, `nes.wait_frame` updates both controller
ports through the same guarded polling routine used by the callback loop. This
makes fresh [`controller_down`, `controller_pressed`, and
`controller_released`](controller-input.md) state available to explicit main
loops without polling a processed frame twice. It does not itself perform PPU
writes. Rendering-sensitive runtime PPU operations must execute in VBlank.
