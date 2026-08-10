# API de paleta

[English](../../runtime/palettes.md) | Português (Brasil)

O NES Pascal expõe quatro paletas de fundo e quatro paletas de sprites. Índices
de paleta e de cor são valores `byte` em tempo de compilação em `$00..$03`; cada
cor é um `nes_color` em `$00..$3F`.

```pascal
nes.set_background_palette($00, $0F, $01, $11, $21);
nes.set_sprite_palette($03, $0F, $06, $16, $26);
nes.set_background_palette_color($02, $03, $30);
nes.set_sprite_palette_color($01, $02, $27);
```

As chamadas completas recebem `(PaletteIndex, Color0, Color1, Color2, Color3)`.
As chamadas individuais recebem `(PaletteIndex, ColorIndex, Color)`. Índices
dinâmicos não são suportados pelo modelo fixo atual de chamadas embutidas.

## Layout do NES e cor universal

Paletas de fundo ocupam `$3F00-$3F0F`; paletas de sprites ocupam `$3F10-$3F1F`.
As entradas de cor zero espelhadas do NES são representadas por uma única cor de
fundo universal canônica em `$3F00`, e não como oito valores independentes. Portanto,
o índice de cor zero em qualquer chamada de paleta completa ou individual atualiza
essa cor canônica. `nes.set_background_color(Color)` é a API direta e explícita para
o mesmo valor. Chamadas posteriores prevalecem deterministicamente.

As três cores independentemente visíveis de cada paleta de fundo ou de sprite são
escritas nos deslocamentos de um a três. Endereços espelhados não são expostos como
entradas separadas para o usuário.

## Inicialização e runtime

Chamadas de nível superior antes de `nes.run` realizam escritas diretas após o
aquecimento da PPU enquanto a renderização estiver desabilitada. As chamadas são
executadas na ordem do código-fonte, de modo que escritas repetidas utilizam o
comportamento da última escrita prevalece.

Chamadas após `nes.run`, em laços principais e em procedimentos preparam valores
em um shadow de paleta de 32 bytes. Uma flag de publicação por paleta mais uma flag
para a cor universal tornam cada atualização preparada atômica. Substituir uma
atualização pendente invalida sua flag antes de escrever os bytes e a publica apenas
após todos os bytes estarem estáveis; a atualização completa mais recente é, portanto,
aplicada no próximo VBlank.

A NMI verifica um conjunto fixo de nove flags. Paletas inalteradas são ignoradas,
flags marcadas (dirty) são limpas à medida que são consumidas, e no máximo oito
transferências de três cores mais a cor universal podem ser executadas em uma única
NMI. Não há fila dinâmica de comandos.

Escritas de paleta alteram o latch de endereçamento da PPU. Após o transmissor e o
callback opcional de VBlank do usuário, um epílogo compartilhado da NMI redefine o
latch e restaura PPUCTRL, scroll X/Y e PPUMASK a partir de shadows pertencentes ao
compilador. Isso mantém o trabalho de paleta compatível com [`nes.set_scroll`](scrolling-and-ppu-state.md)
e evita restaurações locais duplicadas no transmissor.

Consulte [Orçamento de ciclos de VBlank](vblank-cycle-budget.md) para o custo atual do
transmissor limitado e a capacidade restante.
