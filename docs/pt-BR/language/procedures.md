# Procedimentos

[English](../../language/procedures.md) | Português (Brasil)

Declarações de procedimentos aparecem após as variáveis globais e antes do bloco
principal do programa. Um procedimento sem parâmetros omite parênteses:

```pascal
procedure Initialize;
begin
    Counter := $00;
end;
```

Uma chamada é o nome do procedimento seguido por um ponto e vírgula:

```pascal
begin
    Initialize;
    nes.set_background_color($21);
    nes.run;
end.
```

## Parâmetros de valor

Procedimentos podem declarar um ou mais parâmetros de valor. Cada parâmetro declara
um nome e utiliza `byte` ou `boolean`; ponto e vírgula separa os parâmetros:

```pascal
procedure Initialize(Start: byte; Enabled: boolean);
begin
    Counter := Start;
    RenderingEnabled := Enabled;
end;
```

As chamadas colocam expressões de argumentos separadas por vírgula entre parênteses:

```pascal
Initialize($01 + $02, true);
```

A quantidade e os tipos dos argumentos devem corresponder exatamente à declaração.
E3016 reporta uma contagem incorreta de argumentos, E4004 reporta um tipo de argumento
incompatível e E4005 rejeita tipos de parâmetro diferentes de `byte` e `boolean`.
Parênteses vazios não são válidos: escreva `Reset;` em vez de `Reset();` para uma
declaração ou chamada sem parâmetros.

Os argumentos são avaliados da esquerda para a direita e copiados em slots de RAM
de um byte específicos do procedimento antes do `JSR`. Um parâmetro de valor é
inicializado na entrada e pode ser atribuído ou atualizado dentro do procedimento.
Tais alterações modificam apenas a cópia do procedimento; não há modo de passagem por referência.

Nomes de parâmetros são case-insensitive e devem ser únicos dentro do procedimento.
Eles podem ser reutilizados por procedimentos diferentes, mas não podem sombrear
o nome de uma constante, variável ou procedimento global no milestone atual.

## Resolução de nomes e chamadas

Chamadas são case-insensitive. Constantes, variáveis e procedimentos compartilham
um único namespace global. Parâmetros formam escopos locais específicos de procedimentos.
A assinatura de cada procedimento é registrada antes que qualquer corpo seja analisado,
de modo que um procedimento pode chamar outro declarado posteriormente no código-fonte:

```pascal
procedure Start(Value: byte);
begin
    Initialize(Value);
end;

procedure Initialize(Value: byte);
begin
    Counter := Value;
end;
```

Procedimentos podem chamar outros procedimentos em qualquer profundidade acíclica.
E3013 reporta uma chamada desconhecida. E3014 rejeita recursão direta e indireta.

## Estado global e atribuição definitiva

Todas as variáveis são globais. A análise semântica computa as variáveis que cada
procedimento requer na entrada e aquelas que ele definitivamente atribui. Uma
chamada é rejeitada com E3008 quando uma variável global obrigatória não estiver
atribuída. Variáveis definitivamente atribuídas por um procedimento ficam disponíveis
para as instruções seguintes no chamador. As regras de atribuição de condicionais
e laços permanecem conservadoras através dos limites de procedimentos.

## Convenção de chamada

A convenção básica de chamada utiliza a pilha de hardware do 6502: chamadas armazenam
cada argumento em seu slot de parâmetro estático, geram `JSR`, e todo procedimento
termina com `RTS`. Parâmetros utilizam rótulos como `parameter_Initialize_Value`.
Procedimentos possuem rótulos globais de entrada no ca65 como `procedure_Initialize`;
rótulos de controle de fluxo dentro deles utilizam rótulos locais baratos `@` do ca65.
Registradores não fazem parte da interface da linguagem-fonte e sua preservação não é garantida.

O armazenamento estático de parâmetros é seguro porque a recursão direta e indireta
permanece proibida. Não existem registros de ativação na pilha (stack frame),
variáveis locais gerais, parâmetros por referência ou valores de retorno.

## Restrições de runtime

`nes.run`, `nes.wait_frame` e comandos de registro permanecem exclusivos do bloco principal.
Chamadas de paleta, incluindo `nes.set_background_color`, são permitidas em procedimentos
e preparam alterações para o VBlank. O registro de callback dentro de um procedimento
produz E3022. Procedimentos sem parâmetros podem ser registrados como callback de
atualização ou de VBlank sob as regras em [Callbacks de quadro](../runtime/frame-callbacks.md).
