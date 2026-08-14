# Implementação e Medições de Arrays (0.5.8)

> Nota histórica: os números do pool fixo abaixo registram o estado da 0.5.8.
> O milestone [0.5.11](expression-temporaries-0.5.11.md) agora reserva 1 byte de
> expressão e 2 bytes separados de cache de laço, recuperando 13 bytes de ZP.

[English](../../compiler/arrays-0.5.8.md) | Português (Brasil)

A milestone 0.5.8 adiciona arrays globais de tamanho fixo como construção da
linguagem no compilador, não como subsistema de runtime. `ArrayType` preserva o
tipo do elemento, os limites inferior e superior, a quantidade de elementos e
o tamanho total dos elementos de um byte. Leituras e escritas resolvidas
continuam explícitas na análise semântica, layout de memória, análise de
temporários e emissão ca65.

## Lowering e modelo de memória

- Arrays usam `array[$00..$NN] of byte|boolean`; somente o limite inferior
  `$00` é suportado.
- Arrays são alocados de forma contígua, na ordem de declaração, na RAM comum
  do usuário. Eles são deliberadamente excluídos da promoção automática para
  Zero Page.
- Índices constantes se tornam offsets estáticos do símbolo. Índices variáveis
  são avaliados em `X` e usam endereçamento absoluto indexado.
- Uma atribuição indexada avalia primeiro o índice, preserva-o temporariamente
  na pilha de hardware, avalia o valor e então armazena por `,x`. Nenhum símbolo
  fixo do compilador ou estado de runtime de arrays é introduzido.
- Um elemento usado em controle de fluxo booleano alimenta diretamente o
  lowering orientado a branches da 0.5.7. Elementos booleanos armazenados
  permanecem canônicos como `$00`/`$01`.
- Índices conhecidos em tempo de compilação são reduzidos e verificados.
  Índices variáveis não possuem verificação ou metadados de limites em runtime.

## Benchmark de arrays

O novo workload `arrays` preenche arrays de bytes e booleanos em laços, lê e
escreve índices constantes e variáveis, realiza aritmética indexada e ramifica
sobre elementos booleanos.

| Métrica | Resultado |
| --- | ---: |
| Código PRG | 382 B |
| PRG ocupado | 388 B |
| Instruções | 182 |
| Ciclos-base estáticos estimados | 569 |
| Profundidade da árvore de expressão | 2 |
| Máximo de temporários de expressão vivos | 1 |
| Reserva fixa do pool temporário | 16 B |
| Temporários/cache realmente necessários | 3 B |
| Armazenamento dos elementos | 16 B de RAM comum |
| Outro armazenamento regular de runtime/usuário | 4 B |
| Armazenamento escalar promovido automaticamente | 3 B de ZP |
| ZP alocada/reservada pelo benchmark | 28 B |
| ZP livre visível ao alocador | 125 B |
| RAM comum livre visível ao alocador | 1.516 B |
| Recursos de runtime | Nenhum |

Os três bytes necessários de temporários/cache são um byte reutilizável para
`Sum + Values[Index]` e dois bytes `for_limit_*` existentes. A indexação de
arrays em si não adiciona temporário fixo nem efetivamente usado na Zero Page.
Indexação somente por constantes não exige temporário de índice.

`Ciclos-base estáticos estimados` usa a convenção determinística do benchmark:
cada instrução emitida é contada uma vez pelo custo-base do Ricoh 2A03, branches
não são tomados, e contagens de laço, cruzamento de página, interrupções e DMA
são excluídos.

## Verificação de regressão do corpus anterior

O corpus completo de 16 programas da 0.5.5/0.5.7 foi medido antes e depois do
suporte a arrays. Todas as métricas listadas são idênticas; programas sem arrays
não emitem runtime, descritor, metadados, RAM ou estado de Zero Page de arrays.

| Benchmark | Código/ocupado PRG B | Instruções | Ciclos est. | Temps vivos | Temp ZP necessário | Non-ZP alocado |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `minimal` | 239/245 | 108 | 367 | 0 | 0 B | 7 B |
| `arithmetic` | 251/257 | 115 | 383 | 0 | 0 B | 7 B |
| `boolean_expressions` | 382/388 | 170 | 525 | 0 | 0 B | 12 B |
| `conditionals` | 282/288 | 128 | 415 | 0 | 0 B | 5 B |
| `loops` | 317/323 | 146 | 460 | 0 | 0 B | 4 B |
| `counting` | 488/494 | 216 | 700 | 0 | 6 B | 9 B |
| `procedures` | 289/295 | 134 | 466 | 0 | 0 B | 4 B |
| `procedure_parameters` | 350/356 | 155 | 524 | 0 | 0 B | 11 B |
| `controller_input` | 704/710 | 318 | 945 | 0 | 0 B | 265 B |
| `sprite_support` | 583/589 | 273 | 911 | 0 | 0 B | 326 B |
| `metasprite_player` | 1.303/1.309 | 489 | 1.599 | 0 | 0 B | 272 B |
| `sprite_animation` | 1.875/1.881 | 614 | 2.035 | 0 | 0 B | 276 B |
| `palette_support` | 812/818 | 342 | 1.106 | 0 | 0 B | 306 B |
| `background_updates` | 2.166/2.172 | 522 | 1.773 | 1 | 0 B | 995 B |
| `frame_callbacks` | 272/278 | 124 | 438 | 0 | 0 B | 6 B |
| `gameplay_full_stack` | 3.350/3.356 | 815 | 2.712 | 1 | 0 B | 1.260 B |

## Adiado deliberadamente

Verificação de limites em runtime, limites inferiores diferentes de zero,
parâmetros/retornos de array, arrays multidimensionais e dinâmicos, compactação
por bits, arrays de records, semântica de ponteiros, um sistema genérico de
arrays em runtime e redesign do alocador de temporários permanecem fora desta
milestone.
