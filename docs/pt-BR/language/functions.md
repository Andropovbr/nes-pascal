# Funções

[English](../../language/functions.md) | Português (Brasil)

Funções são rotinas nomeadas e alocadas estaticamente que retornam um valor
`byte` ou `boolean`. As declarações aparecem junto dos procedimentos depois da
seção global `var` e antes do bloco principal.

```pascal
function Add(Left: byte; Right: byte): byte;
begin
    Add := Left + Right;
end;

function Ready(Value: byte): boolean;
begin
    Ready := Value >= $10;
end;
```

Os parâmetros são passados por valor e podem ser `byte` ou `boolean`. Uma
declaração sem parâmetros omite a lista; toda chamada usa parênteses, inclusive
sem parâmetros:

```pascal
function CurrentScore: byte;
begin
    CurrentScore := Score;
end;

Score := Add(CurrentScore(), $01);
```

O nome da função é o alvo do resultado e precisa receber um valor do tipo
declarado em todos os caminhos que chegam ao fim. Não há `return` antecipado.

## Ordem de avaliação

Argumentos são avaliados da esquerda para a direita. `and` e `or` mantêm o
curto-circuito da esquerda para a direita. Em aritmética e comparações, um lado
direito simples é consumido depois do esquerdo; quando o lado direito exige
avaliação, ele é avaliado primeiro e preservado. Assim,
`LeftCall() - RightCall()` executa `RightCall()` primeiro.

## Convenção de chamada e limites

Parâmetros usam a convenção estática em RAM comum dos procedimentos. O retorno
é carregado no acumulador `A` antes de `RTS`. Cada função recebe um byte
explícito em RAM comum para o resultado; programas sem funções não alocam esse
armazenamento, segmento ou código.

Chamadas podem alterar `A`, `X`, `Y` e os flags do processador. Nenhum
registrador de uso geral é preservado pelo chamado; somente temporários
gerenciados pelo compilador e os locais estáticos de parâmetros/resultados
transportam valores através da chamada. Os endereços de retorno de `JSR` usam a
pilha de hardware reservada, novamente balanceada por `RTS`.

O compilador analisa o grafo acíclico completo e preserva temporários do
chamador e argumentos anteriores durante chamadas aninhadas. Recursão direta,
indireta e ciclos mistos são rejeitados com `E3014`. Não há variáveis locais,
frames de runtime, parâmetros por referência, argumentos padrão, sobrecarga ou
retornos agregados. Funções não podem ser callbacks de quadro.

Veja o [exemplo de funções](../../../examples/functions.nsp).
