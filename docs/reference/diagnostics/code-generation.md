# Code-generation diagnostics

Code-generation diagnostics use the E5000-E5999 range.

## E5001 - Missing toolchain

- **Category:** Code Generation
- **Explanation:** ca65 or ld65 cannot be found, so the compiler cannot produce
  a ROM.
- **Trigger:**

  ```text
  python -m nes_pascal.cli examples/minimal.nsp -o build/minimal.nes
  ```

  with cc65 absent from `PATH`.

- **Expected compiler output:**

  ```text
  E5001: missing toolchain component: ca65 and ld65.
  ```

- **Suggested fix:** Install cc65 and add ca65 and ld65 to `PATH`.

## E5002 - Toolchain failure

- **Category:** Code Generation
- **Explanation:** ca65 or ld65 returned a nonzero exit status.
- **Trigger:**

  ```text
  ca65 or ld65 rejects its generated input
  ```

- **Expected compiler output:**

  ```text
  E5002: ca65 failed.

  <tool output>
  ```

- **Suggested fix:** Read the included tool output and correct the underlying
  Assembly or linker configuration problem.

## E5003 - User RAM exhausted

- **Category:** Code Generation
- **Explanation:** A global variable or procedure value-parameter slot cannot
  fit in the user RAM region. The diagnostic identifies the symbol, requested
  byte count, available byte count, and source declaration.
- **Trigger:** Declare enough one-byte variables and parameters to exceed the
  `$0310-$07FF` user region. The focused regression source is
  `tests/fixtures/diagnostics/user_ram_exhausted.nsp`, used with a deliberately
  constrained internal test layout.
- **Expected compiler output:**

  ```text
  E5003 program.nsp:5:5

  User RAM cannot allocate Second: requested 1 byte, but 0 bytes remain in User RAM.
  ```

- **Suggested fix:** Reduce the number of variables or parameters. Zero Page is
  intentionally unavailable until milestone 0.3.2.

## E5004 - Temporary RAM exhausted

- **Category:** Code Generation
- **Explanation:** Expression evaluation and cached for-loop limits require
  more bytes than the fixed 16-byte compiler temporary pool.
- **Trigger:** Compile
  `tests/fixtures/diagnostics/temporary_ram_exhausted.nsp`, whose nested
  expression needs 17 temporary bytes.
- **Expected compiler output:**

  ```text
  E5004 temporary_ram_exhausted.nsp:1:1

  Expression and loop code requires 17 temporary bytes, but the Expression temporaries region has only 16 bytes available.
  ```

- **Suggested fix:** Simplify nested expressions or loops. Do not rely on Zero
  Page temporaries before milestone 0.3.2.

## E5005 - Invalid memory layout

- **Category:** Code Generation
- **Explanation:** Internal compiler settings describe an impossible or
  unsupported RAM layout, such as overlapping reservations, a region beyond
  `$07FF`, or a non-page-aligned OAM shadow.
- **Trigger:** This is an internal-configuration diagnostic. Tests construct
  malformed `MemoryLayoutSettings`; no public CLI option changes these values.
- **Expected compiler output:**

  ```text
  E5005 <input>:1:1

  The OAM shadow region must start on a 256-byte page boundary.
  ```

- **Suggested fix:** Restore the supported milestone 0.3.1 NROM defaults.

## E5006 - RAM segment overflow

- **Category:** Code Generation
- **Explanation:** The bytes emitted for an Assembly segment exceed the region
  assigned to that segment. This is checked before ca65 or ld65 runs.
- **Trigger:** This indicates an internal compiler mismatch. Tests inject an
  oversized generated segment into an otherwise valid layout.
- **Expected compiler output:**

  ```text
  E5006 <input>:1:1

  Generated segment for User RAM requires 1265 bytes, but its RAM region contains 1264 bytes.
  ```

- **Suggested fix:** Correct the compiler's allocation or segment generation;
  changing user source should not be necessary for an internal mismatch.
