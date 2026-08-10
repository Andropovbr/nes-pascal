# Atualizações de fundo em runtime

[English](../../runtime/background-updates.md) | Português (Brasil)

O milestone 0.4.4 fornece atualizações limitadas para a nametable 0 após o início
da renderização. Todas as coordenadas e valores são expressões `byte`:

```pascal
nes.set_tile($0F, $0E, $03);
Tile := nes.get_tile($0F, $0E);
nes.set_attribute($03, $03, $E4);
```

`nes.set_tile(x, y, tile)` aceita coordenadas de tiles `x = 0..31` e `y = 0..29`.
Ele enfileira a escrita correspondente na PPU. Quando a NMI escreve o byte na PPU,
ela também atualiza o shadow opcional de 960 bytes de tiles confirmados.
`nes.get_tile(x, y)` lê esse shadow e, portanto, retorna o valor confirmado na PPU,
e não um valor meramente aguardando na fila.

`nes.set_attribute(x, y, value)` aceita coordenadas da tabela de atributos do
hardware `x = 0..7` e `y = 0..7`. O valor é um byte de atributo bruto do NES
para a região selecionada de 4 por 4 tiles; o compilador não codifica quadrantes
de paleta. Atributos não possuem shadow separado em RAM.

Coordenadas literais ou constantes diretas fora desses intervalos geram erros em
tempo de compilação. Outras expressões de coordenadas são verificadas em tempo de
execução: escritas de tiles ou atributos fora do intervalo não fazem nada, e um
`nes.get_tile` fora do intervalo retorna `$00`.

## Quatro escritas por quadro

O runtime possui quatro slots fixos na fila. Cada `nes.set_tile` ou `nes.set_attribute`
bem-sucedido ocupa um slot até que a próxima NMI o consuma. A NMI examina todos os
quatro slots e escreve no máximo quatro bytes através de `$2007` por quadro. A flag
de pronto de um slot é publicada apenas após seu endereço e valor estarem completos.

Quando todos os quatro slots estiverem ocupados, uma escrita posterior é descartada
e `runtime_background_queue_overflow` torna-se `$01`. Uma escrita rejeitada de tile
ou atributo não altera a memória da PPU nem o shadow de tiles confirmados. Entradas
existentes na fila nunca são sobrescritas. Uma vez que a NMI libera os slots, chamadas
posteriores podem ser aceitas mesmo enquanto a flag de estouro persistente (sticky)
permanecer definida.

`nes.background_updates_overflowed()` retorna uma visualização `boolean` dessa flag
persistente. `nes.clear_background_update_overflow()` redefine apenas a flag e não
afeta as escritas enfileiradas.

`nes.clear_background_updates()` descarta todas as escritas que ainda não foram
consumidas. Ela não limpa a flag de estouro e não altera o shadow de tiles confirmados
nem a memória da PPU. Se a NMI já consumiu uma escrita, essa escrita confirmada não
pode ser cancelada.

Quando o programa chama `nes.clear_background_updates()`, o compilador inclui um
bloqueio de cancelamento de um byte verificado uma vez no início do transmissor
limitado da NMI. A instrução que adquire esse bloqueio é a fronteira de concorrência.
Se a NMI passar pela verificação primeiro, ela conclui toda a transmissão limitada
antes que o código principal retome, e o cancelamento então remove apenas as escritas
que ainda estiverem pendentes após isso. Se o código principal adquirir o bloqueio
primeiro, uma NMI interveniente ignora toda a fila; o código principal limpa todas
as quatro flags de pronto e, em seguida, libera o bloqueio. A NMI, portanto, nunca
observa uma fila parcialmente limpa em sequência. Escritas de tiles e atributos
utilizam o mesmo protocolo, e a flag de estouro persistente independente não é alterada.

Escritas repetidas no mesmo endereço ocupam slots separados e são transmitidas na
ordem da fila. Antes dessa NMI, `nes.get_tile()` ainda retorna o valor previamente
confirmado. Após a NMI, ele retorna a última escrita processada para aquele tile.

## Inicialização e estado da PPU

O shadow de 960 bytes é incluído apenas quando `nes.get_tile()` aparece no programa.
Quando o programa chama [`nes.load_background()`](background-loading.md), sua
transferência inicial copia os primeiros 960 bytes do asset para aquele shadow. Sem um
fundo configurado, o código de RESET gerado preenche tanto a nametable 0 quanto o shadow
com zeros enquanto a renderização e a NMI estiverem desabilitadas. Assim, o primeiro
resultado de `get_tile` sempre representa o estado da PPU estabelecido pelo compilador.

Programas de fundo apenas para escrita omitem o shadow. Um programa apenas para tiles
reserva 26 bytes: 22 bytes para o estado da fila e helpers mais quatro bytes compartilhados
de restauração da PPU. Escritas apenas de atributos necessitam de 24 bytes porque não
utilizam os dois helpers de índice de tiles. O bloqueio de cancelamento adiciona um byte
apenas quando `nes.clear_background_updates()` está presente. Um programa combinando
escritas de tiles com `nes.get_tile()` reserva 986 bytes sem cancelamento ou 987 bytes
com cancelamento. Um programa exclusivo de `get_tile` reserva 968 bytes e não instala
o transmissor de fila na NMI. Programas usando apenas as APIs de inspeção/limpeza de
estouro reservam apenas a flag persistente de um byte. O relatório `.map` gerado
identifica cada bloco condicional.

O backend também emite apenas os helpers públicos de fundo referenciados pelo programa.
Programas apenas de tiles, apenas de atributos e apenas de leitura, portanto, omitem os
outros pontos de entrada. O publicador compartilhado da fila, o transmissor e o helper
de índice de tiles permanecem presentes sempre que um ponto de entrada público retido os
chamar; trata-se de seleção explícita de dependências, e não de um otimizador genérico
de código morto.

O transmissor de fundo é executado antes do callback opcional de VBlank do usuário. Um
epílogo compartilhado da NMI então restaura PPUCTRL, scroll X/Y e PPUMASK após todo o
trabalho de VBlank do runtime e do usuário. Operações de fundo e `nes.get_tile` não são
permitidas no caminho de um callback de VBlank porque a NMI detém o consumo da fila.

Atualizações de fundo suportam apenas a nametable 0, escritas de um byte e entradas
brutas de atributos. Elas não adicionam múltiplas nametables, fila genérica da PPU ou streaming.
