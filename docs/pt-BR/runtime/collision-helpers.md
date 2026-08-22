# Helpers de colisão

[English](../../runtime/collision-helpers.md) | Português (Brasil)

O NES Pascal fornece primitivas de consulta para colisões de jogabilidade em
uma tela com coordenadas de byte. Elas não movem objetos, resolvem penetração,
registram entidades nem mantêm um mundo de colisão.

## Representação do retângulo e regras de borda

`nes_rect` é um record comum predefinido, implementado pelo mesmo layout fixo
dos records do usuário:

```pascal
var
    PlayerBounds: nes_rect;

begin
    PlayerBounds.X := $20;
    PlayerBounds.Y := $30;
    PlayerBounds.Width := $08;
    PlayerBounds.Height := $08;
end;
```

Seus quatro campos `byte` consecutivos são X `+0`, Y `+1`, Width `+2` e
Height `+3`. Um `nes_rect` usa RAM estática comum, sem descritor, heap,
ponteiro ou estado oculto por entidade. As APIs aceitam diretamente variáveis
`nes_rect` independentes; um record do usuário apenas estruturalmente parecido
não é compatível.

Os limites são unsigned e semiabertos: `[X, X + Width)` por
`[Y, Y + Height)`. As bordas esquerda e superior pertencem ao retângulo; as
bordas direita e inferior não. Retângulos que apenas se tocam não colidem.
Width ou Height zero nunca colide.

O runtime verifica o fim lógico com o carry do 6502. Um fim exatamente igual
a 256 é válido: X `$F8` e Width `$08` podem conter `$FF`. Um fim maior que 256
é inválido e retorna `false`; X `$FA` com Width `$10` não reaparece no lado
esquerdo. Helpers de bounds produzem um retângulo de área zero quando o
resultado solicitado daria wrap.

## Predicados de ponto e retângulo

```pascal
Inside := nes.point_in_rect(PointX, PointY, PlayerBounds);
Overlap := nes.collides(PlayerBounds, EnemyBounds);
```

```text
nes.point_in_rect(x: byte, y: byte, rectangle: nes_rect): boolean
nes.collides(left: nes_rect, right: nes_rect): boolean
```

Ambos retornam Boolean canônico `$00`/`$01`. O primeiro valida a caixa e
compara distâncias unsigned a partir do canto superior esquerdo. O segundo
valida as duas caixas e, em cada eixo, exige que o início posterior fique
estritamente antes do fim da caixa anterior. Isso fixa a regra semiaberta sem
depender de soma de byte com wrap.

As chamadas são seguras em funções e expressões Boolean com curto-circuito.
Argumentos escalares usam os escopos existentes de chamada; argumentos
`nes_rect` são endereços diretos e não consomem temporário de expressão.
Quando um argumento escalar anterior precisa sobreviver a uma função posterior,
o compilador aluga o pool normal de expressões para que uma consulta de colisão
aninhada não sobrescreva a entrada preparada da chamada externa.
Consultas podem rodar no código principal, em funções, procedimentos e no
callback de update. Elas são rejeitadas no caminho do callback de VBlank porque
o código principal pode ser interrompido enquanto os helpers usam scratch
compartilhado de runtime.

## Bounds de sprite

```pascal
nes.sprite_bounds(PlayerSprite, $01, $02, $06, $05, PlayerBounds);
```

```text
nes.sprite_bounds(
    value: sprite,
    offset_x: byte,
    offset_y: byte,
    width: byte,
    height: byte,
    output: nes_rect
)
```

Os offsets são somas unsigned à posição. `$00, $00, $08, $08` descreve o
sprite 8 por 8 completo. O helper lê X do shadow de OAM e o Y bruto do cache
existente de hide/show, sem duplicar posição. Visibilidade não ativa nem
desativa colisão. Os bits de flip do sprite individual não transformam offsets
explícitos; a caixa continua ancorada à posição da API. Y mantém a convenção
bruta de OAM descrita em [Sprites de hardware](sprites.md).

## Bounds e metadados de metasprite

```pascal
nes.metasprite_bounds(Player, PlayerBounds);
```

A saída usa posição, frame e flips atuais. Não há varredura de componentes em
runtime: o importador calcula uma vez o fallback pelos extremos dos componentes
8 por 8. Frames vazios geram área zero.

Um frame pode declarar uma caixa imutável relativa à âncora:

```json
"collision_box": {
  "x": 1,
  "y": 2,
  "width": 6,
  "height": 5
}
```

`x` e `y` são offsets signed dos metadados; width e height ficam em 1..255.
Offsets normal e invertido devem caber no signed byte. Flip horizontal usa
`-x-width`; flip vertical usa `-y-height`, espelhando caixas assimétricas ao
redor da mesma âncora/pivô da geometria. Os quatro bytes resolvidos entram nas
tabelas PRG apenas quando `nes.metasprite_bounds` é usado; não existe cópia por
instância.

Metadados antigos sem `collision_box` continuam válidos e usam os bounds
visuais. Dimensões, valores ou offsets incompatíveis produzem E6016.

## Mapa de colisão do fundo

`nes.background_collision(x, y)` recebe pixels da tela. X `$00`..`$FF`
seleciona as 32 colunas; Y `$00`..`$EF` seleciona as 30 linhas e
Y `$F0`..`$FF` retorna `false`. O modelo atual é a nametable 0 em uma tela
estática 256 por 240, não coordenadas de mundo com rolagem.

Configure `--collision-map` com um arquivo texto UTF-8 de exatamente 30 linhas
por 32 caracteres:

```text
11111111111111111111111111111111
10000000000000000000000000000001
...
11111111111111111111111111111111
```

`0` é transitável e `1` é sólido. O compilador valida dimensões e valores e
compacta as 960 flags, em ordem de linha e bit menos significativo primeiro,
em 120 bytes imutáveis de PRG-ROM. Quatro bytes compactados por linha evitam
truncamento em posições como o índice lógico 641. Um ponteiro ZP de dois bytes
soma o endereço ROM com carry entre páginas. O resultado é Boolean canônico.

Esse caminho independe de `nes.get_tile` e não liga o shadow confirmado de 960
bytes. `nes.set_tile` muda a imagem, mas não sincroniza o mapa de colisão, que
permanece estático. Colisão de mundo/rolagem está fora deste marco.

## Custos e seleção de recursos

Todos os builtins são entradas declarativas comuns. Sem chamadas de colisão, o
programa recebe zero código, RAM, ZP e dados ROM de colisão.

| Caminho usado | RAM comum específica | Símbolos ZP específicos | Dados PRG do mapa |
| --- | ---: | ---: | ---: |
| ponto/retângulo, retângulos ou bounds | 10 B compartilhados | ponteiro de 2 B | 0 B |
| apenas fundo | 2 B para pixel/índice | ponteiro de 2 B | mapa 120 B + tabela de máscaras 8 B |

Bounds de sprite/metasprite também exigem o estado e shadow de OAM já
documentados. O ponteiro ocupa bytes da partição de política ZP de runtime de
16 bytes e só recebe símbolos quando algum helper é usado.

Veja [`examples/collision_helpers.nsp`](../../../examples/collision_helpers.nsp)
para um programa focado com todos os caminhos públicos.
