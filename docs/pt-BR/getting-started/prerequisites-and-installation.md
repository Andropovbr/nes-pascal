# Pré-requisitos e instalação

[English](../../getting-started/prerequisites-and-installation.md) | Português (Brasil)

## Pré-requisitos

- Python 3.11 ou mais recente;
- GNU Make, opcional para os atalhos do `Makefile`;
- [cc65](https://cc65.github.io/), com `ca65` e `ld65` no `PATH`;
- um emulador de NES como o Mesen para executar a ROM.

O compilador não possui dependências de runtime em Python fora da biblioteca padrão.
Instalar o pacote Python não instala a cadeia de ferramentas cc65: `ca65` e
`ld65` são dependências externas necessárias para a geração final da ROM.

## Instalando o pacote

Instale o NES Pascal a partir do repositório:

```text
python -m pip install .
```

A instalação fornece o comando `nes-pascal`:

```text
nes-pascal --version
nes-pascal examples/minimal.nsp -o build/minimal.nes
```

`python -m nes_pascal.cli` continua suportado como invocação de módulo
equivalente:

```text
python -m nes_pascal.cli examples/minimal.nsp -o build/minimal.nes
```

Para desenvolvimento, uma instalação editável vincula o pacote instalado à
árvore de trabalho para que as alterações de código tenham efeito imediato:

```text
python -m pip install -e .
```

## Executando a partir do repositório

Sem instalar, o compilador pode ser executado diretamente a partir da raiz do
repositório:

```text
python -m nes_pascal.cli examples/minimal.nsp -o build/minimal.nes
```

## Gerando a ROM final

`ca65` e `ld65` devem estar disponíveis no `PATH` para montar e linkar a
Assembly gerada em uma ROM `.nes`. Quando estiverem ausentes, o compilador
ainda grava as saídas `.asm`, `.cfg` e `.map` e depois reporta o diagnóstico
`E5001` de cadeia de ferramentas ausente.

Continue com [Seu primeiro programa](first-program.md).
