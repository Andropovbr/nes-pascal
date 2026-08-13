# Implementação e Medições de Enumerações (0.5.9)

[English](../../compiler/enumerations-0.5.9.md) | Português (Brasil)

A milestone 0.5.9 adiciona tipos de enumeração nominais definidos pelo usuário,
com tamanho de byte. `EnumType` preserva a identidade do tipo, os nomes ordenados
dos membros e seus valores determinísticos durante a análise semântica. Membros
se tornam imediatos tipados de compilação; não existe subsistema de enum em runtime.

## Lowering e armazenamento

- A única sintaxe é `type Name = (Member, ...);`; membros não são qualificados.
- O primeiro membro é `$00`, seguido por valores sequenciais até `$FF`.
- Variáveis usam um byte escalar comum e podem seguir a política existente de
  promoção. Membros, declarações de tipo, descritores e tabelas não consomem
  RAM, ROM ou Zero Page.
- A identidade nominal permanece até o lowering ca65. Atribuições ou comparações
  de igualdade entre enumerações diferentes, ou enumeração e escalar, são rejeitadas.
- Igualdade e desigualdade usam a geração direta de imediato/memória da 0.5.7.
  Uma comparação usada apenas em desvio não materializa um Booleano.

Para `if State = Playing then`, a geração representativa é:

```asm
    lda variable_State
    cmp #$01
    beq @if_then_0
```

## Benchmark de enumerações

O workload `enumerations` realiza transições Title, Playing, Paused e GameOver,
cópias de enum, igualdade, desigualdade, resultados Booleanos armazenados e uma
comparação usada somente como desvio.

| Métrica | Resultado |
| --- | ---: |
| PRG code | 275 B |
| PRG ocupado | 281 B |
| Instruções | 125 |
| Ciclos estáticos estimados | 408 |
| Profundidade da árvore de expressão | 1 |
| Máximo de temporários vivos | 0 |
| Temporários efetivamente requeridos | 0 B |
| Armazenamento de enum | 3 B (1 B em ZP promovida, 2 B em RAM regular) |
| ZP alocada/reservada pelo benchmark | 26 B |
| ZP livre para o alocador | 127 B |
| RAM regular livre para o alocador | 1.530 B |
| Recursos de runtime | Nenhum |

Os 17 workloads anteriores (`minimal` até `arrays` e `gameplay_full_stack`)
permanecem idênticos em todas as métricas de benchmark. Programas sem declaração
de enumeração não adicionam código, estado de runtime, RAM, Zero Page, metadados
de ROM ou descritores de enumeração.

## Adiado deliberadamente

Aritmética, `inc`/`dec`, ordenação, valores numéricos explícitos, flags, sets,
arrays de enum, parâmetros enum de procedimentos, constantes enum em `const`,
reflexão, serialização, records e metadados em runtime permanecem fora desta
milestone.
