# Constantes e variáveis

[English](../../language/constants-and-variables.md) | Português (Brasil)

## Constantes

Uma declaração de constante possui a seguinte gramática:

```text
Identifier : Type = Literal ;
```

As declarações aparecem em uma seção `const` entre o cabeçalho do programa e o bloco principal:

```pascal
const
    BackgroundColor: nes_color = $21;
```

Toda constante requer um tipo explícito. Constantes de `nes_color` e `byte` utilizam
inicializadores hexadecimais; constantes de `boolean` utilizam `true` ou `false`.
Não há inferência de tipos.

Inicializadores de constantes aceitam apenas literais. Eles não podem referenciar outras
constantes nem conter expressões aritméticas.

## Variáveis

Declarações de variáveis aparecem após a seção opcional `const` e antes das declarações
de procedimentos e do bloco principal:

```pascal
var
    BackgroundColor: nes_color;
    Counter: byte;
    Enabled: boolean;
```

Cada declaração contém exatamente um identificador e um tipo escalar ou de array
fixo explícito. O armazenamento é determinístico. Uma variável global escalar referenciada por pelo menos
três operações do código-fonte é elegível para promoção automática para a Zero Page
na ordem de declaração. Se o espaço de promoção opcional não estiver disponível, ela
recorre à RAM comum (fallback) sem alterar seu símbolo ou comportamento. Outras variáveis
globais e todos os parâmetros de valor de procedimentos utilizam RAM comum. O compilador
reporta um erro antes do link se os temporários obrigatórios ou a RAM comum forem
esgotados. Consulte a [Referência de memória da CPU](../runtime/cpu-memory.md).

Arrays fixos são sempre alocações contíguas na RAM comum. Consulte
[Arrays](arrays.md) para a sintaxe, os tipos de elemento e o custo exato de memória.

## Nomes e declarações duplicadas

Nomes de constantes, variáveis e procedimentos compartilham um único namespace
case-insensitive. Declarações duplicadas são erros. A grafia original é preservada
para diagnósticos.

Parâmetros de procedimentos utilizam um namespace local. Seus nomes devem ser únicos
dentro da declaração e não podem sombrear um símbolo global. Procedimentos diferentes
podem reutilizar o mesmo nome de parâmetro.

Variáveis recebem valores por meio de [atribuições](assignments.md) ou outras instruções
de atualização suportadas; a declaração em si não inicializa a variável.
