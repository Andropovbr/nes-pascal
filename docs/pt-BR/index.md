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

- [Guia da Linguagem](language/index.md)
- [Estrutura do programa](language/program-structure.md)
- [Identificadores e literais](language/identifiers-and-literals.md)
- [Tipos embutidos](language/types.md)
- [Constantes e variáveis](language/constants-and-variables.md)
- [Arrays](language/arrays.md)
- [Atribuições](language/assignments.md)
- [Expressões](language/expressions.md)
- [Estruturas condicionais](language/conditionals.md)
- [Laços de repetição](language/loops.md)
- [Incremento e decremento](language/increment-and-decrement.md)
- [Procedimentos](language/procedures.md)

## Runtime do NES

- [Runtime do NES](runtime/index.md)
- [Plataforma-alvo](runtime/target-platform.md)
- [Callbacks de quadro](runtime/frame-callbacks.md)
- [Entrada de controle](runtime/controller-input.md)
- [Sprites de hardware](runtime/sprites.md)
- [Metasprites](runtime/metasprites.md)
- [Animação de sprites](runtime/sprite-animation.md)

## Referência

- [Referência](reference/index.md)
- [Pipeline do compilador](reference/compiler-pipeline.md)
- [Auditoria de otimização e arquitetura (0.5.5)](compiler/optimization-audit-0.5.5.md)
- [Infraestrutura de builtins / intrínsecos (0.5.6)](compiler/builtin-infrastructure.md)
- [Melhorias de baixo risco na geração de código (0.5.7)](compiler/low-risk-codegen-0.5.7.md)
- [Implementação e medições de arrays (0.5.8)](compiler/arrays-0.5.8.md)
- [Recursos não suportados](reference/unsupported-features.md)
- [Diagnósticos do compilador](reference/diagnostics/index.md)
