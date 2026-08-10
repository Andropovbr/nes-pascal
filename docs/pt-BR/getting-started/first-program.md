# Seu primeiro programa

[English](../../getting-started/first-program.md) | Português (Brasil)

O exemplo mínimo exercita todos os tipos embutidos e os dois comandos de
inicialização:

```pascal
program Minimal;

const
    DefaultBackgroundColor: nes_color = $21;

var
    BackgroundColor: nes_color;
    FrameCounter: byte;
    RenderingEnabled: boolean;

begin
    BackgroundColor := DefaultBackgroundColor;
    FrameCounter := $00;
    RenderingEnabled := true;
    nes.set_background_color(BackgroundColor);
    nes.run;
end.
```

O programa declara uma constante tipada e três variáveis globais tipadas. Seu
bloco principal atribui valores a todas as variáveis antes do uso, define a cor
de fundo universal e inicializa o runtime. Como não há instruções após `nes.run`,
o laço estável implícito do compilador mantém a ROM em execução.

Compile-o a partir da raiz do repositório:

```text
python -m nes_pascal.cli examples/minimal.nsp -o build/minimal.nes
```

O comando gera `build/minimal.asm`, `build/minimal.cfg`,
`build/minimal.map`, o arquivo intermediário `build/minimal.o` e
`build/minimal.nes`. O arquivo `.map` detalha todas as alocações na RAM da CPU. Consulte
[Compilando e executando programas](building-and-running.md) para ver os outros
exemplos e instruções de emulador.

As regras de sintaxe e tipos usadas aqui são definidas no
[Guia da Linguagem](../../language/index.md). As operações de runtime estão documentadas
em [Runtime do NES](../../runtime/index.md).
