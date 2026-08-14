# Milestone 0.5.12 — Funções: Auditoria de Completude e Qualidade

[English](../../compiler/milestone-0.5.12-audit.md) | Português (Brasil)

- **Branch:** `audit/0.5.12-validation`
- **Commit base da auditoria:** `40313d5` (merge do PR #26, `0.5.12-functions`)
- **Commit de implementação da milestone:** `1c8f88d` ("Implement 0.5.12 functions")
- **Data da auditoria:** 2026-08-14
- **Papel do auditor:** revisor independente de QA (não o implementador original)

Este documento é um artefato de revisão independente da milestone 0.5.12
(Funções). Ele é distinto do relatório de implementação
[`functions-0.5.12.md`](functions-0.5.12.md), que é o instantâneo da milestone
feito pelo implementador. Esta auditoria registra verificação baseada em
evidências, descobertas de cobertura e um backlog para endurecimento de
acompanhamento.

---

## 1. Matriz de requisitos da milestone

O contrato é a seção Funções de `roadmap/0.md` (identificador `0.5.12`). Todos
os doze requisitos foram verificados contra evidências concretas do repositório,
não nomes ou comentários.

| # | Requisito | Status | Evidência |
| --- | --- | --- | --- |
| 1 | Declarações de função | **Verificado** | Gramática `function` em `parser.py` (nome tipado, lista de parâmetros opcional, tipo de retorno opcional); declarações aceitas entre `var` e o bloco principal; `test_parser_represents_typed_function_and_explicit_call`, `test_parser_rejects_malformed_function_declarations`; declarações intercaladas com procedimentos. |
| 2 | Chamadas de função | **Verificado** | Nó de AST `FunctionCall` e `ResolvedFunctionCall`; toda chamada exige parênteses, incluindo chamadas sem parâmetros; `test_forward_calls_resolve_in_callee_first_order`; chamadas aninhadas em argumentos/aritmética/comparações/condições verificadas em fixtures de runtime e probes. |
| 3 | Valores de retorno `byte` | **Verificado** | Byte de suporte em RAM regular `function_result_<name>`; epílogo `lda function_result_<name>` + `rts`; `test_return_storage_is_regular_ram_and_absent_without_functions`; golden ABI; runtime no Mesen (resultados de aritmética aninhada `$06/$31/$66/$F3`). |
| 4 | Valores de retorno `boolean` | **Verificado** | Materialização canônica `$00`/`$01`; o acumulador carrega o resultado; o `lda` final deixa a flag Z válida para que o chamador faça branch direto de curto-circuito; `test_boolean_function_is_valid_in_short_circuit_expression`; verificação de curto-circuito por probe e no Mesen. |
| 5 | Parâmetros de função | **Verificado** | Parâmetros por valor `byte`/`boolean` usando a ABI estática de RAM regular de procedimento (símbolos `parameter_<name>`); validação de tipo via `E4005`; rejeição de tipos de parâmetro enum e `color` verificada por probe. |
| 6 | Validação do tipo de retorno | **Verificado** | Apenas retornos `byte`/`boolean`; `E4026` para qualquer outro tipo (`tests/fixtures/diagnostics/unsupported_function_return_type.nsp`); literais de resultado errados rejeitados com `E4004` (`wrong_boolean_function_result.nsp`, `wrong_byte_function_result.nsp`). |
| 7 | Chamadas de função dentro de expressões | **Verificado** | Chamadas resolvidas como expressões de valor em aritmética, comparações, índices de array, escritas de campo de record, condições de `if`/`while`/`for`, argumentos de `nes.*` e operandos de curto-circuito; verificado nas camadas de unidade, golden e runtime no Mesen. |
| 8 | Definir armazenamento do valor de retorno ou convenção de chamada | **Verificado** | ABI documentada em `docs/language/functions.md` e `functions-0.5.12.md`: byte de resultado estático em RAM regular por função, resultado retornado em `A`, `A`/`X`/`Y`/flags destruídos pelo chamador, endereços de retorno na pilha de hardware, sem frame de runtime; golden `tests/golden/functions_abi.asm`. |
| 9 | Preservar os temporários de expressão externos através de chamadas de função aninhadas | **Verificado** | `callable_bases` em `TemporaryRequirements`; o codegen pré-adquire o prefixo de base de cada função chamada para que os temporários do corpo da função chamada fiquem acima dos slots vivos do chamador; `_generate_call_arguments` arrenda resultados de argumentos anteriores através de argumentos posteriores que contêm chamadas; análise e codegen concordam; golden de pressão (`Leaf` na base 2, pico de 3 bytes vivos). |
| 10 | Suportar expressões de chamada de função aninhadas sobre o alocador de temporários com escopo | **Verificado** | Chamadas aninhadas reutilizam o pool com escopo da 0.5.11 sem aliasing; probe de 4 níveis (`max_call_depth` 4, 3 temporários vivos do chamador) verificado via Mesen; cadeias de chamada aninhadas com empilhamento de irmãos verificadas. |
| 11 | Definir a ordem de avaliação quando chamadas de função aparecem em expressões maiores | **Verificado** | Documentado e verificado: argumentos da esquerda para a direita; `and`/`or` em curto-circuito da esquerda para a direita (operandos pulados não executam); aritmética/comparação binária mantém primeiro o operando direito quando o lado direito exige avaliação (`LeftCall() - RightCall()` executa `RightCall()` primeiro). Coincide com as regras de redução pré-existentes; sem regressão. |
| 12 | Rejeitar recursão direta e indireta envolvendo funções | **Verificado** | `E3014` para direta (`recursive_function_call.nsp`), indireta (`recursive_function_call_indirect.nsp`) e mista de procedimento/função (`recursive_callable_mixed.nsp`); `test_direct_indirect_and_mixed_recursion_are_rejected`; probe confirmou que um ciclo é rejeitado mesmo quando a função recursiva é inalcançável a partir do bloco principal. |

**Requisitos do roadmap não cobertos:** nenhum. Todos os 12 requisitos estão
implementados, documentados e exercitados por testes, fixtures, goldens ou
benchmarks.

---

## 2. Cobertura semântica positiva

### Casos normais / comuns (cobertos)
- Função única retornando um literal: epílogo canônico `lda function_result_X; rts`.
- Funções parametrizadas: preparação estática de RAM `parameter_*`, cópia de
  argumento da esquerda para a direita.
- Chamadas aninhadas `F() + G() + H()`: redução de operando complexo primeiro à
  direita, offsets de base por chamada (`function_G` base 1, `function_F` base 2
  com dois slots vivos do chamador), pool=2.
- Funções Booleanas em `if F() and G() then` com curto-circuito: caminho da flag
  Z sem `cmp #$00`, ordem de efeitos colaterais da esquerda para a direita
  (verificado no Mesen).
- Interação procedimento/função: procedimentos chamados de corpos de função;
  resultados de função passados diretamente a procedimentos
  (`examples/functions.nsp`).
- Laços `for` dentro de corpos de função: cache `for_limit_*`, avaliação do corpo
  por iteração, `jsr` por chamada (verificado no Mesen `Sum($05)=$0F`).
- Laços `while` com chamadas de função na condição (verificado no Mesen).

### Condições de contorno (cobertas)
- O resultado deve ser atribuído em todo caminho: atribuição apenas no corpo do
  laço, atribuição apenas condicional e leitura antes de atribuição emitem `E3063`
  (verificado por probe); ambos os ramos-definitivo passa (teste unitário).
- Atribuições no lado direito de `and`/`or` em curto-circuito *não* são
  definitivas, atribuições no lado esquerdo permanecem definitivas (testes
  unitários).
- Cadeia de chamada de 4 níveis com `max_call_depth` 4 (verificado no Mesen
  `$04`); argumentos aninhados de 4 níveis com 3 temporários simultaneamente
  vivos (verificado no Mesen `$0E`).
- Função usada como callback de quadro é rejeitada (probe); registro de callback
  dentro de um corpo de função é rejeitado.
- Limites de tipo de parâmetro/resultado: parâmetros `enum`/`color` → `E4005`;
  retornos `enum`/`sprite` → `E4026`; incompatibilidades de argumento
  byte↔boolean → `E4004`.
- Nomes chamáveis compartilham o namespace global com variáveis/procedimentos
  (`test_callable_names_share_the_existing_global_namespace`); um parâmetro
  sombreando o nome da função → `E3004`.

### Interações (cobertas)
- Arrays × funções: `Values[Index()] := Value()` preserva o índice na pilha de
  hardware e o relê após a expressão de valor (verificado no Mesen).
- Records × funções: escritas de campo de array de records usando índice e valor
  de chamada de função (verificado no Mesen `Positions[1].X=$07, .Y=$0E`).
- Builtins × funções: `nes.get_tile($00, Y())` prepara X via `pha`/`pla` em torno
  do `jsr` (verificado em assembly); chamada de argumento
  `nes.set_background_color(F())` (fixture).
- Laços `for` × funções: inicial/final avaliados uma vez em `for_limit_*`;
  chamadas de função no corpo e no valor final; caches `for_limit` são sempre
  alocados depois de todos os temporários de expressão, de modo que temporários
  do corpo da função chamada (limitados por `expression_temporaries`) nunca podem
  criar aliasing com um byte `for_limit_*` vivo.
- Estrutura exigida por `nes.run` inalterada; programas com funções ainda
  satisfazem a validação única de `set_background_color`.
- Wrap-around de 8 bits dentro de corpos de função (verificado no Mesen).

### Casos apenas cobertos indiretamente
- Incompatibilidade de *tipo* de argumento de função (`E4004`) não tem fixture
  negativa dedicada, apenas uma asserção unitária no processo
  (`test_function_diagnostics_cover_call_and_type_errors`) e um probe de CLI
  (P3-1).
- A profundidade máxima de chamada próxima ao limite da pilha de hardware de 256
  bytes não tem guarda em tempo de compilação (P2-1).

---

## 3. Matriz de cobertura de diagnósticos

| Condição inválida | Código esperado | Teste / fixture existente | Status |
| --- | --- | --- | --- |
| Nome de função desconhecido | `E3059` | `tests/fixtures/diagnostics/unknown_function.nsp` + caso unitário `Missing()` | Coberto |
| Contagem de argumentos errada | `E3060` | `tests/fixtures/diagnostics/function_argument_count.nsp` + caso unitário `One()` | Coberto |
| Função usada como declaração | `E3061` | `tests/fixtures/diagnostics/function_used_as_statement.nsp` + caso unitário | Coberto |
| Procedimento usado como expressão | `E3062` | `tests/fixtures/diagnostics/procedure_used_as_expression.nsp` + caso unitário `Value := Work()` | Coberto |
| Resultado lido antes de atribuído / não em todo caminho | `E3063` | `tests/fixtures/diagnostics/undefined_function_result.nsp` + testes unitários de atribuição definitiva | Coberto |
| Tipo de resultado errado / tipo de argumento | `E4004` | `wrong_byte_function_result.nsp`, `wrong_boolean_function_result.nsp` (resultado); tipo de argumento apenas testado por unidade (`Enabled($01)`) | Coberto (resultado); P3-1 (argumento) |
| Tipo de retorno não suportado | `E4026` | `tests/fixtures/diagnostics/unsupported_function_return_type.nsp` | Coberto |
| Tipo de parâmetro não suportado | `E4005` | fixtures de parâmetro pré-existentes exercitadas para enum/`color` via probes; fixture específica de enum `enum_procedure_parameter.nsp` | Coberto |
| Recursão direta / indireta / mista | `E3014` | `recursive_function_call.nsp`, `recursive_function_call_indirect.nsp`, `recursive_callable_mixed.nsp` | Coberto |
| Função registrada como callback de quadro | `E3018` | verificado por probe apenas; a função é declarada mas relatada "Unknown callback procedure" (P3-3) | P3-3 |
| Função chamada sem parênteses | `E3005` | verificado por probe; "Unknown identifier" (P3-4) | P3-4 |
| Chamada de declaração nua com contagem de argumentos errada | `E3061` antes de `E3060` | `function_used_as_statement.nsp` (contagem correta); probe de declaração com contagem errada relata `E3061` (por design, P3-5) | P3-5 |

Todos os seis diagnósticos novos específicos de função (`E3059`–`E3063`, `E4026`)
estão registrados no catálogo canônico (`docs/DIAGNOSTICS.md`,
`docs/reference/diagnostics/index.md`, `semantic.md`/`type-system.md` e os
contrapartes PT-BR mantidos), validados pelo teste de catálogo de diagnósticos e
têm fixtures negativas focadas. As mensagens são específicas e acionáveis, com
texto de sugestão.

---

## 4. Cobertura por camada de parser / semântica / backend

| Camada | Evidência | Avaliação |
| --- | --- | --- |
| Lexer / Parser | Palavra-chave `function`, lista de parâmetros opcional, `: type` opcional, corpo `begin/end`; `F(...)` no nível de declaração parseado como chamada de procedimento para que `E3061` dispare; `test_parser_represents_typed_function_and_explicit_call`, `test_parser_rejects_malformed_function_declarations` | Coberto |
| Semântica | Resolução de `FunctionDeclaration`/`FunctionCall`, `ResolvedFunction`, `ResolvedFunctionCall`, `ResolvedFunctionResultAssignment`; análise de resultado definitivo com regras de caminho cientes de curto-circuito; detecção de ciclos de recursão; namespace global compartilhado; regras de posicionamento de função/callback | Coberto |
| AST | `FunctionDeclaration`, `FunctionCall`, nós `ResolvedFunction*`; tipos dedicados; catálogo de nós resolvidos atualizado | Coberto |
| Layout de memória | Símbolos `function_result_*` em RAM regular em `FUNCTION_RESULTS`; custo zero sem funções (`test_return_storage_is_regular_ram_and_absent_without_functions`, identidade de benchmark); parâmetros reutilizam a ABI de RAM estática de procedimento | Coberto |
| Backend | `codegen_analysis.py` calcula `callable_bases` + `max_call_depth`; `backend_ca65.py` pré-adquire slots de base, arrenda resultados de argumentos através de argumentos que contêm chamadas, emite o epílogo `lda function_result_X; rts`; `_zero_flag_is_valid` permite branch Z direto para resultados booleanos; o comportamento de arrendamento de análise e codegen concorda (verificado por probe em 20+ cenários) | Coberto |
| Suporte de runtime | Nenhum código de runtime novo; pilha de hardware reservada integralmente para endereços de retorno de `JSR`/`RTS`; benchmarks inalterados | Coberto |

---

## 5. Auditoria do Assembly golden

`tests/golden/functions_abi.asm` registra o contrato da ABI de retorno: epílogo
`lda function_result_X` / `rts`, `jsr` do chamador e preparação do resultado.

`tests/golden/functions_temporary_pressure.asm` é o golden crítico de segurança
de temporários: o chamador mantém `expression_temporary_0`, `function_Middle`
adquire `expression_temporary_1` (base 1) e `function_Leaf` adquire
`expression_temporary_2` (base 2) — um pico verificado de três bytes
simultaneamente vivos na profundidade de chamada de origem dois (quatro bytes de
pilha de hardware). Este é exatamente o limite que a milestone não deve regredir.

Classificação: **obrigatório — existe.** A convenção de golden focado é seguida;
nenhum golden de arquivo completo é justificado para Funções.

---

## 6. Validação de toolchain

- O corpus completo de 21 benchmarks (20 pré-existentes + `functions`) monta e
  linka através de ca65/ld65 (`make benchmark`, `make validate`).
- `make rom` produz `build/minimal.nes` (NROM válido).
- A fixture de runtime `tests/fixtures/runtime/functions.nsp` compila para um
  ROM, monta, linka e roda sob Mesen headless (veja seção 7).
- Todos os exemplos públicos, incluindo `examples/functions.nsp`, compilam,
  montam e linkam (validados em `tests/test_integration.py` e no corpus de
  benchmark).
- Sem regressão de configuração de linker: `FUNCTION_RESULTS` fica depois de
  outro armazenamento de resultado do compilador em RAM regular; programas sem
  funções omitem o segmento, os símbolos e os corpos inteiramente.

---

## 7. Cobertura de runtime no Mesen

`tests/mesen/verify_functions.lua` executa `tests/fixtures/runtime/functions.nsp`
e verifica memória de runtime concreta: segurança de parâmetros estáticos
aninhados, argumentos da esquerda para a direita, aritmética complexa primeiro à
direita, comparações, normalização Booleana, efeitos colaterais de
curto-circuito, interação procedimento/função e wrap-around de 8 bits. Está
conectada como `test_functions_preserve_nested_static_parameters_and_short_circuits`;
todos os 29 `MesenIntegrationTests` passam localmente.

A bateria de probes independente adiciona verificação de runtime além da fixture
enviada (cada endereço verificado de forma cruzada contra seu mapa de memória):
- `probe_stress.nsp` — chamadas aninhadas com valores de retorno mistos (`A1=$06,
  A2=$31, A3=$66, B1=$F3`, 11 chamadas `Mark` em ordem documentada).
- `probe_for.nsp` — laço `for` dentro de uma função (`Sum($05)=$0F`,
  `Index=$06`).
- `probe_record_func.nsp` — escritas de campo de array de records com índice e
  valor de chamada de função (`Positions[1].X=$07, .Y=$0E`).
- `probe_depth.nsp` — cadeia de chamada de 4 níveis (`max_call_depth` 4,
  resultado `$04`).
- `probe_deep_temp.nsp` — argumentos aninhados de 4 níveis, 3 temporários vivos
  (`$0E`).
- `probe_while_calls.nsp` — condição `while` com chamadas de função
  (`Result=$02`, `Counter=$03`).

Esta é uma verificação comportamental de temporários seguros para chamadas, ordem
de avaliação e segurança de parâmetros aninhados, não uma verificação de
apenas-ROM-inicializa.

---

## 8. Cobertura de benchmark / recursos

- A entrada dedicada `functions` do corpus compila `examples/functions.nsp` e
  mede os custos de ABI documentados: 365 B de código PRG / 371 B ocupados, 158
  instruções, 560 ciclos-base estáticos estimados, profundidade de expressão 2,
  máximo de temporários vivos 1, profundidade de chamada de origem 2 (pico de
  4 B de endereço de retorno JSR), 3 B de RAM regular de resultado de função.
  Todos os números coincidem com o relatório do implementador.
- **Custo zero sem funções (verificado independentemente):** o relatório
  completo de benchmark foi regenerado no commit pré-0.5.12 (`e077216`) e em
  `1c8f88d`, e os dois foram comparados. Todos os 20 benchmarks pré-existentes
  são **idênticos** em bytes de código/ocupado de PRG, profundidade da árvore de
  expressão, máximo de temporários vivos, contagem de instruções, ciclos
  estáticos estimados e cada coluna de contabilidade de RAM (incluindo Zero Page
  e RAM regular); os únicos novos bytes de resultado no corpus são os 3 B do
  benchmark `functions`. Um programa sem funções não emite bytes de resultado,
  segmento `FUNCTION_RESULTS` ou corpos de função.
- `test_benchmark_accounting.py` reconcilia cada categoria com o espaço de
  endereço de CPU NES de 2.048 bytes, incluindo os três bytes de resultado de
  função de propriedade do compilador e a reconciliação exata de 2 KiB.
- Caches `for_limit_*`, temporários de expressão e resultados de função são
  relatados como categorias distintas; nada é mal rotulado.

---

## 9. Cobertura de documentação

Verificados: `docs/language/functions.md`, `docs/pt-BR/language/functions.md`,
`docs/runtime/cpu-memory.md`, `docs/pt-BR/runtime/cpu-memory.md`,
`docs/reference/unsupported-features.md`,
`docs/reference/diagnostics/{index,semantic,type-system}.md` + PT-BR,
`docs/compiler/functions-0.5.12.md`, `docs/compiler/test-coverage-map.md` +
PT-BR, `docs/index.md`, `docs/DIAGNOSTICS.md`, `docs/getting-started/*`, roadmap
`0.md` + `README.md`, README e `docs/reference/compiler-pipeline.md`.

- O estado do roadmap está correto: `0.5.12` marcado como Concluído com todos os
  12 itens marcados; índice atualizado (última concluída `0.5.12`, próxima
  milestone `0.5.13` Collision Helpers).
- A referência de linguagem (EN + PT-BR) documenta com precisão declarações,
  argumentos da esquerda para a direita, operandos complexos primeiro à direita,
  preservação de curto-circuito, a ABI de RAM estática, registradores destruídos
  pelo chamador, a reserva integral da pilha de hardware, a rejeição de ciclo
  `E3014` e a ausência de locais/frames/recursão/retornos agregados.
- Os índices e páginas de detalhe de diagnósticos (EN + PT-BR) registram todos os
  novos códigos.
- Divergências encontradas e disposição:
  - **Não corrigido (relatado):** `docs/pt-BR/compiler/functions-0.5.12.md` não
    existe, enquanto todo documento de design de milestone anterior
    (`optimization-audit-0.5.5`, `low-risk-codegen-0.5.7`, `arrays-0.5.8`,
    `enumerations-0.5.9`, `records-0.5.10`, `expression-temporaries-0.5.11`)
    tem uma tradução PT-BR mantida. Toda a documentação voltada ao usuário da
    0.5.12 está traduzida; apenas este instantâneo de design interno do
    compilador está faltando (P3-2).
  - **Preciso, verificado:** as afirmações "524 testes automatizados" e "todos
    os 29 testes Mesen headless dedicados" em `functions-0.5.12.md` equivalem à
    suíte viva.

---

## 10. Mapa de cobertura de testes

`docs/compiler/test-coverage-map.md` (EN/PT-BR) adiciona o subsistema 31
"Funções" com Strong em todos os níveis aplicáveis (Semântica, Layout de Memória,
Backend ASM, Golden ASM, Toolchain, Mesen Runtime, Corpus de Benchmark) e N/A
para Lexer/Parser (a gramática é exercitada via testes unitários, mas o mapa de
cobertura a marca como N/A conforme a convenção estabelecida). Esta classificação
é defensável: testes unitários focados para todos os 12 requisitos, fixtures
negativas para cada diagnóstico novo, um golden de ABI focado mais um golden de
pressão de temporários, montagem/linkagem de toolchain do corpus de 21
benchmarks, um teste de runtime no Mesen e contabilidade exata de benchmarks
existem para cada nível aplicável. Nenhuma correção do mapa é justificada.

---

## 11. Auditoria de regressão e interação

- Suíte completa: **524 testes, OK** (0 pulados, 0 falhas), incluindo todos os
  testes pré-existentes de linguagem, backend, memória, golden e runtime, e todos
  os 29 `MesenIntegrationTests`.
- Comparação de benchmark pré/pós-0.5.12 (seção 8): todos os 20 benchmarks
  pré-existentes idênticos byte a byte em cada métrica — sem regressão de
  tamanho, instrução, ciclo, RAM, Zero Page ou pressão de temporários.
- Ordem de avaliação, materialização Booleana, redução de curto-circuito, escritas
  indexadas e redução de laços `for` inalteradas para programas sem funções.
- Probes de interação direcionados: argumentos aninhados, índices de
  array/record com chamadas, argumentos de builtin com chamadas, condições de
  for/while/if com chamadas, cadeias de chamada profundas, aninhamento profundo
  de temporários, rejeição de tipo de parâmetro/resultado, colisões de namespace,
  recursão (incluindo inalcançável), mau uso de callback e chamadas de declaração
  nuas.
- Exemplos, goldens e scripts Mesen pré-existentes não afetados.

---

## 12. Lacunas de cobertura e descobertas

| Severidade | Descoberta |
| --- | --- |
| P0 | Nenhuma encontrada. Nenhum defeito de correção ou semântica identificado no escopo implementado e documentado. |
| P1 | Nenhuma. Todos os 12 requisitos documentados da milestone estão implementados e têm proteção de regressão focada. |
| P2-1 | ~~Sem guarda em tempo de compilação da profundidade máxima de chamada de origem vs. a pilha de hardware de 256 bytes~~ **Resolvido** em `fix/function-call-depth-stack-guard`: um orçamento derivado reserva 10 bytes além dos dois bytes por endereço de retorno de `JSR` ativo (4 bytes para frames de `JSR` internos de runtime alcançáveis a partir de declarações de usuário, 6 bytes para folga de NMI), dando uma profundidade máxima suportada de chamáveis de `(256 - 10) / 2 = 123`. `E5007` (`HARDWARE_STACK_CALL_DEPTH_EXHAUSTED`) rejeita cadeias acíclicas mais profundas em tempo de compilação; o limite de 124 cadeias é coberto por testes focados em `tests/test_functions.py`. |
| P3-1 | Incompatibilidade de *tipo* de argumento de função (`E4004`) não tem fixture negativa dedicada; apenas uma asserção unitária no processo (`Enabled($01)`) e probes de CLI. Mesmo caminho de código do `E4004` pré-existente; baixo valor incremental. |
| P3-2 | `docs/pt-BR/compiler/functions-0.5.12.md` ausente; quebra o padrão de documento de design por milestone no PT-BR (todos os documentos de design de milestone anteriores são traduzidos). Toda a documentação voltada ao usuário da 0.5.12 está traduzida. |
| P3-3 | Uma função registrada como callback de quadro (`nes.on_update(SomeFunction)`) é rejeitada com `E3018` "Unknown callback procedure: SomeFunction" embora a função seja declarada; a rejeição está correta, mas a mensagem não explica que funções não podem ser callbacks. |
| P3-4 | Uma função chamada sem parênteses (`Value := CurrentScore;`) relata `E3005` "Unknown identifier: CurrentScore"; é preciso, mas não sugere o `()` exigido. |
| P3-5 | Uma chamada de declaração nua com contagem de argumentos errada (`F($01, $02);`) relata `E3061` (função usada como declaração) em vez de `E3060` (contagem de argumentos). Por design — chamadas no nível de declaração parseiam como chamadas de procedimento; o erro primário aparece primeiro. |

---

## 13. Resultados de validação local

- `make validate` (`PYTHON=python3`, `MESEN_PATH=/opt/mesen/Mesen`): **OK** —
  suíte completa **524 testes, OK** (0 pulados), corpus de 21 benchmarks montado
  e linkado, `build/minimal.nes` produzido.
- `python3 -m unittest tests.test_integration.MesenIntegrationTests`: **29
  testes, OK**.
- Probes independentes (CLI do compilador + Mesen headless `--testRunner`):
  argumentos aninhados, chamadas indexadas de array/record, condições de
  for/while/if, aninhamento de 4 níveis e de 4 temporários profundos, mau uso de
  callback/tipo/namespace — tudo se comportou como documentado.
- Limite da guarda de profundidade de chamada (probes de cadeia programática):
  122/123 aceitos, 124/125 rejeitados com `E5007`; cadeias mistas de
  função/procedimento em 123/124 se comportam de forma idêntica; uma cadeia
  cíclica de 163 relata `E3014`, nunca `E5007`.
- Determinismo: compilação repetida produz Assembly idêntico byte a byte;
  relatórios de benchmark regenerados deterministicamente entre execuções.
- Nota: `make validate` exige `PYTHON=python3` neste ambiente porque o Makefile
  padroniza para `python`; CI não é afetado.

## 14. Execução do GitHub Actions

Push de `audit/0.5.12-validation`. O pipeline de CI autoritativo
(`.github/workflows/ci.yml`) rodou contra o branch enviado. A execução de
validação final (após o commit de registro `a5add38`) é a execução do GitHub
Actions `31772718704` (número de execução 56, evento `push`, head `a5add38`).

- Job `compiler-toolchain`: **concluído / sucesso**
- Job `mesen-runtime`: **concluído / sucesso**
- Job `ci-gate`: **concluído / sucesso**

## 15. Gate de CI final

O job agregado `ci-gate` **passou** para o branch enviado, confirmando os jobs de
toolchain do compilador e de runtime do Mesen e o gate geral remotamente. A
evidência local (seção 13) concorda com o resultado remoto.

---

## Recomendação

Todos os doze requisitos da milestone 0.5.12 são verificados contra evidências
concretas (implementação, testes unitários, fixtures negativas, dois goldens
focados, montagem/linkagem de toolchain, 29 execuções Mesen headless e
contabilidade exata de benchmarks). A funcionalidade está distribuída
corretamente entre parser, semântica, layout de memória e backend; análise e
codegen concordam sobre a vivacidade de temporários, de modo que uma divergência
de segurança de chamadas seria uma falha sonora em tempo de compilação em vez de
corrupção silenciosa. A ordem de avaliação, a materialização Booleana, a redução
de curto-circuito e todos os invariantes de tamanho/ciclos são preservados
(identidade pré/pós de benchmark no corpus). Não restam descobertas P0, P1 ou P2:
o único item de endurecimento P2 (guarda de profundidade máxima de chamada de
origem, `E5007`) está resolvido em `fix/function-call-depth-stack-guard` com um
orçamento derivado de 123 chamadas e cobertura focada de limites. Os itens P3
restantes são polimento de documentação e redação menor de diagnóstico, nenhum
dos quais bloqueia os critérios de aceite da milestone.

**PRONTA**