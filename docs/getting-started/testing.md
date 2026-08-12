# Testing the compiler

English | [Português (Brasil)](../pt-BR/getting-started/testing.md)

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
deterministic Assembly. Sprite-management tests additionally cover static OAM
ownership, explicit-index coexistence, 64-entry exhaustion, and the combined
position setter. Metasprite tests validate the attached PNG2CHR Studio asset,
its already anchor-relative offset contract, malformed schema variants,
arbitrary signed/sparse/reused layouts, centered and non-centered pivots,
asymmetric horizontal/vertical geometry, bounding-range preservation,
component flip XOR, shared OAM ownership and exhaustion, compact PRG tables,
per-instance RAM, visibility, shorter-frame hiding, edge clipping structure,
and optional Mesen behavior. Sprite-animation tests add symbolic sequence
imports, default and overridden durations, loop policy, one-shot completion,
same-animation stability, restart, hidden advancement, flip preservation,
independent instances, variable component counts, feature emission, and exact
RAM/PRG table costs.
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
sprite, 63 hidden entries, attribute composition, and DMA page selection. The
metasprite player ROM drives all eight D-pad directions and validates in-place
centered flipping, manual frame selection while flipped, source/whole flip
composition, asset-derived fully visible gameplay limits at all four edges,
hide/move/show state, logical Y conversion, component OAM, and DMA. A separate
deterministic clipping fixture validates all four edges,
horizontal, vertical, and combined flips, negative offsets, non-wrapping
coordinates, hidden movement, and flipped frame switching; the user-facing
clipping example remains deliberately slow enough for visual inspection. The
sprite-animation fixture additionally validates exact 2/3/1-frame timing,
loop wrap, one-shot final-frame retention and completion, explicit restart,
hidden playback, independent start times, stale-slot hiding, flip persistence,
manual-frame cancellation, and inactive-instance isolation. The consolidated
player regression verifies that manual and animated consumers emit identical
centered frame geometry, that idle/movement selections do not restart while
repeated, and that facing survives state changes. A second Mesen pass drives
the actual animated-player example through idle, left movement, left-facing
idle, vertical movement, right movement, and right-facing idle. The visual
clipping example also completes one full center/partial-edge cycle under an
automated state/OAM check:

```powershell
$env:MESEN_PATH = "C:\path\to\Mesen.exe"
python -m unittest discover -s tests -v
```

The behavior test is skipped clearly when Mesen or the cc65 toolchain is
unavailable.

## Continuous Integration (CI)

The repository uses GitHub Actions for automated regression testing on every
push and manual trigger (`workflow_dispatch`). All CI jobs run on pinned
`ubuntu-24.04` runners. The pipeline consists of three jobs:

1. **`compiler-toolchain`**: Installs Python and the `cc65` toolchain (`ca65`
   and `ld65`), executes the complete compiler regression test suite (lexer,
   parser, semantic, memory layout, diagnostics, golden assembly, and ROM build
   integration tests), and generates the compiler benchmark report using
   `tools/measure_benchmarks.py`. The generated report is published directly to
   the job step summary and uploaded as the `benchmark-report` build artifact.
   Benchmark metrics are currently observable and informational rather than
   threshold-gated.
2. **`mesen-runtime`**: Depends on `compiler-toolchain`, installs `ca65`/`ld65`
   and MesenCE 2.2.1, configures `MESEN_PATH`, and executes the complete
   suite of headless Mesen behavioral runtime tests.
3. **`ci-gate`**: Acts as the single authoritative gate verifying that both
   `compiler-toolchain` and `mesen-runtime` completed successfully.

### Local vs CI Execution Policy

During development, iterate using focused tests for the subsystem being modified.
While local integration tests gracefully skip when external dependencies (`ca65`,
`ld65`, or Mesen) are absent, authoritative CI jobs must install all required
dependencies and execute all assertions without skipping.

### Canonical Developer Workflow Commands

The repository provides canonical `Makefile` targets that wrap standard Python entry points:

| Target | Command | Requirements | Description |
| :--- | :--- | :--- | :--- |
| `make test` | `python -m unittest discover -s tests -v` | Python | Standard local regression test suite. Skips Mesen tests when `MESEN_PATH` is unset. |
| `make test-all` | `make test` | Python | Explicit alias for `make test` running the complete discovery suite. |
| `make test-mesen` | `python -m unittest tests.test_integration.MesenIntegrationTests -v` | `ca65`, `ld65`, `MESEN_PATH` | Runs the headless Mesen behavioral emulation test suite. |
| `make benchmark` | `python tools/measure_benchmarks.py` | `ca65`, `ld65` | Runs the compiler resource and pattern measurement tool. |
| `make rom` | `python -m nes_pascal.cli examples/minimal.nsp -o build/minimal.nes` | `ca65`, `ld65` | Compiles the canonical representative minimal ROM. |
| `make clean` | Removes `build/`, `*.log`, `benchmark-report.md` | Python | Safely cleans transient build outputs without deleting tracked assets. |
| `make validate` | Runs `test-all`, `benchmark`, `rom` | `ca65`, `ld65` | Comprehensive local pre-push validation. Does not replace the authoritative CI gate. |

To run equivalent commands directly without Make:

```text
# Run focused unit tests during development (e.g. arrays)
python -m unittest tests.test_arrays -v

# Run the standard compiler regression suite
python -m unittest discover -s tests -v

# Run the Mesen runtime behavioral suite (requires ca65, ld65, and MESEN_PATH)
python -m unittest tests.test_integration.MesenIntegrationTests -v

# Generate the benchmark metrics report locally (requires ca65 and ld65 on PATH)
python tools/measure_benchmarks.py

# Build the representative minimal ROM
python -m nes_pascal.cli examples/minimal.nsp -o build/minimal.nes
```

