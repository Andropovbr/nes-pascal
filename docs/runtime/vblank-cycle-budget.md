# VBlank cycle budget

NES Pascal targets NTSC NES. One VBlank is approximately 2,273 CPU cycles.
That is the hardware window, not a safe promise that every one of those cycles
is available: NMI begins after the current instruction completes, OAM DMA has
a one-cycle parity variation, and taken branches can gain a page-crossing
cycle. Programs should retain margin rather than consume the estimate exactly.

The generated NMI performs work in this fixed order:

1. enter NMI, preserve A, X, and Y, and publish frame state;
2. commit sprite-zero staging and run OAM DMA when that helper is used;
3. scan and upload queued palette changes when runtime palette calls exist;
4. call the optional user VBlank callback;
5. restore registers and return.

## Current costs

The following counts use standard Ricoh 2A03 instruction timings and include
subroutine calls and returns where stated. They describe the current generated
code and should be updated when that code changes.

| NMI component | Estimated CPU cycles |
| --- | ---: |
| Hardware entry, register save, frame bookkeeping, register restore, and `RTI` | 52 |
| Palette scan with no dirty colors, including PPUCTRL and scroll restoration | 99 |
| Palette scan with all eight triplets and the universal color dirty, including restoration | 808 |
| Sprite-zero commit plus OAM DMA | 569-570 |
| Empty user VBlank callback dispatch (`JSR` plus `RTS`) | 12 |

The palette maximum writes 25 palette bytes: three independently visible
colors for each of eight palettes plus the universal background color. Its
work is bounded because the runtime scans nine fixed flags and has no dynamic
queue.

Representative worst cases, including an otherwise empty registered VBlank
callback, are:

| Enabled work | Estimated used | Approximate remainder of 2,273 |
| --- | ---: | ---: |
| Clean palette scan | 163 | 2,110 |
| All palette colors dirty | 872 | 1,401 |
| OAM DMA and all palette colors dirty | 1,442 | 831 |

The remainder must cover the callback body, any procedures it calls, timing
jitter, and a safety margin. A program without a registered callback omits the
12-cycle dispatch.

## Scalability limits

The compiler checks whether VBlank callbacks use the supported interrupt-safe
subset, but it does not calculate loop bounds, call-graph cycles, or reject an
over-budget callback. A structurally valid callback can still overrun VBlank.
The current all-dirty palette path and OAM DMA consume about 63 percent of the
nominal window before useful callback work.

This design scales only while additional fixed NMI tasks remain explicitly
bounded and their combined worst case leaves margin. Nametable streaming,
general sprite systems, audio DMA, or other PPU uploads would need a revised
central budget and scheduling policy; none are implemented here. The figures
are NTSC-only and do not claim PAL timing support.

The palette uploader restores PPUCTRL and scroll X/Y from compiler-owned
runtime shadows. `nes.run` initializes them to the current `$80`, `$00`, and
`$00` defaults. This removes the uploader's former `(0, 0)` literal assumption
without adding scrolling APIs. Any future code that changes those PPU values
must update the shadows as part of that later feature.
