# Documentação do NES Pascal

[English](../index.md) | Português (Brasil)

O NES Pascal é uma linguagem compilada e fortemente tipada inspirada no Pascal e
especializada para jogos do Nintendo Entertainment System. Ela compila o código-fonte
para Assembly compatível com o ca65 e produz uma imagem NROM-256 para sistemas
NES NTSC.

Esta documentação descreve apenas o comportamento implementado pelo compilador.
O trabalho planejado é acompanhado separadamente no
[roadmap do projeto](../../roadmap/README.md).

## Primeiros Passos

- [Primeiros Passos](getting-started/index.md)
- [Pré-requisitos e instalação](getting-started/prerequisites-and-installation.md)
- [Seu primeiro programa](getting-started/first-program.md)
- [Compilando e executando programas](getting-started/building-and-running.md)
- [Testando o compilador](getting-started/testing.md)

## Guia da Linguagem

- [Estrutura do programa](language/program-structure.md)
- [Identificadores e literais](language/identifiers-and-literals.md)
- [Tipos embutidos](language/types.md)
- [Constantes e variáveis](language/constants-and-variables.md)
- [Arrays](language/arrays.md)
- [Enumerações](language/enumerations.md)
- [Records](language/records.md)
- [Atribuições](language/assignments.md)
- [Expressões](language/expressions.md)
- [Estruturas condicionais](language/conditionals.md)
- [Laços de repetição](language/loops.md)
- [Incremento e decremento](language/increment-and-decrement.md)
- [Procedimentos](language/procedures.md)
- [Funções](language/functions.md)

## Runtime do NES

- [Runtime do NES](runtime/index.md)
- [Plataforma-alvo](runtime/target-platform.md)
- [Callbacks de quadro](runtime/frame-callbacks.md)
- [Entrada de controle](runtime/controller-input.md)
- [Sprites de hardware](runtime/sprites.md)
- [Metasprites](runtime/metasprites.md)
- [Animação de sprites](runtime/sprite-animation.md)
- [Helpers de colisão](runtime/collision-helpers.md)

## Referência

- [Referência](reference/index.md)
- [Pipeline do compilador](reference/compiler-pipeline.md)
- [Diagnósticos do compilador](reference/diagnostics/index.md)
- [Recursos não suportados](reference/unsupported-features.md)
- [Mapa de cobertura de testes semânticos](compiler/test-coverage-map.md)
- [Histórico de implementação e auditorias do compilador](compiler/index.md)
