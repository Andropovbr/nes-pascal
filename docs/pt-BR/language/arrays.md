# Arrays

[English](../../language/arrays.md) | Português (Brasil)

NES Pascal suporta arrays globais unidimensionais de tamanho fixo. Arrays são
armazenamento estático administrado pelo compilador: não há heap, descritor,
campo de comprimento, alocador em tempo de execução ou runtime genérico.

## Declaração

Os limites usam os literais hexadecimais de byte da linguagem:

```pascal
var
    Values: array[$00..$0F] of byte;
    Flags: array[$00..$07] of boolean;
```

O limite inferior é sempre `$00`. O limite superior inclusivo pode ser de
`$00` a `$FF`, portanto uma declaração contém entre 1 e 256 elementos. Apenas
elementos `byte` e `boolean` são suportados. Arrays podem ser declarados somente
na seção global `var`; não podem ser constantes, variáveis locais, parâmetros
ou valores de retorno.

Cada elemento ocupa um byte. Elementos booleanos usam o mesmo armazenamento
canônico dos booleanos escalares: `false` é `$00` e `true` é `$01`. Arrays
booleanos não usam compactação por bits. Consequentemente:

- `array[$00..$0F] of byte` consome exatamente 16 bytes de RAM;
- `array[$00..$07] of boolean` consome exatamente 8 bytes de RAM.

O compilador aloca cada array como um intervalo determinístico e contíguo na
RAM comum e mostra o intervalo e o tipo no mapa de memória gerado. Arrays não
são promovidos automaticamente para a Zero Page.

## Leitura e escrita de elementos

Um elemento de array é uma expressão tipada com o tipo do elemento:

```pascal
Values[$00] := $10;
Values[Index] := Counter + $01;
Counter := Values[Index] + $01;

Flags[$00] := true;
if Flags[Index] then
    Counter := Counter + $01;
```

O índice deve ter tipo `byte`; índices `boolean` e conversões implícitas são
rejeitados. Atribuições também exigem correspondência exata com o tipo do
elemento.

Uma atribuição indexada avalia o índice antes do valor. Para um índice variável,
o backend preserva esse índice na pilha de hardware enquanto avalia o valor e
então usa endereçamento indexado nativo do 6502. Isso não reserva um byte de
Zero Page específico para arrays.

Como ocorre com variáveis escalares, ler um array antes de qualquer atribuição
anterior a um elemento é rejeitado pela análise de atribuição definida. O
compilador não tenta provar a inicialização elemento a elemento; o programa
continua responsável por atribuir cada elemento que lerá depois.

## Verificação de limites e endereçamento

Um índice constante, incluindo uma expressão constante de byte que o compilador
consiga avaliar, é verificado em tempo de compilação contra os limites
declarados. Um acesso conhecido fora do intervalo produz E4012. O endereço do
elemento é então calculado em tempo de compilação, por exemplo:

```asm
    lda variable_Values + 3
```

Um índice `byte` não constante não é verificado em tempo de execução. Ele
normalmente usa endereçamento absoluto indexado nativo:

```asm
    lda variable_Index
    tax
    lda variable_Values,x
```

Os programas devem garantir que índices variáveis permaneçam dentro do
intervalo declarado. Não há metadados de limites em runtime nem rotina gerada
para verificá-los.

## Limitações atuais

Arrays dinâmicos, abertos, multidimensionais, locais, usados como parâmetro ou
retorno, de records e compactados por bits não são suportados. Arrays não podem
ser atribuídos ou comparados como valores inteiros, e não há ponteiros nem
operações de fatia.
