# Memória da CPU

[English](../../runtime/cpu-memory.md) | Português (Brasil)

O NES Pascal modela exatamente 2.048 bytes de RAM física interna da CPU:
`$0000-$07FF`. Os endereços `$0800-$1FFF` são espelhos de hardware dessa mesma RAM
e nunca são tratados como armazenamento adicional.

## Layout padrão

| Intervalo | Tamanho | Proprietário | Finalidade |
| --- | ---: | --- | --- |
| `$0000-$000F` | 16 bytes | Runtime | Reserva obrigatória de runtime na Zero Page |
| a partir de `$0010` | 0 a 16 bytes combinados | Compiler | Temporários de expressão no pico de uso, seguidos por limites de `for` em cache |
| até `$001F` | bytes restantes | Free | Capacidade de temporários recuperada e visível ao alocador |
| `$0020-$007F` | 96 bytes | Reserved | Espaço estável para futuras declarações explícitas na Zero Page |
| `$0080-$00FF` | 128 bytes | User | Promoção automática opcional de variáveis globais |
| `$0100-$01FF` | 256 bytes | Reserved | Pilha de hardware do 6502 |
| `$0200-$02FF` | 0 ou 256 bytes | Runtime | Shadow de OAM alinhado a página, incluído por operações gerais ou legadas de sprites |
| de `$0200` sem sprites, senão `$0300` | 0 ou 5 bytes | Runtime | Registro legado de preparação do sprite 0, alocado apenas quando usado |
| após blocos anteriores de runtime | 0, 65 ou 66 bytes | Runtime | Tabela de Y lógico de sprites gerais e um ou dois bytes auxiliares |
| após blocos anteriores de runtime | `4N + 8` ou `8N + 8` bytes | Runtime | Estado estático ou com animação de metasprites mais rascunho compartilhado do renderizador |
| após blocos anteriores de runtime | 4 bytes | Runtime | Estado autoritativo de PPUCTRL, PPUMASK e rolagem |
| após blocos anteriores de runtime | 0 ou 41 bytes | Runtime | Shadow de paleta e flags atômicas de dirty, alocado apenas para chamadas de paleta em runtime |
| após blocos anteriores de runtime | 0 ou 960 bytes | Runtime | Shadow de tiles confirmados, incluído apenas por `nes.get_tile` |
| após o shadow opcional de tiles | 0 a 23 bytes | Runtime | Estado condicionalmente selecionado de fila de fundo, flags e helpers |
| após os dados comuns de runtime | um byte por função | Compiler | Armazenamento estático do resultado de cada função |
| após os resultados do compilador | RAM comum restante | User/free | Globais não promovidas e parâmetros de procedimentos/funções |

As janelas da política da Zero Page são fixas e não se sobrepõem. Símbolos de
runtime, slots de expressão medidos e caches do compilador são obrigatórios quando
usados. Eles nunca tomam emprestado do espaço opcional de promoção. O runtime detém
`runtime_frame_counter` em `$0000` e `runtime_frame_ready`
em `$0001`. O laço de atualização detém `runtime_last_processed_frame` em `$0002`.
O estado atual, anterior e a proteção de consulta dos controles ocupam `$0003-$0008`.
Esses bytes de runtime não podem se sobrepor ao armazenamento do compilador. O
Dentro de `$0010-$001F`, o compilador primeiro aloca exatamente o número máximo de
slots de expressão simultaneamente ativos e depois os limites de `for` em cache. O
sufixo não usado fica livre e visível ao alocador. Necessitar de mais de 16 bytes
combinados de expressão/cache é um erro de compilação.

Os slots de expressão têm nomes determinísticos (`expression_temporary_0`,
`expression_temporary_1` e assim por diante). A geração adquire explicitamente o
slot livre de menor índice, mantém o aluguel enquanto o valor é necessário e o
libera para expressões posteriores. A reserva usa o pico medido no programa todo,
não a profundidade da AST nem a quantidade de expressões. Um programa sem essa
necessidade reserva zero bytes de expressão. Valores `for_limit_*` continuam sendo
uma categoria contábil separada.

Escritas com índice variável em arrays e arrays de records continuam preservando o
índice calculado na pilha de hardware do 6502 durante a avaliação do lado direito.
Esses bytes da pilha não contam como reserva de temporários de expressão. Argumentos
de procedimentos, funções e builtins mantêm sua ordem de avaliação e reutilizam o pool apenas
depois que aluguéis anteriores terminam.

Escopos de chamada preservam todos os slots pertencentes ao chamador. Uma chamada
aninhada que produza expressão deve adquirir outro slot até o chamador liberar o
valor ativo. A análise aplica essa regra ao grafo acíclico completo. Argumentos
anteriores também recebem slots quando um argumento posterior pode chamar uma
função e sobrescrever parâmetros estáticos. Cada função tem um byte de resultado
em RAM comum e retorna em `A`; não há frame de runtime nem área fixa global de
retorno. Cada `JSR` ativo usa apenas seu endereço de retorno normal de dois bytes
na pilha de hardware, reportado pela métrica de profundidade de chamadas.

A profundidade máxima estaticamente conhecida de chamadas aninhadas é limitada
para manter os endereços de retorno de `JSR` dentro da pilha de hardware
reservada de 256 bytes (`$0100-$01FF`). Dez bytes são reservados além dos
endereços de retorno: quatro para frames de `JSR` internos do runtime
alcançáveis a partir de instruções do usuário e seis para uma NMI que pode
ocorrer durante a execução do código do jogo. Com dois bytes por chamada ativa,
a profundidade máxima suportada de chamadas de fonte é 123 (`(256 - 10) / 2`).
Um programa cuja cadeia de chamadas mais profunda exceda esse limite é rejeitado
na compilação com `E5007`; recursão é rejeitada antes com `E3014`.

Operações gerais de sprites incluem condicionalmente o shadow de OAM de 256 bytes
alinhado a página em `$0200-$02FF`. Elas reservam `runtime_sprite_logical_y` em
`$0300-$033F` e `runtime_sprite_value` em `$0340`. `nes.sprite_set_position` adiciona
condicionalmente `runtime_sprite_secondary_value` em `$0341`; os quatro bytes de
estado autoritativo da PPU iniciam, portanto, em `$0341` ou `$0342`. A tabela de Y
lógico permite que ocultar/exibir restaure uma posição para cada um dos 64 sprites.
O helper legado do exemplo de controles reserva, em vez disso, um registro de preparação
de cinco bytes; quando ambas as APIs são usadas, esse registro precede o estado de 65
ou 66 bytes de sprites gerais.

Programas apenas com metasprites reservam `$0200-$02FF` para o shadow compartilhado
de OAM. Eles também reservam dois ponteiros indiretos de dois bytes em `$0009-$000C`,
quatro bytes de RAM comum por instância (X, Y, quadro, flags) e oito bytes de rascunho
compartilhados em RAM comum. Uma instância, portanto, utiliza 12 bytes comuns mais quatro
bytes compartilhados na Zero Page; cada instância adicional adiciona quatro bytes comuns.
Esses blocos seguem qualquer estado de runtime de sprites individuais e precedem o
estado de paleta/PPU/fundo. Os índices de componentes estaticamente detidos e a geometria
imutável residem na PRG-ROM, e não na RAM.

Quando um programa utiliza uma operação de animação ou consulta de conclusão, cada
instância de metasprite adiciona quatro bytes de RAM comum para ID de animação, índice
de sequência, temporizador de quadro e flags de reprodução. O custo resultante em RAM
comum é `8N + 8`; o shadow de OAM, o rascunho compartilhado e os ponteiros na Zero Page
não aumentam. Programas limitados à seleção estática de quadros mantêm `4N + 8` e omitem
todo o estado e rotinas de animação.

Programas sem operações individuais de sprites, metasprites ou OAM omitem o símbolo de
OAM, segmento no Assembly, região no linker, código de DMA e estado de sprites. Sua
alocação comum de runtime e usuário inicia em `$0200`, disponibilizando essa página de
256 bytes em vez de reservá-la implicitamente.

Bytes de resultado de funções começam imediatamente após os dados comuns de
runtime e antes do armazenamento comum do usuário. Eles aparecem no segmento
`FUNCTION_RESULTS` e em `Compiler Symbols` no mapa. Um programa sem funções
omite a região, o segmento, os símbolos e o código.

Programas com chamadas de paleta em runtime reservam um shadow de paleta de 32 bytes,
quatro flags de paleta de fundo, quatro flags de paleta de sprites, uma flag de cor
universal e quatro bytes de restauração da PPU na RAM comum de runtime. Os bytes de
restauração armazenam PPUCTRL, PPUMASK, scroll X e scroll Y. Esse bloco de 45 bytes
inicia em `$0200` sem sprites, `$0305` após a preparação legada de sprite fixo,
`$0341-$0342` após a API geral, ou `$0346-$0347` quando ambas as APIs estão incluídas.
Ele não utiliza Zero Page adicional. A RAM do usuário se inicia imediatamente após os
blocos de runtime alocados condicionalmente.

Todo programa reserva quatro bytes de RAM comum para os shadows autoritativos de
PPUCTRL, PPUMASK, rolagem horizontal e rolagem vertical. Um programa que chama
`nes.set_scroll` reserva três bytes adicionais para um par pendente publicado atomicamente.
Programas sem essa chamada mantêm os padrões zerados de rolagem e omitem o registro de preparação.

Escritas apenas de tiles reservam 16 bytes para quatro arrays de pronto/endereço/valor,
uma flag de estouro persistente, cinco bytes auxiliares e quatro bytes de restauração de
estado da PPU: 26 bytes no total. Escritas apenas de atributos omitem os dois helpers de
índice de tiles e necessitam de 24 bytes. `nes.clear_background_updates()` adiciona
condicionalmente o bloqueio de cancelamento de um byte; APIs apenas de estouro necessitam
apenas da flag persistente. O shadow de 960 bytes de tiles confirmados 32 por 30 é
adicionado apenas quando `nes.get_tile()` é utilizado. A fila mais o shadow reservam,
portanto, 986 bytes sem cancelamento e, sem sprites, iniciam a RAM do usuário em `$05DA`.
Adicionar cancelamento eleva isso para 987 bytes e inicia a RAM do usuário em `$05DB`. Um
programa apenas com `get_tile` necessita do shadow, quatro bytes auxiliares de índice de
tiles e os quatro bytes de estado da PPU, totalizando 968 bytes.

Com suporte a paleta em runtime, a paleta e a fila compartilham os quatro bytes de
estado da PPU. Paleta, fila e shadow reservam 1.027 bytes sem cancelamento ou 1.028 bytes
com cancelamento, deixando 509 ou 508 bytes de RAM comum quando nenhum helper de sprite
é utilizado. O suporte legado a sprite fixo reserva a página de 256 bytes de OAM e cinco
bytes escalares, deixando 248 ou 247 bytes. A API geral de sprites reserva essa página
mais 65 bytes, ou 66 com `nes.sprite_set_position`, deixando 188 a 186 bytes; incluir ambas
deixa 183 a 181 bytes. O espaço de promoção automática na Zero Page permanece disponível
independentemente. O shadow permanece como a implementação mais clara de leituras aleatórias
de tiles confirmados. Mapas de metatiles, dicionários de tiles modificados e caches compactos
de leitura foram postergados porque adicionariam custo de busca ou complexidade em runtime.

A validação de callbacks de VBlank rejeita qualquer operação acessível que utilize
slots de expressão ou caches compartilhados do compilador. O caminho de interrupção utiliza,
portanto, o estado da Zero Page pertencente ao runtime mais as variáveis do callback,
nunca expressões do contexto principal ou armazenamento de laços em cache.

O intervalo explícito futuro impede que uma sintaxe futura para variáveis explícitas
na Zero Page desloque a ABI de promoção automática. A sintaxe de Zero Page explícita
ainda não está implementada.

## Política de promoção automática

A promoção é opcional e conservadora:

1. Apenas variáveis globais são candidatas. Parâmetros de procedimentos e funções sempre utilizam RAM comum.
2. O compilador conta as operações estáticas do código-fonte que leem ou escrevem em cada global.
   Ele não estima iterações de laços ou frequência de chamadas de procedimentos.
3. Uma variável global torna-se elegível após pelo menos três referências no código-fonte.
4. Globais elegíveis são consideradas estritamente na ordem de declaração. Elas não são ranqueadas por frequência.
5. Cada variável global elegível de um byte utiliza o próximo endereço de `$0080` em diante.
6. Se o intervalo automático estiver cheio, as variáveis restantes recorrem à RAM comum sem erro, alteração de símbolo ou mudança semântica.

Todos os tipos embutidos atuais ocupam um byte e podem ser promovidos. A política não
realiza análise de tempo de vida, sobreposição de armazenamento, análise de grafo de
chamadas, perfilamento dinâmico ou estimativa avançada de pontos críticos (hotness).

Os segmentos do ca65 são marcados como `zeropage`, de modo que instruções que referenciam
globais promovidas ou temporários do compilador utilizam opcodes de Zero Page. Variáveis
comuns mantêm o endereçamento absoluto.

## Mapa de memória gerado

Compilar o exemplo focado `examples/zero_page.nsp` em `build/zero_page.nes`
grava `build/zero_page.map`. O relatório separa a reserva de expressão no pico,
caches do compilador, reserva por política, Zero Page recuperada, promoção
opcional e reserva de hardware. Ele identifica cada símbolo do usuário como
`Zero Page` ou `Regular RAM`.

Um trecho da tabela de regiões gerada é:

```text
Start  End    Size  Owner     Region
$0000  $000F    16  Runtime   Zero Page runtime
$0010  ----      0  Compiler  Expression temporaries
$0010  $001F    16  Free      Recovered temporary Zero Page
$0020  $007F    96  Reserved  Future explicit Zero Page
$0080  $00FF   128  User      Automatic Zero Page variables (2 used, 126 available)
$0100  $01FF   256  Reserved  6502 hardware stack
$0200  $0203     4  Runtime   Runtime data
$0204  $0204     1  User      Regular user variables
$0205  $07FF  1531  Free      General free RAM
```

O mapa também imprime `Expression temporary reservation: 0 bytes (maximum
simultaneously live)` e `Other compiler caches: 0 bytes` neste exemplo. O `.cfg`
gerado, os segmentos no Assembly e o relatório `.map` utilizam todos o mesmo
objeto de layout validado, de modo que seus cálculos de endereço não podem divergir.

A tabela de símbolos de runtime também reporta:

```text
$0000       1  runtime_frame_counter  volatile 8-bit NMI frame counter
$0001       1  runtime_frame_ready    best-effort advisory frame-ready latch
$0002       1  runtime_last_processed_frame  persistent update-loop baseline
$0003       1  runtime_controller_1_current  controller 1 current state
$0004       1  runtime_controller_1_previous controller 1 previous state
$0005       1  runtime_controller_2_current  controller 2 current state
$0006       1  runtime_controller_2_previous controller 2 previous state
$0007       1  runtime_controller_polled_frame most recently polled frame
$0008       1  runtime_controller_poll_valid distinguishes initial RAM from frame zero
```

Quando o suporte a sprites gerais está presente, a tabela de regiões adiciona o shadow
de OAM em `$0200-$02FF`, e a tabela de símbolos de runtime reporta `runtime_oam_shadow`,
`runtime_sprite_logical_y` e `runtime_sprite_value`. `runtime_sprite_secondary_value`
aparece apenas com `nes.sprite_set_position`. Os cinco símbolos `runtime_sprite_zero_*`
são adicionalmente reportados apenas para o helper legado de compatibilidade do sprite 0.

Quando o suporte a paleta em runtime está presente, a tabela também reporta
`runtime_palette_shadow`, `runtime_palette_background_0_dirty` até
`runtime_palette_background_3_dirty`, `runtime_palette_sprite_0_dirty` até
`runtime_palette_sprite_3_dirty`, `runtime_palette_universal_dirty`,
`runtime_ppuctrl_shadow`, `runtime_scroll_x_shadow` e `runtime_scroll_y_shadow`.

Quando `nes.get_tile` está presente, a tabela reporta `runtime_background_shadow`.
Quando atualizações enfileiradas estão presentes, ela reporta os arrays de quatro
elementos `runtime_background_queue_ready`, `runtime_background_queue_high`,
`runtime_background_queue_low` e `runtime_background_queue_value`. Gravadores e APIs
de estouro adicionam `runtime_background_queue_overflow`; cancelamento adiciona
`runtime_background_queue_cancel_lock`. Helpers de coordenadas, valores e índice de
tiles são reportados apenas para pontos de entrada que os utilizam. Os símbolos de
restauração da PPU são alocados para transferências de paleta ou fundo e compartilhados
quando ambos os recursos estão presentes.
