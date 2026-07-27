# NES Runtime

The implemented runtime provides a small initialization sequence for an NTSC
NROM program. It exposes two source-language commands:

- [`nes.set_background_color`](set-background-color.md) sets the universal
  NES background palette color;
- [`nes.run`](run.md) completes initialization and enters a stable loop.

Both commands belong to the top-level main program block. They cannot appear
inside conditionals, loops, or procedures because initialization commands must
execute in a predictable sequence.

See [Target platform](target-platform.md) for the generated ROM format and
hardware initialization behavior.
