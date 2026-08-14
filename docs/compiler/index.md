# Compiler Implementation and Audit History

English | [Português (Brasil)](../pt-BR/compiler/index.md)

This page indexes the point-in-time reports written as the compiler and its
runtime were implemented. It collects milestone-scoped implementation reports,
architecture and optimization audits, and independent milestone audits in one
place so the regular [Reference](../reference/index.md) navigation can stay
focused on durable, user-facing material.

These documents are historical. Each one records the compiler as it was when
the corresponding milestone completed, including its measurements and its
limitations. Statements that later milestones made stale are preserved as
written, with explicit historical notes added where relevant.

## Document types

- **Implementation report** — the implementer's milestone snapshot describing
  what was built, how it was lowered, and what it measured.
- **Architecture / optimization audit** — a baseline analysis of the
  compiler's architecture, generated code, and resource usage.
- **Independent milestone audit** — a point-in-time quality review of a
  completed milestone performed by an independent reviewer.

## Release 0.5

### 0.5.5 — Compiler architecture and code generation audit

- [Milestone 0.5.5: Compiler architecture and code generation audit](optimization-audit-0.5.5.md) — architecture / optimization audit and benchmark baseline.

### 0.5.6 — Builtin infrastructure

- [Builtin / intrinsic infrastructure](builtin-infrastructure.md) — implementation report.

### 0.5.7 — Low-risk code generation improvements

- [Low-risk code generation improvements](low-risk-codegen-0.5.7.md) — implementation report.

### 0.5.8 — Arrays

- [Array implementation and measurements](arrays-0.5.8.md) — implementation report.

### 0.5.9 — Enumerations

- [Enumeration implementation and measurements](enumerations-0.5.9.md) — implementation report.

### 0.5.10 — Records

- [Record implementation and measurements](records-0.5.10.md) — implementation report.
- [Milestone 0.5.10 — Records: completeness and quality audit](milestone-0.5.10-audit.md) — independent milestone audit.

### 0.5.11 — Expression temporary allocation

- [Expression temporary allocation](expression-temporaries-0.5.11.md) — implementation report.
- [Milestone 0.5.11 — Expression temporary allocation: completeness and quality audit](milestone-0.5.11-audit.md) — independent milestone audit.

### 0.5.12 — Functions

- [Functions implementation and ABI](functions-0.5.12.md) — implementation report.
- [Milestone 0.5.12 — Functions: completeness and quality audit](milestone-0.5.12-audit.md) — independent milestone audit.

## Cross-cutting audits

- [Diagnostic catalog and error-message consistency audit](diagnostic-consistency-audit.md) — cross-cutting QA audit of the diagnostic catalog, coverage, message quality, precedence, and EN/PT-BR parity.

For durable, non-milestone compiler material, see the
[Semantic test coverage map](test-coverage-map.md) and the
[Reference](../reference/index.md) section.
