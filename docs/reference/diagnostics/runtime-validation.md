# Runtime-validation diagnostics

Runtime-validation diagnostics use the E6000-E6999 range.

## E6001 - File access failure

- **Category:** Runtime Validation
- **Explanation:** The compiler driver cannot read its source or write an
  output artifact at runtime.
- **Trigger:**

  ```text
  python -m nes_pascal.cli missing.nsp -o build/missing.nes
  ```

- **Expected compiler output:**

  ```text
  E6001: could not access a file: <operating-system error>
  ```

- **Suggested fix:** Check the path, file existence, and filesystem
  permissions.
