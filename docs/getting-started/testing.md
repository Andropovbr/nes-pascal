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
and absolute opcodes for fallback storage. Toolchain tests are skipped with an
explicit message when `ca65` or `ld65` is unavailable.

To include the optional headless Mesen behavior test, point `MESEN_PATH` to
the emulator executable before running the suite. The test compiles the
behavior examples, executes their ROMs, and verifies final variables,
procedure-parameter storage, promoted and regular-RAM addresses where
applicable, and the universal background color:

```powershell
$env:MESEN_PATH = "C:\path\to\Mesen.exe"
python -m unittest discover -s tests -v
```

The behavior test is skipped clearly when Mesen or the cc65 toolchain is
unavailable.
