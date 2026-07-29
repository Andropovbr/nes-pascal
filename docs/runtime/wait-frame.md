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
the separate `runtime_frame_ready` byte is advisory runtime state only.

NMI preserves A, X, Y, processor status through the interrupt protocol, and
stack balance. It does not call procedures, execute user statements, or
process a generic PPU command queue.

`nes.wait_frame` synchronizes CPU work with frames but does not itself perform
PPU writes. Rendering-sensitive runtime PPU operations must execute in VBlank.
