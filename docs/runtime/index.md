# NES Runtime

The implemented runtime provides a small initialization sequence and a
runtime-owned NMI handler for an NTSC NROM program. It exposes five
source-language commands:

- [`nes.set_background_color`](set-background-color.md) sets the universal
  NES background palette color;
- [`nes.run`](run.md) completes initialization, enables NMI and rendering at
  VBlank, and starts the frame-synchronized runtime phase;
- [`nes.wait_frame`](wait-frame.md) waits for the volatile NMI frame counter
  to change;
- [`nes.on_update`](frame-callbacks.md) statically registers one parameterless
  procedure for the main-thread frame loop;
- [`nes.on_vblank`](frame-callbacks.md) statically registers one restricted,
  parameterless procedure for NMI VBlank work.

The initialization commands belong to the top-level main program block.
`nes.wait_frame` may appear in main-block loops and conditionals after
`nes.run`, but not in procedures. The only user code executed by NMI is the
single statically validated VBlank callback, when registered.

See [Target platform](target-platform.md) for the generated ROM format and
hardware initialization behavior. See [CPU memory](cpu-memory.md) for the
physical RAM limit, reserved regions, user capacity, and generated memory-map
artifact.
