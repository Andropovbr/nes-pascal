# Melhorias de Baixo Risco na Geração de Código

> Nota histórica: a reserva fixa descrita abaixo foi substituída pelo pool com
> escopo exato no [milestone 0.5.11](expression-temporaries-0.5.11.md).

[English](../../compiler/low-risk-codegen-0.5.7.md) | Português (Brasil)

O milestone 0.5.7 adiciona um conjunto pequeno de decisões locais no lowering
para ca65. Ele não é um otimizador geral: o backend continua emitindo Assembly
legível diretamente, sem reescrita textual de Assembly, IR de instruções, grafo
de fluxo de controle ou rastreamento global de registradores/flags.

## Regras implementadas

O backend agora:

- emite `ADC #value` e `SBC #value` quando o operando aritmético direito é um
  byte conhecido em tempo de compilação;
- emite `ADC variable`, `SBC variable` e `CMP variable` para variáveis estáveis
  quando a avaliação do lado esquerdo não possui efeitos de runtime;
- emite `CMP #value` para operandos imediatos de comparação;
- mantém o caminho RHS-first original com temporário quando o consumo direto
  poderia tornar a ordem de avaliação observável;
- converte expressões Boolean usadas por `if`, `while` e `repeat` diretamente
  em branches;
- preserva a materialização canônica `$00`/`$01` quando um Boolean é armazenado
  ou usado como dado;
- usa os flags produzidos por um `LDA` final comprovado, materialização Boolean
  ou consulta builtin suportada, sem acrescentar `CMP #$00`;
- trata condições com consultas de controle pelo caminho existente de
  `BuiltinId`, sem contornar o registro de builtins;
- preserva a avaliação short-circuit de `and`, `or` e `not`;
- mantém caminhos potencialmente distantes atrás de `JMP` absoluto. Branches
  relativos apontam somente para labels ou trampolins próximos.

A reserva fixa de 16 bytes de temporários na Zero Page não mudou. Somente os
símbolos gerados e o uso efetivo de temporários podem diminuir. ABIs de runtime,
convenções de chamada, descritores de builtins, regiões de memória e a semântica
pública da linguagem permanecem inalterados.

## Assembly representativo

Um operando aritmético imediato não passa mais pela Zero Page:

```asm
; antes
lda #$01
sta expression_temporary_0
lda variable_Counter
clc
adc expression_temporary_0

; depois
lda variable_Counter
clc
adc #$01
```

Uma variável estável pode ser consumida diretamente:

```asm
; antes
lda variable_Right
sta expression_temporary_0
lda variable_Left
sec
sbc expression_temporary_0

; depois
lda variable_Left
sec
sbc variable_Right
```

Uma comparação usada apenas como fluxo de controle não materializa mais um
Boolean:

```asm
; antes
lda #$08
sta expression_temporary_0
lda variable_Counter
cmp expression_temporary_0
bcc @comparison_true
lda #$00
jmp @comparison_end
@comparison_true:
lda #$01
@comparison_end:
cmp #$00
bne @if_then
jmp @if_else

; depois
lda variable_Counter
cmp #$08
bcc @if_then
jmp @if_else       ; long-branch-safe false path
```

A mesma comparação ainda produz dados canônicos em uma atribuição:

```asm
lda variable_Counter
cmp #$08
bcc @comparison_true
lda #$00              ; false
jmp @comparison_end
@comparison_true:
lda #$01              ; true
@comparison_end:
sta variable_Flag
```

## Método de benchmark

O corpus inalterado de 16 programas do milestone 0.5.5 foi medido imediatamente
antes e depois da mudança do backend com `tools/measure_benchmarks.py`.

Tamanhos de PRG e contagens de instruções são medidos na saída gerada. `Ciclos
estáticos estimados` é intencionalmente mais limitado que timing de runtime:
conta cada instrução emitida uma vez pelo custo base do Ricoh 2A03, considera
branches como não tomados e exclui iterações dinâmicas, page crossing,
interrupções e DMA. Ele serve para comparação determinística, não para prever o
orçamento de um quadro.

| Benchmark | Código PRG B (delta) | PRG ocupado B | Instruções | Ciclos estáticos estimados | Temps vivos | Bytes temp/cache ZP | Non-ZP B |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `minimal` | 239 -> 239 (0, 0.0%) | 245 -> 245 | 108 -> 108 (0, 0.0%) | 367 -> 367 (0, 0.0%) | 0 -> 0 | 0 -> 0 | 7 -> 7 |
| `arithmetic` | 259 -> 251 (-8, -3.1%) | 265 -> 257 | 119 -> 115 (-4, -3.4%) | 395 -> 383 (-12, -3.0%) | 2 -> 0 | 2 -> 0 | 7 -> 7 |
| `boolean_expressions` | 416 -> 382 (-34, -8.2%) | 422 -> 388 | 187 -> 170 (-17, -9.1%) | 571 -> 525 (-46, -8.1%) | 1 -> 0 | 1 -> 0 | 12 -> 12 |
| `conditionals` | 303 -> 282 (-21, -6.9%) | 309 -> 288 | 138 -> 128 (-10, -7.2%) | 440 -> 415 (-25, -5.7%) | 1 -> 0 | 1 -> 0 | 5 -> 5 |
| `loops` | 404 -> 317 (-87, -21.5%) | 410 -> 323 | 187 -> 146 (-41, -21.9%) | 563 -> 460 (-103, -18.3%) | 1 -> 0 | 1 -> 0 | 4 -> 4 |
| `counting` | 533 -> 488 (-45, -8.4%) | 539 -> 494 | 237 -> 216 (-21, -8.9%) | 751 -> 700 (-51, -6.8%) | 2 -> 0 | 7 -> 6 | 9 -> 9 |
| `procedures` | 330 -> 289 (-41, -12.4%) | 336 -> 295 | 153 -> 134 (-19, -12.4%) | 511 -> 466 (-45, -8.8%) | 2 -> 0 | 1 -> 0 | 4 -> 4 |
| `procedure_parameters` | 366 -> 350 (-16, -4.4%) | 372 -> 356 | 163 -> 155 (-8, -4.9%) | 544 -> 524 (-20, -3.7%) | 1 -> 0 | 1 -> 0 | 11 -> 11 |
| `controller_input` | 889 -> 704 (-185, -20.8%) | 895 -> 710 | 404 -> 318 (-86, -21.3%) | 1146 -> 945 (-201, -17.5%) | 1 -> 0 | 1 -> 0 | 265 -> 265 |
| `sprite_support` | 583 -> 583 (0, 0.0%) | 589 -> 589 | 273 -> 273 (0, 0.0%) | 911 -> 911 (0, 0.0%) | 0 -> 0 | 0 -> 0 | 326 -> 326 |
| `metasprite_player` | 1437 -> 1303 (-134, -9.3%) | 1443 -> 1309 | 551 -> 489 (-62, -11.3%) | 1741 -> 1599 (-142, -8.2%) | 1 -> 0 | 1 -> 0 | 272 -> 272 |
| `sprite_animation` | 2007 -> 1875 (-132, -6.6%) | 2013 -> 1881 | 675 -> 614 (-61, -9.0%) | 2175 -> 2035 (-140, -6.4%) | 1 -> 0 | 1 -> 0 | 276 -> 276 |
| `palette_support` | 812 -> 812 (0, 0.0%) | 818 -> 818 | 342 -> 342 (0, 0.0%) | 1106 -> 1106 (0, 0.0%) | 0 -> 0 | 0 -> 0 | 306 -> 306 |
| `background_updates` | 2166 -> 2166 (0, 0.0%) | 2172 -> 2172 | 522 -> 522 (0, 0.0%) | 1773 -> 1773 (0, 0.0%) | 1 -> 1 | 0 -> 0 | 995 -> 995 |
| `frame_callbacks` | 272 -> 272 (0, 0.0%) | 278 -> 278 | 124 -> 124 (0, 0.0%) | 438 -> 438 (0, 0.0%) | 0 -> 0 | 0 -> 0 | 6 -> 6 |
| `gameplay_full_stack` | 3478 -> 3350 (-128, -3.7%) | 3484 -> 3356 | 874 -> 815 (-59, -6.8%) | 2848 -> 2712 (-136, -4.8%) | 1 -> 1 | 1 -> 0 | 1260 -> 1260 |

Toda alocação non-ZP, a reserva fixa da Zero Page, o layout das variáveis
promovidas, a memória livre visível ao allocator e a seleção de features de
runtime permaneceram iguais. A quantidade de símbolos de temporário/cache do
compilador diminuiu quando operandos diretos tornaram esses símbolos
desnecessários; `counting` ainda precisa de seis bytes de cache `for_limit_*`.

`minimal`, `sprite_support`, `palette_support`, `background_updates` e
`frame_callbacks` não mudaram porque seus caminhos gerados não contêm os padrões
aritméticos/de comparação otimizados. O isolamento de features também não
mudou: rotinas de controller, OAM, animação de metasprite, fila de paleta,
background shadow e callbacks são emitidas sob as mesmas condições de antes.

| Benchmark representativo | Features de runtime do registro antes e depois |
| --- | --- |
| `minimal` | Nenhuma |
| `controller_input` | `CONTROLLER_QUERY`, `LEGACY_SPRITE_ZERO` |
| `sprite_support` | `SPRITE_API`, `SPRITE_SET_POSITION` |
| `metasprite_player` | `CONTROLLER_QUERY`, `METASPRITE_API` |
| `sprite_animation` | `CONTROLLER_QUERY`, `METASPRITE_ANIMATION`, `METASPRITE_API` |
| `background_updates` | `BACKGROUND_CLEAR_OVERFLOW`, `BACKGROUND_CLEAR_UPDATES`, `BACKGROUND_GET_TILE`, `BACKGROUND_INSPECT_OVERFLOW`, `BACKGROUND_SET_ATTRIBUTE`, `BACKGROUND_SET_TILE` |
| `gameplay_full_stack` | `BACKGROUND_GET_TILE`, `BACKGROUND_SET_ATTRIBUTE`, `BACKGROUND_SET_TILE`, `CONTROLLER_QUERY`, `METASPRITE_ANIMATION`, `METASPRITE_API` |

## Adiado deliberadamente

Este milestone não implementa rastreamento do acumulador entre expressões,
raciocínio de flags entre blocos básicos, eliminação de stores ou reloads, um
passo peephole geral, CFG/SSA, IR 6502 estruturado, alocação de registradores,
mudanças de ABI ou redesenho do pool de temporários. Operandos complexos ou com
possíveis efeitos continuam no caminho conservador com temporário.
