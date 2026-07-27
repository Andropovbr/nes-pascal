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
mapper, banks, vectors, CHR data, and final size. It is skipped with an
explicit message when `ca65` or `ld65` is unavailable.

To include the optional headless Mesen behavior test, point `MESEN_PATH` to
the emulator executable before running the suite. The test compiles the
behavior examples, executes their ROMs, and verifies final variables and the
universal background color:

```powershell
$env:MESEN_PATH = "C:\path\to\Mesen.exe"
python -m unittest discover -s tests -v
```

The behavior test is skipped clearly when Mesen or the cc65 toolchain is
unavailable.
