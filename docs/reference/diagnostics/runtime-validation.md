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

## E6002 - CHR-ROM asset not found

- **Category:** Runtime Validation
- **Explanation:** A path explicitly configured with `--chr` does not identify
  an existing file. The diagnostic shows both the original and resolved paths.
- **Trigger:** Compile with `--chr assets/missing.chr` when that file does not
  exist relative to the source file directory.
- **Expected compiler output:** `E6002` followed by the configured path and its
  resolved absolute path.
- **Suggested fix:** Correct the path or add the file. Omitting `--chr` is the
  explicit way to request generated empty CHR-ROM.

## E6003 - CHR-ROM asset read failure

- **Category:** Runtime Validation
- **Explanation:** The configured CHR-ROM path exists or was resolved, but the
  operating system did not allow the compiler to read its bytes.
- **Trigger:** Configure an unreadable file or a directory as `--chr`.
- **Expected compiler output:** `E6003` followed by the original path, resolved
  path, and operating-system error.
- **Suggested fix:** Select a readable regular file and check its permissions.

## E6004 - Invalid CHR-ROM size

- **Category:** Runtime Validation
- **Explanation:** Mapper 0 NROM currently accepts exactly one 8192-byte
  (8 KiB) CHR-ROM bank.
- **Trigger:** Configure an empty file or any file smaller or larger than 8192
  bytes.
- **Expected compiler output:** `E6004` followed by the expected 8192 bytes and
  the actual byte count.
- **Suggested fix:** Provide a raw `.chr` file containing exactly 8192 bytes.
