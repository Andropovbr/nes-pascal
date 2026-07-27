# NES Pascal

NES Pascal is a prototype of a compiled, strongly typed language inspired by
Pascal and specialized for Nintendo Entertainment System games. It compiles
the implemented language subset to readable ca65 Assembly and produces an
NTSC NROM-256 ROM.

The compiler currently supports explicitly typed constants and global
variables, exact-type assignments, one-byte arithmetic, comparisons,
short-circuit Boolean expressions, structured conditionals and loops,
increment and decrement operations, and parameterless acyclic procedures. Its
runtime sets the universal background color, enables rendering, and enters a
stable loop.

## Documentation

The documentation is organized for direct browsing on GitHub and future use
with a static documentation generator:

- [Documentation home](docs/index.md)
- [Getting Started](docs/getting-started/index.md)
- [Language Guide](docs/language/index.md)
- [NES Runtime](docs/runtime/index.md)
- [Reference](docs/reference/index.md)
- [Compiler diagnostics](docs/reference/diagnostics/index.md)
- [Project roadmap](roadmap/README.md)

The documentation describes implemented behavior. The roadmap tracks planned
work and must not be read as a list of currently supported features.

## Quick start

Requirements and installation instructions are in
[Prerequisites and installation](docs/getting-started/prerequisites-and-installation.md).

Compile the minimal example from the repository root:

```text
python -m nes_pascal.cli examples/minimal.nsp -o build/minimal.nes
```

The command generates `build/minimal.asm`, `build/minimal.o`, and
`build/minimal.nes`. The complete walkthrough is in
[Your first program](docs/getting-started/first-program.md); commands for every
example and Mesen instructions are in
[Building and running programs](docs/getting-started/building-and-running.md).

## Tests

Run the complete suite with:

```text
python -m unittest discover -s tests -v
```

Toolchain-dependent tests are skipped with a clear message when ca65, ld65,
or the optional Mesen executable is unavailable. See
[Testing the compiler](docs/getting-started/testing.md) for all supported test
commands.

## Architecture and limits

The [compiler pipeline](docs/reference/compiler-pipeline.md) documents the
lexer, parser, AST, semantic analysis, ca65 backend, assembler, and linker
stages. The [target-platform reference](docs/runtime/target-platform.md)
documents the generated ROM and NES startup behavior.

See [Unsupported features](docs/reference/unsupported-features.md) for the
explicit language, runtime, and platform limitations.
