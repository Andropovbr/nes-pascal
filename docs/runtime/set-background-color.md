# `nes.set_background_color`

`nes.set_background_color` sets the universal NES background palette color.

## Syntax

A constant reference may be passed:

```pascal
nes.set_background_color(BackgroundColor);
```

Direct hexadecimal literals remain supported:

```pascal
nes.set_background_color($21);
```

The argument must resolve to a valid `nes_color`. It may also be a previously
assigned `nes_color` variable:

```pascal
BackgroundColor := $21;
nes.set_background_color(BackgroundColor);
```

See [`nes_color`](../language/types.md#nes_color) for its `$00..$3F` range and
[Assignments](../language/assignments.md) for definite-assignment rules.

## Placement and call count

A valid program must call `nes.set_background_color` exactly once before
`nes.run`. The call must be in the top-level program block. It cannot appear
inside a conditional, loop, or procedure.

These restrictions keep the initialization sequence unconditional and ensure
that the PPU palette write executes exactly once at a safe time.
