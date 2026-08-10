# Pré-requisitos e instalação

[English](../../getting-started/prerequisites-and-installation.md) | Português (Brasil)

## Pré-requisitos

- Python 3.11 ou mais recente;
- GNU Make, opcional para os atalhos do `Makefile`;
- [cc65](https://cc65.github.io/), com `ca65` e `ld65` no `PATH`;
- um emulador de NES como o Mesen para executar a ROM.

O compilador não possui dependências de runtime em Python fora da biblioteca padrão.

## Executando a partir do repositório

O compilador pode ser executado diretamente a partir da raiz do repositório. Uma instalação
em modo editável é opcional:

```text
python -m pip install -e .
```

Continue com [Seu primeiro programa](first-program.md).
