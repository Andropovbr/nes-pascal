# VBlank cycle budget

NES Pascal targets NTSC NES. One VBlank is approximately 2,273 CPU cycles.
That is the hardware window, not a safe promise that every one of those cycles
is available: NMI begins after the current instruction completes, OAM DMA has
a one-cycle parity variation, and taken branches can gain a page-crossing
cycle. Programs should retain margin rather than consume the estimate exactly.

The generated NMI performs work in this fixed order:

1. enter NMI, preserve A, X, and Y, and publish frame state;
2. commit legacy sprite-zero staging when present, then run OAM DMA when any
   sprite operation is linked;
3. scan and upload queued palette changes when runtime palette calls exist;
4. scan up to four queued background writes when runtime background calls exist;
5. call the optional user VBlank callback;
6. commit a complete pending scroll pair when `nes.set_scroll` is linked;
7. reset the PPU latch and restore PPUCTRL, scroll X/Y, and PPUMASK;
8. restore registers and return.

The 1 KiB `nes.load_background()` transfer is not part of this budget. Neither
is the equivalent zero fill generated when `nes.get_tile` is used without a
configured background. Both run once during RESET initialization while
rendering and NMI are disabled.

## Current costs

The following counts use standard Ricoh 2A03 instruction timings and include
subroutine calls and returns where stated. They describe the current generated
code and should be updated when that code changes.

| NMI component | Estimated CPU cycles |
| --- | ---: |
| Hardware entry, register save, frame bookkeeping, register restore, and `RTI` | 52 |
| Palette scan with no dirty colors | 75 |
| Palette scan with all eight triplets and the universal color dirty | 784 |
| Background uploader skipped while cancellation owns its lock | 19 |
| Background queue scan with no published slots and no cancellation support | 67 |
| Background queue scan with four write-only slots and no cancellation support | 203 |
| Background queue scan with four confirmed tiles and no cancellation support | 335 |
| Additional lock check when cancellation support is linked | 6 |
| General-sprite OAM DMA, including `$2003` reset | 525-526 |
| Legacy sprite-zero commit plus OAM DMA | 569-570 |
| Empty user VBlank callback dispatch (`JSR` plus `RTS`) | 12 |
| Final PPU state restoration | 36 |
| Linked scroll commit with no pending pair | 7 |
| Linked scroll commit with a pending pair | 28 |

The palette maximum writes 25 palette bytes: three independently visible
colors for each of eight palettes plus the universal background color. Its
work is bounded because the runtime scans nine fixed flags and has no dynamic
queue.

Representative worst cases, including an otherwise empty registered VBlank
callback, are:

| Enabled work | Estimated used | Approximate remainder of 2,273 |
| --- | ---: | ---: |
| Clean palette scan | 175 | 2,098 |
| All palette colors dirty | 884 | 1,389 |
| General OAM DMA and all palette colors dirty | 1,410 | 863 |
| Four background writes with confirmed shadow updates | 435 | 1,838 |
| All palette colors dirty and four confirmed tile writes | 1,219 | 1,054 |
| General OAM DMA, all palette colors dirty, and four confirmed tile writes | 1,745 | 528 |

The remainder must cover the callback body, any procedures it calls, timing
jitter, and a safety margin. A program without a registered callback omits the
12-cycle dispatch. Linking cancellation adds six cycles to each row containing
background work; the final row then becomes 1,751 used and 522 remaining.
Linking `nes.set_scroll` adds seven cycles when no pair is pending or 28 cycles
when NMI commits one, reducing the corresponding remainder by that amount.
Metasprites use the same general OAM DMA row: component layout is calculated
before NMI in main/update context, so component count adds no VBlank work.
Programs using the legacy `nes.set_sprite_zero` compatibility helper add up to
44 cycles for its atomic record commit, reproducing the former 1,789-cycle
combined worst case before cancellation or scroll work.

## Scalability limits

The compiler checks whether VBlank callbacks use the supported interrupt-safe
subset, but it does not calculate loop bounds, call-graph cycles, or reject an
over-budget callback. A structurally valid callback can still overrun VBlank.
The current all-dirty palette path, four confirmed tile writes, and general
OAM DMA consume about 77 percent of the nominal window before useful callback work. The
background contribution is bounded by four single-byte PPU writes per frame;
additional requests are rejected and set a sticky overflow flag. Write-only
programs omit the shadow confirmation work and use a 203-cycle uploader
maximum, or 209 cycles when cancellation support is linked.

Only programs containing `nes.clear_background_updates()` link the one-byte
cancellation lock and its uploader check. This adds six cycles to their normal
queue scans. When the lock is held, the call returns in 19 cycles without
touching PPU state or any queue slot. If NMI passed the check before
cancellation acquired the lock, NMI finishes its bounded scan before main code
can continue; this is the atomic all-or-none boundary documented for
`nes.clear_background_updates()`. Programs using only overflow inspection or
clearing omit the background uploader entirely.

This design scales only while additional fixed NMI tasks remain explicitly
bounded and their combined worst case leaves margin. Nametable streaming,
automatic animation work in NMI, audio DMA, or other PPU uploads would need a
revised central budget and scheduling policy; none are implemented here. The
figures are NTSC-only and do not claim PAL timing support.

One shared epilogue restores PPUCTRL, scroll X/Y, and PPUMASK after every
runtime uploader and the optional user callback. `nes.run` preserves bits while
enabling the current `$80` PPUCTRL and `$1E` PPUMASK default; scroll
starts at `($00, $00)`. This central cost replaces the former duplicate
uploader-local restoration costs.
