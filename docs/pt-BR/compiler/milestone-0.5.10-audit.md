# Milestone 0.5.10 — Records: Auditoria de Completude e Qualidade

[English](../../compiler/milestone-0.5.10-audit.md) | Português (Brasil)

- **Branch:** `audit/0.5.10-validation`
- **Commit base da auditoria:** `b9e4075` (merge do PR #21, `0.5.10-records`)
- **Commit de implementação da milestone:** `36534f7` ("Implement 0.5.10 records")
- **Data da auditoria:** 2026-08-13
- **Papel do auditor:** revisor independente de QA (não o implementador original)

Este documento é um artefato de revisão independente da milestone 0.5.10
(Records). Ele é distinto do relatório de implementação
[`records-0.5.10.md`](records-0.5.10.md), que é o instantâneo da milestone feito
pelo implementador. Esta auditoria registra verificação baseada em evidências,
descobertas de cobertura e um backlog para endurecimento de acompanhamento.

---

## 1. Matriz de requisitos da milestone

O contrato é a seção Records de `roadmap/0.md` (identificador `0.5.10`,
anteriormente Milestone 26). Todos os onze requisitos foram verificados contra
evidências concretas do repositório, não nomes ou comentários.

| # | Requisito | Status | Evidência |
| --- | --- | --- | --- |
| 1 | Tipos de record definidos pelo usuário | **Verificado** | Parsing de `RecordTypeDeclaration` (`nes_pascal/parser.py:143-186`), resolução semântica (`nes_pascal/semantic.py:_resolve_record_types`); testes `test_lexer_and_parser_preserve_named_record_structure`, `test_resolves_nominal_layout_and_typed_fields` (`tests/test_records.py`); exemplo `examples/records.nsp`. |
| 2 | Campos byte | **Verificado** | `RecordField` com `BuiltInType.BYTE`; offsets de campo verificados (`tests/test_records.py:106-109`); golden `tests/golden/records.asm` (`sta variable_Player`). |
| 3 | Campos Booleanos | **Verificado** | Campo `BuiltInType.BOOLEAN`, canônico `$00`/`$01`; golden `records.asm` (`sta variable_Player + 2`, `lda #$01 ; true`); Mesen verifica `Enemies[0].Visible` em `$0207` (`tests/mesen/verify_records.lua`). |
| 4 | Campos de enumeração | **Verificado** | Campo `EnumType`; regras de atribuição por tipo exato (`test_enum_fields_reject_members_from_a_different_enum`); golden `cmp #$01`; Mesen verifica `Enemies[0].State` em `$0206`. |
| 5 | Variáveis de record | **Verificado** | `ResolvedVariable` com `RecordType`; RAM regular contígua (`test_records_and_record_arrays_are_contiguous_regular_ram`); Mesen verifica `Player.X/Y/State/Visible` em `$0214-$0217`. |
| 6 | Acesso a campo de record | **Verificado** | `RecordFieldExpression` → `ResolvedRecordField` (`semantic.py`), `_load_record_field` (`backend_ca65.py:3057-3076`); leituras no golden; leituras em runtime no Mesen. |
| 7 | Atribuição a campo de record | **Verificado** | `RecordFieldAssignment` → `ResolvedRecordFieldAssignment`; escritas diretas e com offset escalado; escritas no golden; escritas em runtime no Mesen. |
| 8 | Arrays de records | **Verificado** | Elemento de `ArrayType` como `RecordType`; `_type_storage_size` (`memory_layout.py`); escalonamento ciente do tamanho (potências de dois via `asl`, outros via adição repetida local); `test_rejects_variable_scaled_offsets_beyond_one_byte`; Mesen `Enemies[1]` em `$0208-$020B`. |
| 9 | Calcular tamanhos de records em tempo de compilação | **Verificado** | `RecordType.size` = quantidade de campos; tamanho 4 verificado (`tests/test_records.py:105`); arrays de records dimensionados em 16/32 bytes no teste de layout; o mapa de memória informa nomes de tipos. |
| 10 | Gerar offsets de campos | **Verificado** | `RecordField.offset` baseado em zero; offsets `[0,1,2,3]` verificados; golden `variable_Player + 1/2/3`; `_resolved_record_field_operand` dobra `index * size + offset`. |
| 11 | Detectar definições recursivas não suportadas de records | **Verificado** | `E4023` para autorreferência direta (`semantic.py:_resolve_record_types`); fixture `recursive_record_definition.nsp`; verificado em `test_record_diagnostic_fixtures_are_focused_and_stable`. Recursão indireta (mútua) também é rejeitada (`E4022`, tipo de campo aninhado não suportado). |

**Requisitos do roadmap não cobertos:** nenhum. Todos os 11 requisitos estão
implementados, documentados e exercitados por testes ou fixtures.

---

## 2. Cobertura semântica positiva

### Casos normais / comuns (cobertos)
- Leituras e escritas de campos de record isolados (`Player.X`, `Player.Y`, `Player.Active`, `Player.State`): golden + Mesen + testes unitários.
- Acesso a elemento de array de records com índices constantes e variáveis: `Enemies[$00]`, `Enemies[$02]`, `Enemies[Index]` (golden, `test_indexed_write_preserves_index_before_evaluating_rhs`, Mesen).
- Campos enum e Booleanos com regras de tipo exatas: `test_field_types_use_existing_strict_assignment_rules`, `test_enum_fields_reject_members_from_a_different_enum`.
- Leituras de campo dentro de condições `if` e comparações: golden (`if Player.Active then`, `if Player.State = Moving then`); Mesen (`if Enemies[Index].State = Active then`).

### Condições de contorno (cobertas)
- Offset escalado máximo legal exatamente `$FF` aceito; `$100` rejeitado (`test_rejects_variable_scaled_offsets_beyond_one_byte`, e `array[$00..$3F]` de tamanho 4 verificado por probe → offset 255 aceito, `array[$00..$40]` → 259 rejeitado).
- Record com 256 campos aceito; 257 campos rejeitado (`E4024`) — verificado por probe, mas não na suíte automatizada (veja P2-1).
- Record de um byte nunca promovido automaticamente para Zero Page (`test_one_byte_record_is_never_automatically_promoted`).
- Record vazio rejeitado (`E4024`) — verificado por probe, não na suíte automatizada (veja P2-1).
- Tamanho de record não potência de dois usa adição repetida local (`test_non_power_of_two_record_size_uses_local_repeated_addition`).
- Índice constante grande de array de records dobra em um endereço ca65 de 16 bits (`variable_Enemies + 960` para `Enemies[$F0]`) — verificado por probe.

### Interações (cobertas ou verificadas por probe)
- Records × aritmética: `Result := Result + Player.X` emite operando RHS direto `adc variable_Player` (verificado por probe).
- Records × operadores Booleanos: `not`, `and` em curto-circuito com campos de record (verificado por probe).
- Records × comparações: igualdade com operandos imediatos e de campo (golden, probe).
- Records × procedimentos: campo de record como argumento `byte` (`Take(Player.X)`) — verificado por probe, não na suíte (veja P3).
- Records × fluxo de controle: laços `for` sobre arrays de records, `while`/`repeat` com condições de campo — verificado por probe, não na suíte (veja P3).
- Records × atribuição definitiva: escrita de campo marca o record como atribuído; leitura antes de atribuição produz `E3008` tanto para records isolados quanto para arrays de records (verificado por unidade/probe; regra agregada consistente com arrays).
- Records × callbacks: callback de update lendo um campo de record global; aplicação do requisito de bloco principal (verificado por probe).
- Records inteiros rejeitados como valores: atribuição `E4025` (fixture), comparação `E4025` (verificado por probe, veja P2-2), leitura escalar `E4025`, argumentos de procedimento/builtin de record inteiro (verificado por probe).
- Arrays de enum permanecem rejeitados (`E4010`); campos de record não podem ser arrays nem records aninhados (`E4022`).

### Casos apenas cobertos acidentalmente
- Campos de record dentro de procedimentos e laços não fazem parte da suíte automatizada; eles funcionam pelos mesmos caminhos de resolução dos casos cobertos, mas carecem de testes de regressão focados (P3).

---

## 3. Matriz de cobertura de diagnósticos

| Condição inválida | Código esperado | Teste / fixture existente | Status |
| --- | --- | --- | --- |
| Campo de record duplicado | `E4019` | `tests/fixtures/diagnostics/duplicate_record_field.nsp` + `test_records.py` | Coberto |
| Campo de record desconhecido (atribuição) | `E4020` | `tests/fixtures/diagnostics/unknown_record_field.nsp` + `test_records.py` | Coberto |
| Campo de record desconhecido (leitura de expressão) | `E4020` | sem fixture dedicada (mesmo caminho de código da atribuição) | lacuna P3 |
| Acesso a campo em escalar (atribuição) | `E4021` | `tests/fixtures/diagnostics/field_access_on_non_record.nsp` + `test_records.py` | Coberto |
| Acesso a campo em escalar (leitura) | `E4021` | sem fixture dedicada (mesmo caminho de código) | lacuna P3 |
| Tipo de campo não suportado — campo array | `E4022` | `tests/fixtures/diagnostics/unsupported_record_field_type.nsp` + `test_records.py` | Coberto |
| Tipo de campo não suportado — campo de record aninhado/desconhecido | `E4022` | sem fixture | lacuna P3 |
| Definição recursiva direta de record | `E4023` | `tests/fixtures/diagnostics/recursive_record_definition.nsp` + `test_records.py` | Coberto |
| Record vazio | `E4024` | `tests/fixtures/diagnostics/empty_record_definition.nsp` + `test_records.py` | **Resolvido** |
| Record excedendo 256 campos | `E4024` | `tests/fixtures/diagnostics/oversized_record_definition.nsp` + `test_records.py` | **Resolvido** |
| Offset variável de array de records > `$FF` | `E4024` | `test_rejects_variable_scaled_offsets_beyond_one_byte` | Coberto |
| Atribuição de record inteiro | `E4025` | `tests/fixtures/diagnostics/invalid_record_usage.nsp` + `test_records.py` | Coberto |
| Comparação de record inteiro | `E4025` | `tests/fixtures/diagnostics/whole_record_comparison.nsp` + `test_records.py` | **Resolvido** |
| Record inteiro usado como escalar | `E4025` | sem fixture (verificado por probe) | lacuna P3 |
| Tipo de record desconhecido para uma variável | `E4001` | `test_unknown_record_type_uses_the_existing_unknown_type_diagnostic` | Coberto |
| Identificador de record desconhecido (leitura) | `E3005` | sem fixture dedicada (caminho de identificador genérico) | lacuna P3 |
| Leitura de campo de record antes de atribuição | `E3008` | sem fixture específica de record (caminho genérico de atribuição definitiva) | lacuna P3 |
| Tipo de record como tipo de parâmetro de procedimento | `E4001` "Unknown type" | sem teste — diagnóstico enganoso (veja P3-3) | lacuna P3 |

Todos os oito códigos de diagnóstico novos de records (`E4019`-`E4025`) estão
registrados no catálogo, documentados em `docs/DIAGNOSTICS.md` e
`docs/reference/diagnostics/type-system.md`, e validados por
`test_diagnostic_catalog.py`.

Caminhos de erro implementados no código mas nunca exercitados por um teste:
record inteiro usado como escalar, e tipo de record usado como tipo de
parâmetro. Os dois caminhos P2 antes não exercitados (record vazio, record acima
de 256 campos) e a comparação de record inteiro agora são cobertos pelas
fixtures adicionadas na tarefa de endurecimento abaixo (veja
[Descobertas P2 resolvidas](#descobertas-p2-resolvidas)).

---

## 4. Cobertura por camada de parser / semântica / backend

| Camada | Evidência | Avaliação |
| --- | --- | --- |
| Lexer | `TokenKind.RECORD` verificado via `tokenize("Entity = record X: byte; end;")` (`test_records.py`) | Coberto |
| Parser | Teste de estrutura de record, testes de declaração malformada (`E2102`), probes de ordenação de seção de tipos, tratamento de DOT em atribuição/expressão (`parser.py`) | Coberto |
| AST | `RecordType`/`RecordField`/`RecordFieldExpression`/`RecordFieldAssignment` + nós resolvidos; testes unitários de layout nominal | Coberto |
| Semântica | 17 testes unitários, 9 fixtures focadas, testes de rigidez de tipo, atribuição definitiva, hooks de segurança de VBlank, `_expression_type_hint` para comparações | Coberto |
| Layout de memória | layout contíguo, dimensionamento de array de records, exclusão de promoção, esgotamento de RAM (`E5003`), contabilidade de temporários, saída de mapa de memória | Coberto |
| Backend | assembly golden, escalonamento de potência de dois e não potência de dois, ordem de avaliação de escrita indexada, operandos RHS diretos, `_zero_flag_is_valid` para cargas de campo | Coberto |
| Suporte de runtime | nenhum necessário — nenhum runtime de record, descritor ou helper emitido (verificado: `record_runtime`/`record_descriptor` ausentes; `runtime_features == ()`) | Coberto |

---

## 5. Auditoria do Assembly golden

`tests/golden/records.asm` é um golden parcial focado cobrindo o núcleo de
declarações `Index`/`Player`/`Enemies` da fixture de codegen `records.nsp`:
escritas de campo diretas e com índice constante, leituras de campo, código de
branch enum/Booleano, e escritas/leituras escaladas com índice variável (`asl`
×2, `adc #$01`, `tax`, `lda ...,x`). Ele segue a convenção estabelecida de golden
focado usada para arrays (`arrays-addressing.asm`) e enumerações
(`enumerations.asm`).

Classificação: **obrigatório — existe.** O endereçamento com índice escalado e os
operandos de campo diretos são formatos de redução críticos para estabilidade e
estão adequadamente protegidos. Nenhum golden de arquivo completo adicional é
justificado.

---

## 6. Validação de toolchain

- `examples/records.nsp` compila por NES Pascal → ca65 → ld65 → uma imagem NROM
  válida (40976 bytes; cabeçalho `NES`/`$1A`, 2 bancos de PRG, 1 banco de CHR,
  mapper 0).
- Automatizado: `test_records_example_builds_valid_nrom_image`
  (`tests/test_integration.py`) valida cabeçalho, mapper, bancos, vetores,
  tamanho de CHR e tamanho de ROM.
- Assembly gerado inspecionado: offsets de campo (`variable_Player + 1/2/3`),
  indexação escalada (`variable_Enemies,x`), layout de memória corresponde aos
  endereços esperados no Mesen.

---

## 7. Cobertura de runtime no Mesen

`tests/mesen/verify_records.lua` executa `examples/records.nsp` no Mesen headless
e verifica memória de runtime concreta:
- `Enemies[0].X/Y/State/Visible` em `$0204-$0207`,
- `Enemies[1].X/Y/State/Visible` em `$0208-$020B` (escrita escalada com índice variável),
- `Player.X/Y/State/Visible` em `$0214-$0217`,
- `Index` em `$0080`, `Result` em `$0081`, `IsVisible` em `$0218`.

Esta é uma verificação comportamental significativa (layout fixo, indexação
escalada, armazenamento de campos enum/Booleano e um branch de comparação com
índice variável), não uma verificação de apenas-ROM-inicializa. Conectada como
`test_records_preserve_fixed_layout_and_scaled_indexing`; passa localmente.

---

## 8. Cobertura de benchmark / recursos

- Benchmark `records` adicionado ao corpus (`tools/measure_benchmarks.py`) com
  asserções exatas de métricas (`test_records_benchmark_reports_focused_resource_accounting`):
  PRG 389/395 B, 196 instruções, 605 ciclos-base estáticos, profundidade de
  árvore 2, máximo de temporários vivos 0, armazenamento de records 20 B de RAM
  regular, ZP promovida 2 B, recursos de runtime nenhum.
- Os 19 workloads de benchmark pré-existentes mantêm as métricas anteriores;
  verificados contra as linhas de base documentadas em `arrays-0.5.8.md` e
  `enumerations-0.5.9.md` (PRG/instruções/ciclos todos inalterados).
- A contabilidade de armazenamento de records (`_type_storage_size`) cobre
  records isolados e arrays de records; sem reservas ocultas de ZP; sem emissão
  de recursos de runtime para programas sem records.
- Nenhum limite ou gate de desempenho foi introduzido.

---

## 9. Cobertura de documentação

Verificados: `docs/language/records.md`, `docs/compiler/records-0.5.10.md`,
`docs/reference/diagnostics/type-system.md`, `docs/DIAGNOSTICS.md`,
`docs/reference/unsupported-features.md`, `docs/language/{arrays,assignments,
expressions,program-structure,types,constants-and-variables}.md`,
`docs/language/index.md`, `docs/reference/index.md`, `docs/index.md`,
`docs/getting-started/building-and-running.md`, `README.md`, roadmap
`0.md` + `README.md` e `docs/compiler/test-coverage-map.md` — cada um verificado
em EN e no PT-BR mantido.

- O estado do roadmap está correto: `0.5.10` marcado como Concluído com todos os
  11 itens marcados; índice atualizado (próxima milestone `0.5.11`).
- Sincronização EN/PT-BR verificada (cabeçalhos traduzidos, identificadores de
  diagnósticos preservados, mesmas seções/códigos; lista de rastreamento do PT-BR
  atualizada).
- Divergências encontradas e disposição:
  - **Corrigido durante esta auditoria:** `docs/reference/diagnostics/index.md`
    (EN e PT-BR) omitia os sete diagnósticos de record `E4019`-`E4025` do índice
    por código, pulando de `E4018` → `E5001`. Isso era uma inconsistência
    mecânica de documentação; linhas adicionadas em ambos os idiomas.
  - **Não corrigido (relatado):** `records-0.5.10.md` afirma "486 testes
    automatizados"; a suíte atual é 490 (0 pulados neste ambiente). O número é
    um instantâneo pontual desatualizado (P3).
  - **Histórico por convenção:** `arrays-0.5.8.md`, `enumerations-0.5.9.md` e
    `optimization-audit-0.5.5.md` ainda listam "arrays de records"/"records" como
    trabalho futuro. Estes são relatórios pontuais de milestone e são mantidos
    como instantâneos históricos (nota P3).

---

## 10. Mapa de cobertura de testes

`docs/compiler/test-coverage-map.md` (EN/PT-BR) adiciona o subsistema 29
"Records" com Strong em todas as camadas. Esta classificação é defensável:
testes focados, nove fixtures de diagnóstico, um golden focado, um teste de
build de toolchain, um teste de runtime no Mesen e um benchmark com asserções
exatas de métricas existem para cada camada. Nenhuma correção do mapa é
justificada. As fraquezas restantes são as lacunas de fixture P3 da seção 3, que
não mudam a classificação das camadas.

---

## 11. Auditoria de regressão e interação

- Suíte completa (491 testes) passa, incluindo todos os testes pré-existentes de
  linguagem, backend, memória e runtime — sem regressão no comportamento coberto.
- Métricas de benchmark pré-existentes inalteradas (verificadas contra as linhas
  de base documentadas) — sem regressões de tamanho de código, ciclos ou memória.
- Exemplos, goldens e scripts Mesen pré-existentes não afetados.
- Probes de interação direcionados (records × enums, arrays, procedimentos,
  builtins, laços, callbacks, atribuição definitiva, curto-circuito Booleano,
  operandos RHS diretos, uso de temporários em comparações aninhadas) todos se
  comportam corretamente.

---

## 12. Lacunas de cobertura e descobertas

| Severidade | Descoberta |
| --- | --- |
| P0 | Nenhuma encontrada. Nenhum defeito de correção ou semântica identificado. |
| P1 | Nenhuma. Todos os requisitos documentados da milestone estão implementados e têm proteção de regressão focada. |
| P2-1 | Sem fixture/teste automatizado para os caminhos `E4024` de record vazio e >256 campos (apenas o caminho de offset variável é testado). Ambos estão documentados e verificados por probe. **Resolvido pela tarefa de endurecimento (veja abaixo).** |
| P2-2 | Sem fixture/teste automatizado para comparação de record inteiro (`E4025`); apenas a atribuição de record inteiro é testada por fixture. Comportamento verificado por probe. **Resolvido pela tarefa de endurecimento (veja abaixo).** |
| P3-1 | O índice de referência de diagnósticos omitia `E4019`-`E4025` (EN + PT-BR). **Corrigido durante esta auditoria.** |
| P3-2 | A contagem "486 testes automatizados" de `records-0.5.10.md` está desatualizada/não reproduzível (suíte atual: 490). |
| P3-3 | Um record declarado usado como tipo de parâmetro de procedimento relata `E4001` "Unknown type: Rec", o que é enganoso; tipos de parâmetro enum recebem um `E3007` dedicado no parse. Nenhum teste existe. |
| P3-4 | Vários caminhos de erro de record implementados carecem de fixtures dedicadas (leitura de campo desconhecido, acesso a campo em escalar em leitura, record inteiro como escalar, leitura de campo de record antes de atribuição) — mesmos caminhos de código dos casos cobertos; baixo valor incremental. |
| P3-5 | Documentos históricos de milestone (`arrays-0.5.8.md`, `enumerations-0.5.9.md`, `optimization-audit-0.5.5.md`) mantêm o texto "records ainda não suportados"; aceitos como instantâneos históricos. |

---

## Descobertas P2 resolvidas

A tarefa de endurecimento de acompanhamento `chore/records-p2-diagnostic-hardening`
encerrou P2-1 e P2-2 com fixtures negativas focadas e asserções. Nenhum
comportamento de compilador, parser, AST, semântica, backend, runtime, layout de
memória ou definição de diagnóstico mudou; as fixtures e os testes dependem das
verificações já implementadas.

| Descoberta P2 | Fixture | Código esperado | Asserção |
| --- | --- | --- | --- |
| Regra de layout de record vazio | `tests/fixtures/diagnostics/empty_record_definition.nsp` | `E4024` | Adicionada a `test_record_diagnostic_fixtures_are_focused_and_stable` (rejeição + código + ocorrência única) e a `test_record_layout_and_usage_fixtures_target_the_intended_rule` (mensagem "Record Empty must declare at least one field.") |
| Record acima de 256 campos | `tests/fixtures/diagnostics/oversized_record_definition.nsp` (257 campos `F0`-`F256`) | `E4024` | Mesmas asserções; mensagem "Record Large exceeds the supported 256-byte layout." |
| Comparação de record inteiro | `tests/fixtures/diagnostics/whole_record_comparison.nsp` (`if A = B then`) | `E4025` | Mesmas asserções; mensagem "Whole-record comparison is not supported for type Position." |

- `oversized_record_definition.nsp` usa o menor caso determinístico que excede o
  máximo legal (257 campos); o máximo legal (256 campos) e a semântica de layout
  de record são inalterados.
- `whole_record_comparison.nsp` atribui ambos os campos do record antes de
  comparar, de modo que a fixture atinja a restrição de valor de record inteiro
  em vez de um diagnóstico anterior de atribuição definitiva.
- A suíte cresceu em um método de teste (17 testes de Records agora); a contagem
  da suíte completa na seção 13 é atualizada de acordo.

---

## 13. Resultados de validação local

- `python3 -m unittest discover -s tests`: **491 testes, OK** (0 pulados), depois
  que a tarefa de endurecimento adicionou um método de teste de Records (490
  antes).
- `make test-mesen` (`MesenIntegrationTests`): **27 testes, OK**, incluindo
  `test_records_preserve_fixed_layout_and_scaled_indexing`.
- `make validate` (teste + benchmark + ROM): **OK**; `benchmark-report` gerado e
  `build/minimal.nes` produzido.
- Probes focados de caminhos de código não testados (record vazio, record de 257
  campos, comparação de record inteiro, referências a campo enum adiante,
  recursão mútua, comparações aninhadas com temporários de record, índice
  constante > 255) todos produziram os diagnósticos esperados ou o assembly
  correto.

Nota: `make validate` exige `PYTHON=python3` neste ambiente porque o Makefile
padroniza para `python`; CI não é afetado.

## 14. Execução do GitHub Actions

CI remoto não estava acessível a partir deste ambiente (sem `gh`/rede). O gate de
CI autoritativo (`.github/workflows/ci.yml`: job do compilador, job do Mesen,
`ci-gate`) não pôde ser reverificado remotamente. Evidência local para os mesmos
jobs é relatada acima; a validação remota deve ser confirmada por uma execução de
push/PR.

## 15. Gate de CI final

Não verificável remotamente a partir deste ambiente; o equivalente local de cada
job de CI passou. Esta auditoria não alega sucesso de CI remoto. Os requisitos da
milestone e a evidência local acima são autoritativos para esta revisão.

---

## Recomendação

**PRONTA COM ENDURECIMENTO DE ACOMPANHAMENTO**

Todos os onze requisitos da milestone 0.5.10 são verificados contra evidências
concretas (implementação, testes, fixtures, golden, toolchain, Mesen, benchmark,
documentação). A funcionalidade está distribuída por todas as etapas do
compilador, tem verificação significativa em emulador e não introduz regressão.
Não existem descobertas P0 ou P1. A recomendação é direcionada pelas adições de
cobertura de teste P2 (diagnósticos de layout de record vazio/estourado e
comparação de record inteiro) e pelo polimento P3 de documentação e
diagnósticos, nenhum dos quais bloqueia os critérios de aceite da milestone.