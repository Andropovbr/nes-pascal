# Prerequisites and installation

English | [Português (Brasil)](../pt-BR/getting-started/prerequisites-and-installation.md)

## Prerequisites

- Python 3.11 or newer;
- GNU Make, optional for the `Makefile` shortcuts;
- [cc65](https://cc65.github.io/), with `ca65` and `ld65` on `PATH`;
- an NES emulator such as Mesen to run the ROM.

The compiler has no runtime Python dependencies outside the standard library.
Installing the Python package does not install the cc65 toolchain: `ca65` and
`ld65` are external dependencies required for the final ROM build.

## Installing the package

Install NES Pascal from the repository:

```text
python -m pip install .
```

The installation provides the `nes-pascal` command:

```text
nes-pascal --version
nes-pascal examples/minimal.nsp -o build/minimal.nes
```

`python -m nes_pascal.cli` remains supported as an equivalent module
invocation:

```text
python -m nes_pascal.cli examples/minimal.nsp -o build/minimal.nes
```

For development, an editable installation links the installed package to the
working tree so source changes take effect immediately:

```text
python -m pip install -e .
```

## Running from the repository

Without installing, the compiler can run directly from the repository root:

```text
python -m nes_pascal.cli examples/minimal.nsp -o build/minimal.nes
```

## Building the final ROM

`ca65` and `ld65` must be available on `PATH` to assemble and link the
generated Assembly into a `.nes` ROM. When they are missing, the compiler
still writes the `.asm`, `.cfg`, and `.map` outputs and then reports the
`E5001` missing-toolchain diagnostic.

Continue with [Your first program](first-program.md).
