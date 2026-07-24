# AGENTS.md

## Project objective

This repository contains a prototype of a compiled, strongly typed, structured
language inspired by Pascal and specialized for Nintendo Entertainment System
game development.

The language compiles to ca65-compatible Assembly. ca65 and ld65 produce the
final ROM in iNES format.

The goal is not to implement complete Pascal or initially create a
general-purpose language.

## Philosophy

The language must:

- be easy to read;
- use strong typing;
- avoid implicit conversions;
- generate predictable code;
- expose relevant hardware costs;
- prevent dangerous constructs whenever possible;
- produce educational error messages;
- generate readable ca65 Assembly;
- let programmers understand the relationship between source and generated Assembly;
- prefer simplicity over completeness;
- every new feature should justify its existence;
- do not add abstractions, optimizations, or language constructs unless they are required by the current milestone;
- the generated Assembly should be easy to understand, even if a future optimization could make it smaller or faster;
- the language must not completely hide how the NES works.

English is the only language used in source code, diagnostics, documentation,
tests, generated output, and developer-facing artifacts. Do not add
localization infrastructure.

## Initial constraints

For the current prototype:

- use Python 3.11 or newer to implement the compiler;
- generate ca65-compatible Assembly;
- generate ROMs for NTSC NES;
- use only Ricoh 2A03/6502 instructions;
- do not use 65C02-only instructions;
- use mapper 0, NROM;
- use 32 KiB of PRG-ROM;
- use 8 KiB of CHR-ROM;
- do not implement dynamic memory;
- do not implement recursion;
- do not implement object orientation;
- do not implement runtime strings;
- do not implement advanced optimizations prematurely;
- do not generate intermediate C.


## Current milestone

The compiler must accept:

```pascal
program Minimal;

const
    DefaultBackgroundColor: nes_color = $21;
    MaximumFrameCounter: byte = $10;

var
    BackgroundColor: nes_color;
    FrameCounter: byte;
    NextFrameCounter: byte;
    RenderingEnabled: boolean;
    WithinLimit: boolean;

begin
    BackgroundColor := DefaultBackgroundColor;
    FrameCounter := $00;
    NextFrameCounter := FrameCounter + $01;
    RenderingEnabled := true;
    WithinLimit := RenderingEnabled and
        (NextFrameCounter <= MaximumFrameCounter);
    if WithinLimit then
        BackgroundColor := DefaultBackgroundColor
    else
        BackgroundColor := $0F;
    nes.set_background_color(BackgroundColor);
    nes.run;
end.
```

The built-in types `nes_color`, `byte`, and `boolean` each occupy one byte.
Variables require explicit declarations and assignments require exact type
matches. A direct hexadecimal literal remains valid as the argument to
`nes.set_background_color`. Arithmetic expressions support unary and binary
`+` and `-`, parentheses, and `byte` operands only. Arithmetic wraps modulo
256. Comparisons produce `boolean` values. Boolean expressions support `not`,
`and`, and `or`, with short-circuit evaluation for the binary operators.
Conditional statements support `if`, optional `else`, nested conditionals,
and compound `begin`/`end` branches.

The compiler must generate ca65 Assembly, assemble it, and link a valid `.nes`
ROM. When opened in an emulator, the NES must:

1. initialize correctly;
2. wait for a safe time to access the PPU;
3. set the universal background color;
4. enable rendering;
5. remain in a stable loop.

Do not implement loops, multiplication, division, user-defined procedures,
sprites, controller input, or audio yet.

## Expected pipeline

```text
examples/minimal.nsp
        |
        v
lexer
        |
        v
parser
        |
        v
AST
        |
        v
semantic analysis, name resolution, and type checking
        |
        v
resolved AST
        |
        v
ca65 backend
        |
        v
build/minimal.asm
        |
        v
ca65 and ld65
        |
        v
build/minimal.nes
```

## Compiler architecture

Keep components separate:

- `lexer.py`: converts characters to tokens;
- `parser.py`: converts tokens to an AST;
- `ast.py`: contains parsed and resolved AST nodes;
- `semantic.py`: validates declarations, resolves names, checks assignments,
  and enforces definite assignment;
- `backend_ca65.py`: converts the resolved AST to ca65 Assembly;
- `cli.py`: coordinates compilation, file generation, and external tools.

Do not translate source text directly to Assembly with string replacement.
Keep a small explicit AST even in the prototype.

## NES backend rules

- Generated code must use ca65 syntax.
- Produce the iNES header explicitly.
- Provide NMI, RESET, and IRQ vectors.
- RESET must disable interrupts, initialize the stack, and stabilize the PPU.
- Write to the PPU only at safe times.
- Use an empty 8 KiB CHR-ROM.
- Allocate current variables in regular CPU RAM, not zero page.
- Include generated Assembly comments identifying the source of each block.
- Do not introduce a generic game engine.
- Do not copy a large library to solve the minimal program.

## Type and syntax scope

The language is strongly typed, but implement types only when explicitly
requested.

Currently supported:

- `nes_color`: one byte, `$00..$3F`, intended for NES palette values;
- `byte`: one byte, `$00..$FF`;
- `boolean`: one byte, `false` or `true`;
- explicitly typed constants;
- explicitly typed variables in a `var` section;
- assignment with `:=`;
- constant and initialized-variable references;
- `byte` arithmetic using unary and binary `+` and `-`;
- equality and inequality for operands of exactly matching types;
- ordered comparisons for `byte`;
- boolean operators `not`, `and`, and `or`;
- `if` statements with optional `else`;
- nested conditionals and compound branches;
- parentheses in expressions.

Do not implement type inference, implicit conversions, user-defined types,
multiplication, division, or loops yet.

## Diagnostics

Whenever possible, every compiler error must include:

- file;
- line;
- column;
- error code;
- clear description;
- related source excerpt;
- correction suggestion when useful.

Example:

```text
E2101 examples/minimal.nsp:7:5

Unknown command: nes.background.

Perhaps you meant:
    nes.set_background_color(value);
```

Do not expose Python stack traces for ordinary source errors.

## Quality

Before completing a task:

1. run the tests;
2. compile the minimal example;
3. confirm a valid iNES header;
4. confirm the NROM image size;
5. add and run a practical gameplay-oriented test when the implemented
   features make one possible;
6. report the commands run;
7. describe known limitations;
8. never alter golden tests merely to hide a failure.

## Tests

Use:

- unit tests for lexer and parser;
- semantic-analysis and type-checking tests;
- assignment and variable-storage tests;
- golden tests for generated Assembly;
- an integration test invoking ca65 and ld65;
- header and ROM-size validation;
- invalid syntax and invalid semantic value tests.

Tests that require ca65 must be skipped with a clear message when the toolchain
is not installed.

Whenever practical, complement unit, golden, and structural ROM tests with a
small behavior-oriented example based on a realistic NES use case. If the
current language or runtime cannot express the scenario yet, document the
missing capabilities instead of claiming that the behavior was validated.

## Documentation

Documentation is a first-class deliverable and must always remain synchronized with the implementation.

Every completed feature or milestone must include documentation updates before the work is considered finished.

### General Rules

- Use English for all documentation.
- Use Markdown as the source format.
- Do not write HTML documentation manually.
- Keep documentation concise, accurate, and implementation-driven.
- Remove obsolete documentation whenever behavior changes.

### Documentation Updates

When implementing a new feature, always update every affected document.

This may include:

- README.md
- ROADMAP.md
- LANGUAGE.md
- compiler architecture documentation
- runtime documentation
- backend documentation
- examples
- API reference
- language reference

If a document does not exist yet and would improve the project, create it.

### Examples

Every user-visible language feature should include at least one working example.

Examples must compile successfully and remain synchronized with the compiler behavior.

### Roadmap

When a milestone is completed:

- mark it as completed in ROADMAP.md;
- add the next planned milestone if appropriate;
- keep the roadmap aligned with the current implementation.

### Consistency

Never leave documentation behind the implementation.

Code, tests, examples, and documentation must evolve together.

## Project Evolution

The compiler must evolve through small, incremental milestones.

Each milestone should:

- introduce a minimal set of new features;
- keep the compiler in a working state;
- include automated tests;
- update the documentation;
- avoid implementing features from future milestones.

Do not implement functionality that has not yet been planned.

Prefer a small, complete milestone over a large, incomplete implementation.

## Compiler Diagnostics

Compiler diagnostics are part of the public API.

Every diagnostic must have:

- a stable diagnostic code;
- a concise title;
- a detailed explanation;
- one or more code examples;
- suggested fixes.

Whenever a new diagnostic is introduced or an existing one changes, update the diagnostics reference.

Diagnostics documentation must remain synchronized with the compiler implementation.

Maintain a diagnostics index listing every diagnostic code and its meaning.

Diagnostics are educational.

Every error message should help the programmer understand:

- what happened;
- why it happened;
- how to fix it.

Prefer clear explanations over short messages.

Use the canonical diagnostic namespaces:

```text
E1000-E1999  Lexical Analysis
E2000-E2999  Parser / Syntax
E3000-E3999  Semantic Analysis
E4000-E4999  Type System
E5000-E5999  Code Generation
E6000-E6999  Runtime Validation
W1000-W1999  Warnings
I1000-I1999  Informational Messages
```

Never emit a diagnostic outside these ranges, assign one code to multiple
diagnostics, or reuse a retired code for a different meaning. Register new
errors in `nes_pascal/diagnostics.py` and document them in
`docs/DIAGNOSTICS.md`.

## Diagnostics Validation

Every new language feature must include negative test cases.

Whenever a new compiler diagnostic is introduced or modified:

- create at least one source file that intentionally triggers it;
- verify that the expected diagnostic is emitted;
- verify that unrelated diagnostics are not emitted;
- update the diagnostics documentation.

Diagnostics are part of the compiler's public interface and must remain stable.

## Example Programs

Every new language feature must include at least one example program.

Example programs are part of the project and must compile successfully.

When implementing a feature:

- create a new example if none exists;
- update existing examples when appropriate;
- keep examples small and focused;
- demonstrate the intended usage of the feature.

Examples should also serve as regression tests for future compiler changes.

## Implementation style

- Prefer simple, explicit code.
- Use Python type hints.
- Avoid dependencies when the standard library is sufficient.
- Do not use parser generators in the prototype.
- Use custom exceptions for compilation errors.
- Document important architectural decisions.
- Do not perform broad refactors outside the task scope.
- Do not implement future features without a request.

## Milestone Completion

A milestone is only considered complete when all of the following are satisfied:

- implementation is complete;
- automated tests pass;
- example programs compile successfully;
- documentation is updated;
- diagnostics are documented;
- ROADMAP.md reflects the current state.

## Regression Policy

Existing behavior must not regress.

When fixing a bug:

- add a regression test reproducing the original problem;
- verify that the bug no longer occurs;
- verify that previously working examples continue to compile.

Every reported bug should become a permanent automated test whenever practical.

## Work process

Before writing code:

1. read this file;
2. read relevant documents under `docs/`;
3. inspect the existing structure;
4. present a short plan;
5. implement only the requested milestone.

When choosing between a generic solution and a small predictable solution,
choose the small predictable solution.
