# Records

[English](../../language/records.md) | Português (Brasil)

O NES Pascal suporta tipos record nomeados e de layout fixo para agrupar dados
estáticos de jogo. Records são tipos nominais: duas declarações continuam sendo
tipos diferentes mesmo quando possuem os mesmos campos e layout.

## Declaração e layout

Declare records na seção opcional `type`:

```pascal
type
    EnemyState = (Inactive, Active, Dead);
    Enemy = record
        X: byte;
        Y: byte;
        State: EnemyState;
        Visible: boolean;
    end;
```

Os campos preservam a ordem de declaração, e seus nomes não diferenciam
maiúsculas de minúsculas dentro do record. Campos duplicados produzem E4019.
Os tipos permitidos são `byte`, `boolean` e uma enumeração declarada. Cada campo
ocupa exatamente um byte; booleanos continuam sendo bytes canônicos `$00`/`$01`
e não são compactados em bits. Não há alinhamento nem padding: o exemplo usa
`X +0`, `Y +1`, `State +2`, `Visible +3` e tamanho total de 4 bytes.

Campos não podem ser outros records nem arrays. Definições diretamente
recursivas produzem E4023 em vez de iniciar um layout infinito. Records vazios
e layouts acima de 256 bytes também são rejeitados.

## Variáveis e campos

```pascal
var
    Player: Enemy;
    Result: byte;

begin
    Player.X := $20;
    Player.State := Active;
    Player.Visible := true;
    Result := Player.X;
end.
```

Uma variável record é uma única alocação contígua em RAM regular com o tamanho
do tipo. Ela nunca é promovida automaticamente para Zero Page, mesmo quando
possui um único campo. Leituras e escritas usam o tipo exato do campo; portanto,
um byte bruto não pode ser atribuído a um campo enum ou Booleano. Campos
desconhecidos produzem E4020, e acesso de campo em escalar produz E4021.

Campos isolados possuem endereços conhecidos em compilação. O backend emite
operandos ca65 diretos como `variable_Player + 2`; não existe cálculo de
ponteiro, descritor, tabela de reflexão, objeto de inicialização, heap ou rotina
de runtime para records.

Records inteiros não são valores gerais de expressão. Atribuição, comparação,
argumentos e retornos de records inteiros são rejeitados; opere em campos
individuais. O record predefinido `nes_rect` é aceito pelos builtins de colisão
como referência direta e nominalmente tipada. Esse contrato restrito não cria
semântica geral de valores record.

A análise de atribuição definida segue a regra existente para agregados usada
por arrays: após a atribuição de um campo, a variável record é considerada
inicializada como um todo. O programa continua responsável por atribuir cada
campo que lerá depois.

## Arrays de records

```pascal
var
    Enemies: array[$00..$07] of Enemy;
    Index: byte;

begin
    Enemies[$03].X := $40;
    Enemies[Index].State := Active;
end.
```

As regras existentes de arrays fixos continuam válidas, mas o armazenamento
considera o tamanho do record. Oito elementos `Enemy` de 4 bytes ocupam
exatamente 32 bytes contíguos de RAM regular. Nenhum descritor por elemento ou
byte oculto de Zero Page é emitido.

Para índice constante, o compilador resolve todo o offset:

```text
base + (índice * tamanho do record) + offset do campo
```

Para índice variável, o backend converte explicitamente o índice lógico em
offset de bytes. Tamanhos potência de dois usam instruções `asl` locais (`2`,
`4` e `8` bytes exigem um, dois e três shifts). Outros tamanhos usam uma pequena
sequência inline e determinística de adições repetidas. Atribuições indexadas
avaliam o índice primeiro e preservam o offset escalado na pilha de hardware do
6502 durante a avaliação do lado direito.

O acesso por índice variável só é aceito quando todo offset escalado possível
para o campo escolhido cabe em `$00..$FF`. Arrays maiores ainda podem usar
índices constantes, mas um acesso variável que poderia truncar o offset produz
E4024. Assim como em arrays de byte, não há bounds check em runtime.

## Limitações atuais

Não há records anônimos, aninhados, dinâmicos, variantes, packed, herdados ou
com métodos. Records não podem ser parâmetros nem retornos, e não existem
referências, ponteiros, construtores, destrutores, operadores de record inteiro,
informação de tipo em runtime ou arrays multidimensionais.
