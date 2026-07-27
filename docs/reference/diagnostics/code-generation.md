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
