# Implementação e Medições de Records (0.5.10)

[English](../../compiler/records-0.5.10.md) | Português (Brasil)

A milestone 0.5.10 adiciona records nominais de layout fixo como metadados de
compilação e armazenamento estático contíguo. `RecordType` preserva nome, campos
tipados e ordenados, offsets iniciados em zero, tamanho total e identidade
nominal. Leituras e escritas permanecem explícitas pela análise semântica,
análise de temporários, layout de memória, benchmarks e geração ca65.

## Layout e lowering

- Campos `byte`, `boolean` e enum ocupam um byte sem padding.
- Records isolados e arrays de records ficam contíguos em RAM regular e não são
  promovidos automaticamente para Zero Page.
- Campos isolados ou com índice constante viram operandos diretos com símbolo e
  offset. Um record de 4 bytes no índice 2 começa em `base + 8`.
- Índices variáveis são multiplicados pelo tamanho conhecido: potências de dois
  usam `asl`; outros tamanhos usam adição repetida local. Nenhum runtime genérico
  de multiplicação ou temporário permanente é vinculado.
- Escritas indexadas avaliam o índice primeiro e preservam o offset escalado na
  pilha de hardware durante a avaliação do lado direito.
- O acesso variável é rejeitado quando o offset máximo do campo pode exceder
  255. Índices constantes continuam sendo expressões de endereço ca65 diretas.

Lowering representativo:

```asm
    lda #$20
    sta variable_Player

    lda variable_Index
    asl a
    asl a
    clc
    adc #$01
    tax
    lda variable_Enemies,x
```

## Benchmark de records

O workload `records` usa uma entidade de 4 bytes, array de quatro entidades,
campos de record isolado, campos enum e Booleanos, índices constantes e
variáveis, leituras, escritas, aritmética e branch por campo enum.

| Métrica | Resultado |
| --- | ---: |
| Código PRG | 389 B |
| PRG ocupado | 395 B |
| Instruções | 196 |
| Ciclos-base estáticos estimados | 605 |
| Profundidade da árvore de expressão | 2 |
| Máximo de temporários vivos | 0 |
| Reserva fixa do pool temporário | 16 B |
| Temporários/cache realmente necessários | 0 B |
| Armazenamento de records | 20 B de RAM regular |
| Outro armazenamento regular do usuário | 1 B |
| Escalares promovidos automaticamente | 2 B de ZP |
| ZP alocada/reservada pelo benchmark | 27 B |
| ZP livre visível ao alocador | 126 B |
| RAM regular livre visível ao alocador | 1.511 B |
| Recursos de runtime | Nenhum |

O array contribui 16 bytes e o record isolado, 4 bytes. Os escalares de índice
e resultado seguem a política existente; nenhum record, campo, descritor, cache
de escala ou helper de runtime consome Zero Page.

Os 19 workloads anteriores preservam métricas de PRG, instruções, ciclos, RAM,
Zero Page e pressão de temporários. Programas sem records não emitem
armazenamento, código, metadados ou recursos de runtime específicos de records.

A validação local final passou em 486 testes automatizados e na suíte dedicada
de 27 testes de runtime no Mesen. O exemplo público de records foi montado e
linkado como imagem NROM válida, e todo o corpus de benchmark reconciliou os
totais dos 2 KiB de RAM.

## Deliberadamente adiado

Records aninhados e anônimos, atribuição/igualdade de records inteiros,
parâmetros e retornos de record, referências, ponteiros, records packed ou
variantes, métodos, construtores, destrutores, RTTI, bounds checks em runtime,
arrays multidimensionais, runtime de multiplicação e redesign do alocador de
temporários permanecem fora desta milestone.
