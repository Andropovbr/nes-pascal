# AGENTS.md

## Purpose

This file defines stable working rules for automated coding agents contributing to this repository.

It must contain long-lived engineering principles and workflow rules only.

Do not use this file to record:

* the current milestone;
* the current release;
* the next planned feature;
* temporary implementation status;
* historical project state;
* lists of currently supported language features;
* version-specific feature inventories.

Those belong in the roadmap, documentation, project configuration, source code, and tests.

When this file conflicts with explicit instructions from the user for the current task, follow the user's explicit instructions.

---

## Project Objective

NES Pascal is a compiled, strongly typed, structured language inspired by Pascal and specialized for Nintendo Entertainment System development.

The project prioritizes:

* readable source code;
* strong and predictable semantics;
* explicit hardware costs;
* deterministic code generation;
* understandable generated Assembly;
* useful compiler diagnostics;
* incremental evolution;
* close correspondence between language behavior and NES hardware behavior.

The goal is not to reproduce complete ISO Pascal or to become a general-purpose programming language.

---

## Sources of Truth

Do not infer current project state from this file.

Before making changes, inspect the relevant authoritative sources.

Use the following hierarchy:

1. the user's explicit task;
2. the roadmap for milestone scope and planned work;
3. canonical documentation for public behavior;
4. project configuration for supported tools and environments;
5. source code for implementation details;
6. automated tests for established behavior and regression coverage;
7. GitHub Actions for authoritative full-regression validation.

For milestone work:

1. read `roadmap/README.md`;
2. identify the explicit current milestone;
3. open the relevant release roadmap;
4. implement only the requested scope.

Never determine the current milestone by historical numbering, assumptions, or content from this file.

---

## Engineering Philosophy

Prefer simple, explicit, predictable solutions.

The project should:

* favor readability over cleverness;
* prefer small specialized abstractions over generic frameworks;
* avoid premature optimization;
* avoid unnecessary dependencies;
* expose relevant NES hardware constraints rather than hiding them completely;
* generate Assembly that remains understandable to a human reader;
* preserve deterministic behavior whenever practical;
* evolve through small, complete increments;
* keep language semantics strict and unsurprising.

Every new abstraction, optimization, language construct, runtime mechanism, or dependency must justify its existence.

Do not introduce architecture intended only for hypothetical future features.

Do not implement future roadmap work opportunistically.

---

## Scope Discipline

Implement only what is required by the current task and its explicitly defined acceptance criteria.

Do not:

* expand the task into adjacent roadmap items;
* perform broad refactors without a concrete need;
* redesign working subsystems merely for stylistic reasons;
* introduce speculative extensibility;
* silently change public language behavior;
* silently change future roadmap scope;
* remove planned roadmap work without explicit approval.

If the requested work exposes missing architectural or roadmap work, report it separately.

Prefer:

> small, complete, tested change

over:

> broad, partially implemented redesign.

---

## Repository Awareness

Before editing code:

1. inspect the working tree;
2. identify the active branch;
3. inspect relevant recent commits when useful;
4. read the files directly related to the task;
5. read relevant tests;
6. read relevant documentation;
7. understand existing conventions before introducing new ones.

Do not assume a file, subsystem, command, dependency, mapper, runtime model, memory policy, or language feature exists merely because it would be conventional.

Inspect first.

Do not overwrite or discard unrelated local changes.

Do not clean the working tree by deleting files unless you have established that they are generated or disposable.

---

## Language and Compiler Architecture

Keep compiler stages clearly separated.

Typical responsibilities include:

* lexical analysis;
* parsing;
* AST representation;
* semantic analysis and name resolution;
* type checking;
* memory/resource analysis;
* backend code generation;
* command-line/build orchestration.

Do not bypass established compiler stages with ad-hoc source-text transformation.

Do not translate source code directly into Assembly through string replacement or similar shortcuts.

Public language behavior should have an explicit representation in the compiler architecture.

When introducing a new language feature, determine which compiler stages genuinely need to understand it and avoid duplicating feature-specific logic unnecessarily across the pipeline.

Prefer shared infrastructure when multiple features have the same semantics, but do not create generic machinery solely in anticipation of future use.

---

## Type-System Principles

NES Pascal is strongly typed.

Unless explicitly defined otherwise by the language specification or roadmap:

* avoid implicit conversions;
* require predictable type compatibility;
* reject ambiguous operations;
* preserve deterministic evaluation semantics;
* keep compiler diagnostics precise when types are incompatible.

Do not invent new types, conversions, operators, or coercion rules outside the requested scope.

The canonical language documentation defines currently supported types and syntax.

---

## NES Backend Principles

Generated code must respect the actual target hardware.

Backend work should:

* generate valid ca65-compatible Assembly;
* use only instructions valid for the configured CPU target;
* respect PPU timing and synchronization requirements;
* preserve interrupt and runtime invariants;
* respect the compiler's memory-layout model;
* keep generated code deterministic whenever practical;
* avoid hidden runtime costs when they can reasonably be exposed;
* keep generated Assembly readable;
* identify compiler/runtime-generated behavior clearly when useful;
* avoid unnecessary runtime code and data when a feature is unused.

Do not assume a specific mapper, ROM size, CHR strategy, memory allocation policy, mirroring mode, or other evolving target constraint from this file.

Read the roadmap, documentation, configuration, and implementation that define the target currently being worked on.

Do not introduce a generic game engine as part of compiler work unless explicitly requested.

---

## Memory and Runtime Discipline

NES memory is limited and hardware-visible.

When changing memory allocation or runtime state:

* understand which physical memory region owns each allocation;
* preserve non-overlap guarantees;
* preserve deterministic allocation when expected;
* distinguish runtime, compiler temporary, hardware shadow, and user storage;
* account for both zero-page and regular RAM costs where relevant;
* avoid allocating state for unused features when practical;
* verify that linker configuration and compiler memory accounting agree.

Changes affecting shared memory layout have a broad regression surface and require stronger validation.

---

## Code Generation Quality and Benchmark Policy

Backend and code-generation improvements must preserve both semantic correctness and established code-quality invariants.

When modifying backend lowering or introducing optimizations:

* accompany code-generation changes with focused backend tests and golden Assembly assertions;
* investigate any unexpected changes in generated Assembly output before accepting them;
* run relevant benchmark measurements whenever lowering or expression evaluation rules change;
* monitor for unexpected regressions across:
  * PRG-ROM size;
  * instruction count;
  * estimated static cycles;
  * RAM usage;
  * Zero Page usage;
  * expression temporary pressure;
* ensure any measurable regression in size, memory, or cycles is intentional, necessary, and documented;
* optimization must never break:
  * language semantics;
  * expression and argument evaluation order;
  * short-circuit evaluation for boolean operators;
  * canonical Boolean materialization (`$00`/`$01`) when a boolean value is stored, passed, returned, or required as data;
  * long-branch safety and boundary handling;
  * runtime correctness and hardware invariants;
* prefer small, local, directly provable code-generation transformations unless the roadmap explicitly introduces a broader optimization architecture.

### Benchmark Corpus Policy

The benchmark corpus serves as a stable historical baseline for evaluating code generation and resource usage.

* Once a benchmark program is established as a baseline, avoid repurposing or modifying its source code.
* Prefer adding new representative benchmark programs to measure new language capabilities rather than rewriting existing ones.
* Preserve historical comparability across releases whenever practical.


---

## Diagnostics

Compiler diagnostics are part of the public interface.

Diagnostics must be:

* stable;
* specific;
* actionable;
* associated with the correct compiler phase;
* useful to a programmer learning what went wrong.

Whenever practical, diagnostics should include:

* file;
* line;
* column;
* diagnostic code;
* concise description;
* relevant source context;
* corrective guidance when useful.

Ordinary source errors must not expose Python stack traces.

Maintain the canonical diagnostic namespaces defined by the project.

Do not:

* reuse an existing diagnostic code for a different meaning;
* assign one code to multiple unrelated diagnostics;
* silently change a documented diagnostic contract;
* emit diagnostics outside the project's defined ranges.

When introducing or changing a diagnostic:

1. register it in the canonical diagnostic catalog;
2. add a focused negative fixture;
3. verify the expected diagnostic is emitted;
4. verify unrelated diagnostics are not emitted;
5. update the diagnostic documentation.

---

## Test Strategy

Automated tests are required for project behavior.

Use the smallest appropriate layer for each assertion:

* lexer/parser tests for syntax;
* semantic tests for language rules;
* backend tests for generated code structure;
* golden tests for stable generated Assembly;
* diagnostic fixtures for error behavior;
* toolchain integration tests for ca65/ld65 compatibility;
* ROM/header/layout checks for generated artifacts;
* emulator tests for behavior that must be verified at runtime.

Tests should verify behavior, not implementation accidents, unless the implementation property itself is an intentional contract.

Every new capability should include appropriate:

* positive tests;
* negative tests;
* edge cases;
* integration coverage when relevant.

Every bug fix should include a regression test reproducing the original problem whenever practical.

A bug should not be considered permanently fixed if nothing prevents the same regression from returning.

---

## Local Test Execution Policy

GitHub Actions is the authoritative full-regression environment.

The repository provides canonical `Makefile` targets (`make test`, `make test-all`, `make test-mesen`, `make benchmark`, `make rom`, `make clean`, `make validate`) wrapping the standard entry points.

During normal implementation work:

1. run focused tests for the subsystem being changed;
2. run representative build or compilation smoke tests (`make rom`);
3. run relevant runtime/emulator tests when practical (`make test-mesen`);
4. run local pre-push validation (`make validate`) before completing broad changes;
5. iterate using the smallest test set that gives useful feedback.

Do not repeatedly run the entire regression suite locally after every small edit.

Run broader or full local regression when modifying high-impact shared infrastructure such as:

* parser infrastructure;
* AST representation;
* semantic-analysis infrastructure;
* builtin registration or dispatch;
* backend code-generation infrastructure;
* memory layout or allocation;
* shared interrupt/NMI behavior;
* shared runtime infrastructure;
* build/link infrastructure.

A focused test failure may also justify expanding the local test scope.

---

## CI Policy

The GitHub Actions pipeline is the authoritative full-regression check.

The final commit of completed work should pass the repository's CI gate.

Required CI dependencies must be explicitly installed and validated.

A missing required dependency must not produce a false green result.

In particular:

* required toolchain components must be present;
* required emulator/runtime dependencies must be present;
* runtime tests must actually execute in their authoritative CI job;
* infrastructure failures must fail the appropriate job.

Never hide failures using mechanisms such as:

* `continue-on-error`;
* `|| true` around required validation;
* shell pipelines that discard the real exit status;
* unconditional success commands;
* dependency-related skips presented as successful runtime validation.

When piping required test output through tools such as `tee`, preserve the test process exit status.

Diagnostic artifact upload may run after a failure, but artifact handling must never convert a failed validation into success.

The aggregate CI gate must fail whenever any required upstream validation does not succeed.

A task is not fully validated until the final commit passes the authoritative CI gate when remote CI validation is available.

If CI cannot be accessed, report that clearly instead of claiming full validation.

---

## Local Dependency Skips

Some integration tests may support graceful local skipping when optional external tools are not installed.

That behavior is useful for local development and must not be confused with authoritative CI validation.

Local execution may report a clear skip when an optional local dependency is unavailable.

Authoritative CI jobs must install and validate the dependencies required by those jobs and must not rely on skips as proof of success.

---

## Golden Tests

Golden Assembly is an intentional regression contract.

Never update a golden file merely because a test failed.

When generated Assembly changes:

1. determine why it changed;
2. verify that the change is required and correct;
3. inspect the semantic and runtime consequences;
4. update the golden file only when the new output represents the intended behavior;
5. document meaningful behavioral or architectural changes when appropriate.

An unexpected golden diff is evidence to investigate, not something to normalize automatically.

---

## Runtime and Emulator Tests

Use emulator-based tests when behavior cannot be proven reliably from generated Assembly alone.

Runtime tests are especially valuable for:

* frame synchronization;
* NMI behavior;
* PPU state;
* controller state;
* sprite/OAM behavior;
* animation;
* timing-sensitive runtime state;
* interactions among multiple compiler/runtime features.

Prefer deterministic tests that:

* execute a generated ROM;
* inspect known runtime state;
* terminate explicitly with success or failure;
* have bounded execution time.

Do not replace automated runtime validation with manual emulator inspection when an automated assertion is practical.

Manual testing may complement automated tests but does not replace them.

---

## Documentation

Documentation is a first-class deliverable.

Canonical English documentation must remain synchronized with implementation.

When changing user-visible behavior:

1. identify affected canonical documentation;
2. update it in the same task whenever practical;
3. update examples and references that would otherwise become stale;
4. remove obsolete statements instead of accumulating contradictory history.

Prefer updating an existing document over creating a new document unnecessarily.

Do not put temporary implementation status in long-lived reference documentation.

### Documentation Languages

English is canonical for:

* source code;
* identifiers;
* compiler diagnostics;
* tests;
* generated output;
* internal developer-facing artifacts;
* primary documentation.

Translated documentation may exist in locale-specific directories such as `docs/pt-BR/`.

Canonical English documentation remains the source of truth.

When a maintained translated version exists for canonical documentation changed by the task, keep the translation synchronized when documentation updates are within task scope.

Do not localize:

* language syntax;
* compiler diagnostic identifiers;
* generated Assembly symbols;
* internal source identifiers;

unless explicitly planned.

---

## Examples

User-visible language features should have representative example programs whenever appropriate.

Examples must:

* compile successfully;
* remain synchronized with current language behavior;
* stay focused;
* demonstrate intended usage;
* avoid unrelated complexity.

Examples should also serve as useful regression inputs when practical.

Do not keep obsolete examples merely as historical artifacts inside the active documentation or test path.

Historical material belongs in version control history unless there is an explicit reason to preserve it in the repository.

---

## Roadmap Discipline

The roadmap defines project evolution.

Before milestone work:

1. read the roadmap index;
2. identify the explicitly designated current milestone;
3. open the relevant release roadmap;
4. understand its acceptance criteria;
5. implement only that scope.

When a milestone is completed:

* update its status and checklist;
* update the roadmap index;
* identify the next milestone using the roadmap;
* keep roadmap state aligned with implementation.

Do not infer the next milestone from numbering alone.

Do not renumber or rewrite completed historical milestones without explicit approval.

Do not silently expand, remove, or redefine future roadmap scope.

If implementation exposes missing future work, propose it separately.

---

## Regression Policy

Existing documented behavior must not regress unintentionally.

When changing shared infrastructure, consider downstream effects across:

* parsing;
* semantic analysis;
* generated Assembly;
* memory usage;
* ROM construction;
* runtime behavior;
* diagnostics;
* examples;
* documentation.

Passing focused tests is necessary during development.

Passing authoritative CI is required for final regression confidence.

Passing the existing suite is necessary but not sufficient for a new feature: new behavior must have tests that actually exercise it.

---

## Implementation Style

Prefer:

* straightforward Python;
* type hints;
* small functions with clear responsibilities;
* explicit data structures;
* deterministic output;
* standard-library solutions when sufficient;
* focused commits;
* minimal diffs.

Avoid:

* broad unrelated refactors;
* hidden global state;
* unnecessary metaprogramming;
* speculative abstractions;
* parser generators unless explicitly adopted by the project;
* dependencies that provide little value;
* generated code that is difficult to relate back to source behavior.

Follow existing project conventions before introducing new ones.

---

## Generated and Temporary Files

Do not commit generated or temporary artifacts unless they are intentionally versioned fixtures, assets, golden outputs, or examples.

Before deleting or ignoring a file type, verify whether the repository intentionally versions files of that type.

NES development commonly uses file extensions that may represent either generated output or canonical project assets.

Do not globally ignore or delete formats such as Assembly, linker configuration, ROM, CHR, palette, map, or metadata files without inspecting their role in the repository.

Keep temporary build artifacts out of commits.

---

## Git Workflow

Before starting:

* inspect `git status`;
* identify the current branch;
* avoid modifying unrelated work.

During implementation:

* keep changes focused;
* use meaningful commits;
* do not mix unrelated cleanup with feature work;
* preserve useful history when debugging CI or regressions.

Before completion:

1. review the full diff;
2. ensure no accidental files were added;
3. run appropriate focused local validation;
4. commit the intended changes;
5. push the branch when requested or required by the workflow;
6. confirm CI was triggered when remote access is available;
7. verify the final CI result.

Never claim a remote validation succeeded without checking it.

---

## Work Process

For a normal task:

1. read this file;
2. understand the user's request;
3. inspect repository status and structure;
4. read relevant roadmap entries when scope depends on them;
5. read relevant documentation;
6. inspect relevant implementation and tests;
7. form a short implementation plan;
8. make the smallest correct change;
9. run focused tests while iterating;
10. expand testing when the change has broader impact;
11. update tests, examples, diagnostics, and documentation as required;
12. review the final diff;
13. commit and push when appropriate;
14. verify authoritative CI when available;
15. report the result accurately.

Do not spend time rediscovering unrelated parts of the repository.

---

## Completion Criteria

A task is complete only when all requirements relevant to that task have been addressed.

For feature or milestone work, this normally includes:

* implementation;
* appropriate automated tests;
* regression coverage;
* examples when applicable;
* diagnostics when applicable;
* documentation;
* roadmap updates when applicable;
* focused local validation;
* successful authoritative CI validation when available.

Before reporting completion, provide:

* a concise summary of what changed;
* files or subsystems changed;
* local tests executed;
* CI status;
* known limitations or unresolved issues;
* any proposed follow-up work that was intentionally kept out of scope.

Do not present planned, skipped, unverified, or partially implemented work as complete.

---

## Maintaining This File

`AGENTS.md` should remain stable and policy-oriented.

Do not add:

* current milestone descriptions;
* feature inventories;
* release status;
* temporary workarounds;
* implementation snapshots;
* benchmark results;
* historical notes;
* task-specific instructions.

If information changes frequently, it belongs somewhere else.

Use:

* the roadmap for planning and milestone state;
* documentation for public behavior;
* project configuration for supported environments and dependencies;
* tests for executable behavior contracts;
* source code for implementation details;
* version control history for historical state.

The purpose of this file is to help an agent reliably understand **how to work on the project**, not to describe **where the project happens to be today**.
