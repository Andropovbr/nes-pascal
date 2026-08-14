# Expressões

[English](../../language/expressions.md) | Português (Brasil)

## Expressões aritméticas

A aritmética é definida apenas para valores de `byte`. Os operandos podem ser
literais hexadecimais, constantes de `byte`, variáveis de `byte` previamente
atribuídas, campos `byte` de [records](records.md) previamente atribuídos ou
expressões aritméticas aninhadas.

Operadores suportados:

- `+` unário, que mantém o valor inalterado;
- `-` unário, que calcula a negação em complemento de dois;
- `+` binário;
- `-` binário.

Parênteses agrupam expressões. Operadores unários possuem maior precedência do que
operadores binários. Os operadores binários `+` e `-` possuem igual precedência
e associam da esquerda para a direita:

```pascal
Counter := $08 - $03 + $01;
Result := -(Counter + Step);
```

Todos os resultados sofrem wrap módulo 256. Por exemplo, `$FF + $01` produz `$00`,
e `$00 - $01` produz `$FF`. Esse comportamento reflete diretamente a aritmética de
um byte do 6502.

Expressões aritméticas sempre possuem o tipo `byte`. Elas não podem ser atribuídas
a `nes_color` ou `boolean`, e esses tipos não podem ser usados como operandos.
O compilador reporta E4004 para esses usos incompatíveis.

Declarações de constantes aceitam apenas literais; seus inicializadores não podem
conter expressões aritméticas.

## Comparações

Toda comparação produz um valor `boolean` normalizado: `$00` para `false` ou
`$01` para `true`.

Igualdade e desigualdade utilizam `=` e `<>`. Ambos os operandos devem ter
exatamente o mesmo tipo. Eles suportam `byte`, `nes_color`, `boolean` e valores da
mesma [enumeração](enumerations.md) definida pelo usuário:

```pascal
Equal := Counter = Limit;
Different := BackgroundColor <> $0F;
SameState := Enabled = true;
```

Comparações ordenadas utilizam `<`, `>`, `<=` e `>=`. Elas aceitam apenas operandos
de `byte` e utilizam ordenação sem sinal de um byte:

```pascal
BelowLimit := Counter < Limit;
AtLeastOne := Counter >= $01;
```

Comparar tipos diferentes produz E4004. Comparações ordenadas de enumerações
produzem E4017; valores enum expõem apenas igualdade e desigualdade.

Campos de records participam conforme seu tipo escalar ou enum declarado.
Records inteiros não podem ser comparados; compare campos individuais.

## Expressões booleanas

Os operadores `not`, `and` e `or` aceitam apenas operandos `boolean` e produzem
um resultado `boolean` normalizado:

```pascal
Ready := Enabled and not Paused;
InRange := (Counter >= Minimum) and (Counter <= Maximum);
```

`and` e `or` são avaliados da esquerda para a direita e realizam avaliação de
curto-circuito (short-circuit). O operando direito de `and` é ignorado quando o
operando esquerdo é `false`; o operando direito de `or` é ignorado quando o operando
esquerdo é `true`.

As consultas de controle `nes.controller_down`, `nes.controller_pressed` e
`nes.controller_released` são expressões booleanas embutidas. Elas aceitam um índice
de controle em tempo de compilação e exatamente uma constante `nes.button_*`.
Consulte [Entrada de controle](../runtime/controller-input.md) para a semântica
de transição de quadros e a lista completa de botões.

## Precedência

A precedência de expressões, da mais alta para a mais baixa, é:

1. parênteses;
2. `+` unário, `-` unário e `not`;
3. `+` e `-` binários;
4. comparações;
5. `and`;
6. `or`.

Utilize parênteses para negar uma comparação:

```pascal
Different := not (Counter = Limit);
```
