# Mapa de Cobertura de Testes Semânticos

[English](../../compiler/test-coverage-map.md) | Português (Brasil)

Este documento fornece um mapa abrangente de cobertura de testes semânticos em todos os 28 subsistemas implementados no NES Pascal. Ele cataloga o nível atual de proteção automatizada através das fases do compilador, diagnósticos, testes de golden assembly, builds na cadeia de ferramentas, verificação em runtime no emulador Mesen, medições do corpus de benchmark e documentação/exemplos.

---

## 1. Matriz de Cobertura por Subsistema

A matriz adota os seguintes níveis de verificação semântica:
* **Forte (Strong):** Asserções dedicadas e abrangentes em testes unitários/integração, com cobertura de limites e casos negativos.
* **Parcial (Partial):** Testado indiretamente ou com verificações básicas, carecendo de cenários específicos de limite.
* **Ausente (Missing):** Sem verificação automatizada direta neste nível.
* **N/A:** Não aplicável ao papel arquitetural do subsistema.

| # | Subsistema | Lexer / Parser | Análise Semântica | Diagnósticos e Fixtures | Layout de Memória | Backend ASM | Golden ASM | Toolchain (ca65/ld65) | Runtime no Mesen | Corpus de Benchmark | Observações |
| :- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| 1 | **Variáveis e tipos escalares** | Forte | Forte | Forte | Forte | Forte | Forte | Forte | Forte | Forte | `byte`, `boolean`, `nes_color` |
| 2 | **Constantes (`const`)** | Forte | Forte | Forte | Forte | Forte | Forte | Forte | Forte | Forte | Valores imediatos inline |
| 3 | **Aritmética (+, -)** | Forte | Forte | Forte | Forte | Forte | Forte | Forte | Forte | Forte | Wrap de 8 bits, unário/binário |
| 4 | **Comparações relacionais** | Forte | Forte | Forte | Forte | Forte | Forte | Forte | Forte | Forte | Desvios diretos por flags da CPU |
| 5 | **Expressões booleanas** | Forte | Forte | Forte | Forte | Forte | Forte | Forte | Forte | Forte | `not`, `and`, `or`, curto-circuito |
| 6 | **Condicionais (`if`/`else`)** | Forte | Forte | Forte | Forte | Forte | Forte | Forte | Forte | Forte | Ramos aninhados |
| 7 | **Laços (`while`, `repeat`)** | Forte | Forte | Forte | Forte | Forte | Forte | Forte | Forte | Forte | Controlados por condição |
| 8 | **Contagem e controle de laço** | Forte | Forte | Forte | Forte | Forte | Forte | Forte | Forte | Forte | `for`, `inc`, `dec`, `break`, `continue` |
| 9 | **Procedimentos** | Forte | Forte | Forte | Forte | Forte | Forte | Forte | Forte | Forte | Sem parâmetros, chamadas acíclicas |
| 10 | **Parâmetros de procedimento** | Forte | Forte | Forte | Forte | Forte | Forte | Forte | Forte | Forte | Parâmetros por valor `byte`/`boolean` |
| 11 | **Atribuição definitiva** | N/A | Forte | Forte | Forte | Forte | Forte | Forte | Forte | Forte | Rejeição de leitura não inicializada |
| 12 | **Alocação de Zero Page** | N/A | Forte | Forte | Forte | Forte | Forte | Forte | Forte | Forte | Threshold de promoção e fallback |
| 13 | **Layout de memória em runtime** | N/A | N/A | Forte | Forte | Forte | Forte | Forte | Forte | Forte | Reconciliação física de 2 KiB |
| 14 | **NMI e sincronização de quadros** | Forte | Forte | Forte | Forte | Forte | Forte | Forte | Forte | Forte | `nes.wait_frame`, contador de quadros |
| 15 | **Callbacks de quadro** | Forte | Forte | Forte | Forte | Forte | Forte | Forte | Forte | Forte | `nes.on_update`, `nes.on_vblank` |
| 16 | **Entrada de controles** | Forte | Forte | Forte | Forte | Forte | Forte | Forte | Forte | Forte | Leitura de portas duplas, botões |
| 17 | **Carregamento de CHR-ROM** | N/A | Forte | Forte | Forte | Forte | Ausente | Forte | Forte | Ausente | Validação de `--chr` (8 KiB exatos) |
| 18 | **Carregamento de nametable** | Forte | Forte | Forte | Forte | Forte | Ausente | Forte | Forte | Ausente | Transferência de 1 KiB raw na inicialização |
| 19 | **Atualizações de fundo em runtime** | Forte | Forte | Forte | Forte | Forte | Ausente | Forte | Forte | Forte | Fila de VBlank com 4 escritas, shadow de tiles |
| 20 | **Gerenciamento de paletas** | Forte | Forte | Forte | Forte | Forte | Ausente | Forte | Forte | Forte | Shadow de 32 bytes, uploader em VBlank |
| 21 | **Rolagem e estado da PPU** | Forte | Forte | **Forte** | Forte | Forte | Ausente | Forte | Forte | Ausente | Preparação de scroll, restauração de latch; fixtures de tipo para ambas as posições de argumento |
| 22 | **Sprites de hardware básicos** | Forte | Forte | Forte | Forte | Forte | Ausente | Forte | Forte | Forte | Shadow de 64 entradas de OAM, DMA em NMI |
| 23 | **Gerenciamento de sprites** | Forte | Forte | Forte | Forte | Forte | Ausente | Forte | Forte | Forte | Reserva estática de pool de 64 slots |
| 24 | **Metasprites** | Forte | Forte | Forte | Forte | Forte | Ausente | Forte | Forte | Forte | Geometria de âncora, flip, recorte de borda |
| 25 | **Animação de sprites** | Forte | Forte | Forte | Forte | Forte | Ausente | Forte | Forte | Forte | Sequências, temporizadores, avanço |
| 26 | **Infraestrutura de builtins** | Forte | Forte | Forte | Forte | Forte | Parcial | Forte | Forte | Forte | Registro unificado e validação |
| 27 | **Otimizações de codegen de baixo risco** | N/A | N/A | N/A | Forte | Forte | Forte | Forte | Forte | Forte | Operandos diretos, branch em flags |
| 28 | **Arrays** | Forte | Forte | Forte | Forte | Forte | Forte | Forte | Forte | Forte | 1D fixo, indexação, limites |

---

## 2. Respostas às Perguntas Canônicas de Auditoria

### 1. Quais subsistemas implementados não possuem cobertura em runtime no Mesen?
* **Carregamento de asset CHR-ROM (`--chr`) — ✅ Resolvido (P1):** `verify_chr_asset.lua` agora lê todos os 8 192 bytes da tabela de padrões da PPU (`$0000–$1FFF`) via `emu.read(..., emu.memType.nesPpuDebug)` e valida o padrão determinístico completo de `chr_asset.chr`, incluindo o marcador terminal único (`$0A`) no offset `$1FFF`.
* *Nota sobre primitivas puras em tempo de compilação:* Os arquivos `arithmetic.nsp`, `boolean_expressions.nsp` e `conditionals.nsp` isolados não possuem scripts `.lua` individuais dedicados; entretanto, seu comportamento em runtime é completamente validado de forma transitiva em `verify_low_risk_codegen.lua`, `verify_arrays.lua` e `verify_counting.lua`.

### 2. Quais recursos voltados ao hardware dependem exclusivamente de testes estáticos/goldens?
* **Embarque de CHR-ROM — ✅ Resolvido (P1):** Além da validação binária da ROM, `verify_chr_asset.lua` agora verifica o padrão CHR correto na tabela de padrões da PPU emulada em runtime.
* Todos os demais recursos voltados ao hardware (Paletas, Nametables, Atualizações no VBlank, Rolagem/Scroll, Sprites de Hardware, Metasprites, Animação, Controles, Callbacks de NMI, Sincronização de Quadros) contam com testes comportamentais dedicados no Mesen headless via Lua.

### 3. Quais recursos têm cobertura no Mesen mas possuem cobertura semântica/diagnóstica fraca?
* **Rolagem e Estado da PPU — ✅ Resolvido (P1):** Dois fixtures negativos dedicados (`invalid_set_scroll_x_type.nsp`, `invalid_set_scroll_y_type.nsp`) agora verificam explicitamente que passar `boolean` no argumento `x` ou `y` de `nes.set_scroll` gera `E4004` (incompatibilidade de tipo), confirmando que `E3046` (contagem de argumentos) não toma precedência.

### 4. Quais recursos do compilador não possuem representação dedicada no benchmark?
* `chr_asset` (embarque isolado de CHR)
* `scrolling_ppu_state` (preparação de scroll e espelhamento)
* `nametable_loading` (transferência inicial de nametable)
* `slow_update_callback` (coalescência de quadros lentos)
* `frame_synchronization` (sincronização de laço isolada)
* `zero_page` / `memory_layout` (benchmarks puros de layout, embora todos os benchmarks reportem métricas de memória)

### 5. Quais exemplos não são exercitados por testes de toolchain ou de runtime?
* **Nenhum.** Todos os programas de exemplo em `examples/` (`minimal.nsp`, `arithmetic.nsp`, `boolean_expressions.nsp`, `conditionals.nsp`, `loops.nsp`, `counting.nsp`, `procedures.nsp`, `procedure_parameters.nsp`, `controller_input.nsp`, `sprite_support.nsp`, `metasprite_player.nsp`, `sprite_animation.nsp`, `palette_support.nsp`, `background_updates.nsp`, `frame_callbacks.nsp`, `frame_synchronization.nsp`, `gameplay_full_stack.nsp`, `nametable_loading.nsp`, `scrolling_ppu_state.nsp`, `slow_update_callback.nsp`, `zero_page.nsp`, `memory_layout.nsp`, `metasprite_clipping.nsp`, `arrays.nsp`, `chr_asset.nsp`) são compilados, montados e validados em `tests/test_integration.py` e/ou `tools/measure_benchmarks.py`.

### 6. Quais goldens protegem saídas amplas mas carecem de asserções focadas?
* `tests/golden/minimal.asm`, `tests/golden/memory_layout.asm`, `tests/golden/zero_page.asm` e `tests/golden/frame_synchronization.asm` capturam o assembly completo gerado.
* Subsistemas como Metasprites, Animação de Sprites, Atualizações de Fundo, Paletas e Rolagem dependem de testes estruturais focados com regex no backend e testes de integração no Mesen, em vez de arquivos golden completos.

### 7. Quais testes dependem primariamente do formato interno de implementação em vez de comportamento observável?
* Determinadas asserções regex em `tests/test_backend.py` verificam comentários específicos do assembly ou nomes de símbolos temporários (`expression_temporary_0`). Testes orientados a comportamento em `test_backend_optimizations.py`, `test_arrays.py` e `test_integration.py` asseguram sequências de instruções observáveis, alocações de memória e estado de hardware.

### 8. Há arquivos de teste cujas responsabilidades tornaram-se excessivamente amplas?
* `tests/test_integration.py` abriga atualmente três responsabilidades distintas:
  1. Testes de Integração da Cadeia de Ferramentas (validação de build `ca65`/`ld65`, cabeçalhos de ROM, parâmetros de CLI)
  2. Testes de Regressão de Golden Assembly (comparação de 15 fixtures `.asm`)
  3. Testes de Integração de Runtime no Mesen (orquestração de 24 execuções do Mesen headless)
  Embora bem estruturado (~800 linhas), manter a separação será importante à medida que novas versões da linguagem expandirem os testes de runtime.

### 9. Há inconsistências óbvias de nomenclatura/histórico que valha a pena limpar posteriormente?
* O método `test_parses_all_milestone_three_variable_types` foi identificado e renomeado para `test_parses_scalar_and_color_variable_types`.
* O exemplo de recorte visual (`examples/metasprite_clipping.nsp`) e o fixture headless de unidade (`tests/fixtures/runtime/metasprite_clipping.nsp`) atendem a propósitos distintos (demonstração visual vs validação rápida headless) e estão devidamente documentados.

---

## 3. Análise de Lacunas (Gaps)

### Alta Prioridade (P1) — Todos Resolvidos
1. **✅ P1 — Validação em runtime no Mesen da tabela de padrões CHR-ROM** *(resolvido)*:
   * *Subsistema:* Carregamento de Asset CHR-ROM (`--chr`)
   * *Adicionado:* `tests/mesen/verify_chr_asset.lua` — lê todos os 8 192 bytes da tabela de padrões da PPU (`$0000–$1FFF`) via `emu.memType.nesPpuDebug` e verifica o padrão determinístico de `examples/assets/chr_asset.chr`, incluindo o byte terminal único `$0A` em `$1FFF`.
   * *Integrado:* `MesenIntegrationTests.test_chr_asset_is_visible_in_ppu_pattern_tables` em `tests/test_integration.py`.
   * *Atualização na matriz:* Subsistema 17 — camada Runtime no Mesen: **Ausente → Forte**.

2. **✅ P1 — Fixtures negativos de diagnóstico focados para tipos de argumentos de `nes.set_scroll`** *(resolvido)*:
   * *Subsistema:* Rolagem e Estado da PPU
   * *Adicionados:* `tests/fixtures/diagnostics/invalid_set_scroll_x_type.nsp` e `invalid_set_scroll_y_type.nsp`.
   * *Testes adicionados:* `test_boolean_x_argument_fixture_emits_type_diagnostic_not_argument_count` e `test_boolean_y_argument_fixture_emits_type_diagnostic_not_argument_count` em `tests/test_scrolling_ppu_state.py`, cada um verificando `E4004` e confirmando que `E3046` não toma precedência.
   * *Atualização na matriz:* Subsistema 21 — camada Diagnósticos: anotação atualizada para indicar que ambas as posições de argumento estão cobertas.

### Média Prioridade (P2)
1. **P2 — Adicionar fixtures focados de Golden Assembly para subsistemas de hardware**:
   * *Subsistemas:* Metasprites, Animação de Sprites, Paletas, Atualizações de Fundo, Rolagem
   * *Camada Ausente:* Golden Assembly
   * *Relevância:* Embora protegidos por testes estruturais com regex e testes no Mesen, trechos golden focados evitam regressões inesperadas no emissor de assembly.
   * *Escopo:* Médio (5 arquivos golden `.asm` focados).

2. **P2 — Incluir `scrolling_ppu_state` no corpus de benchmark**:
   * *Subsistema:* Rolagem e Estado da PPU
   * *Camada Ausente:* Medição de Benchmark / Recursos
   * *Relevância:* Mede o impacto em ciclos estáticos e pegada em PRG da preparação de rolagem e restauração de PPU.
   * *Escopo:* Pequeno (Adicionar entrada em `tools/measure_benchmarks.py`).

3. **P2 — Dividir `tests/test_integration.py` em suítes de teste focadas**:
   * *Subsistema:* Infraestrutura de Testes
   * *Camada Ausente:* Arquitetura de Testes
   * *Relevância:* Separa integração do toolchain, comparações de goldens e orquestração de runtime do Mesen em módulos limpos (`test_toolchain.py`, `test_goldens.py`, `test_mesen_runtime.py`).
   * *Escopo:* Médio (Refatoração de testes sem alteração de comportamento).

### Baixa Prioridade (P3)
1. **P3 — Normalizar docstrings e convenções de nomenclatura em testes legados de parser**:
   * *Subsistema:* Testes de Parser / Lexer
   * *Camada Ausente:* Manutenção de Testes
   * *Relevância:* Garante docstrings e nomes uniformes nas suítes de teste iniciais.
   * *Escopo:* Pequeno.

---

## 4. Backlog Priorizado de Seguimento

* `[P1 ✅]` ~~Adicionar teste de validação de padrões da PPU no Mesen para carregamento de CHR-ROM (`verify_chr_asset.lua`).~~ **Resolvido** — `tests/mesen/verify_chr_asset.lua` valida todos os 8 192 bytes da tabela de padrões da PPU em runtime.
* `[P1 ✅]` ~~Adicionar fixture negativo de diagnóstico focado para tipos inválidos de argumentos em `nes.set_scroll`.~~ **Resolvido** — Fixtures `invalid_set_scroll_x_type.nsp` e `invalid_set_scroll_y_type.nsp` com asserções de `E4004` para ambas as posições de argumento.
* `[P2]` Adicionar fixtures de golden assembly focados para rotinas de runtime de hardware (paletas, fila de fundo, renderizador de metasprites).
* `[P2]` Adicionar especificação de benchmark de `scrolling_ppu_state` em `tools/measure_benchmarks.py`.
* `[P2]` Separar `tests/test_integration.py` em `test_toolchain.py`, `test_goldens.py` e `test_mesen.py`.
* `[P3]` Limpar convenções de nomenclatura e docstrings de testes legados.
