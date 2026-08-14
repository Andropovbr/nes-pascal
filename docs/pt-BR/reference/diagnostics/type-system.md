# Diagnósticos do sistema de tipos

[English](../../../reference/diagnostics/type-system.md) | Português (Brasil)

Diagnósticos do sistema de tipos utilizam o intervalo E4000-E4999.

## E4001 - Tipo desconhecido

- **Categoria:** Type System
- **Explicação:** Uma declaração especifica um tipo não fornecido pela linguagem implementada.
- **Gatilho:**

  ```pascal
  Counter: word;
  ```

- **Saída esperada do compilador:**

  ```text
  E4001 demo.nsp:1:10

  Unknown type: word.
  ```

- **Correção sugerida:** Utilize `nes_color`, `byte`, `boolean`, `sprite` ou `metasprite`.

## E4002 - Valor inválido para `nes_color`

- **Categoria:** Type System
- **Explicação:** Valores de `nes_color` são limitados ao intervalo de paleta do NES
  `$00..$3F` em declarações, atribuições e em todas as APIs de paleta.
- **Gatilho:**

  ```pascal
  BackgroundColor := $80;
  ```

- **Saída esperada do compilador:**

  ```text
  E4002 demo.nsp:1:20

  Value $80 is not valid for type nes_color.

  Allowed range: $00..$3F.
  ```

- **Correção sugerida:** Utilize um valor hexadecimal de `$00` até `$3F`.

## E4003 - Valor inválido para `byte`

- **Categoria:** Type System
- **Explicação:** Um `byte` ocupa um byte e não pode representar valores acima de `$FF`.
- **Gatilho:**

  ```pascal
  Counter := $100;
  ```

- **Saída esperada do compilador:**

  ```text
  E4003 demo.nsp:1:12

  Value $100 is not valid for type byte.

  Allowed range: $00..$FF.
  ```

- **Correção sugerida:** Utilize um valor hexadecimal de `$00` até `$FF`.

## E4004 - Tipos incompatíveis

- **Categoria:** Type System
- **Explicação:** Atribuições e argumentos de intrínsecos exigem correspondência exata
  de tipos. Conversões numérico-para-booleano e outras conversões implícitas são proibidas.
  Expressões aritméticas e seus operandos devem ter o tipo `byte`. Operandos de comparação
  devem seguir as regras de tipos do operador de comparação, e operadores booleanos
  exigem operandos `boolean`. Alvos e quantidades de incremento/decremento, além de variáveis
  de controle e limites de `for`, devem ter o tipo `byte`. Argumentos de procedimentos
  devem corresponder exatamente aos tipos de parâmetros `byte` ou `boolean` correspondentes.
- **Gatilho:**

  ```pascal
  Counter := Active;
  ```

- **Saída esperada do compilador:**

  ```text
  E4004 demo.nsp:1:12

  Cannot assign a value of type boolean to variable Counter of type byte.

  The source and target types must match.
  ```

- **Correção sugerida:** Utilize um valor de origem com exatamente o tipo de destino.
  Utilize `true` ou `false` para um literal booleano e use aritmética apenas com valores
  de `byte`. Compare tipos correspondentes e use `not`, `and` e `or` apenas com valores `boolean`.

## E4005 - Tipo de parâmetro não suportado

- **Categoria:** Type System
- **Explicação:** A convenção atual de chamada de parâmetros de valor suporta apenas
  `byte` e `boolean`. Embora `nes_color`, `sprite` e `metasprite` continuem tipos globais
  válidos, eles ainda não podem ser usados para um parâmetro.
- **Gatilho:**

  ```pascal
  procedure SetColor(Color: nes_color);
  begin
  end;
  ```

- **Saída esperada do compilador:**

  ```text
  E4005 demo.nsp:1:27

  Type nes_color is not supported for procedure parameters.
  ```

- **Correção sugerida:** Declare o parâmetro de valor como `byte` ou `boolean`, ou
  mantenha um valor `nes_color` no estado global.

## E4006 - Tipo de argumento de controle inválido

- **Categoria:** Type System
- **Explicação:** Os argumentos de índice de controle e de botão descrevem valores
  `byte` em tempo de compilação. Valores booleanos não podem selecionar uma porta ou botão.
- **Gatilho:** `nes.controller_down(true, nes.button_a)` ou um argumento booleano de botão.
- **Saída esperada do compilador:** `E4006` identifica o argumento e seu tipo real.
- **Correção sugerida:** Passe `$01` ou `$02` como controle e exatamente uma constante
  `nes.button_*` como botão.

## E4007 - Tipo de argumento de paleta inválido

- **Categoria:** Type System
- **Explicação:** Índices de paleta e de cor exigem valores `byte` em tempo de compilação,
  enquanto argumentos de cor exigem `nes_color`. Nenhuma conversão implícita é realizada.
- **Gatilho:** Passar um índice booleano ou uma variável `byte` como cor de paleta.
- **Saída esperada do compilador:** `E4007` identifica o argumento, tipo real e tipo exigido.
- **Correção sugerida:** Utilize uma constante `byte` para índices e um valor `nes_color`
  atribuído para cores.

## E4008 - Valor inválido para `sprite`

- **Categoria:** Type System
- **Explicação:** Um `sprite` é um índice de OAM de hardware fortemente tipado e deve
  selecionar uma das 64 entradas do NES.
- **Gatilho:** Compilar `tests/fixtures/diagnostics/invalid_sprite_value.nsp`, ou declarar
  ou atribuir um valor `sprite` acima de `$3F`.
- **Saída esperada do compilador:** `E4008` identifica o literal inválido e o intervalo
  suportado `$00..$3F`.
- **Correção sugerida:** Utilize um índice de sprite de `$00` até `$3F`.

## E4009 - Valor inválido para `metasprite`

- **Categoria:** Type System
- **Explicação:** Um `metasprite` é uma identidade de instância estática opaca. Um
  número hexadecimal não é uma instância de metasprite ou quadro simbólico.
- **Gatilho:** Compilar `tests/fixtures/diagnostics/invalid_metasprite_value.nsp`, que
  atribui um literal hexadecimal a uma variável `metasprite`.
- **Saída esperada do compilador:** `E4009` rejeita o literal sem convertê-lo para uma
  identidade de instância.
- **Correção sugerida:** Atribua o resultado de `nes.metasprite_create(imported.frame)` à variável.

## E4010 - Tipo de elemento de array inválido

- **Categoria:** Type System
- **Explicação:** Arrays fixos suportam `byte`, `boolean` ou um record declarado
  como tipo de elemento.
- **Gatilho:** Declarar `array[$00..$03] of nes_color`.
- **Correção sugerida:** Use `byte`, `boolean` ou um record declarado como tipo
  do elemento.

## E4011 - Tipo de índice de array inválido

- **Categoria:** Type System
- **Explicação:** Um índice de array deve ser uma expressão estrita de tipo
  `byte`.
- **Gatilho:** Indexar um array com um valor `boolean`.
- **Correção sugerida:** Use uma variável, literal, constante ou expressão
  aritmética de tipo `byte`.

## E4012 - Índice de array fora dos limites

- **Categoria:** Type System
- **Explicação:** Um índice conhecido em tempo de compilação está fora do
  intervalo inclusivo declarado para o array.
- **Gatilho:** Ler ou escrever `Values[$08]` quando `Values` foi declarado como
  `array[$00..$07] of byte`.
- **Correção sugerida:** Use um índice constante dentro dos limites declarados.
  Índices variáveis continuam sendo responsabilidade do programa em runtime.

## E4013 - Uso inválido de array

- **Categoria:** Type System
- **Explicação:** Uma variável escalar foi indexada, ou um array foi usado ou
  atribuído como um valor escalar inteiro.
- **Gatilho:** Compilar `Counter[$00] := $01` ou `Counter := Values`.
- **Correção sugerida:** Indexe um array declarado e leia ou escreva um único
  elemento.

## E4014 - Limites de array inválidos

- **Categoria:** Type System
- **Explicação:** Arrays usam um intervalo de byte iniciado em zero, com limite
  inferior `$00` e superior não maior que `$FF`.
- **Gatilho:** Declarar `array[$01..$04] of byte`.
- **Correção sugerida:** Declare um intervalo como
  `array[$00..$03] of byte`.

## E4015 - Membro de enumeração duplicado

- **Categoria:** Type System
- **Explicação:** Todo nome de membro dentro de uma enumeração deve ser único.
- **Gatilho:** Declarar `GameState = (Title, Playing, Title)`.
- **Correção sugerida:** Renomeie ou remova o membro repetido.

## E4016 - Membros de enumeração em excesso

- **Categoria:** Type System
- **Explicação:** Valores enum ocupam um byte e podem representar no máximo 256
  membros.
- **Gatilho:** Declarar uma enumeração com 257 membros.
- **Correção sugerida:** Reduza a declaração para 256 membros ou menos.

## E4017 - Comparação de enumeração inválida

- **Categoria:** Type System
- **Explicação:** Enumerações expõem igualdade e desigualdade, não ordenação ordinal.
- **Gatilho:** Compilar `State < Playing` para uma variável enum.
- **Correção sugerida:** Use `=` ou `<>`, ou modele uma ordenação necessária com
  `byte`.

## E4018 - Membro de enumeração desconhecido

- **Categoria:** Type System
- **Explicação:** Um valor esperado como membro de enum não foi declarado por
  essa enumeração.
- **Gatilho:** Atribuir `Missing` a uma variável `GameState`.
- **Correção sugerida:** Use um membro declarado pelo tipo enum de destino.

## E4019 - Campo duplicado em record

- **Categoria:** Sistema de Tipos
- **Explicação:** Os nomes de campos devem ser únicos dentro de um record,
  seguindo as regras case-insensitive da linguagem.
- **Gatilho:** Compile
  `tests/fixtures/diagnostics/duplicate_record_field.nsp`.
- **Correção sugerida:** Renomeie ou remova o campo repetido.

## E4020 - Campo de record desconhecido

- **Categoria:** Sistema de Tipos
- **Explicação:** O campo selecionado não foi declarado pelo tipo record.
- **Gatilho:** Compile
  `tests/fixtures/diagnostics/unknown_record_field.nsp`.
- **Correção sugerida:** Selecione um campo declarado pelo record de destino.

## E4021 - Acesso a campo em valor que não é record

- **Categoria:** Sistema de Tipos
- **Explicação:** A seleção de campo com ponto exige uma variável record ou um
  elemento de array de records.
- **Gatilho:** Compile
  `tests/fixtures/diagnostics/field_access_on_non_record.nsp`.
- **Correção sugerida:** Remova o seletor de campo ou use um valor record
  declarado.

## E4022 - Tipo de campo de record não suportado

- **Categoria:** Sistema de Tipos
- **Explicação:** Campos de records atualmente aceitam apenas `byte`, `boolean`
  e tipos de enumeração declarados. Arrays e records aninhados não são campos
  nesta milestone.
- **Gatilho:** Compile
  `tests/fixtures/diagnostics/unsupported_record_field_type.nsp`.
- **Correção sugerida:** Armazene os dados aninhados separadamente ou use um
  tipo de campo de um byte suportado.

## E4023 - Definição recursiva de record

- **Categoria:** Sistema de Tipos
- **Explicação:** Um record não pode conter a si mesmo diretamente. Layouts
  recursivos não têm tamanho estático finito.
- **Gatilho:** Compile
  `tests/fixtures/diagnostics/recursive_record_definition.nsp`.
- **Correção sugerida:** Remova o campo recursivo e armazene um identificador
  ou índice explícito em byte.

## E4024 - Layout ou offset indexado de record inválido

- **Categoria:** Sistema de Tipos
- **Explicação:** Um record está vazio ou excede o layout suportado de 256
  bytes, ou um acesso variável a array de records pode exigir um offset acima
  de `$FF` e sofrer truncamento no endereçamento indexado do 6502.
- **Gatilho:** Declare um record vazio, um record com mais de 256 campos de um
  byte ou indexe por variável um array de records suficientemente grande.
- **Correção sugerida:** Use um layout fixo suportado, reduza o tamanho, divida
  o array ou use um índice constante em tempo de compilação.

## E4025 - Uso inválido de record

- **Categoria:** Sistema de Tipos
- **Explicação:** Records são agregados estáticos, não valores de expressão
  completos na milestone 0.5.10.
- **Gatilho:** Compile
  `tests/fixtures/diagnostics/invalid_record_usage.nsp`.
- **Correção sugerida:** Leia, atribua ou compare os campos tipados
  individualmente.
