# Testing the compiler

Run the complete suite with:

```text
python -m unittest discover -s tests -v
```

Or use:

```text
make test
```

The integration test assembles and links the ROM, then validates its header,
mapper, banks, vectors, CHR data, final size, generated linker configuration,
and CPU memory map. Focused memory-layout tests cover physical boundaries,
reserved regions, deterministic allocation, mandatory temporary exhaustion,
optional promotion fallback, malformed internal settings, and segment
capacity. A ca65 listing test verifies Zero Page opcodes for promoted symbols
and NMI runtime state, plus absolute opcodes for fallback storage. Structural
backend tests verify register preservation, the counter-authoritative wait
loop, persistent pending-frame detection, VBlank-gated rendering startup, and
the separation of main-thread update calls from the restricted NMI callback.
Controller tests verify serial bit order, independent current/previous state,
compile-time arguments, transition masking, one guarded poll per processed
frame, Zero Page opcodes, fixed sprite staging, general sprite setters,
attribute preservation, visibility state, OAM initialization and DMA, and
deterministic Assembly.
Toolchain tests are skipped with an explicit message when `ca65` or `ld65` is
unavailable.

To include the optional headless Mesen behavior test, point `MESEN_PATH` to
the emulator executable or its containing directory before running the suite.
The test compiles the
behavior examples, executes their ROMs, and verifies final variables,
procedure-parameter storage, promoted and regular-RAM addresses where
applicable, NMI counter progress, three distinct `nes.wait_frame` iterations,
update and VBlank callback progress across 8-bit frame-counter wraparound, and
slow-update pending-frame behavior without nested calls, and the universal
background color. The controller ROM additionally drives both virtual ports,
checks every direction and button behavior, verifies OAM consistency, and
runs across an 8-bit frame-counter wrap. The sprite ROM verifies one visible
sprite, 63 hidden entries, attribute composition, and DMA page selection:

```powershell
$env:MESEN_PATH = "C:\path\to\Mesen.exe"
python -m unittest discover -s tests -v
```

The behavior test is skipped clearly when Mesen or the cc65 toolchain is
unavailable.
