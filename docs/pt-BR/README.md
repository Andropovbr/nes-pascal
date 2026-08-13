# Tradução da Documentação do NES Pascal (Português do Brasil)

[English](../index.md) | Português (Brasil)

Esta pasta contém a tradução completa da documentação do **NES Pascal** para Português do Brasil (`pt-BR`).

## Diretrizes de Tradução

- **Fonte canônica:** A documentação em inglês (`docs/`) é a fonte oficial e autoritativa do projeto.
- **Espelhamento de estrutura:** A estrutura de diretórios e os nomes de arquivos em `docs/pt-BR/` espelham exatamente a documentação em inglês para permitir comparações automatizadas e navegação consistente.
- **Nomes de arquivos inalterados:** Caminhos e nomes de arquivos não são traduzidos.
- **Sincronização:** Todas as 53 páginas de documentação voltadas ao usuário estão 100% traduzidas e sincronizadas.

## Status da Tradução

### Documentação Principal
- [x] `docs/index.md` -> `docs/pt-BR/index.md`
- [x] `docs/DIAGNOSTICS.md` -> `docs/pt-BR/DIAGNOSTICS.md`
- [x] `docs/LANGUAGE.md` -> `docs/pt-BR/LANGUAGE.md`

### Getting Started (Primeiros Passos)
- [x] `docs/getting-started/index.md` -> `docs/pt-BR/getting-started/index.md`
- [x] `docs/getting-started/prerequisites-and-installation.md` -> `docs/pt-BR/getting-started/prerequisites-and-installation.md`
- [x] `docs/getting-started/first-program.md` -> `docs/pt-BR/getting-started/first-program.md`
- [x] `docs/getting-started/building-and-running.md` -> `docs/pt-BR/getting-started/building-and-running.md`
- [x] `docs/getting-started/testing.md` -> `docs/pt-BR/getting-started/testing.md`

### Language Guide (Guia da Linguagem)
- [x] `docs/language/index.md` -> `docs/pt-BR/language/index.md`
- [x] `docs/language/program-structure.md` -> `docs/pt-BR/language/program-structure.md`
- [x] `docs/language/identifiers-and-literals.md` -> `docs/pt-BR/language/identifiers-and-literals.md`
- [x] `docs/language/types.md` -> `docs/pt-BR/language/types.md`
- [x] `docs/language/constants-and-variables.md` -> `docs/pt-BR/language/constants-and-variables.md`
- [x] `docs/language/arrays.md` -> `docs/pt-BR/language/arrays.md`
- [x] `docs/language/enumerations.md` -> `docs/pt-BR/language/enumerations.md`
- [x] `docs/language/assignments.md` -> `docs/pt-BR/language/assignments.md`
- [x] `docs/language/expressions.md` -> `docs/pt-BR/language/expressions.md`
- [x] `docs/language/conditionals.md` -> `docs/pt-BR/language/conditionals.md`
- [x] `docs/language/loops.md` -> `docs/pt-BR/language/loops.md`
- [x] `docs/language/increment-and-decrement.md` -> `docs/pt-BR/language/increment-and-decrement.md`
- [x] `docs/language/procedures.md` -> `docs/pt-BR/language/procedures.md`

### NES Runtime (Runtime do NES)
- [x] `docs/runtime/index.md` -> `docs/pt-BR/runtime/index.md`
- [x] `docs/runtime/target-platform.md` -> `docs/pt-BR/runtime/target-platform.md`
- [x] `docs/runtime/frame-callbacks.md` -> `docs/pt-BR/runtime/frame-callbacks.md`
- [x] `docs/runtime/controller-input.md` -> `docs/pt-BR/runtime/controller-input.md`
- [x] `docs/runtime/sprites.md` -> `docs/pt-BR/runtime/sprites.md`
- [x] `docs/runtime/metasprites.md` -> `docs/pt-BR/runtime/metasprites.md`
- [x] `docs/runtime/sprite-animation.md` -> `docs/pt-BR/runtime/sprite-animation.md`
- [x] `docs/runtime/set-background-color.md` -> `docs/pt-BR/runtime/set-background-color.md`
- [x] `docs/runtime/palettes.md` -> `docs/pt-BR/runtime/palettes.md`
- [x] `docs/runtime/background-loading.md` -> `docs/pt-BR/runtime/background-loading.md`
- [x] `docs/runtime/background-updates.md` -> `docs/pt-BR/runtime/background-updates.md`
- [x] `docs/runtime/run.md` -> `docs/pt-BR/runtime/run.md`
- [x] `docs/runtime/scrolling-and-ppu-state.md` -> `docs/pt-BR/runtime/scrolling-and-ppu-state.md`
- [x] `docs/runtime/wait-frame.md` -> `docs/pt-BR/runtime/wait-frame.md`
- [x] `docs/runtime/vblank-cycle-budget.md` -> `docs/pt-BR/runtime/vblank-cycle-budget.md`
- [x] `docs/runtime/cpu-memory.md` -> `docs/pt-BR/runtime/cpu-memory.md`

### Reference (Referência)
- [x] `docs/reference/index.md` -> `docs/pt-BR/reference/index.md`
- [x] `docs/reference/compiler-pipeline.md` -> `docs/pt-BR/reference/compiler-pipeline.md`
- [x] `docs/reference/unsupported-features.md` -> `docs/pt-BR/reference/unsupported-features.md`
- [x] `docs/reference/diagnostics/index.md` -> `docs/pt-BR/reference/diagnostics/index.md`
- [x] `docs/reference/diagnostics/lexical.md` -> `docs/pt-BR/reference/diagnostics/lexical.md`
- [x] `docs/reference/diagnostics/syntax.md` -> `docs/pt-BR/reference/diagnostics/syntax.md`
- [x] `docs/reference/diagnostics/semantic.md` -> `docs/pt-BR/reference/diagnostics/semantic.md`
- [x] `docs/reference/diagnostics/type-system.md` -> `docs/pt-BR/reference/diagnostics/type-system.md`
- [x] `docs/reference/diagnostics/code-generation.md` -> `docs/pt-BR/reference/diagnostics/code-generation.md`
- [x] `docs/reference/diagnostics/runtime-validation.md` -> `docs/pt-BR/reference/diagnostics/runtime-validation.md`

### Compiler Internals (Internos do Compilador)
- [x] `docs/compiler/builtin-infrastructure.md` -> `docs/pt-BR/compiler/builtin-infrastructure.md`
- [x] `docs/compiler/low-risk-codegen-0.5.7.md` -> `docs/pt-BR/compiler/low-risk-codegen-0.5.7.md`
- [x] `docs/compiler/arrays-0.5.8.md` -> `docs/pt-BR/compiler/arrays-0.5.8.md`
- [x] `docs/compiler/enumerations-0.5.9.md` -> `docs/pt-BR/compiler/enumerations-0.5.9.md`
- [x] `docs/compiler/test-coverage-map.md` -> `docs/pt-BR/compiler/test-coverage-map.md`
- [x] `docs/compiler/optimization-audit-0.5.5.md` -> `docs/pt-BR/compiler/optimization-audit-0.5.5.md`
