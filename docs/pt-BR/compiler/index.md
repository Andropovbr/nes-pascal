# Histórico de Implementação e Auditorias do Compilador

[English](../../compiler/index.md) | Português (Brasil)

Esta página indexa os relatórios pontuais escritos durante a implementação do
compilador e de seu runtime. Ela reúne em um só lugar os relatórios de
implementação por marco, as auditorias de arquitetura e otimização e as
auditorias independentes de marcos, para que a navegação normal da
[Referência](../reference/index.md) permaneça focada em material durável e
voltado ao usuário.

Estes documentos são históricos. Cada um registra o compilador como ele estava
quando o marco correspondente foi concluído, incluindo suas medições e suas
limitações. Afirmações que marcos posteriores tornaram obsoletas são
preservadas como escritas, com notas históricas explícitas adicionadas quando
relevante.

## Tipos de documento

- **Relatório de implementação** — o instantâneo do implementador no marco,
  descrevendo o que foi construído, como foi reduzido e o que foi medido.
- **Auditoria de arquitetura / otimização** — uma análise de linha de base da
  arquitetura, do código gerado e do uso de recursos do compilador.
- **Auditoria independente de marco** — uma revisão de qualidade pontual de um
  marco concluído, realizada por um revisor independente.

## Release 0.5

### 0.5.5 — Auditoria de arquitetura e geração de código do compilador

- [Marco 0.5.5: Auditoria de arquitetura e geração de código do compilador](optimization-audit-0.5.5.md) — auditoria de arquitetura / otimização e linha de base de benchmarks.

### 0.5.6 — Infraestrutura de builtins

- [Infraestrutura de builtins / intrínsecos](builtin-infrastructure.md) — relatório de implementação.

### 0.5.7 — Melhorias de baixo risco na geração de código

- [Melhorias de baixo risco na geração de código](low-risk-codegen-0.5.7.md) — relatório de implementação.

### 0.5.8 — Arrays

- [Implementação e medições de arrays](arrays-0.5.8.md) — relatório de implementação.

### 0.5.9 — Enumerações

- [Implementação e medições de enumerações](enumerations-0.5.9.md) — relatório de implementação.

### 0.5.10 — Records

- [Implementação e medições de records](records-0.5.10.md) — relatório de implementação.

### 0.5.11 — Alocação de temporários de expressão

- [Alocação de temporários de expressão](expression-temporaries-0.5.11.md) — relatório de implementação.

Para material durável do compilador que não é específico de um marco, consulte
o [Mapa de cobertura de testes semânticos](test-coverage-map.md) e a seção
[Referência](../reference/index.md).
