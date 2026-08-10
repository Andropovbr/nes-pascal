# Incremento e decremento

[English](../../language/increment-and-decrement.md) | Português (Brasil)

`inc` e `dec` atualizam uma variável `byte` inicializada. As formas de um argumento
adicionam ou subtraem um:

```pascal
inc(Counter);
dec(Counter);
```

Uma expressão opcional de `byte` especifica a quantidade:

```pascal
inc(Counter, Step);
dec(Counter, Step + $01);
```

As atualizações sofrem wrap módulo 256, assim como as demais operações aritméticas
de `byte`. Incrementar `$FF` produz `$00`; decrementar `$00` produz `$FF`. As formas
de um argumento geram as instruções `INC` e `DEC` do 6502 diretamente.

O alvo já deve estar atribuído, pois a atualização lê seu valor anterior. O alvo e
a quantidade opcional devem ter o tipo `byte`; usos incompatíveis produzem E4004.

Um parâmetro de valor de `byte` inicializado pode ser usado como alvo. A atualização
modifica apenas a cópia local do parâmetro no procedimento.

A variável de controle de um laço `for` não pode ser alterada com `inc` ou `dec` dentro
do corpo daquele laço. Consulte [laços `for`](loops.md#for).
