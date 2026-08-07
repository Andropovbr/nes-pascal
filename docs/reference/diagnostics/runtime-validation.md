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

## E6005 - Invalid background asset configuration

- **Category:** Runtime Validation
- **Explanation:** Combined and split background options conflict, one half of
  a split configuration is missing, or background data was configured without
  a matching `nes.load_background()` call.
- **Trigger:** Use `--nametable` with either split option, specify only one
  split file, or configure data for a program without the command.
- **Expected compiler output:** `E6005` explains the conflicting or missing
  configuration element.
- **Suggested fix:** Use `--nametable` alone, or use both split options, and
  keep exactly one `nes.load_background();` call before `nes.run;`.

## E6006 - Background asset not found

- **Category:** Runtime Validation
- **Explanation:** A configured nametable, tile, or attribute path does not
  identify an existing file. Both the original and resolved paths are shown.
- **Trigger:** Configure a missing file through any nametable option.
- **Expected compiler output:** `E6006` includes the user-provided path and
  source-relative resolved path.
- **Suggested fix:** Correct the path or add the missing file.

## E6007 - Background asset read failure

- **Category:** Runtime Validation
- **Explanation:** The path resolved, but the operating system could not read
  the configured background file.
- **Trigger:** Configure an unreadable file or a directory.
- **Expected compiler output:** `E6007` includes the path and operating-system
  error.
- **Suggested fix:** Select a readable regular file and check permissions.

## E6008 - Invalid background asset size

- **Category:** Runtime Validation
- **Explanation:** Raw background data has a fixed hardware-native size.
- **Trigger:** Provide a combined nametable other than 1024 bytes, tile data
  other than 960 bytes, or attribute data other than 64 bytes.
- **Expected compiler output:** `E6008` includes expected and actual sizes.
- **Suggested fix:** Export exactly 1024 combined bytes or exactly 960+64
  separate bytes without headers or metadata.

## E6009 - Background asset required

- **Category:** Runtime Validation
- **Explanation:** The source calls `nes.load_background()`, but no background
  bytes were configured.
- **Trigger:** Compile such a program without any nametable options.
- **Expected compiler output:** `E6009` identifies the missing configuration.
- **Suggested fix:** Pass `--nametable`, or pass both
  `--nametable-tiles` and `--nametable-attributes`.

## E6010 - Invalid mirroring configuration

- **Category:** Runtime Validation
- **Explanation:** NROM currently supports only static horizontal or vertical
  nametable mirroring.
- **Trigger:** Pass any other value to `--mirroring`.
- **Expected compiler output:** `E6010` followed by the configured value.
- **Suggested fix:** Use `--mirroring horizontal` or `--mirroring vertical`.
