# Rolagem e estado da PPU

[English](../../runtime/scrolling-and-ppu-state.md) | Português (Brasil)

`nes.set_scroll(x, y)` prepara um par de rolagem horizontal e vertical:

```pascal
nes.set_scroll($08, $04);
```

Ambos os argumentos devem ser valores `byte`. A chamada escreve apenas na RAM do
runtime; ela nunca escreve em `$2005` diretamente. Múltiplas chamadas antes da
próxima NMI utilizam a semântica de a última escrita prevalece. A publicação é
atômica: a NMI enxerga ou o par completo anterior ou o par completo mais recente,
nunca um eixo antigo e outro novo.

A rolagem tem como padrão `($00, $00)`. Cada NMI executa transferências limitadas
de paleta e fundo, invoca o callback opcional de VBlank do usuário, envia o par
completo de rolagem mais recente, redefine o latch compartilhado da PPU com `$2002`
e, em seguida, restaura o estado autoritativo nesta ordem:

1. PPUCTRL a partir de seu shadow de runtime;
2. rolagem horizontal através da primeira escrita em `$2005`;
3. rolagem vertical através da segunda escrita em `$2005`;
4. PPUMASK a partir de seu shadow de runtime.

Existem exatamente duas escritas em `$2005` nesta restauração final da NMI. PPUCTRL,
PPUMASK e ambos os bytes de rolagem ativa ocupam quatro bytes de RAM comum em cada
programa. Programas usando `nes.set_scroll` adicionam três bytes para o par pendente
e sua flag de publicação. `nes.run` habilita a NMI e a renderização definindo os bits
necessários nos shadows, preservando bits não relacionados. Seu valor normal de
habilitação de PPUMASK é `$1E`: fundo e sprites são renderizados, incluindo ambos nos
oito pixels mais à esquerda. A inicialização e as transferências completas de fundo
ainda mantêm o shadow de PPUMASK em `$00` até que `nes.run` alcance um VBlank seguro.

## Espelhamento

O compilador utiliza por padrão o espelhamento horizontal de nametables, preservando
o comportamento dos programas existentes. Selecione o espelhamento vertical em tempo
de compilação com:

```text
python -m nes_pascal.cli examples/scrolling_ppu_state.nsp -o build/scrolling_ppu_state.nes --mirroring vertical
```

`horizontal` e `vertical` definem o bit 0 da flag 6 do cabeçalho iNES como `0` e `1`,
respectivamente. Trata-se de uma escolha estática no cabeçalho NROM; ela não se altera
em tempo de execução.

O recurso atual foi projetado para posições de rolagem fixas em fundos estáticos.
Ele não adiciona movimento de câmera, streaming de nametables, espelhamento de quatro
telas, espelhamento controlado por mapper, split scrolling ou APIs de rolagem além de `nes.set_scroll`.
