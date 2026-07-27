# Your first program

The minimal example exercises every built-in type and the two implemented NES
runtime commands:

```pascal
program Minimal;

const
    DefaultBackgroundColor: nes_color = $21;

var
    BackgroundColor: nes_color;
    FrameCounter: byte;
    RenderingEnabled: boolean;

begin
    BackgroundColor := DefaultBackgroundColor;
    FrameCounter := $00;
    RenderingEnabled := true;
    nes.set_background_color(BackgroundColor);
    nes.run;
end.
```

The program declares one typed constant and three typed global variables. Its
main block assigns every variable before use, sets the universal background
color, enables rendering, and enters the runtime's stable loop.

Compile it from the repository root:

```text
python -m nes_pascal.cli examples/minimal.nsp -o build/minimal.nes
```

The command generates `build/minimal.asm`, the intermediate
`build/minimal.o`, and `build/minimal.nes`. See
[Building and running programs](building-and-running.md) for the other
examples and emulator instructions.

The syntax and type rules used here are defined in the
[Language Guide](../language/index.md). The runtime operations are documented
under [NES Runtime](../runtime/index.md).
