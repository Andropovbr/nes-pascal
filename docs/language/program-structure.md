# Program structure

A program contains:

1. the `program` keyword;
2. a program name;
3. a semicolon;
4. an optional `const` section;
5. an optional `var` section;
6. zero or more procedure declarations;
7. a block beginning with `begin`;
8. a sequence of statements;
9. the `end` keyword;
10. a final period.

Example:

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

The declaration sections must appear in this order. The main block completes
the program and contains the top-level initialization sequence.
