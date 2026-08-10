# NES Pascal documentation

NES Pascal is a compiled, strongly typed language inspired by Pascal and
specialized for Nintendo Entertainment System games. It compiles source code
to ca65-compatible Assembly and produces an NROM-256 image for NTSC NES
systems.

This documentation describes only behavior implemented by the compiler.
Planned work is tracked separately in the
[project roadmap](https://github.com/Andropovbr/nes-pascal/blob/main/roadmap/README.md).

## Getting Started

- [Getting Started](getting-started/index.md)
- [Prerequisites and installation](getting-started/prerequisites-and-installation.md)
- [Your first program](getting-started/first-program.md)
- [Building and running programs](getting-started/building-and-running.md)
- [Testing the compiler](getting-started/testing.md)

## Language Guide

- [Language Guide](language/index.md)
- [Program structure](language/program-structure.md)
- [Identifiers and literals](language/identifiers-and-literals.md)
- [Built-in types](language/types.md)
- [Constants and variables](language/constants-and-variables.md)
- [Assignments](language/assignments.md)
- [Expressions](language/expressions.md)
- [Conditional statements](language/conditionals.md)
- [Loops](language/loops.md)
- [Increment and decrement](language/increment-and-decrement.md)
- [Procedures](language/procedures.md)

## NES Runtime

- [NES Runtime](runtime/index.md)
- [Target platform](runtime/target-platform.md)
- [Frame callbacks](runtime/frame-callbacks.md)
- [Controller input](runtime/controller-input.md)
- [Hardware sprites](runtime/sprites.md)
- [Metasprites](runtime/metasprites.md)
- [Sprite animation](runtime/sprite-animation.md)

## Reference

- [Reference](reference/index.md)
- [Compiler pipeline](reference/compiler-pipeline.md)
- [Optimization and architecture audit (0.5.5)](compiler/optimization-audit-0.5.5.md)
- [Unsupported features](reference/unsupported-features.md)
- [Compiler diagnostics](reference/diagnostics/index.md)
