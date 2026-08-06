# Background loading

`nes.load_background()` uploads one complete static background during program
initialization:

```pascal
begin
    nes.load_background();
    nes.set_background_color($0F);
    nes.run;
end.
```

The command takes no arguments, is optional, and may appear at most once. It
must be an unconditional top-level statement before `nes.run`; it cannot be
used in a procedure, conditional, loop, or after rendering starts.

## Combined 1 KiB asset

Configure one raw 1024-byte nametable with `--nametable`:

```text
python -m nes_pascal.cli examples/nametable_loading.nsp -o build/nametable_loading.nes --chr assets/chr_asset.chr --nametable assets/nametable_loading.nam
```

The first 960 bytes are the row-major 32-by-30 tile indexes for PPU addresses
`$2000-$23BF`. The final 64 bytes are the hardware-native attribute table for
`$23C0-$23FF`. There is no header, compression, conversion, or metadata.

## Separate tile and attribute files

The same bytes may be configured separately:

```text
python -m nes_pascal.cli game.nsp -o build/game.nes --nametable-tiles assets/screen.tiles --nametable-attributes assets/screen.attributes
```

The tile file must contain exactly 960 bytes and the attribute file exactly 64
bytes. Both options are required together. They cannot be combined with
`--nametable`.

All asset paths are resolved from the directory containing the `.nsp` source,
not the compiler process working directory. Relative `.` and `..` components,
platform-native separators, and absolute paths are supported. Missing,
unreadable, conflicting, incomplete, or incorrectly sized configurations stop
compilation; the compiler never substitutes empty background data.

## Generated behavior and limits

The validated 1024 bytes are embedded unchanged once in PRG-ROM. During RESET
initialization, generated code explicitly keeps rendering disabled, resets the
PPU address latch, selects `$2000`, and copies all four 256-byte pages through
`$2007`. Later initialization commands may configure palettes. `nes.run` waits
for VBlank, restores the current PPU state, and then enables rendering.

This remains the initialization-only bulk upload for nametable 0. After
`nes.run`, bounded single-byte tile and attribute changes use the
[runtime background update APIs](background-updates.md). Multiple screens,
mirroring selection, scrolling, and asset conversion remain unsupported.
If `nes.get_tile` is linked without this command, RESET instead zeroes
nametable 0 so the confirmed RAM shadow starts consistent with the PPU.
