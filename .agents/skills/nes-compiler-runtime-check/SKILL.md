---
name: nes-compiler-runtime-check
description: Validate the NES Pascal source-to-ROM runtime path when behavior depends on actual NES execution or hardware state.
---

Pipeline:

`.nsp -> NES Pascal -> .asm -> ca65 -> ld65 -> .nes -> Mesen/runtime assertion`

Use for PPU/NMI/controller/OAM/scrolling/timing-sensitive behavior or cross-feature runtime interactions.

1. Build a minimal representative `.nsp` program.
2. Confirm compiler success and inspect generated Assembly only as needed.
3. Confirm ca65/ld65 produce the ROM.
4. Prefer the automated Mesen integration entry point (`make test-mesen` or focused test).
5. Assert deterministic known runtime state when automation supports it.
6. Bound execution time and use explicit success/failure conditions.
7. Manual emulator inspection may supplement but not replace an available automated assertion.
8. Never claim Mesen/runtime validation if the ROM was not executed.

Report source fixture, runtime assertion and result.
