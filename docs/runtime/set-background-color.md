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

## Initialization and runtime behavior

A valid program must establish its initial background color with exactly one
top-level call before `nes.run`. That call writes `$3F00` directly while
rendering is disabled.

Calls after `nes.run` or inside procedures update the canonical palette shadow
and publish the change for the next VBlank. They never write `$2006/$2007`
from normal runtime code. Repeated pending changes are last-write-wins. See
[Palette API](palettes.md) for color-zero mirroring and queue details.
