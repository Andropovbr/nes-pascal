# Tipos embutidos

[English](../../language/types.md) | Português (Brasil)

O NES Pascal oferece cinco tipos embutidos. Cada um ocupa um byte, mas os tipos
são distintos e não são convertidos implicitamente. Também há
[enumerações definidas pelo usuário](enumerations.md), que são tipos nominais de um byte.

## `nes_color`

`nes_color` ocupa um byte e representa um valor de paleta do NES. Seu intervalo
permitido é `$00..$3F`.

O mesmo intervalo é aplicado para atribuições escalares, chamadas de cor de fundo
universal, paletas completas de fundo e sprites e cores de paleta individuais.
Os valores nunca sofrem wrap ou máscara para se ajustarem ao intervalo.

Válido:

```pascal
const
    BackgroundColor: nes_color = $21;
```

Inválido:

```pascal
const
    BackgroundColor: nes_color = $80;
```

Diagnóstico esperado:

```text
E4002 path/to/source.nsp:4:34

Value $80 is not valid for type nes_color.

Allowed range: $00..$3F.
```

## `byte`

`byte` ocupa um byte e aceita valores hexadecimais de `$00` até `$FF`.

```pascal
const
    Maximum: byte = $FF;
```

Um valor maior produz E4003.

## `boolean`

`boolean` ocupa um byte. `false` é representado por zero e `true` por um.
Nenhuma conversão de hexadecimal para booleano é permitida.

```pascal
const
    RenderingEnabled: boolean = true;
```

Atribuições e operandos de operadores devem obedecer às regras exatas de tipos
descritas em [Atribuições](assignments.md) e [Expressões](expressions.md).

## `sprite`

`sprite` é um índice de OAM de hardware fortemente tipado. Ele ocupa um byte, mas seus
valores permitidos são `$00..$3F`, selecionando os 64 sprites de hardware do NES.

```pascal
var
    PlayerSprite: sprite;

begin
    PlayerSprite := nes.sprite_create();
end;
```

Um valor acima de `$3F` produz E4008. `sprite` não é intercambiável implicitamente
com `byte`, não suporta aritmética ou `inc`/`dec`, e é passado diretamente para a
[API de sprites de hardware](../runtime/sprites.md). `nes.sprite_create()` produz
um valor de `sprite` estaticamente reservado; não é uma função geral nem uma alocação
dinâmica de objeto em runtime.

## `metasprite`

`metasprite` é uma identidade opaca de um byte para um objeto lógico criado
estaticamente composto por vários sprites de hardware. Não é um índice de OAM
e nenhum literal hexadecimal pode ser convertido para ele.

```pascal
var
    Player: metasprite;

begin
    nes.import_metasprite(player);
    Player := nes.metasprite_create(player.idle_0);
end;
```

Cada local de criação possui uma identidade estável e slots de componentes de posse
estática. O tipo suporta atribuição e a [API de metasprites](../runtime/metasprites.md),
mas não suporta aritmética, comparações, `inc`, `dec`, constantes ou parâmetros
de procedimento. E4009 rejeita valores numéricos em um contexto de metasprite.

Nomes de quadros e animações importados são tipos de símbolos internos em tempo
de compilação, e não tipos embutidos declaráveis pelo usuário. Símbolos de quadros
selecionam quadros manuais/de criação; símbolos de animação são aceitos apenas pela
[API de animação de sprites](../runtime/sprite-animation.md). Nenhum deles pode ser
armazenado em uma variável ou sintetizado a partir de um byte.

Parâmetros de valor de procedimentos atualmente suportam apenas `byte` e `boolean`.
`nes_color`, `sprite` e `metasprite` permanecem tipos globais válidos, mas produzem
E4005 quando usados como tipo de parâmetro. `nes_color` e `sprite` também suportam
constantes tipadas; identidades de `metasprite` originam-se apenas de locais de criação.
