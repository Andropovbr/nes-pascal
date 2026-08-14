# Milestone 0.5.5: Auditoria de Arquitetura do Compilador e Geração de Código

> Linha de base histórica: o milestone 0.5.11 substituiu o modelo fixo por
> profundidade de AST identificado aqui por alocação com escopo baseada no pico
> real de uso. Consulte [Alocação de Temporários de Expressão (0.5.11)](expression-temporaries-0.5.11.md).

[English](../../compiler/optimization-audit-0.5.5.md) | Português (Brasil)

Este documento estabelece a linha de base oficial de arquitetura, geração de código e consumo de recursos para o compilador **NES Pascal** a partir do milestone **0.5.5**.

Ele avalia o estado atual do compilador, mede o código 6502 gerado em um conjunto expandido de 16 benchmarks, analisa débitos técnicos e riscos arquiteturais, avalia oportunidades de otimização, reconcilia o orçamento de ciclos de NMI/VBlank com as especificações do runtime e define uma sequência priorizada de milestones subsequentes.

---

## 1. Resumo Executivo

O NES Pascal atingiu um nível de maturidade em que os programas compilados são executados como jogos arcade multissistemas realistas no NES (exercitando entrada de controle, callbacks de quadro, DMA de OAM, metasprites, inversão por pivô, recorte, animação de sprites e atualizações de fundo).

### Principais Conclusões da Auditoria

1. **Pipeline Determinístico e Funcional:**
   O pipeline do compilador (Lexer -> Parser -> AST -> Análise Semântica -> Layout de Memória -> Backend ca65 -> Linker ld65) é estável, determinístico e passa em todos os testes automatizados (incluindo 21 testes de integração comportamental no emulador Mesen).

2. **Escalabilidade de Builtins / Intrínsecos é a Prioridade Imediata:**
   O compilador utiliza famílias dedicadas de nós na AST para modelar rotinas de hardware `nes.*`. Com as próximas versões adicionando áudio APU, música, efeitos sonoros (SFX), colisões, temporizadores, HUD e uma biblioteca padrão, continuar esse padrão causará uma proliferação rápida de código repetitivo em múltiplos módulos do compilador. Um registro unificado de `BuiltinCall` / `ResolvedBuiltinCall` é um **pré-requisito crítico antes da Release 0.6 (Áudio)**.

3. **Alocação de Temporários de Expressão é um Pré-requisito de Correção para Funções:**
   Temporários de expressão são atualmente alocados por profundidade estática na AST (`expression_temporary_{depth}`) com uma reserva incondicional de 16 bytes na Zero Page. Em todos os 16 benchmarks, o número máximo real de temporários de expressão simultaneamente ativos é **no máximo 2**. A avaliação de chamadas aninhadas de funções dentro de expressões (`Foo(A + Bar(B + C))`) criaria conflito de nomes e corromperia temporários da expressão externa sob o esquema atual de redefinição de profundidade. O pooling de temporários em tempo de compilação com escopo é um **pré-requisito de correção essencial antes de Funções**.

4. **Pressão Cumulativa de RAM é Dominada por Shadows Condicionais a Recursos:**
   O benchmark de jogabilidade full-stack (`gameplay_full_stack`) combina metasprites animados, consulta de controles, DMA de OAM e atualizações de tiles de fundo. O armazenamento de compilador/runtime/usuário aloca ou reserva **1.293 bytes** (~63,1%) dos 2.048 bytes de RAM física: 33 bytes na Zero Page, 1.004 bytes na RAM comum de runtime/usuário e um shadow de OAM de 256 bytes. Incluindo a página de 256 bytes da pilha de hardware e 99 bytes indisponíveis pela política atual da Zero Page, **1.648 bytes** (~80,5%) do espaço de endereçamento da CPU estão comprometidos ou reservados, restando 400 bytes visíveis ao alocador. O shadow de tiles de 960 bytes domina a RAM comum de runtime/usuário (95,6%), mas permanece estritamente condicional ao recurso e é omitido em atualizações de fundo apenas para escrita.

5. **Ineficiências na Geração de Código são Dominadas por Quatro Padrões Medidos:**
   - **Constantes Imediatas em Temporários:** Aritmética binária (`+`, `-`) e comparações (`=`, `<`, etc.) armazenam incondicionalmente operandos do lado direito em temporários da Zero Page mesmo quando o operando é um imediato `#$XX` em tempo de compilação ou uma variável direta de memória.
   - **Materialização de Valores Booleanos:** Condições em `if`, `while`, `repeat` e `for` materializam resultados booleanos como `$00` ou `$01` no acumulador, realizam um `CMP #$00` redundante e então realizam o desvio, em vez de desviar diretamente com base nas flags de status do processador (`BEQ`, `BNE`, `BCC`, `BCS`).
   - **`CMP #$00` Redundante:** Instruções como `LDA`, `TAX`, `INX`, `DEX`, `AND`, `ORA` e `EOR` já definem as flags Zero (`Z`) e Negativo (`N`) da CPU, tornando testes posteriores de zero redundantes.
   - **Preparação em RAM nas Convenções de Chamada:** Rotinas internas de runtime passam argumentos através de posições fixas de rascunho em RAM (`runtime_metasprite_offset_x`, `runtime_sprite_value`) onde registradores da CPU (`A`, `X`, `Y`) poderiam transportar 2 a 3 parâmetros diretamente.

6. **Orçamento de NMI / VBlank Reconciliado com Margens de Segurança Explícitas:**
   O VBlank teórico do NTSC fornece 2.273 ciclos de CPU. O pior caso de trabalho de NMI no runtime combinado (DMA de OAM + todos os 25 bytes de paleta marcados + 4 escritas de tiles confirmados + envio de rolagem + restauração de latch) consome **~1.779 ciclos de CPU** (~78,3% do VBlank). Os **~494 ciclos restantes** antes da margem de segurança resultam em um **orçamento recomendado seguro para callbacks do usuário de ~250–300 ciclos de CPU** em quadros de pior caso e **~1.200–1.400 ciclos** em quadros típicos.

7. **IR Linear para 6502 é Risco Médio de Migração; IRs Pesados são Prematuros:**
   A arquitetura 6502 (8 bits, 3 registradores, Zero Page de 256 bytes) não se beneficia de alocadores complexos de registradores por coloração de grafos ou IRs SSA multinível. Um **IR Linear para 6502** leve com instruções estruturadas e passos básicos de peephole fornece alto retorno sobre investimento, mas sua migração no backend representa um **risco Médio** que deve seguir uma estratégia incremental de 4 fases.

---

## 2. Pipeline do Compilador Hoje

```text
Código-Fonte (.nsp)
       |
       v
  [ lexer.py ]           --> Tokens
       |
       v
  [ parser.py ]          --> AST não tipada (ast.py)
       |
       v
 [ semantic.py ]         --> Resolução de escopo, tipagem estrita, atribuição definitiva
       |
       v
[ memory_layout.py ]     --> Detecção de recursos, promoção para Zero Page, .cfg do ld65, .map da CPU
       |
       v
[ backend_ca65.py ]      --> Geração de código Assembly (list[str]), cabeçalho iNES, rotinas de runtime
       |
       v
  [ ca65 & ld65 ]        --> Objeto montado (.o) e ROM final (.nes)
```

---

## 3. Corpus de Benchmarks

A auditoria avaliou 16 programas determinísticos representando subsistemas específicos do compilador, cargas de trabalho isoladas de recursos e um cenário de jogabilidade full-stack combinado:

| Benchmark | Arquivo-Fonte | Características Principais |
| :--- | :--- | :--- |
| `minimal` | [`examples/minimal.nsp`](../../../examples/minimal.nsp) | Linha de base de runtime mínimo, cor da PPU, `nes.run` |
| `arithmetic` | [`examples/arithmetic.nsp`](../../../examples/arithmetic.nsp) | Negação unária, adição/subtração binária, wraparound de 8 bits |
| `boolean_expressions` | [`examples/boolean_expressions.nsp`](../../../examples/boolean_expressions.nsp) | Igualdade, comparações relacionais, `not`, `and`, `or` |
| `conditionals` | [`examples/conditionals.nsp`](../../../examples/conditionals.nsp) | Ramos `if`/`else`, condicionais aninhadas |
| `loops` | [`examples/loops.nsp`](../../../examples/loops.nsp) | `while`, `repeat`/`until`, `break`, `continue` |
| `counting` | [`examples/counting.nsp`](../../../examples/counting.nsp) | `inc`, `dec`, laços `for` ascendentes/descendentes |
| `procedures` | [`examples/procedures.nsp`](../../../examples/procedures.nsp) | Procedimentos sem parâmetros, chamadas acíclicas |
| `procedure_parameters` | [`examples/procedure_parameters.nsp`](../../../examples/procedure_parameters.nsp) | Parâmetros de valor `byte` e `boolean` em slots de RAM de procedimento |
| `controller_input` | [`examples/controller_input.nsp`](../../../examples/controller_input.nsp) | Consulta de controles duplos, estado `down`/`pressed`/`released`, sprite 0 |
| `sprite_support` | [`examples/sprite_support.nsp`](../../../examples/sprite_support.nsp) | Shadow de OAM com 64 entradas, posicionamento, paletas, flip, visibilidade |
| `metasprite_player` | [`examples/metasprite_player.nsp`](../../../examples/metasprite_player.nsp) | Posicionamento de metasprite com múltiplos componentes, flip, quadros manuais |
| `sprite_animation` | [`examples/sprite_animation.nsp`](../../../examples/sprite_animation.nsp) | Jogador animado: temporizador, repetição/disparo único, avanço de quadros, orientação |
| `palette_support` | [`examples/palette_support.nsp`](../../../examples/palette_support.nsp) | Atualizações completas de paleta de 32 bytes, fila de paleta no VBlank |
| `background_updates` | [`examples/background_updates.nsp`](../../../examples/background_updates.nsp) | Fila de atualização de tiles/atributos no VBlank, shadow de tiles de 960 bytes |
| `frame_callbacks` | [`examples/frame_callbacks.nsp`](../../../examples/frame_callbacks.nsp) | Laço determinístico de atualização na thread principal e sincronização de NMI |
| `gameplay_full_stack` | [`examples/gameplay_full_stack.nsp`](../../../examples/gameplay_full_stack.nsp) | **Benchmark full-stack combinado**: metasprite animado, controles, DMA de OAM, atualizações de fundo, leitura do shadow de tiles, estado do usuário |

---

## 4. Metodologia de Medição

As medições são coletadas de forma determinística:
1. **Bytes Ocupados de PRG-ROM:** Extraídos diretamente das tabelas de segmentos do mapa de link do `ld65` (`CODE` + `VECTORS`), distinguindo a pegada real em bytes da imagem NROM preenchida de 32 KiB.
2. **Contabilidade de RAM da CPU:** Extraída do `ProgramMemoryLayout` determinístico do compilador e tabelas de símbolos `.map`.
3. **Profundidade da Árvore de Expressão:** Calculada como a altura máxima das subárvores de operadores (0 para literais/variáveis folha).
4. **Máximo de Temporários de Expressão Ativos:** Indica o número máximo de bytes `expression_temporary_X` simultaneamente necessários em qualquer ponto de avaliação único.
5. **Frequência de Padrões em Assembly:** Analisada a partir dos arquivos `.asm` gerados usando casamento por expressões regulares.
6. **Estimativas de Ciclos:** Calculadas utilizando tabelas padrão de ciclos de instrução do Ricoh 2A03.

---

## 5. Resultados de Recursos da Linha de Base

### Contabilidade de RAM da CPU

`ZP Aloc./Reservado` combina símbolos de runtime utilizados, a reserva fixa de 16 bytes de temporários do compilador e variáveis promovidas do usuário. `ZP Reservado por Política` cobre o espaço de endereçamento indisponível pela política do compilador, mas não consumido pelo programa.

| Benchmark | ZP Aloc./Reservado | ZP Temp Necessário | Runtime/Usuário Comum | Shadow de OAM | Não-ZP Alocado | Pilha Reservada | ZP Reservado por Política | RAM Comum Livre no Alocador | ZP Livre no Alocador | Total Livre no Alocador | Aloc./Reservado Compilador/Runtime/Usuário | Total Comprometido/Reservado |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `minimal` | 25 B | 0 B | 7 B | 0 B | 7 B | 256 B | 103 B | 1.529 B | 128 B | 1.657 B | 32 B | 391 B |
| `arithmetic` | 25 B | 2 B | 7 B | 0 B | 7 B | 256 B | 103 B | 1.529 B | 128 B | 1.657 B | 32 B | 391 B |
| `boolean_expressions` | 26 B | 1 B | 12 B | 0 B | 12 B | 256 B | 103 B | 1.524 B | 127 B | 1.651 B | 38 B | 397 B |
| `conditionals` | 27 B | 1 B | 5 B | 0 B | 5 B | 256 B | 103 B | 1.531 B | 126 B | 1.657 B | 32 B | 391 B |
| `loops` | 28 B | 1 B | 4 B | 0 B | 4 B | 256 B | 103 B | 1.532 B | 125 B | 1.657 B | 32 B | 391 B |
| `counting` | 28 B | 7 B | 9 B | 0 B | 9 B | 256 B | 103 B | 1.527 B | 125 B | 1.652 B | 37 B | 396 B |
| `procedures` | 28 B | 1 B | 4 B | 0 B | 4 B | 256 B | 103 B | 1.532 B | 125 B | 1.657 B | 32 B | 391 B |
| `procedure_parameters` | 27 B | 1 B | 11 B | 0 B | 11 B | 256 B | 103 B | 1.525 B | 126 B | 1.651 B | 38 B | 397 B |
| `controller_input` | 30 B | 1 B | 9 B | 256 B | 265 B | 256 B | 103 B | 1.271 B | 123 B | 1.394 B | 295 B | 654 B |
| `sprite_support` | 26 B | 0 B | 70 B | 256 B | 326 B | 256 B | 103 B | 1.210 B | 127 B | 1.337 B | 352 B | 711 B |
| `metasprite_player` | 34 B | 1 B | 16 B | 256 B | 272 B | 256 B | 99 B | 1.264 B | 123 B | 1.387 B | 306 B | 661 B |
| `sprite_animation` | 34 B | 1 B | 20 B | 256 B | 276 B | 256 B | 99 B | 1.260 B | 123 B | 1.383 B | 310 B | 665 B |
| `palette_support` | 25 B | 0 B | 50 B | 256 B | 306 B | 256 B | 103 B | 1.230 B | 128 B | 1.358 B | 331 B | 690 B |
| `background_updates` | 25 B | 0 B | 995 B | 0 B | 995 B | 256 B | 103 B | 541 B | 128 B | 669 B | 1.020 B | 1.379 B |
| `frame_callbacks` | 25 B | 0 B | 6 B | 0 B | 6 B | 256 B | 103 B | 1.530 B | 128 B | 1.658 B | 31 B | 390 B |
| `gameplay_full_stack` | 33 B | 1 B | 1.004 B | 256 B | 1.260 B | 256 B | 99 B | 276 B | 124 B | 400 B | 1.293 B | 1.648 B |

---

## 6. Principais Oportunidades de Otimização

### 1. Operandos Imediatos e de Variáveis Diretas
Instruções aritméticas e comparações que utilizam constantes literais (ex.: `+ $01`) ou variáveis simples atualmente gravam em temporários na Zero Page antes da operação. Emitir operandos imediatos diretos (`adc #$01`) ou de memória direta (`adc variable_x`) economiza ciclos e bytes na PRG-ROM.

### 2. Desvios Booleanos sem Materialização
Condicionais (`if`, `while`) atualmente materializam `$00` ou `$01` no acumulador e executam `CMP #$00` antes do desvio. Desviar diretamente nas flags de status do 6502 (`BEQ`, `BNE`, `BCC`, `BCS`) elimina múltiplas instruções por instrução de controle de fluxo.

### 3. Remoção de `CMP #$00` Redundantes
Instruções de carga e lógicas (`LDA`, `TAX`, `AND`, `ORA`, etc.) já atualizam as flags `Z` e `N`. O teste redundante subsequente contra zero pode ser removido com segurança.

---

## 7. Reconciliação do Orçamento de Ciclos no VBlank

O VBlank do NES NTSC oferece 2.273 ciclos de CPU. No pior caso combinado de runtime:
- Entrada de hardware, contabilidade, restauração e `RTI`: 52 ciclos
- Restauração final de PPU: 36 ciclos
- DMA de OAM: 526 ciclos
- Upload completo de paleta marcada: 784 ciclos
- Fila de fundo com 4 tiles confirmados: 335 ciclos
- Envio de rolagem: 28 ciclos
- Verificação de cancelamento: 6 ciclos
- Despacho de callback vazio: 12 ciclos

**Total de Pior Caso:** ~1.779 ciclos de CPU (~78,3% da janela de VBlank).

**Margem Recomendada para Callbacks do Usuário:**
- Quadros de pico (pior caso): ~250 a 300 ciclos de CPU.
- Quadros típicos de jogabilidade (apenas DMA de OAM e paleta limpa): ~1.200 a 1.400 ciclos de CPU.

---

## 8. Sequência Priorizada de Milestones Subsequentes

1. **Infraestrutura de Builtins / Intrínsecos:** Pipeline unificado de `BuiltinCall` antes de expandir as APIs.
2. **Melhorias de Baixo Risco na Geração de Código:** Operandos imediatos diretos, desvios booleanos diretos e remoção de comparações redundantes.
3. **Arrays:** Arrays globais de tamanho fixo com indexação.
4. **Enumerações:** Tipos enumerados definidos pelo usuário.
5. **Records:** Tipos de registros definidos pelo usuário com deslocamentos de campos em tempo de compilação.
6. **Alocação de Temporários de Expressão:** Pooling de temporários com escopo para suportar aninhamento seguro de expressões com chamadas de função.
7. **Funções:** Declarações de função e valores de retorno sobre a alocação segura de temporários.
8. **Emissor Estruturado para 6502 e Otimizações de Linha de Base:** IR Linear, passes de peephole e otimizações sistemáticas.
