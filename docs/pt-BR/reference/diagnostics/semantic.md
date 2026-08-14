# Diagnósticos semânticos

[English](../../../reference/diagnostics/semantic.md) | Português (Brasil)

Diagnósticos de análise semântica utilizam o intervalo E3000-E3999.

## E3001 - `nes.run` ausente

- **Categoria:** Semantic Analysis
- **Explicação:** Um programa válido deve iniciar o runtime com exatamente uma
  instrução `nes.run` incondicional de nível superior.
- **Gatilho:**

  ```pascal
  begin
      nes.set_background_color($21);
  end.
  ```

- **Saída esperada do compilador:**

  ```text
  E3001 demo.nsp:4:1

  The program must start the runtime with nes.run.
  ```

- **Correção sugerida:** Adicione uma instrução `nes.run;` de nível superior após a inicialização
  e antes de qualquer instrução `nes.wait_frame`.

## E3002 - Instrução após `nes.run`

- **Categoria:** Semantic Analysis
- **Explicação:** Instruções comuns da thread principal, incluindo atualizações de paleta
  enfileiradas, podem seguir `nes.run`, mas chamadas adicionais a `nes.run` não são permitidas.
- **Gatilho:**

  ```pascal
  nes.run;
  nes.run;
  ```

- **Saída esperada do compilador:**

  ```text
  E3002 demo.nsp:2:1

  nes.run may appear only once.
  ```

- **Correção sugerida:** Remova a chamada duplicada a `nes.run`.

## E3003 - Contagem inválida de chamadas de cor de fundo

- **Categoria:** Semantic Analysis
- **Explicação:** Um programa válido requer exatamente uma chamada de inicialização para
  `nes.set_background_color` antes de `nes.run`. Chamadas enfileiradas posteriores são permitidas.
- **Gatilho:**

  ```pascal
  begin
      nes.run;
  end.
  ```

- **Saída esperada do compilador:**

  ```text
  E3003 demo.nsp:3:1

  The program must set its initial background color exactly once.
  ```

- **Correção sugerida:** Adicione uma chamada `nes.set_background_color(value);` antes de `nes.run`.

## E3004 - Símbolo duplicado

- **Categoria:** Semantic Analysis
- **Explicação:** Constantes, variáveis e procedimentos compartilham um namespace
  case-insensitive. Nomes de parâmetros são case-insensitive dentro de um procedimento e não
  podem sombrear um símbolo global.
- **Gatilho:**

  ```pascal
  var
      Color: byte;
      COLOR: byte;
  ```

- **Saída esperada do compilador:**

  ```text
  E3004 demo.nsp:3:5

  Symbol COLOR is already declared.
  ```

- **Correção sugerida:** Utilize um nome único no escopo atual. Renomeie um parâmetro se ele
  duplicar outro parâmetro ou um símbolo global.

## E3005 - Identificador desconhecido

- **Categoria:** Semantic Analysis
- **Explicação:** Uma expressão de valor referencia um nome que não foi declarado.
- **Gatilho:**

  ```pascal
  Counter := Missing;
  ```

- **Saída esperada do compilador:**

  ```text
  E3005 demo.nsp:1:12

  Unknown identifier: Missing.
  ```

- **Correção sugerida:** Declare a constante ou variável referenciada antes do uso.

## E3006 - Atribuição a constante

- **Categoria:** Semantic Analysis
- **Explicação:** Constantes não podem ser modificadas após a declaração.
- **Gatilho:**

  ```pascal
  Maximum := $10;
  ```

- **Saída esperada do compilador:**

  ```text
  E3006 demo.nsp:1:1

  Cannot assign to constant Maximum.
  ```

- **Correção sugerida:** Atribua o valor a uma variável em vez disso.

## E3007 - Alvo de atribuição desconhecido

- **Categoria:** Semantic Analysis
- **Explicação:** O lado esquerdo de uma atribuição não é uma variável declarada.
- **Gatilho:**

  ```pascal
  Missing := $01;
  ```

- **Saída esperada do compilador:**

  ```text
  E3007 demo.nsp:1:1

  Unknown variable: Missing.
  ```

- **Correção sugerida:** Declare o alvo na seção `var`.

## E3008 - Variável lida antes da atribuição

- **Categoria:** Semantic Analysis
- **Explicação:** O valor de uma variável é lido antes que uma instrução anterior o
  atribua, ou um procedimento é chamado antes que as variáveis globais necessárias tenham sido atribuídas.
- **Gatilho:**

  ```pascal
  var
      BackgroundColor: nes_color;
  begin
      nes.set_background_color(BackgroundColor);
  ```

- **Saída esperada do compilador:**

  ```text
  E3008 demo.nsp:4:30

  Variable BackgroundColor is read before it is assigned.

      nes.set_background_color(BackgroundColor);
                               ^^^^^^^^^^^^^^^
  ```

- **Correção sugerida:** Atribua a variável antes de lê-la ou antes de chamar um procedimento que a exija.

## E3009 - Comando de runtime dentro de condicional

- **Categoria:** Semantic Analysis
- **Explicação:** `nes.run` deve ser executado exatamente uma vez no bloco principal de
  nível superior e não pode ser colocado em um caminho de execução condicional. Chamadas de
  paleta são permitidas e enfileiram alterações após o início do runtime.
- **Gatilho:**

  ```pascal
  if Enabled then
      nes.run;
  ```

- **Saída esperada do compilador:**

  ```text
  E3009 demo.nsp:2:5

  nes.run cannot appear inside a conditional branch.
  ```

- **Correção sugerida:** Mova o comando de runtime do NES para fora da condicional e coloque-o
  no bloco principal de nível superior.

## E3010 - Controle de laço fora de laço

- **Categoria:** Semantic Analysis
- **Explicação:** `break` e `continue` necessitam de um laço `while`, `repeat` ou `for`
  delimitador que forneça seu alvo de controle de fluxo.
- **Gatilho:**

  ```pascal
  begin
      break;
  end.
  ```

- **Saída esperada do compilador:**

  ```text
  E3010 demo.nsp:2:5

  break can appear only inside a loop.
  ```

- **Correção sugerida:** Mova a instrução para dentro de um laço ou remova-a.

## E3011 - Comando de runtime dentro de laço

- **Categoria:** Semantic Analysis
- **Explicação:** `nes.run` deve ser executado exatamente uma vez e não pode ser repetido
  por um laço. Chamadas de paleta são permitidas e enfileiram alterações após o início do runtime.
- **Gatilho:**

  ```pascal
  while Running do
      nes.run;
  ```

- **Saída esperada do compilador:**

  ```text
  E3011 demo.nsp:2:5

  nes.run cannot appear inside a loop body.
  ```

- **Correção sugerida:** Mova o comando de runtime do NES para fora do laço e para o bloco
  principal de nível superior.

## E3012 - Modificação da variável de controle do for

- **Categoria:** Semantic Analysis
- **Explicação:** Um laço `for` detém sua variável de controle enquanto seu corpo está em
  execução. Atribuir a ela, atualizá-la com `inc` ou `dec`, ou reutilizá-la como a variável
  de controle de um `for` aninhado tornaria o término do laço imprevisível.
- **Gatilho:**

  ```pascal
  for Index := $00 to $03 do
      Index := $01;
  ```

- **Saída esperada do compilador:**

  ```text
  E3012 demo.nsp:2:5

  For control variable Index cannot be modified inside its loop body.
  ```

- **Correção sugerida:** Remova a modificação, use uma variável diferente no corpo ou
  atualize a variável de controle após o laço.

## E3013 - Procedimento desconhecido

- **Categoria:** Semantic Analysis
- **Explicação:** Uma chamada direta de procedimento deve resolver para um procedimento
  declarado. Todas as declarações de procedimentos aparecem antes do bloco principal, mas
  sua ordem relativa não restringe chamadas.
- **Gatilho:**

  ```pascal
  begin
      Missing;
  end.
  ```

- **Saída esperada do compilador:**

  ```text
  E3013 demo.nsp:2:5

  Unknown procedure: Missing.
  ```

- **Correção sugerida:** Declare o procedimento antes do bloco principal do programa ou
  corrija a grafia da chamada.

## E3014 - Ciclo recursivo entre rotinas

- **Categoria:** Semantic Analysis
- **Explicação:** A convenção de chamada suporta procedimentos e funções
  aninhados de forma acíclica, mas não suporta recursão direta, indireta ou mista.
- **Gatilho:**

  ```pascal
  procedure Again;
  begin
      Again;
  end;
  ```

- **Saída esperada do compilador:**

  ```text
  E3014 demo.nsp:4:5

  Recursive procedure call involving Again is not supported.
  ```

- **Correção sugerida:** Remova o ciclo de chamadas recursivas e expresse o trabalho
  repetido com um laço suportado.

## E3015 - Comando de runtime dentro de rotina

- **Categoria:** Semantic Analysis
- **Explicação:** `nes.run` pertence à sequência principal de inicialização e `nes.wait_frame`
  depende da fase conhecida de runtime do bloco principal. Chamadas de paleta são permitidas
  em procedimentos e funções e publicam alterações para o VBlank. A restrição vale para
  ambos os tipos de rotina.
- **Gatilho:**

  ```pascal
  procedure WaitInsideProcedure;
  begin
      nes.wait_frame;
  end;
  ```

- **Saída esperada do compilador:**

  ```text
  E3015 demo.nsp:4:5

  nes.wait_frame cannot appear inside a procedure.
  ```

- **Correção sugerida:** Mova o comando de runtime para o bloco principal do programa.

## E3016 - Contagem incorreta de argumentos de procedimento

- **Categoria:** Semantic Analysis
- **Explicação:** Cada chamada de procedimento deve fornecer exatamente um argumento
  para cada parâmetro de valor declarado. Procedimentos sem parâmetros continuam usando
  uma chamada direta sem parênteses.
- **Gatilho:**

  ```pascal
  procedure Initialize(Value: byte);
  begin
  end;

  begin
      Initialize;
  end.
  ```

- **Saída esperada do compilador:**

  ```text
  E3016 demo.nsp:7:5

  Procedure Initialize expects 1 argument(s), but 0 were provided.
  ```

- **Correção sugerida:** Passe exatamente a quantidade declarada de argumentos, na mesma
  ordem que os parâmetros.

## E3017 - Espera de quadro antes do início do runtime

- **Categoria:** Semantic Analysis
- **Explicação:** `nes.wait_frame` observa um contador alterado pela NMI. Antes de `nes.run`,
  a NMI está desabilitada e a espera nunca seria concluída.
- **Gatilho:** Compilar `tests/fixtures/diagnostics/frame_wait_before_run.nsp`, ou escrever:

  ```pascal
  nes.set_background_color($21);
  nes.wait_frame;
  nes.run;
  ```

- **Saída esperada do compilador:**

  ```text
  E3017 frame_wait_before_run.nsp:4:5

  nes.wait_frame cannot execute before nes.run starts NMI.
  ```

- **Correção sugerida:** Mova `nes.wait_frame` e seu laço de quadros para depois da chamada
  incondicional de nível superior `nes.run`.

## E3018 - Procedimento de callback desconhecido

- **Categoria:** Semantic Analysis
- **Explicação:** Um registro de callback referencia um procedimento que não foi declarado.
- **Gatilho:** `nes.on_update(Missing);`
- **Saída esperada do compilador:**

  ```text
  E3018 demo.nsp:4:19

  Unknown callback procedure: Missing.
  ```

- **Correção sugerida:** Declare um procedimento sem parâmetros antes do bloco principal ou
  corrija o identificador.

## E3019 - Assinatura de callback inválida

- **Categoria:** Semantic Analysis
- **Explicação:** Callbacks de atualização e de VBlank devem ser procedimentos sem parâmetros
  e sem valor de retorno.
- **Gatilho:** Registrar `procedure Update(Value: byte);` com `nes.on_update(Update);`.
- **Saída esperada do compilador:** `E3019` seguido por `Callback procedure Update must not have parameters.`
- **Correção sugerida:** Utilize um procedimento declarado sem lista de parâmetros.

## E3020 - Callback de atualização duplicado

- **Categoria:** Semantic Analysis
- **Explicação:** Apenas um callback estático de atualização pode ser registrado.
- **Gatilho:** Colocar duas instruções `nes.on_update(...)` na inicialização.
- **Saída esperada do compilador:** `E3020` seguido por `Only one update callback may be registered.`
- **Correção sugerida:** Mantenha um único registro de atualização e despache explicitamente
  a partir desse procedimento quando necessário.

## E3021 - Callback de VBlank duplicado

- **Categoria:** Semantic Analysis
- **Explicação:** Apenas um callback estático de VBlank pode ser registrado.
- **Gatilho:** Colocar duas instruções `nes.on_vblank(...)` na inicialização.
- **Saída esperada do compilador:** `E3021` seguido por `Only one VBlank callback may be registered.`
- **Correção sugerida:** Mantenha um único registro de VBlank e chame apenas helpers seguros
  e sem parâmetros a partir dele.

## E3022 - Contexto de registro de callback inválido

- **Categoria:** Semantic Analysis
- **Explicação:** O registro é uma inicialização em tempo de compilação, não uma operação em
  runtime. Ele deve ser incondicional, de nível superior e antes de `nes.run`.
- **Gatilho:** Colocar `nes.on_update(Update);` em um `if`, laço, procedimento ou após `nes.run`.
- **Saída esperada do compilador:** `E3022` seguido por uma explicação do contexto de registro de callback.
- **Correção sugerida:** Mova o registro para a inicialização incondicional de nível superior antes de `nes.run`.

## E3023 - Operação não segura para VBlank

- **Categoria:** Semantic Analysis
- **Explicação:** Um callback de VBlank ou helper alcançável contém uma operação não limitada
  ou utiliza armazenamento temporário compartilhado não reentrante do compilador.
- **Gatilho:** Utilizar `while`, `repeat`, `for`, aritmética, comparação, `nes.wait_frame`
  ou outra instrução não suportada no caminho de chamada do VBlank.
- **Saída esperada do compilador:** `E3023` identifica a operação não segura e o caminho de
  procedimentos que a alcança.
- **Correção sugerida:** Restrinja o código de VBlank a atribuições escalares livres de temporários,
  `inc`/`dec` simples, condicionais seguras, chamadas de preparação de paleta com valores livres
  de temporários e helpers validados.

## E3024 - Grafo de chamadas de callback inválido

- **Categoria:** Semantic Analysis
- **Explicação:** Um callback de VBlank alcança lógica de atualização ou um procedimento
  parametrizado. Tal chamada não faz parte do subconjunto conservador e seguro para interrupções.
- **Gatilho:** Chamar o callback registrado de atualização ou um procedimento com parâmetros de
  valor a partir de um callback de VBlank ou helper alcançável.
- **Saída esperada do compilador:** `E3024` identifica a aresta de chamada inválida.
- **Correção sugerida:** Mantenha a lógica de atualização fora da NMI e utilize apenas helpers
  sem parâmetros e transitivamente seguros para VBlank.

## E3025 - Registro conflitante de callbacks

- **Categoria:** Semantic Analysis
- **Explicação:** Um único procedimento não pode ser registrado tanto para o contexto de
  atualização na thread principal quanto para o contexto de VBlank na NMI neste milestone.
- **Gatilho:** Registrar `Both` com `nes.on_update(Both);` e `nes.on_vblank(Both);`.
- **Saída esperada do compilador:** `E3025` seguido por `Procedure Both cannot be registered as both update and VBlank callbacks.`
- **Correção sugerida:** Declare procedimentos sem parâmetros separados para os dois contextos de execução.

## E3026 - Índice de controle inválido

- **Categoria:** Semantic Analysis
- **Explicação:** Consultas aos controles padrão suportam apenas as portas 1 e 2.
- **Gatilho:** `nes.controller_down($03, nes.button_a)` ou índice `$00`.
- **Saída esperada do compilador:** `E3026` identifica a constante inválida.
- **Correção sugerida:** Passe `$01`, `$02` ou uma constante `byte` declarada com um desses valores.

## E3027 - Índice dinâmico de controle

- **Categoria:** Semantic Analysis
- **Explicação:** O índice do controle deve ser selecionado em tempo de compilação para que a
  geração de código possa utilizar um byte fixo de estado em runtime.
- **Gatilho:** Passar uma variável ou expressão como o primeiro argumento da consulta de controle.
- **Saída esperada do compilador:** `E3027` seguido por `requires a compile-time controller index`.
- **Correção sugerida:** Utilize `$01`, `$02` ou uma constante declarada direta de `byte`.

## E3028 - Botão de controle inválido

- **Categoria:** Semantic Analysis
- **Explicação:** Uma consulta de controle aceita exatamente uma constante `nes.button_*` padrão,
  e não um literal, constante de usuário, expressão ou nome desconhecido de botão.
- **Gatilho:** `nes.controller_down($01, nes.button_fire)`.
- **Saída esperada do compilador:** `E3028` identifica o botão inválido.
- **Correção sugerida:** Utilize A, B, Select, Start, Up, Down, Left ou Right através de sua
  constante embutida documentada.

## E3029 - Contagem inválida de argumentos de controle

- **Categoria:** Semantic Analysis
- **Explicação:** Cada consulta de controle requer um índice de controle e uma constante de botão.
- **Gatilho:** Omitir qualquer argumento ou fornecer um argumento extra.
- **Saída esperada do compilador:** `E3029` reporta a contagem fornecida.
- **Correção sugerida:** Utilize uma chamada como `nes.controller_pressed($01, nes.button_start)`.

## E3030 - Contagem inválida de argumentos do sprite zero

- **Categoria:** Semantic Analysis
- **Explicação:** O helper fixo de sprite do exemplo de controles requer valores de X, Y, tile e atributos.
- **Gatilho:** Chamar `nes.set_sprite_zero` com quantidade diferente de quatro argumentos.
- **Saída esperada do compilador:** `E3030` reporta a contagem fornecida.
- **Correção sugerida:** Passe exatamente quatro expressões `byte`. Este helper não é uma API geral de sprites.

## E3031 - Índice de paleta de fundo inválido

- **Categoria:** Semantic Analysis
- **Explicação:** Um índice de paleta de fundo deve ser um valor `byte` em tempo de compilação
  de `$00` até `$03`.
- **Gatilho:** Passar `$04` ou uma expressão dinâmica para `nes.set_background_palette` ou sua
  forma de cor individual.
- **Saída esperada do compilador:** `E3031` identifica o índice e API inválidos.
- **Correção sugerida:** Utilize `$00..$03` ou uma constante `byte` nesse intervalo.

## E3032 - Índice de paleta de sprite inválido

- **Categoria:** Semantic Analysis
- **Explicação:** Um índice de paleta de sprite deve ser um valor `byte` em tempo de compilação
  de `$00` até `$03`.
- **Gatilho:** Passar `$04` ou uma expressão dinâmica para `nes.set_sprite_palette` ou sua
  forma de cor individual.
- **Saída esperada do compilador:** `E3032` identifica o índice e API inválidos.
- **Correção sugerida:** Utilize `$00..$03` ou uma constante `byte` nesse intervalo.

## E3033 - Índice de cor de paleta inválido

- **Categoria:** Semantic Analysis
- **Explicação:** Atualizações individuais de paleta selecionam a cor `$00..$03` em tempo de compilação.
- **Gatilho:** Passar o índice de cor `$04` ou uma expressão dinâmica.
- **Saída esperada do compilador:** `E3033` identifica o índice de cor inválido.
- **Correção sugerida:** Utilize `$00..$03` ou uma constante `byte` nesse intervalo.

## E3034 - Contagem inválida de argumentos de paleta

- **Categoria:** Semantic Analysis
- **Explicação:** Chamadas completas de paleta requerem um índice e quatro cores; chamadas
  individuais requerem índice de paleta, índice de cor e cor.
- **Gatilho:** Omitir um argumento ou fornecer um argumento extra.
- **Saída esperada do compilador:** `E3034` reporta a contagem esperada e real.
- **Correção sugerida:** Utilize a assinatura documentada de cinco ou três argumentos.

## E3035 - Contagem inválida de argumentos de carga de fundo

- **Categoria:** Semantic Analysis
- **Explicação:** `nes.load_background()` seleciona o fundo configurado pelas opções do
  compilador e, portanto, não recebe argumentos na linguagem-fonte.
- **Gatilho:** `nes.load_background($00);`
- **Saída esperada do compilador:** `E3035` reporta a contagem de argumentos fornecida.
- **Correção sugerida:** Chame `nes.load_background();` sem argumentos.

## E3036 - Carga de fundo após início do runtime

- **Categoria:** Semantic Analysis
- **Explicação:** Uma transferência completa de 1 KiB de nametable é exclusiva da inicialização
  e não pode ser executada após `nes.run` habilitar a renderização.
- **Gatilho:** Colocar `nes.load_background();` após `nes.run;`.
- **Saída esperada do compilador:** `E3036` identifica o comando inseguro.
- **Correção sugerida:** Mova a carga para a inicialização incondicional de nível superior antes de `nes.run;`.

## E3037 - Carga duplicada de fundo

- **Categoria:** Semantic Analysis
- **Explicação:** O programa NROM atual suporta uma carga de fundo estática na nametable 0.
- **Gatilho:** Chamar `nes.load_background();` duas vezes no bloco principal.
- **Saída esperada do compilador:** `E3037` aponta para a segunda chamada.
- **Correção sugerida:** Mantenha uma chamada de inicialização e um asset configurado.

## E3038 - Contagem inválida de argumentos de set-tile

- **Categoria:** Semantic Analysis
- **Explicação:** `nes.set_tile` requer X do tile, Y do tile e o índice do tile.
- **Gatilho:** Compilar `tests/fixtures/diagnostics/set_tile_argument_count.nsp`, ou omitir ou adicionar um argumento a `nes.set_tile`.
- **Saída esperada do compilador:** `E3038` reporta a contagem esperada e real.
- **Correção sugerida:** Chame `nes.set_tile(x, y, tile)` com três valores `byte`.

## E3039 - Contagem inválida de argumentos de get-tile

- **Categoria:** Semantic Analysis
- **Explicação:** `nes.get_tile` requer X do tile e Y do tile.
- **Gatilho:** Compilar `tests/fixtures/diagnostics/get_tile_argument_count.nsp`, ou omitir ou adicionar um argumento a `nes.get_tile`.
- **Saída esperada do compilador:** `E3039` reporta a contagem esperada e real.
- **Correção sugerida:** Chame `nes.get_tile(x, y)` com dois valores `byte`.

## E3040 - Contagem inválida de argumentos de set-attribute

- **Categoria:** Semantic Analysis
- **Explicação:** `nes.set_attribute` requer X do atributo, Y do atributo e um byte de atributo bruto.
- **Gatilho:** Compilar `tests/fixtures/diagnostics/set_attribute_argument_count.nsp`.
- **Saída esperada do compilador:** `E3040` reporta a contagem esperada e real.
- **Correção sugerida:** Chame `nes.set_attribute(x, y, value)` com três valores `byte`.

## E3041 - Contagem inválida de argumentos de clear-background-updates

- **Categoria:** Semantic Analysis
- **Explicação:** `nes.clear_background_updates()` não recebe argumentos.
- **Gatilho:** Compilar `tests/fixtures/diagnostics/clear_background_updates_argument_count.nsp`.
- **Saída esperada do compilador:** `E3041` reporta a contagem fornecida.
- **Correção sugerida:** Chame `nes.clear_background_updates();` sem argumentos.

## E3042 - Coordenada de tile inválida

- **Categoria:** Semantic Analysis
- **Explicação:** Uma coordenada literal ou constante direta de tile está fora da área
  lógica de 32 por 30 tiles da nametable 0.
- **Gatilho:** Compilar `tests/fixtures/diagnostics/invalid_tile_coordinate.nsp`, usar X acima
  de 31 ou Y acima de 29 em `nes.set_tile` ou `nes.get_tile`.
- **Saída esperada do compilador:** `E3042` identifica a coordenada e o intervalo válido.
- **Correção sugerida:** Utilize X de 0 a 31 e Y de 0 a 29. Coordenadas dinâmicas são verificadas pelo runtime.

## E3043 - Coordenada de atributo inválida

- **Categoria:** Semantic Analysis
- **Explicação:** Uma coordenada literal ou constante direta de atributo está fora da grade
  de entradas de atributos 8 por 8 do hardware para a nametable 0.
- **Gatilho:** Compilar `tests/fixtures/diagnostics/invalid_attribute_coordinate.nsp`, usar X acima
  de 7 ou Y acima de 7 em `nes.set_attribute`.
- **Saída esperada do compilador:** `E3043` identifica a coordenada e o intervalo válido.
- **Correção sugerida:** Utilize X e Y de 0 a 7. Coordenadas dinâmicas são verificadas pelo runtime.

## E3044 - Contagem inválida de argumentos de consulta de estouro de fundo

- **Categoria:** Semantic Analysis
- **Explicação:** `nes.background_updates_overflowed()` lê uma flag fixa de runtime e não recebe argumentos.
- **Gatilho:** Compilar `tests/fixtures/diagnostics/background_updates_overflowed_argument_count.nsp`.
- **Saída esperada do compilador:** `E3044` reporta a contagem fornecida.
- **Correção sugerida:** Chame `nes.background_updates_overflowed()` sem argumentos e utilize seu resultado `boolean`.

## E3045 - Contagem inválida de argumentos de limpeza de estouro de fundo

- **Categoria:** Semantic Analysis
- **Explicação:** `nes.clear_background_update_overflow()` limpa uma flag fixa de runtime e não recebe argumentos.
- **Gatilho:** Compilar `tests/fixtures/diagnostics/clear_background_update_overflow_argument_count.nsp`.
- **Saída esperada do compilador:** `E3045` reporta a contagem fornecida.
- **Correção sugerida:** Chame `nes.clear_background_update_overflow();` sem argumentos.

## E3046 - Contagem inválida de argumentos de set-scroll

- **Categoria:** Semantic Analysis
- **Explicação:** `nes.set_scroll` requer exatamente dois argumentos: rolagem horizontal e rolagem vertical.
- **Gatilho:** Chamar `nes.set_scroll` com menos ou mais de dois argumentos.
- **Saída esperada do compilador:** `E3046` seguido pelas contagens esperada e real de argumentos.
- **Correção sugerida:** Passe exatamente dois valores `byte`, por exemplo `nes.set_scroll($08, $04);`.

## E3047 - Contagem inválida de argumentos da API de sprites

- **Categoria:** Semantic Analysis
- **Explicação:** Setters de propriedades de sprites requerem um índice `sprite` e um valor de
  propriedade. `nes.sprite_hide` e `nes.sprite_show` requerem apenas o índice do sprite.
- **Gatilho:** Compilar `tests/fixtures/diagnostics/sprite_argument_count.nsp`, ou omitir ou adicionar
  um argumento a uma instrução `nes.sprite_*`.
- **Saída esperada do compilador:** `E3047` reporta as contagens esperada e real de argumentos do comando.
- **Correção sugerida:** Passe exatamente os argumentos documentados para a API de sprites.

## E3048 - Paleta de sprite de hardware inválida

- **Categoria:** Semantic Analysis
- **Explicação:** Os bits 0-1 de atributos da OAM selecionam uma de quatro paletas de sprites.
  Um literal ou constante direta passada para `nes.sprite_set_palette` deve estar em `$00..$03`.
- **Gatilho:** Compilar `tests/fixtures/diagnostics/invalid_sprite_palette.nsp`, ou passar `$04` ou
  maior como valor de paleta em tempo de compilação.
- **Saída esperada do compilador:** `E3048` identifica o valor e o intervalo válido.
- **Correção sugerida:** Utilize a paleta de sprite `$00`, `$01`, `$02` ou `$03`.

## E3049 - Contagem inválida de argumentos de sprite-create

- **Categoria:** Semantic Analysis
- **Explicação:** `nes.sprite_create()` é uma expressão de reserva de OAM sem parâmetros em tempo de compilação.
- **Gatilho:** Compilar `tests/fixtures/diagnostics/sprite_create_argument_count.nsp` ou passar qualquer
  argumento para `nes.sprite_create`.
- **Saída esperada do compilador:** `E3049` reporta que zero argumentos eram esperados e identifica a contagem fornecida.
- **Correção sugerida:** Chame `nes.sprite_create()` com parênteses vazios.

## E3050 - Capacidade de sprites de hardware na OAM esgotada

- **Categoria:** Semantic Analysis
- **Explicação:** Reservas explícitas de sprites individuais, locais distintos de `nes.sprite_create()`
  e componentes de metasprites detidos estaticamente compartilham a capacidade fixa de 64 entradas de OAM do NES.
  A alocação estática não pode reservar outra entrada ou grupo de componentes não conflitante.
- **Gatilho:** Compilar `tests/fixtures/diagnostics/sprite_capacity_exhausted.nsp` ou de outra forma
  reservar todos os 64 índices antes de outro local de criação.
- **Saída esperada do compilador:** `E3050` identifica o local de criação que não pode receber uma entrada de OAM.
- **Correção sugerida:** Remova uma reserva de sprite individual, local de criação de sprite ou instância
  de metasprite. A alocação nunca causa wrap, cria alias com um proprietário, trunca um metasprite ou retorna um sentinela.

## E3051 - Importação de metasprite inválida

- **Categoria:** Semantic Analysis
- **Explicação:** Uma importação de metasprite em tempo de compilação deve ser uma instrução direta de
  nível superior antes de `nes.run`, deve nomear um asset configurado com `--metasprite`, e todo asset
  configurado deve ser importado.
- **Gatilho:** Compilar `tests/fixtures/diagnostics/invalid_metasprite_import.nsp` sem configurar seus
  metadados de `player`, aninhar a importação ou movê-la para após o início do runtime.
- **Saída esperada do compilador:** `E3051` identifica a importação inválida ou o asset configurado que
  carece de uma instrução de importação.
- **Correção sugerida:** Configure o JSON e escreva `nes.import_metasprite(player);` diretamente no bloco
  principal antes de `nes.run;`.

## E3052 - Importação duplicada de metasprite

- **Categoria:** Semantic Analysis
- **Explicação:** Uma raiz de asset configurada pode ser importada exatamente uma vez.
- **Gatilho:** Compilar `tests/fixtures/diagnostics/duplicate_metasprite_import.nsp` com o asset player configurado.
- **Saída esperada do compilador:** `E3052` identifica a segunda importação.
- **Correção sugerida:** Mantenha uma importação de nível superior para cada raiz de asset.

## E3053 - Criação de metasprite inválida

- **Categoria:** Semantic Analysis
- **Explicação:** `nes.metasprite_create` requer exatamente um quadro simbólico importado como `player.idle_0`.
  O local de criação possui uma identidade estática persistente e não é uma alocação de heap.
- **Gatilho:** Compilar `tests/fixtures/diagnostics/invalid_metasprite_create.nsp` ou chamar o intrínseco
  sem um quadro simbólico.
- **Saída esperada do compilador:** `E3053` explica o formato inválido de criação.
- **Correção sugerida:** Importe o asset e passe um símbolo de quadro.

## E3054 - Contagem inválida de argumentos da API de metasprites

- **Categoria:** Semantic Analysis
- **Explicação:** Posição recebe um metasprite e dois bytes; setters de quadro e flip e seleção de
  animação recebem um metasprite e um valor; ocultar/exibir, reinício de animação e consultas de conclusão
  de animação recebem um metasprite.
- **Gatilho:** Compilar `tests/fixtures/diagnostics/metasprite_argument_count.nsp`.
- **Saída esperada do compilador:** `E3054` reporta as contagens esperada e real.
- **Correção sugerida:** Passe exatamente os argumentos documentados pela API de metasprites.

## E3055 - Quadro de metasprite incompatível

- **Categoria:** Semantic Analysis
- **Explicação:** Uma instância de metasprite detém capacidade de OAM para todos os quadros em seu asset
  de criação. Um quadro de outro asset não pode ser selecionado com segurança.
- **Gatilho:** Compilar `tests/fixtures/diagnostics/incompatible_metasprite_frame.nsp` com ambos os assets
  referenciados configurados.
- **Saída esperada do compilador:** `E3055` nomeia a instância e os assets de quadros.
- **Correção sugerida:** Selecione um quadro do mesmo asset utilizado na criação.

## E3056 - Animação de metasprite inválida

- **Categoria:** Semantic Analysis
- **Explicação:** `nes.metasprite_set_animation` requer uma animação simbólica importada pertencente
  ao asset de criação da instância. Nomes de animação são símbolos exclusivos do compilador e não
  podem ser substituídos por valores numéricos.
- **Gatilho:** Compilar `tests/fixtures/diagnostics/invalid_metasprite_animation.nsp`, ou passar uma
  animação estaticamente conhecida de outro asset.
- **Saída esperada do compilador:** `E3056` identifica a seleção de animação não simbólica ou incompatível.
- **Correção sugerida:** Passe um símbolo como `player.movement_right` a partir do mesmo asset importado
  utilizado por `nes.metasprite_create`.

## E3057 - Contexto de builtin inválido

- **Categoria:** Semantic Analysis
- **Explicação:** Builtins comuns são registrados como instruções autônomas ou expressões produtoras
  de valor. Um builtin de instrução não pode ser atribuído nem aninhado em uma expressão, e um builtin
  de valor não pode ser usado como uma instrução autônoma.
- **Gatilho:** Compilar `tests/fixtures/diagnostics/invalid_builtin_context.nsp`, ou escrever
  `nes.sprite_create();` como uma instrução autônoma.
- **Saída esperada do compilador:** `E3057` nomeia o builtin e seu contexto registrado.
- **Correção sugerida:** Utilize builtins de instrução diretamente e consuma resultados de builtins
  de valor em uma expressão de tipo compatível.

## E3058 - Contagem inválida de argumentos de builtin

- **Categoria:** Semantic Analysis
- **Explicação:** A assinatura centralizada de builtin requer uma quantidade fixa de argumentos.
  Builtins com um diagnóstico existente de contagem específico para a operação mantêm esse código;
  `E3058` cobre assinaturas comuns que anteriormente não possuíam um diagnóstico dedicado.
- **Gatilho:** Compilar `tests/fixtures/diagnostics/invalid_builtin_argument_count.nsp`.
- **Saída esperada do compilador:** `E3058` reporta as contagens esperada e fornecida de argumentos.
- **Correção sugerida:** Passe exatamente os argumentos documentados para o builtin.

## E3059 - Função desconhecida

- **Categoria:** Análise Semântica
- **Explicação:** Uma expressão chama um nome de função que não foi declarado.
- **Gatilho:** Compile `tests/fixtures/diagnostics/unknown_function.nsp`.
- **Correção sugerida:** Declare a função antes do bloco principal e chame-a com parênteses.

## E3060 - Contagem incorreta de argumentos de função

- **Categoria:** Análise Semântica
- **Explicação:** Uma chamada não fornece exatamente um valor para cada parâmetro declarado.
- **Gatilho:** Compile `tests/fixtures/diagnostics/function_argument_count.nsp`.
- **Correção sugerida:** Passe exatamente os argumentos declarados, incluindo `()` em chamadas sem parâmetros.

## E3061 - Função usada como instrução

- **Categoria:** Análise Semântica
- **Explicação:** Uma função produz um valor e não pode ser descartada como instrução isolada.
- **Gatilho:** Compile `tests/fixtures/diagnostics/function_used_as_statement.nsp`.
- **Correção sugerida:** Use a chamada em uma expressão ou atribuição de tipo compatível.

## E3062 - Procedimento usado como expressão

- **Categoria:** Análise Semântica
- **Explicação:** Um procedimento não possui retorno e não pode aparecer onde uma expressão é necessária.
- **Gatilho:** Compile `tests/fixtures/diagnostics/procedure_used_as_expression.nsp`.
- **Correção sugerida:** Chame uma função que retorne o tipo necessário.

## E3063 - Resultado de função indefinido

- **Categoria:** Análise Semântica
- **Explicação:** O resultado é lido antes de ser atribuído ou não recebe valor em todos os caminhos do corpo.
- **Gatilho:** Compile `tests/fixtures/diagnostics/undefined_function_result.nsp`.
- **Correção sugerida:** Atribua o nome da função em todos os caminhos antes do fim ou antes da leitura.
