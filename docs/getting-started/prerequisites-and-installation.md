# Prerequisites and installation

## Prerequisites

- Python 3.11 or newer;
- GNU Make, optional for the `Makefile` shortcuts;
- [cc65](https://cc65.github.io/), with `ca65` and `ld65` on `PATH`;
- an NES emulator such as Mesen to run the ROM.

The compiler has no runtime Python dependencies outside the standard library.

## Running from the repository

The compiler can run directly from the repository root. An editable
installation is optional:

```text
python -m pip install -e .
```

Continue with [Your first program](first-program.md).
