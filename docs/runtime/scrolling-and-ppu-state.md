# Scrolling and PPU state

English | [Português (Brasil)](..\pt-BR\runtime\scrolling-and-ppu-state.md)

`nes.set_scroll(x, y)` stages one horizontal and vertical scroll pair:

```pascal
nes.set_scroll($08, $04);
```

Both arguments must be `byte` values. The call writes only runtime RAM; it
never writes `$2005` directly. Multiple calls before the next NMI use
last-write-wins semantics. Publication is atomic: NMI sees either the previous
complete pair or the newest complete pair, never one old and one new axis.

Scroll defaults to `($00, $00)`. Each NMI performs bounded palette and
background uploads, invokes the optional user VBlank callback, commits the
latest complete scroll pair, resets the shared PPU latch with `$2002`, and
then restores the authoritative state in this order:

1. PPUCTRL from its runtime shadow;
2. horizontal scroll through the first `$2005` write;
3. vertical scroll through the second `$2005` write;
4. PPUMASK from its runtime shadow.

There are exactly two `$2005` writes in this final NMI restoration. PPUCTRL,
PPUMASK, and both active scroll bytes occupy four regular-RAM bytes in every
program. Programs using `nes.set_scroll` add three bytes for the pending pair
and its publication flag. `nes.run` enables NMI and rendering by setting the
required bits in the shadows, preserving unrelated bits. Its normal PPUMASK
enable value is `$1E`: background and sprites are rendered, including both in
the leftmost eight pixels. Initialization and complete background uploads still
keep the PPUMASK shadow at `$00` until `nes.run` reaches a safe VBlank.

## Mirroring

The compiler defaults to horizontal nametable mirroring, preserving existing
program behavior. Select vertical mirroring at compile time with:

```text
python -m nes_pascal.cli game.nsp -o build/game.nes --mirroring vertical
```

`horizontal` and `vertical` set iNES header flag 6 bit 0 to `0` and `1`,
respectively. This is a static NROM header choice; it does not change at
runtime.

The current feature is intended for fixed scroll positions on static
backgrounds. It does not add camera movement, nametable streaming, four-screen
mirroring, mapper-controlled mirroring, split scrolling, or scrolling APIs
beyond `nes.set_scroll`.
