# Enumerações

[English](../../language/enumerations.md) | Português (Brasil)

O NES Pascal suporta tipos de enumeração definidos pelo usuário para domínios
finitos, como estados de jogo. Uma enumeração é nominal: sua representação de
um byte não a torna intercambiável com `byte` nem com outro tipo de enumeração.

## Declaração e membros

Declare enumerações na seção opcional `type`, antes de `const` e `var`:

```pascal
type
    GameState = (Title, Playing, Paused, GameOver);
```

Os membros são constantes de compilação não qualificadas no namespace do
programa. Eles recebem valores em byte na ordem da declaração: `Title` é `$00`,
`Playing` é `$01`, `Paused` é `$02` e `GameOver` é `$03`. Uma enumeração contém
de um a 256 membros. Nomes são case-insensitive, devem ser únicos e não podem
colidir com outro símbolo no nível do programa.

## Variáveis, atribuições e comparações

```pascal
var
    State: GameState;
    PreviousState: GameState;
    IsGameOver: boolean;

begin
    State := Title;
    PreviousState := State;

    if PreviousState <> Paused then
        State := GameOver;

    IsGameOver := State = GameOver;
end.
```

Variáveis de enumeração ocupam exatamente um byte e seguem a alocação global
determinística normal, incluindo a política opcional existente de promoção para
Zero Page. Membros não ocupam RAM, ROM, Zero Page, tabela de runtime ou
metadados.

Atribuições, igualdade (`=`) e desigualdade (`<>`) exigem exatamente o mesmo
tipo de enumeração. `GameState`, `Direction` e `byte` continuam distintos mesmo
quando seus valores subjacentes coincidem. Comparações produzem booleanos
canônicos; usadas diretamente por `if`, o backend desvia a partir da comparação
em byte.

Não há conversão implícita para ou de `byte`; literais hexadecimais e Booleanos
não podem ser atribuídos a uma enumeração. Aritmética, `inc`/`dec`, comparações
ordenadas, valores numéricos explícitos, constantes de enum em `const`, arrays
de enum, parâmetros de procedimento enum e reflexão em runtime não foram
implementados.

As declarações globais preservam o comportamento existente de memória zerada na
inicialização. Isso corresponde naturalmente ao primeiro membro, mas o
compilador não emite inicialização específica de enumeração; programas ainda
devem respeitar as regras normais de atribuição definida antes da leitura.
