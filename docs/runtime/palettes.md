# Palette API

English | [Português (Brasil)](..\pt-BR\runtime\palettes.md)

NES Pascal exposes four background palettes and four sprite palettes. Palette
and color indexes are compile-time `byte` values in `$00..$03`; each color is
a `nes_color` in `$00..$3F`.

```pascal
nes.set_background_palette($00, $0F, $01, $11, $21);
nes.set_sprite_palette($03, $0F, $06, $16, $26);
nes.set_background_palette_color($02, $03, $30);
nes.set_sprite_palette_color($01, $02, $27);
```

The full calls take `(PaletteIndex, Color0, Color1, Color2, Color3)`. The
individual calls take `(PaletteIndex, ColorIndex, Color)`. Dynamic indexes are
not supported by the current fixed built-in-call model.

## NES layout and universal color

Background palettes occupy `$3F00-$3F0F`; sprite palettes occupy
`$3F10-$3F1F`. NES mirrored color-zero entries are represented by one
canonical universal background color at `$3F00`, not as eight independent
values. Therefore color index zero in any full or individual palette call
updates that canonical color. `nes.set_background_color(Color)` is the direct,
explicit API for the same value. Later calls win deterministically.

The three independently visible colors of each background or sprite palette
are written to offsets one through three. Mirrored addresses are not exposed
as separate user-facing entries.

## Initialization and runtime

Top-level calls before `nes.run` write directly after the PPU warm-up while
rendering is disabled. Calls execute in source order, so repeated writes use
last-write-wins behavior.

Calls after `nes.run`, in main loops, and in procedures stage values in a
32-byte palette shadow. One publish flag per palette plus one universal-color
flag makes each staged update atomic. Replacing a pending update invalidates
its flag before writing bytes and publishes it only after all bytes are stable;
the latest complete update is therefore applied at the next VBlank.

NMI checks a fixed set of nine flags. Unchanged palettes are skipped, dirty
flags are cleared as they are consumed, and at most eight three-color uploads
plus the universal color can run in one NMI. There is no dynamic command queue.

Palette writes change the PPU address latch. After the uploader and optional
user VBlank callback, one shared NMI epilogue resets the latch and restores
PPUCTRL, scroll X/Y, and PPUMASK from compiler-owned shadows. This keeps palette
work compatible with [`nes.set_scroll`](scrolling-and-ppu-state.md) and avoids
duplicated uploader-local restoration.

See [VBlank cycle budget](vblank-cycle-budget.md) for the bounded uploader's
current cost and remaining capacity.
