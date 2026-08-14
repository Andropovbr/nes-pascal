# Program structure

English | [Português (Brasil)](../pt-BR/language/program-structure.md)

A program contains:

1. the `program` keyword;
2. a program name;
3. a semicolon;
4. an optional `type` section;
5. an optional `const` section;
6. an optional `var` section;
7. zero or more procedure and function declarations;
8. a block beginning with `begin`;
9. a sequence of statements;
10. the `end` keyword;
11. a final period.

Example:

```pascal
program Minimal;

const
    DefaultBackgroundColor: nes_color = $21;

var
    BackgroundColor: nes_color;
    FrameCounter: byte;
    RenderingEnabled: boolean;

procedure Initialize(Start: byte; Enabled: boolean);
begin
    FrameCounter := Start;
    RenderingEnabled := Enabled;
end;

begin
    BackgroundColor := DefaultBackgroundColor;
    Initialize($00, true);
    nes.set_background_color(BackgroundColor);
    nes.run;
end.
```

The declaration sections must appear in this order: `type`, `const`, then
`var`, followed by any interleaved [procedures](procedures.md) and
[functions](functions.md). The main block contains
the top-level initialization sequence and may continue with frame-synchronized
main-thread logic after `nes.run`.

The `type` section may declare nominal [enumerations](enumerations.md) and
fixed-layout [records](records.md). Record fields may use any declared enum in
the section; nested record fields remain unsupported.

Static `nes.on_update(Procedure)` and `nes.on_vblank(Procedure)` registrations,
when present, belong to the unconditional top-level initialization sequence
before `nes.run`. See [Frame callbacks](../runtime/frame-callbacks.md).

The optional `nes.load_background()` command is also an unconditional,
top-level initialization statement before `nes.run`. It has no arguments and
requires configured [nametable data](../runtime/background-loading.md).

Bounded [runtime background updates](../runtime/background-updates.md) may be
staged from main code or procedures. Their queue-mutating operations are not
allowed on a VBlank callback path; the simple overflow query is safe there.
