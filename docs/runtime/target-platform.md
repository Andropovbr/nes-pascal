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

The RESET path disables interrupts, initializes the stack, and waits for the
PPU to stabilize. PPU writes occur only at safe times during initialization.
The program sets the universal background color, enables rendering, and then
remains in a stable loop.

The runtime does not provide frame callbacks, a frame-based game loop, sprite
management, controller input, or audio.

## Memory

Global variables occupy one byte each in regular CPU RAM. The compiler does
not allocate user variables or expression temporaries in zero page. CHR-ROM is
empty, so the runtime does not provide game graphics or an asset pipeline.

The generated Assembly is intentionally readable and includes comments that
identify the source of generated blocks. The backend is not a generic game
engine.
