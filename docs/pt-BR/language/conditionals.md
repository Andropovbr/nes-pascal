# Estruturas condicionais

[English](../../language/conditionals.md) | Português (Brasil)

Uma condição `if` deve ter o tipo `boolean`. Uma condicional pode conter uma instrução:

```pascal
if Enabled then
    Counter := $01;
```

O ramo opcional `else` segue as regras de posicionamento de ponto e vírgula do Pascal.
Não há ponto e vírgula entre a instrução final do ramo `then` e o `else`; um ponto
e vírgula encerra a estrutura condicional completa:

```pascal
if Enabled then
    Counter := $01
else
    Counter := $02;
```

Utilize `begin` e `end` para um ramo contendo múltiplas instruções:

```pascal
if Enabled then
begin
    Counter := Counter + $01;
    Ready := true;
end
else
begin
    Counter := $00;
    Ready := false;
end;
```

Condicionais podem ser aninhadas. Um `else` sem um bloco delimitador pertence ao
`if` não casado mais próximo.

## Atribuição definitiva

A análise de atribuição definitiva segue o fluxo de controle. Uma variável atribuída
em ambos os ramos de um `if/else` é considerada atribuída após a estrutura. Uma
atribuição realizada apenas no ramo `then`, ou em um `if` sem `else`, não é garantida posteriormente.

## Restrições de runtime

[`nes.run`](../runtime/run.md) deve permanecer no bloco principal de nível superior.
Chamadas de paleta dentro de condicionais de runtime são permitidas e preparam
alterações para o VBlank; chamadas de nível superior anteriores a `nes.run` realizam
escritas diretas durante a inicialização.

## Fluxo de controle gerado

O backend emite um desvio relativo próximo seguido por um `JMP` absoluto. Isso mantém
os desvios condicionais válidos mesmo quando o corpo de um ramo excede o alcance de
desvio relativo do 6502.
