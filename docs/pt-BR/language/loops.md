# Laços de repetição

[English](../../language/loops.md) | Português (Brasil)

O NES Pascal suporta laços `while`, `repeat`/`until` e `for` ascendentes ou descendentes.
Laços podem ser aninhados.

## `while`

`while` verifica uma condição `boolean` antes de cada iteração:

```pascal
while Counter < Limit do
    Counter := Counter + $01;
```

Um corpo composto utiliza `begin` e `end`:

```pascal
while Running do
begin
    Counter := Counter + $01;
    Running := Counter < Limit;
end;
```

## `repeat` / `until`

`repeat` executa seu corpo antes de verificar sua condição `boolean`, portanto o
corpo é executado pelo menos uma vez:

```pascal
repeat
    Counter := Counter - $01;
until Counter = $00;
```

## `for`

Um laço `for` ascendente inclui ambos os limites:

```pascal
for Index := $00 to $03 do
    inc(Total);
```

Um laço descendente utiliza `downto`:

```pascal
for Index := $03 downto $00 do
begin
    inc(Total, $02);
end;
```

A variável de controle, a expressão inicial e a expressão final devem todas ter o
tipo `byte`. O compilador atribui o valor inicial antes de avaliar e armazenar em cache
o valor final. A expressão final é avaliada exatamente uma vez. O corpo pode ser uma
única instrução ou um bloco `begin`/`end`, e laços `for` podem ser aninhados.

A variável de controle é definitivamente atribuída após o laço, mesmo quando o
intervalo inicial está vazio, pois a inicialização ocorre antes da primeira verificação
de intervalo. Um laço não vazio que termina normalmente a deixa com o valor final;
um intervalo vazio a deixa com o valor inicializado. Atribuir à variável de controle,
aplicar `inc` ou `dec` a ela, ou reutilizá-la como variável de controle de um laço
aninhado produz E3012.

As verificações de término ocorrem antes do incremento ou decremento, de modo que
`$FF` para `to` e `$00` para `downto` terminam sem dar a volta (wrap) para outra iteração.

## `break` e `continue`

`break` sai do laço mais interno. `continue` transfere o controle para a próxima
verificação de condição do laço mais interno. Em um laço `for`, `continue` avança
para o próximo valor da variável de controle.

```pascal
while Counter < Limit do
begin
    Counter := Counter + $01;
    if Counter = SkipValue then
        continue;
    if Counter = StopValue then
        break;
end;
```

Utilizar qualquer uma das instruções fora de um laço produz E3010. Em laços aninhados,
`break` e `continue` sempre têm como alvo o laço mais interno.

## Atribuição definitiva

A análise de atribuição definitiva é intencionalmente conservadora. Atribuições
feitas apenas dentro de um laço não são consideradas garantidas após o laço,
porque o corpo de um `while` pode não ser executado e o controle de fluxo do laço
pode pular instruções. Atribua valores antes de entrar em um laço quando eles forem
necessários posteriormente ou em uma condição de `repeat`.

A variável de controle do `for` é a exceção: sua inicialização é garantida antes
da primeira verificação de intervalo.

## Restrições de runtime

`nes.run` não pode ser colocado dentro de laços. Laços podem ser executados durante
a inicialização ou após `nes.run`; chamadas de paleta após o início do runtime
enfileiram atualizações limitadas de VBlank. Um laço no bloco principal pode usar
`nes.wait_frame` para sincronizar cada iteração com uma NMI distinta:

```pascal
nes.run;
while Running do
begin
    nes.wait_frame;
    inc(Frames);
end;
```

O corpo do laço permanece código comum da thread principal; a NMI não o executa.

## Fluxo de controle gerado

O backend utiliza saltos absolutos para os retornos e saídas de laço, com desvios
relativos direcionados apenas a rótulos próximos. Corpos de laço grandes e aninhados,
portanto, não dependem do limite de alcance de desvio relativo do 6502. O mesmo padrão
de desvio próximo e salto absoluto mantém válidos os corpos grandes de `for`.
