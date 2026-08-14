# Your first program

English | [Português (Brasil)](../pt-BR/getting-started/first-program.md)

The minimal example exercises every built-in type and the two initialization
commands:

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
color, and starts the runtime. Because no statements follow `nes.run`, the
compiler's implicit stable loop keeps the ROM running.

Compile it from the repository root:

```text
python -m nes_pascal.cli examples/minimal.nsp -o build/minimal.nes
```

After [installing the package](prerequisites-and-installation.md), the
equivalent `nes-pascal` command is also available:

```text
nes-pascal examples/minimal.nsp -o build/minimal.nes
```

The command generates `build/minimal.asm`, `build/minimal.cfg`,
`build/minimal.map`, the intermediate `build/minimal.o`, and
`build/minimal.nes`. The `.map` file explains every CPU RAM allocation. See
[Building and running programs](building-and-running.md) for the other
examples and emulator instructions.

The syntax and type rules used here are defined in the
[Language Guide](../language/index.md). The runtime operations are documented
under [NES Runtime](../runtime/index.md).
