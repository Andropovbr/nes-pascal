# Milestone 0.5.11 — Alocação de Temporários de Expressão: Auditoria de Completude e Qualidade

[English](../../compiler/milestone-0.5.11-audit.md) | Português (Brasil)

- **Branch:** `audit/0.5.11-validation`
- **Commit base da auditoria:** `9640da8` (merge do PR #24, `0.5.11-expression-temporaries`)
- **Commit de implementação da milestone:** `ea3e17d` ("Implement 0.5.11 expression temporary allocation")
- **Data da auditoria:** 2026-08-14
- **Papel do auditor:** revisor independente de QA (não o implementador original)

Este documento é um artefato de revisão independente da milestone 0.5.11
(Alocação de Temporários de Expressão). Ele é distinto do relatório de
implementação
[`expression-temporaries-0.5.11.md`](expression-temporaries-0.5.11.md), que é o
instantâneo da milestone feito pelo implementador. Esta auditoria registra
verificação baseada em evidências, descobertas de cobertura e um backlog para
endurecimento de acompanhamento.

---

## 1. Matriz de requisitos da milestone

O contrato é a seção Alocação de Temporários de Expressão de `roadmap/0.md`
(identificador `0.5.11`). Todos os vinte requisitos foram verificados contra
evidências concretas do repositório, não nomes ou comentários.

| # | Requisito | Status | Evidência |
| --- | --- | --- | --- |
| 1 | Substituir a reserva incondicional de 16 bytes de temporários de expressão por um requisito derivado em tempo de compilação | **Verificado** | `analyze_program_temporaries` (`nes_pascal/codegen_analysis.py`) calcula `expression_temporary_bytes`; `memory_layout.py` dimensiona a região do linker para o total medido. `arithmetic`/`minimal` agora reservam 0 bytes de expressão (relatório de benchmark, `make validate`). |
| 2 | Definir um pool de temporários gerenciado pelo compilador com escopo | **Verificado** | `TemporaryPool`/`TemporarySlot` com `call_scope` (`codegen_analysis.py`); arrenda o slot livre mais baixo, liberação explícita; testes unitários `test_lowest_slot_reuse_and_call_scope_are_deterministic`, `test_pool_exhaustion_never_reuses_a_live_slot` (`tests/test_expression_temporaries.py`). |
| 3 | Rastrear aquisição e liberação de temporários durante a redução de expressões | **Verificado** | Chamadas `acquire`/`release` em `_load_binary_expression`, `_comparison_setup` e no caminho de decremento do `for` (`nes_pascal/backend_ca65.py`); o emissor verifica que seu pico observado corresponde exatamente à reserva. |
| 4 | Calcular o máximo de temporários de expressão simultaneamente vivos para o programa compilado | **Verificado** | `expression_temporary_requirement` por declaração, máximo em todo o programa; verificado contra o pico de emissão em `generate()`; bateria de probes (redução primeiro à direita, empilhamento de irmãos, cadeias aninhadas à esquerda) reproduziu máximos exatos incluindo uma cadeia de 17 slots. |
| 5 | Alocar apenas o número necessário de temporários de expressão | **Verificado** | Região do linker igual ao total medido; 19 de 20 benchmarks reservam zero bytes de expressão, `arrays` reserva um; `test_zero_temp_program_reserves_and_emits_no_expression_slot`. |
| 6 | Preservar o posicionamento em Zero Page para temporários enquanto houver capacidade | **Verificado** | Slots de expressão permanecem no prefixo de política `$0010-$001F`; regiões `ZP_TEMP`/`ZP_TEMP_FREE`; endereços de usuário inalterados (janela explícita futura `$0020-$007F`, promoção automática `$0080-$00FF`); `test_runtime_temporary_and_user_regions_are_deterministic`. |
| 7 | Detectar o esgotamento do pool de temporários deterministicamente | **Verificado** | `E5004` em tempo de compilação; `tests/fixtures/diagnostics/temporary_ram_exhausted.nsp` (cadeia de 18 termos, 17 temporários) emite `E5004 ... requires 17 bytes (17 expression temporaries and 0 compiler caches), but only 16 bytes are available.`; verificado em `tests/test_memory_layout.py:230-247`; probe de contorno: 17 termos (16 temporários) aceitos, 18 termos (17 temporários) rejeitados. |
| 8 | Suportar árvores de expressão aninhadas sem aliasing acidental | **Verificado** | Arrendamento do slot livre mais baixo com liberação explícita; cadeias aninhadas de 2 e 3 níveis mantêm os slots 0/1, 0/1/2 distintos; `test_one_two_and_deeper_requirements_match_actual_liveness`, `test_sequential_deep_expressions_reuse_three_slots`; golden focado `tests/golden/expression-temporaries.asm`. |
| 9 | Suportar expressões de índice de array sem corromper o estado da expressão ao redor | **Verificado** | Leituras aninhadas `Values[Indexes[I]]`, índices de record escalados, escritas indexadas; escritas indexadas ainda salvam o índice na pilha de hardware 6502 durante a avaliação do RHS; Mesen verifica escritas/leituras indexadas; `test_arrays_records_procedure_arguments_and_builtins_share_one_pool`. |
| 10 | Preservar a semântica de avaliação de argumentos de chamada de procedimento | **Verificado** | Preparação de argumentos da esquerda para a direita mantida; fluxos de instrução pré/pós-0.5.11 idênticos byte a byte para os benchmarks `procedure_parameters`/`procedures`; asserções focadas de assembly na fixture de temporários de expressão. |
| 11 | Definir o comportamento de salvar/restaurar ou de não-aliasing exigido para futuras chamadas de função aninhadas | **Verificado** | `call_scope` preserva todo arrendamento de propriedade do chamador; a redução aninhada só pode adquirir um slot não arrendado; chamadas de valor de builtin já exercitam o limite; contrato adiante documentado para Funções. Frames de runtime e salvar/restaurar são deliberadamente adiados (0.5.12). |
| 12 | Tornar o modelo de temporários seguro para chamadas antes que Funções sejam habilitadas | **Verificado** | Pool + `call_scope` é estruturalmente não-aliasing através de limites de chamada; a redução de argumentos de builtin o exercita; `test_lowest_slot_reuse_and_call_scope_are_deterministic`. Nenhuma sintaxe de Funções introduzida. |
| 13 | Preservar mapas de memória determinísticos | **Verificado** | `test_linker_configuration_and_memory_map_are_reproducible`, `test_temporary_symbol_allocation_is_deterministic`; regeneração idêntica byte a byte entre compilações repetidas. |
| 14 | Relatar a reserva de temporários de expressão nos diagnósticos de memória | **Verificado** | O mapa de memória imprime as linhas `Expression temporary reservation: N bytes (maximum simultaneously live)`, `Compiler caches` separadas e `Recovered temporary Zero Page`; verificado contra os mapas de `memory_layout.nsp`/`counting.nsp`. |
| 15 | Adicionar testes para requisitos de zero, um, dois e mais temporários | **Verificado** | `test_zero_temp_program_reserves_and_emits_no_expression_slot`, `test_one_two_and_deeper_requirements_match_actual_liveness`, `test_sequential_deep_expressions_reuse_three_slots`. |
| 16 | Adicionar testes provando que programas simples não reservam mais bytes de temporários de expressão não usados | **Verificado** | `test_zero_temp_program_reserves_and_emits_no_expression_slot`; `arithmetic`/`minimal` reservam 0 bytes e não emitem `expression_temporary_0`. |
| 17 | Adicionar testes para expressões aninhadas de array/índice | **Verificado** | Fixture de runtime `tests/fixtures/runtime/expression_temporaries.nsp` (`Values[Indexes[I]]` aninhado, escritas indexadas, leituras/escritas de array de records) + script Mesen `tests/mesen/verify_expression_temporaries.lua` + golden focado. |
| 18 | Adicionar testes de regressão para ordem de avaliação de expressões e wrap-around de 8 bits | **Verificado** | Fixture de runtime verifica wrap-around `$F0 + $20 = $10`, reutilização sequencial de slots, materialização de comparação aninhada; identidade de fluxo de instruções pré/pós em todo o corpus prova a preservação da ordem. |
| 19 | Comparar o uso de Zero Page com a linha de base 0.5.5 | **Verificado** | Tabela "0.5.5 fixed-window comparison" de `expression-temporaries-0.5.11.md` (janela legada, máximo vivo, nova expressão, caches, ZP líquida economizada por benchmark; agregado comparativo de 311 bytes); a nota histórica de `optimization-audit-0.5.5.md` preserva a linha de base. Verificação pontual contra a saída de benchmark viva. |
| 20 | Não implementar Funções nesta milestone | **Verificado** | Nenhuma sintaxe/parsing/valores de retorno de função; o roadmap marca 0.5.11 como Concluído e 0.5.12 Funções como Planejado; `docs/compiler/expression-temporaries-0.5.11.md` adia Funções explicitamente. |

**Requisitos do roadmap não cobertos:** nenhum. Todos os 20 requisitos estão
implementados, documentados e exercitados por testes, fixtures, goldens ou
benchmarks.

---

## 2. Cobertura semântica positiva

### Casos normais / comuns (cobertos)
- Aritmética direta e programas simples: 0 temporários, 16 bytes de ZP
  recuperados (unidade + benchmark).
- Expressões de dois e três operandos: pico de 1 e 2 slots; cadeia aninhada de
  quatro operandos: pico 3 (tabela de fixture e golden focado).
- Declarações sequenciais reutilizam `expression_temporary_0`; declarações
  posteriores reutilizam todos os slots.
- A materialização de comparação mantém o resultado aritmético e o operando de
  comparação distintos (pico 2).

### Condições de contorno (cobertas)
- Capacidade exata: 17 termos (16 temporários) aceitos; 18 termos (17
  temporários) `E5004` (verificado por probe).
- 16 termos + 1 byte de cache aceitos; 17 termos + 1 byte de cache `E5004`
  (verificado por probe).
- 0 temporários + 16 bytes de cache aceitos; 0 temporários + 17 bytes de cache
  `E5004` (verificado por probe).
- Temporários obrigatórios nunca tomam emprestado o espaço opcional de promoção
  (`test_zero_page.py:100`, `counting.nsp` no limite de 5 bytes).
- Região de linker `ZP_TEMP` de tamanho zero aceita pelo ld65 (todos os
  benchmarks e o link do ROM minimal).
- `ZP_TEMP` de tamanho zero com `ZP_TEMP_FREE` de tamanho zero (saturação exata
  de 16 bytes) aceitos.

### Interações (cobertas)
- Arrays × expressões: cadeias `Values[Index] + Values[Index]` (fixture, probes
  de contorno).
- Índices aninhados: `Values[Indexes[I]]` (fixture, Mesen).
- Records: leituras e escritas de array de records dentro de expressões
  (fixture, Mesen).
- Argumentos de procedimento: duas expressões de argumento avaliadas e
  preparadas (fixture, Mesen).
- Argumentos de valor de builtin: `nes.set_background_color($21)` (fixture).
- Laços `for`: caches `for_limit_*` como categoria de contabilidade separada
  compartilhando a mesma janela (relatório de benchmark; counting/arrays mantêm
  caches, nunca mal rotulados).
- Wrap-around de 8 bits: `$F0 + $20 = $10` (Mesen).
- Redução Booleana de curto-circuito e comparações diretas por flag inalteradas
  (identidade de instruções de benchmark).

### Casos apenas cobertos indiretamente
- A saturação exata de 16 bytes de temporários+caches combinados não tem teste
  unitário dedicado, apenas verificação por probe (P3-1).

---

## 3. Matriz de cobertura de diagnósticos

| Condição inválida | Código esperado | Teste / fixture existente | Status |
| --- | --- | --- | --- |
| Temporários de expressão + caches excedem 16 bytes | `E5004` | `tests/fixtures/diagnostics/temporary_ram_exhausted.nsp` + `tests/test_memory_layout.py:230-247` | Coberto |
| Armazenamento obrigatório toma emprestado o espaço opcional de promoção | `E5004` | `tests/test_zero_page.py:100` (`counting.nsp` no limite de 5 bytes) | Coberto |
| Requisito combinado e componentes declarados | mensagem de `E5004` | verificada: "requires 17 bytes (17 expression temporaries and 0 compiler caches), but only 16 bytes are available." | Coberto |
| Esgotamento do pool nunca reutiliza um slot vivo | `TemporaryPoolExhausted` | `test_pool_exhaustion_never_reuses_a_live_slot` (unidade) | Coberto |
| Pico do emissor divergente vs. reserva | asserção interna | asserção de `generate()`, exercitada pela fixture focada e pelo corpus de benchmark | Coberto |
| Borda de saturação programática (temporários+caches exatamente 16; 17) | contorno de `E5004` | verificado por probe no limite da CLI | lacuna P3-1 (unidade) |

`E5004` está registrado no catálogo, documentado em `docs/DIAGNOSTICS.md` e
`docs/reference/diagnostics/code-generation.md`, e validado por
`test_diagnostic_catalog.py`. A mensagem do diagnóstico em si é precisa, declara
o requisito combinado e seus componentes, e nunca envolve, cria aliasing, toma
emprestado espaço de promoção ou derrama silenciosamente.

**Defeito de documentação (P3-2):** o exemplo "Expected compiler output" de
`E5004` em `docs/reference/diagnostics/code-generation.md` (EN e PT-BR) mostra o
texto da mensagem pré-0.5.11 ("Expression and loop code requires 17 temporary
bytes...") em vez do texto real emitido ("Compiler-managed Zero Page storage
requires 17 bytes (17 expression temporaries and 0 compiler caches), but only 16
bytes are available."). Os testes de catálogo validam apenas a presença e a
unicidade dos códigos, não o texto da mensagem do exemplo.

---

## 4. Cobertura por camada de parser / semântica / backend

| Camada | Evidência | Avaliação |
| --- | --- | --- |
| Lexer / Parser | Sem mudança de sintaxe; sem novos tokens ou gramática | N/A (corretamente N/A no mapa de cobertura) |
| Semântica | Nenhuma semântica de linguagem-fonte mudada; sem novos tipos de nó resolvidos | N/A (corretamente N/A no mapa de cobertura) |
| AST | Inalterado; o modelo de temporários é interno ao compilador | N/A (corretamente N/A no mapa de cobertura) |
| Layout de memória | dimensionamento em `memory_layout.py`, regiões de linker `ZP_TEMP`/`ZP_TEMP_FREE`, local de lançamento de E5004, relato em mapa de memória; testes determinísticos de região/símbolo | Coberto |
| Backend | análise pré-layout em `codegen_analysis.py` + aquisição com escopo em `backend_ca65.py`; 7 testes unitários focados; golden | Coberto |
| Suporte de runtime | nenhum necessário — sem mudanças de runtime, sem descritor/helper emitido | Coberto |

---

## 5. Auditoria do Assembly golden

`tests/golden/expression-temporaries.asm` é um golden parcial focado registrando
toda declaração e uso de temporário de expressão: declarações dos slots 0/1/2,
sequências de adquirir/armazenar/consumir/liberar, reutilização sequencial,
índices de array aninhados, escritas indexadas, acesso a array de records,
materialização de comparação e preparação de argumentos de procedimento. Ele
segue a convenção estabelecida de golden focado.

Classificação: **obrigatório — existe.** Ele protege o contrato de identidade,
reutilização e ordenação determinísticas, que é a superfície crítica para a
estabilidade desta milestone. Nenhum golden de arquivo completo adicional é
justificado.

---

## 6. Validação de toolchain

- O corpus completo de 20 benchmarks monta e linka através de ca65/ld65 com a
  nova região variável `ZP_TEMP`, incluindo os casos de tamanho zero e de
  saturação exata (`make validate`).
- `make rom` produz `build/minimal.nes` (NROM válido) sob o novo layout.
- A fixture de runtime de temporários de expressão compila para um ROM e roda sob
  Mesen headless (veja seção 7).
- Sem regressão de configuração de linker: `ZP_TEMP_FREE` é ordenado entre
  `ZP_TEMP` e a janela explícita, e todas as regiões permanecem sem sobreposição
  e dentro dos limites de Zero Page.

---

## 7. Cobertura de runtime no Mesen

`tests/mesen/verify_expression_temporaries.lua` executa a fixture de temporários
de expressão e verifica memória de runtime concreta:
- resultado aritmético de três níveis,
- wrap-around `$F0 + $20 = $10`,
- reutilização sequencial de slots,
- leituras aninhadas `Values[Indexes[I]]`,
- escritas indexadas de array,
- leituras e escritas de array de records,
- materialização de comparação aninhada,
- duas expressões de argumento de procedimento.

Os endereços da fixture foram verificados de forma cruzada independentemente
contra o mapa de memória real (conteúdos da região de temporários de expressão
`$0217-$0219`, índice `$020A`, resultado de record `$0215`, base de arrays
`$0210`, resultado `$0216`) e todos coincidiram. Conectada como
`test_expression_temporaries_preserve_nested_runtime_values`; todos os 28
`MesenIntegrationTests` passam localmente. Esta é uma verificação comportamental,
não uma verificação de apenas-ROM-inicializa.

---

## 8. Cobertura de benchmark / recursos

- `test_benchmark_accounting.py` reconcilia cada categoria com o espaço de
  endereço de CPU NES de 2.048 bytes do corpus; o relatório de `make benchmark`
  é regenerado idêntico byte a byte (verificado com `md5sum` em duas execuções).
- Temporários de expressão são relatados como categoria própria; caches
  `for_limit_*` são separados e nunca mal rotulados como temporários de expressão
  (`counting` mantém 6, `arrays` mantém 2).
- **Invariantes de qualidade de código preservados:** o Assembly gerado pré-0.5.11
  vs. pós-0.5.11 é idêntico byte a byte para todos os 20 benchmarks, exceto uma
  única mudança de comentário na declaração de `expression_temporary_0`
  ("reusable" → "scoped reusable"). O tamanho de código/ocupado de PRG, a
  contagem de instruções e os ciclos estáticos estimados são inalterados; apenas
  a reserva de dados e o relato no mapa diferem.
- 19 benchmarks agora reservam zero bytes de expressão; `arrays` reserva um. A
  economia líquida de ZP vs. a janela legada de 16 bytes está documentada por
  benchmark (agregado comparativo de 311 bytes) e corresponde às medições vivas.
- Nenhum novo limite ou gate de desempenho foi introduzido.

---

## 9. Cobertura de documentação

Verificados: `docs/compiler/expression-temporaries-0.5.11.md`,
`docs/runtime/cpu-memory.md`, `docs/reference/diagnostics/code-generation.md`,
`docs/DIAGNOSTICS.md`, `docs/compiler/test-coverage-map.md`, `docs/index.md`,
README, roadmap `0.md` + `README.md`, mais as notas históricas adicionadas a
`arrays-0.5.8.md`, `low-risk-codegen-0.5.7.md`, `optimization-audit-0.5.5.md` e
`records-0.5.10.md` — cada um verificado em EN e no PT-BR mantido.

- O estado do roadmap está correto: `0.5.11` marcado como Concluído com todos os
  20 itens marcados; índice atualizado (última concluída `0.5.11`, próxima
  milestone `0.5.12` Funções).
- Sincronização EN/PT-BR verificada (cabeçalhos, mesmas seções/códigos,
  identificadores de diagnósticos preservados; índice e mapa de cobertura do
  PT-BR atualizados; contagem do Mesen 27→28 em ambos).
- Notas históricas nos relatórios 0.5.5/0.5.7/0.5.8/0.5.10 são precisas
  (verificadas contra a saída de benchmark viva: `arrays` 1 expressão + 2 bytes
  de cache = 13 recuperados; `records` 0 bytes = 16 recuperados).
- Divergências encontradas e disposição:
  - **Não corrigido (relatado):** a mensagem de exemplo de `E5004` em
    `code-generation.md` (EN + PT-BR) está desatualizada (P3-2).
  - **Não corrigido (relatado):** "Recovered temporary Zero Page" é descrito como
    "allocator-visible free memory"; ela é livre na configuração do linker e
    relatada como Livre no mapa, mas nenhum alocador do compilador coloca dados
    lá atualmente. É texto prospectivo, não um erro (P3-3, informativo).
  - **Preciso, verificado:** a afirmação "475 testes automatizados não-Mesen e
    todos os 28 testes Mesen headless dedicados" equivale à suíte atual de 503
    testes (475 + 28); não está desatualizada.

---

## 10. Mapa de cobertura de testes

`docs/compiler/test-coverage-map.md` (EN/PT-BR) adiciona o subsistema 30
"Alocação de temporários de expressão" com Strong em Diagnósticos e Fixtures,
Layout de Memória, Backend ASM, Golden ASM, Toolchain, Mesen Runtime e Corpus de
Benchmark, e N/A para Lexer/Parser/Semântica. Esta classificação é defensável:
testes unitários focados, uma fixture de esgotamento, um golden focado,
montagem/linkagem de toolchain do corpus, um teste de runtime no Mesen e
contabilidade exata de benchmarks existem para cada nível aplicável. Nenhuma
correção do mapa é justificada.

---

## 11. Auditoria de regressão e interação

- Suíte completa: **503 testes, OK** (475 não-Mesen + 28 Mesen), sem pulos, sem
  falhas — incluindo todos os testes pré-existentes de linguagem, backend,
  memória, golden e runtime.
- Assembly gerado pré/pós-0.5.11 idêntico byte a byte em todos os 20 benchmarks
  (exceto um comentário) — sem regressão de instrução, tamanho ou ciclo, e a
  ordem de avaliação de expressões é preservada para cada formato do corpus.
- `make validate` (test-all + benchmark + rom): **OK**.
- Probes de interação direcionados: limites de capacidade de 17/18 termos,
  limites combinados de temporários+caches, regiões de tamanho zero e saturadas,
  bateria de pico de vivacidade em todos os formatos de declaração/expressão,
  texto e posição da mensagem de E5004 (`1:1`) e verificação cruzada de endereço
  de fixture vs. mapa de memória.
- Exemplos, goldens e scripts Mesen pré-existentes não afetados.

---

## 12. Lacunas de cobertura e descobertas

| Severidade | Descoberta |
| --- | --- |
| P0 | Nenhuma encontrada. Nenhum defeito de correção ou semântica identificado. |
| P1 | Nenhuma. Todos os 20 requisitos documentados da milestone estão implementados e têm proteção de regressão focada. |
| P2 | Nenhuma. Limites de capacidade, esgotamento do pool, não-uso-emprestado de promoção e invariantes de contabilidade são todos cobertos por testes ou fixtures. |
| P3-1 | Nenhum teste unitário automatizado para o limite exato de saturação combinada (temporários + caches); verificado apenas por probes de CLI. Mesmo caminho de código da fixture; baixo valor incremental. |
| P3-2 | `docs/reference/diagnostics/code-generation.md` mostra o texto da mensagem pré-0.5.11 no "Expected compiler output" de `E5004` (EN e PT-BR). |
| P3-3 | O texto "Recovered temporary Zero Page ... allocator-visible free memory" é prospectivo; nenhum alocador coloca dados no sufixo recuperado atualmente (informativo). |

---

## 13. Resultados de validação local

- `make test-all` (`PYTHON=python3`, `MESEN_PATH=/opt/mesen/Mesen`): **503
  testes, OK** (0 pulados), incluindo `test_expression_temporaries` (7),
  `test_benchmark_accounting`, `test_memory_layout` e todos os 28
  `MesenIntegrationTests`.
- `make benchmark`: **OK**; relatório regenerado idêntico byte a byte entre
  execuções; contabilidade reconcilia com 2.048 bytes.
- `make rom`: **OK**; `build/minimal.nes` produzido.
- `make validate` (teste + benchmark + rom): **OK**.
- Diff de Assembly pré/pós em 20 benchmarks: idêntico byte a byte exceto um
  comentário; PRG/instruções/ciclos inalterados.
- Determinismo: compilação repetida produz Assembly idêntico byte a byte e
  relatórios de benchmark idênticos.
- Nota: `make validate` exige `PYTHON=python3` neste ambiente porque o Makefile
  padroniza para `python`; CI não é afetado.

## 14. Execução do GitHub Actions

Push de `audit/0.5.11-validation` (`ab557e2`). O pipeline de CI autoritativo
(`.github/workflows/ci.yml`) rodou contra o branch enviado: execução do GitHub
Actions `31767587223` (número de execução 50, evento `push`, head `ab557e2`).

- Job `compiler-toolchain`: **concluído / sucesso**
- Job `mesen-runtime`: **concluído / sucesso**
- Job `ci-gate`: **concluído / sucesso**

## 15. Gate de CI final

O job agregado `ci-gate` **passou** para o branch enviado, confirmando os jobs de
toolchain do compilador e de runtime do Mesen e o gate geral remotamente. A
evidência local (seção 13) concorda com o resultado remoto.

---

## Recomendação

**PRONTA**

Todos os vinte requisitos da milestone 0.5.11 são verificados contra evidências
concretas (implementação, testes unitários, fixture de esgotamento, golden
focado, montagem/linkagem de toolchain, runtime no Mesen, contabilidade de
benchmark, documentação). A funcionalidade está distribuída corretamente entre
análise, layout de memória e backend; o emissor verifica o acordo exato com a
análise pré-layout, de modo que a divergência análise/emissão é uma falha sonora
em tempo de compilação em vez de corrupção silenciosa. A ordem de avaliação, a
materialização Booleana, a redução de curto-circuito e todos os invariantes de
tamanho de código/ciclos são preservados (fluxos idênticos byte a byte no
corpus). Não existem descobertas P0, P1 ou P2. Os itens P3 restantes são polimento
de documentação e um detalhe de teste de contorno, nenhum dos quais bloqueia os
critérios de aceite da milestone.