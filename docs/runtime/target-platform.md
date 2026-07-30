# Target platform

NES Pascal generates ca65-compatible Assembly for the Ricoh 2A03 CPU and uses
only 6502 instructions. It does not generate intermediate C or use 65C02-only
instructions.

## ROM format

Generated programs target NTSC NES systems with mapper 0, NROM-256:

- an explicit iNES header;
- 32 KiB of PRG-ROM;
- 8 KiB of empty CHR-ROM;
- NMI, RESET, and IRQ vectors.

The output image is 40,976 bytes: a 16-byte iNES header, 32 KiB of PRG-ROM,
and 8 KiB of CHR-ROM.

## Startup behavior

The RESET path disables interrupts, initializes the stack and runtime-owned
RAM, and waits for the PPU to stabilize. Initialization palette writes remain
safe while rendering is disabled. `nes.run` waits for VBlank before enabling
NMI and rendering.

Each NMI preserves A, X, Y, and stack balance, increments one volatile 8-bit
frame counter, and sets an advisory frame-ready byte. If registered, one
restricted VBlank callback runs next through direct `JSR`; its procedure ends
with `RTS`, then NMI restores registers and owns the final `RTI`. Ordinary
update logic runs only on the main thread. Its persistent last-processed frame
byte preserves a pending NMI across slow callbacks and coalesces older backlog.
There is no generic PPU command queue, sprite management, controller input, or
audio.

## Memory

The NES exposes 2 KiB of physical internal CPU RAM at `$0000-$07FF`.
`$0800-$1FFF` contains mirrors, not additional storage. Zero Page has separate
runtime, compiler-temporary, future-explicit, and automatic-promotion regions.
Frequently referenced globals may be promoted conservatively; parameters and
fallback variables use regular RAM. See [CPU memory](cpu-memory.md) for the
complete deterministic policy.

CHR-ROM is empty, so the runtime does not provide game graphics or an asset
pipeline.

The generated Assembly is intentionally readable and includes comments that
identify the source of generated blocks. The backend is not a generic game
engine.
