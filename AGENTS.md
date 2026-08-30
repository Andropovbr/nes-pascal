# AGENTS.md

## Purpose

This file is the canonical, provider-neutral policy for automated coding agents working on NES Pascal.

Keep long-lived project rules here. Put repeatable procedures in `.agents/skills/` and specialist behavior in `.agents/roles/`.
Provider-specific files under `.codex/` and `.gemini/` are adapters only and must not redefine project architecture.

When this file conflicts with explicit instructions from the user for the current task, follow the user's explicit instructions.

## Project

NES Pascal is a compiled, strongly typed, structured language inspired by Pascal and specialized for Nintendo Entertainment System development.

The goal is not full ISO Pascal compatibility or a general-purpose language. The project prioritizes:

- readable source;
- strict and predictable semantics;
- explicit NES hardware costs;
- deterministic compilation;
- understandable ca65 Assembly;
- useful diagnostics;
- incremental evolution;
- correctness on real NES constraints.

## Sources of truth

Use this order:

1. explicit user task;
2. current milestone and release roadmap;
3. canonical documentation;
4. project configuration/toolchain;
5. source code;
6. tests and golden outputs;
7. GitHub Actions for authoritative full-regression validation.

For milestone work, inspect `roadmap/README.md` and the relevant release roadmap. Do not infer current scope from old milestone numbering or this file.

## Priority order

When constraints conflict, prefer:

1. correct language semantics;
2. correct generated/runtime behavior;
3. NES hardware safety;
4. small, reviewable scope;
5. clear implementation;
6. deterministic code generation;
7. measured resource/performance efficiency;
8. extensibility required by current work only.

Do not add speculative architecture or future roadmap work.

## Cost-aware agent policy

Use the cheapest capable execution path.

Subagents consume their own model/tool budget. Do not delegate merely because delegation is available.

### Default workflow

For ordinary implementation:

1. inspect only files needed for the task;
2. identify existing contracts/tests before designing new behavior;
3. use `ze_da_oficina` for bounded, sufficiently specified implementation;
4. use deterministic skills for recurring validation/checklists;
5. use one focused `fiscal` review after meaningful changes;
6. escalate to a specialist only when an unresolved decision genuinely requires its domain expertise.

Avoid parallel write-heavy agents. Parallelism is mainly for independent read-only investigation or validation.

A lightweight worker that encounters an unresolved language, architecture, backend, or NES-runtime decision must report the decision and evidence rather than invent a broad redesign.

Do not ask multiple expensive specialists to independently answer the same question unless their domains are genuinely different.

### Specialist routing

Use `professor_carvalho` for unresolved public language-semantics decisions, such as:

- syntax meaning and edge cases;
- type compatibility and conversions;
- operator legality;
- name/scope behavior;
- procedure/function parameter semantics;
- constants, enums, arrays, records, sets, pointers or future type features;
- semantic diagnostics;
- compatibility questions where NES Pascal intentionally differs from Pascal traditions.

Do not invoke it for mechanical parser edits or semantics already established by docs/tests.

Use `seu_camilo` for compiler-architecture decisions, such as:

- boundaries between lexer/parser/AST/semantic/backend;
- ownership of information between compiler stages;
- cross-cutting compiler APIs;
- data representation spanning multiple stages;
- compiler/runtime architectural coupling;
- broad memory-layout architecture;
- refactors whose effect crosses multiple compiler subsystems.

Do not invoke it for localized implementation or style-only refactors.

Use `relampago_marquinhos` for backend/code-generation/performance decisions, such as:

- 6502 lowering strategy;
- expression and control-flow codegen;
- calling conventions and temporaries;
- branch-range handling;
- Zero Page/code-size/cycle trade-offs;
- generated Assembly that appears unexpectedly expensive;
- optimizations supported by measurement or generated-code evidence.

Do not invoke it for speculative optimization.

Use `mestre_ppu` for NES runtime/hardware decisions, such as:

- PPU/NMI/OAM/controller contracts;
- frame/VBlank behavior;
- scrolling and PPU state;
- ROM header/mapper/mirroring integration;
- linker/runtime memory regions;
- runtime builtins that directly manipulate NES hardware;
- emulator/runtime behavior that cannot be decided from compiler semantics alone.

Do not invoke it merely because generated code targets the NES.

Use `fiscal` for focused post-change review. Fiscal checks correctness, scope, regression risk, tests and missing validation; it does not redesign the system.

### Communication budget

All agents:

- lead with result/findings;
- cite files, symbols, commands and measurements that matter;
- do not restate the prompt or this file;
- do not narrate routine reads/searches;
- do not paste large diffs or full files;
- distinguish measured facts from estimates;
- state blockers and unverified claims explicitly.

Use the `caveman` skill when terse engineering handoff is useful.

## Repository awareness

Before editing:

- inspect working tree and active branch;
- preserve unrelated local changes;
- read the directly relevant implementation, tests and docs;
- inspect recent commits only when they materially help;
- follow existing conventions.

Do not assume a feature, mapper, runtime mechanism, dependency or file exists. Inspect first.

## Compiler architecture

Keep compiler stages explicit and separated:

- lexical analysis;
- parsing;
- AST representation;
- semantic/name/type analysis;
- memory/resource analysis;
- backend code generation;
- CLI/build orchestration.

Do not implement language features through ad-hoc source-text rewriting or bypass established stages.

A public feature should have an explicit representation in the compiler architecture where required. Share infrastructure when semantics are genuinely shared; do not create generic machinery solely for hypothetical future features.

Use `language-feature-check` for the standard impact checklist.

## Language semantics

NES Pascal is strongly typed.

Unless explicitly documented otherwise:

- avoid implicit conversions;
- reject ambiguous operations;
- preserve deterministic evaluation order;
- preserve strict, understandable compatibility rules;
- keep public diagnostics precise;
- do not invent syntax, coercions, operators or types outside current scope.

Language behavior is a public contract. Changing it requires tests and documentation appropriate to the change.

## Diagnostics

Diagnostics are part of the public interface.

They must be stable, specific, actionable and emitted by the appropriate phase.

Do not:

- reuse a diagnostic code for a new meaning;
- assign one code to unrelated failures;
- silently change a documented diagnostic;
- expose Python tracebacks for ordinary source errors.

When adding/changing diagnostics, use `diagnostic-check`.

## NES backend

Generated code must:

- be valid for the configured CPU/toolchain;
- be ca65-compatible;
- preserve language semantics;
- respect memory-layout/runtime invariants;
- remain deterministic where practical;
- remain understandable to humans;
- avoid runtime code/data for unused features when practical.

Do not assume mapper, ROM/CHR size, mirroring or memory policies from this file. Read the current roadmap/configuration/implementation.

## Code-generation invariants

Optimization or lowering changes must not break:

- evaluation order;
- short-circuit Boolean semantics;
- canonical stored Boolean representation when required;
- long-branch safety;
- calling/runtime contracts;
- type semantics;
- hardware invariants.

Unexpected generated-Assembly changes require investigation.

Use focused backend tests and golden Assembly where output shape is an intentional contract.
Never update a golden file merely because a test failed.

Use `golden-assembly-check` for the standard workflow.

## Memory and runtime

NES memory is constrained and hardware-visible.

When changing allocation/runtime state:

- identify the physical region that owns each allocation;
- preserve non-overlap guarantees;
- distinguish user storage, runtime state, compiler temporaries and hardware shadows;
- account for Zero Page and regular RAM when relevant;
- avoid unused runtime allocation where practical;
- verify compiler accounting and linker behavior agree.

Shared memory-layout changes have a broad regression surface.

## Performance discipline

Correctness before optimization.

For suspected code-generation inefficiency:

1. establish a representative source case;
2. inspect generated Assembly and/or measure;
3. identify the bottleneck;
4. make the smallest useful change;
5. compare under the same conditions;
6. record the result.

Never claim an optimization is faster/smaller without measurement or reliable generated-code evidence.

Use `compiler-benchmark` for standardized comparisons.

## Testing strategy

Use the smallest useful test layer:

- lexer/parser tests for syntax;
- semantic tests for language rules;
- backend tests for generated structure;
- golden tests for stable Assembly contracts;
- diagnostic fixtures for errors;
- ca65/ld65 integration for toolchain compatibility;
- ROM/header/layout checks for artifacts;
- Mesen tests for runtime behavior.

New behavior should normally include positive, negative and boundary coverage appropriate to its semantics.
Bug fixes should include a regression test when practical.

Use `compiler-test-check` to choose validation scope.

## Local validation

Canonical Makefile targets include:

- `make test`
- `make test-all`
- `make test-mesen`
- `make benchmark`
- `make rom`
- `make validate`

During implementation, iterate with focused tests first.

Run broader validation when changing high-impact shared infrastructure such as parser/AST/semantic infrastructure, builtin dispatch, backend infrastructure, memory layout, shared runtime/NMI behavior or build/link integration.

Do not repeatedly run the full suite after every small edit.

GitHub Actions remains the authoritative full-regression environment when accessible.
Never report CI success if CI was not actually checked.

## Runtime/emulator validation

Use Mesen when runtime behavior cannot be proven reliably from compiler output alone, especially for:

- NMI/frame synchronization;
- PPU state;
- controller behavior;
- sprites/OAM;
- scrolling;
- animation;
- timing-sensitive interactions.

Prefer deterministic automated emulator checks over manual-only inspection.

Use `nes-compiler-runtime-check`.

## Roadmap discipline

Implement only the current requested scope.

Do not:

- opportunistically implement future milestones;
- renumber completed historical milestones without approval;
- silently redefine future roadmap scope;
- expand a task into adjacent features;
- perform broad unrelated refactors.

When milestone work is involved, use `roadmap-milestone-check`.

## Documentation

English is canonical for source, identifiers, diagnostics, tests, generated output and primary technical documentation unless an existing canonical file establishes otherwise.

Update documentation when public behavior changes. Keep maintained translations synchronized when they are in scope.

Prefer updating an existing document over adding redundant documentation.

Do not put temporary implementation status in long-lived reference docs.

## Implementation style

Prefer:

- straightforward Python;
- type hints;
- small, focused functions;
- explicit data structures;
- deterministic output;
- standard library where sufficient;
- focused commits;
- minimal diffs.

Avoid:

- broad unrelated refactors;
- hidden global state;
- unnecessary metaprogramming;
- speculative abstractions;
- dependencies with weak value;
- generated code that is difficult to relate back to source semantics.

## Completion checklist

Before declaring meaningful implementation complete:

1. requested behavior is implemented;
2. focused relevant tests pass;
3. generated code/diagnostics are inspected when affected;
4. ROM/toolchain integration is validated when relevant;
5. runtime behavior is validated when relevant;
6. resource/benchmark impact is checked when relevant;
7. docs/roadmap are updated when required;
8. final diff remains in scope;
9. Fiscal performs one focused review when appropriate;
10. limitations and unverified checks are stated clearly.

Prefer evidence over ceremony.
