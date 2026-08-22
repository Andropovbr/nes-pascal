# Sprites de hardware

[English](../../runtime/sprites.md) | Português (Brasil)

O NES Pascal expõe as 64 entradas de OAM do NES como sprites de hardware gerenciados
individualmente. Um valor `sprite` identifica exatamente uma entrada de quatro bytes
na OAM; não é uma entidade de jogo nem um metasprite multi-tile. Utilize a
[API de metasprites](metasprites.md) separada para objetos compilados com múltiplos
componentes. Não há animação automática, colisão, ordenação, flicker ou mitigação de
8 sprites por scanline ainda.

## Índices de sprites

O tipo embutido `sprite` ocupa um byte, mas é distinto de `byte`. Seu intervalo
válido é `$00..$3F`, selecionando os sprites de hardware de 0 a 63.

```pascal
const
    PlayerSprite: sprite = $00;

var
    EnemySprite: sprite;
```

Não há conversão implícita entre `sprite` e `byte`. Literais hexadecimais diretos
são aceitos onde um argumento de sprite é esperado e são verificados contra o limite
de 64 entradas. Parâmetros de procedimento do tipo `sprite` ainda não são suportados.

## Alocação estática e posse

`nes.sprite_create()` é uma expressão de reserva em tempo de compilação:

```pascal
PlayerSprite := nes.sprite_create();
EnemySprite := nes.sprite_create();
```

Cada local sintaticamente distinto de chamada detém um sprite de hardware por todo o
programa. O compilador processa os locais na ordem do código-fonte e atribui o menor
índice de OAM não reservado. A execução repetida do mesmo local, incluindo um local
em um laço ou procedimento chamado repetidamente, produz o mesmo índice; não é uma
alocação em tempo de execução. Locais condicionais reservam seu slot quer o ramo seja
executado ou não. Não há mapa de bits em runtime, lista de livres, `destroy` ou reutilização.

A posse explícita é estabelecida por constantes `sprite`, atribuições diretas de
literais de sprite, argumentos diretos literais/constantes da API de sprites e o helper
legado de sprite zero. Esses índices são reservados antes da alocação automática,
independentemente de sua ordem no código-fonte. Múltiplas referências explícitas podem
intencionalmente apontar para o mesmo sprite de hardware (alias), mas `sprite_create()`
nunca seleciona um slot explicitamente detido ou previamente criado.

O programa resolvido registra cada índice reservado de OAM como `individual_explicit`,
`individual_created` ou `metasprite_component`. Esses metadados não consom RAM em runtime.
A criação de metasprites aloca componentes apenas a partir do complemento não reservado
dessa mesma tabela de 64 entradas, portanto sprites individuais e metasprites não colidem.

Se um local de criação exceder a capacidade restante, a compilação é interrompida com
E3050. O mesmo diagnóstico reporta um metasprite cujo quadro máximo não cabe. A alocação
nunca sofre wrap, cria alias, sobrescreve outro proprietário, trunca um metasprite ou
retorna um sentinela. `nes.sprite_create()` não recebe argumentos e E3049 reporta uma
lista de argumentos inválida.

## Layout de OAM e API

Cada sprite de hardware ocupa quatro bytes no shadow de OAM em runtime:

| Deslocamento | Significado |
| ---: | --- |
| 0 | Coordenada Y |
| 1 | Índice do tile |
| 2 | Atributos |
| 3 | Coordenada X |

As operações públicas são:

```pascal
nes.sprite_set_x(PlayerSprite, $78);
nes.sprite_set_y(PlayerSprite, $70);
nes.sprite_set_position(PlayerSprite, $78, $70);
nes.sprite_set_tile(PlayerSprite, $01);
nes.sprite_set_palette(PlayerSprite, $02);
nes.sprite_set_attributes(PlayerSprite, $00);
nes.sprite_hide(PlayerSprite);
nes.sprite_show(PlayerSprite);
nes.sprite_set_flip_horizontal(PlayerSprite, true);
nes.sprite_set_flip_vertical(PlayerSprite, false);
nes.sprite_set_behind_background(PlayerSprite, false);
```

X, Y, tile e atributos brutos são valores `byte`. Os helpers de flip, prioridade e
visibilidade operam de forma independente. Uma paleta de sprite em tempo de compilação
acima de 3 produz E3048. Uma paleta dinâmica de `byte` fora de `0..3` é ignorada em
tempo de execução, mantendo os atributos existentes inalterados.

Esta API de sprites individuais expõe o byte Y de hardware da OAM diretamente. A PPU
desenha a primeira linha do sprite na scanline após esse valor, e `$FF` é utilizado como
o sentinela oculto. Nenhuma conversão de tela lógica `Y - 1` é realizada. A
[API de metasprites](metasprites.md) de nível mais alto aceita, em vez disso, uma
âncora lógica de tela e converte cada componente visível com `OAM Y = topo lógico do componente - 1`.

`nes.sprite_set_position(sprite, x, y)` é equivalente aos setters separados de X e Y.
Para um valor de sprite dinâmico, seu deslocamento na OAM é calculado uma vez antes de
ambas as coordenadas serem escritas. A operação também atualiza o Y de OAM em cache do
runtime sem exibir implicitamente um sprite oculto.

[`nes.sprite_bounds`](collision-helpers.md) pode copiar essa posição X/Y bruta
atual para um `nes_rect` com offsets e dimensões unsigned explícitos. Ele
reutiliza o shadow de OAM e o cache de Y lógico sem duplicar estado do sprite.

## Byte de atributos

O runtime segue o formato de atributos de OAM do NES:

| Bits | Significado |
| --- | --- |
| 0-1 | Paleta do sprite, 0 a 3 |
| 2-4 | Bits de hardware não utilizados; retidos pelos helpers de propriedades |
| 5 | Prioridade atrás do fundo (behind-background) |
| 6 | Flip horizontal |
| 7 | Flip vertical |

`nes.sprite_set_attributes` substitui o byte completo. Os helpers de paleta, flip e
prioridade realizam operações de leitura-modificação-escrita e preservam todos os bits
não relacionados.

## Visibilidade

Todos os 64 sprites iniciam ocultos. A inicialização escreve `$FF` em cada byte Y do
shadow de OAM antes que a NMI ou a renderização possam expor o conteúdo da RAM.

`nes.sprite_hide` salva o byte Y bruto visível atual da OAM em um cache de 64 bytes
pertencente ao runtime e, em seguida, escreve `$FF` na OAM. Chamadas repetidas de
ocultação preservam o valor salvo. `nes.sprite_show` restaura esse byte. Chamar
`nes.sprite_set_y` enquanto oculto atualiza o cache, mas mantém o sprite oculto; uma
exibição posterior utilizará o novo valor. Os 64 bytes extras mantêm a exibição/ocultação
determinística sem introduzir um modelo de objetos de sprites maior.

## DMA e contexto de execução

Quando qualquer operação de sprite é incluída, o runtime reserva o shadow de OAM de
`$0200-$02FF` alinhado a página. No início de cada NMI, após a contabilidade de quadros
e antes das transferências de paleta/fundo ou do callback de VBlank do usuário, ele redefine
`$2003` para zero e escreve a página `$02` em `$4014`. Isso copia todos os 256 bytes para
a OAM da PPU durante o VBlank. O código do usuário nunca escreve diretamente na OAM da PPU.

Setters de sprites atualizam a RAM da CPU e destinam-se à inicialização, código principal
comum ou `nes.on_update`. Eles são rejeitados no callback de VBlank do usuário porque a
NMI detém o DMA e o estado de rascunho dos helpers de sprites não é reentrante. Alterações
feitas por um callback de atualização ficam visíveis após a transferência da próxima NMI.

Consulte [Memória da CPU](cpu-memory.md) para alocações exatas e
[Orçamento de ciclos de VBlank](vblank-cycle-budget.md) para o custo de DMA.
