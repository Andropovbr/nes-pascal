# Alocação de Temporários de Expressão (0.5.11)

> O milestone [0.5.12](../../language/functions.md) agora estende esse modelo
> ao grafo acíclico completo de procedimentos e funções.

[English](../../compiler/expression-temporaries-0.5.11.md) | Português (Brasil)

O milestone 0.5.11 substitui o modelo incondicional de 16 bytes baseado na
profundidade da AST por alocação determinística em tempo de compilação baseada
no número máximo real de valores simultaneamente ativos. A mudança afeta o
armazenamento do compilador, não a sintaxe nem a semântica aritmética do NES
Pascal. Functions continuam não implementadas.

## Pool com escopo e modelo de vida

`TemporaryPool` aluga o slot numerado livre de menor índice, registra as
quantidades atual e máxima de slots ativos e exige liberação explícita. O backend
e a análise anterior ao layout usam as mesmas regras de adquirir/usar/liberar:

1. Avaliar primeiro o operando direito conforme a ordem já estabelecida quando
   o caminho direto da 0.5.7 não é permitido.
2. Adquirir um slot somente depois que esse resultado existir em `A`.
3. Armazenar o resultado e manter o slot alugado durante a avaliação da esquerda.
4. Consumir o byte armazenado e então liberar o slot.

Expressões sequenciais reutilizam `expression_temporary_0` em vez de acumular
armazenamento. Uma expressão aninhada à esquerda pode manter os slots 0, 1, 2 e
seguintes ativos sem conflito. O emissor é limitado pela quantidade reservada
pela análise de memória e assegura internamente que o pico emitido coincide
exatamente com a reserva.

Imediatos diretos, operandos de memória direta seguros, redução booleana
orientada a branches e eliminação local de testes contra zero da 0.5.7 não
mudaram. A aritmética de byte continua usando `ADC`/`SBC` do 6502 e fazendo
wraparound módulo 256.

## Chamadas, índices e categorias separadas

Escopos de chamada preservam todo aluguel pertencente ao chamador. Redução
aninhada recebe o mesmo pool e só pode adquirir um slot não alugado. Chamadas de
valor de builtins atuais já atravessam esse limite. A futura análise de Functions
deverá estender a mesma regra pelo grafo de chamadas e atribuir slots sem
sobreposição a cada cadeia ativa chamador/chamado. Este é um modelo pertencente
ao chamador em tempo de compilação; o milestone não adiciona frames de runtime,
valores de retorno ou Functions.

Argumentos de procedimentos mantêm a preparação da esquerda para a direita:
cada argumento é totalmente avaliado e armazenado no parâmetro antes do próximo.
Argumentos de builtins mantêm a ordem definida pelo emissor. As expressões atuais
da linguagem não expõem um efeito colateral de usuário forte o bastante para um
oráculo de ordem em runtime, portanto testes focados de Assembly também fixam a
sequência existente, direita-primeiro, para expressões complexas.

Escritas em arrays e arrays de records com índice variável continuam salvando o
índice calculado na pilha de hardware do 6502 durante a avaliação do lado direito.
Esse uso da pilha é separado dos slots de expressão na Zero Page. Leituras como
`Values[Indexes[I]]`, índices escalados de records, escritas indexadas, argumentos
de procedimentos e de builtins usam o mesmo pool de expressão com escopo.

O armazenamento do compilador é reportado em categorias separadas:

- temporários de expressão: pico exato de slots ativos;
- caches do compilador: atualmente bytes `for_limit_*`, contados separadamente;
- símbolos de runtime na Zero Page;
- variáveis do usuário promovidas para Zero Page;
- reserva da pilha de hardware.

A capacidade combinada de expressão/cache permanece em 16 bytes em
`$0010-$001F`. Símbolos reais ocupam o prefixo; o sufixo não usado aparece como
`Recovered temporary Zero Page` e fica livre para o alocador. A janela explícita
futura continua em `$0020-$007F` e a promoção automática em `$0080-$00FF`, sem
mover endereços existentes de usuário na Zero Page.

Se slots de expressão mais caches ultrapassarem 16 bytes, a compilação falha com
`E5004`. O diagnóstico informa o requisito combinado, seus componentes de
expressão e cache e a capacidade disponível. Ele nunca reutiliza um slot ativo,
toma espaço da promoção opcional ou faz spill silencioso.

## Validação focada

| Caso | Pico de slots de expressão | Resultado |
| --- | ---: | --- |
| aritmética direta / programas simples | 0 | sem `expression_temporary_0`; 16 bytes de ZP recuperados |
| `Values[I] + Values[J]` | 1 | somente slot 0 |
| `(Values[I] + Values[J]) + Values[K]` | 2 | slots 0 e 1 sem conflito |
| `((Values[I] + Values[J]) + Values[K]) + Values[L]` | 3 | slots 0, 1 e 2; statements posteriores os reutilizam |
| comparação aninhada | 2 | resultado aritmético e operando da comparação permanecem distintos |
| soma indexada aninhada à esquerda com 18 termos | 17 | `E5004` determinístico contra a capacidade de 16 bytes |

A regressão de runtime verifica aritmética com três slots, wraparound
`$F0 + $20 = $10`, reutilização sequencial, índices aninhados de arrays,
escritas indexadas, leitura e escrita de arrays de records, materialização de
comparação aninhada e duas expressões em argumentos de procedimento. O golden
focado registra cada declaração e uso de temporário.

## Comparação com a janela fixa da 0.5.5

`Janela fixa legada` é a antiga janela combinada de 16 bytes para
temporários/caches. `Nova expressão` contém apenas a reserva de expressão; os
caches aparecem separados. `ZP líquida salva` desconta caches ainda necessários.

| Benchmark | Janela fixa legada | Pico real | Nova expressão | Outros caches | ZP líquida salva | ZP aloc./reservada antiga | ZP aloc./reservada nova | ZP livre antiga | ZP livre nova |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `minimal` | 16 B | 0 | 0 B | 0 B | 16 B | 25 B | 9 B | 128 B | 144 B |
| `arithmetic` | 16 B | 0 | 0 B | 0 B | 16 B | 25 B | 9 B | 128 B | 144 B |
| `boolean_expressions` | 16 B | 0 | 0 B | 0 B | 16 B | 26 B | 10 B | 127 B | 143 B |
| `conditionals` | 16 B | 0 | 0 B | 0 B | 16 B | 27 B | 11 B | 126 B | 142 B |
| `loops` | 16 B | 0 | 0 B | 0 B | 16 B | 28 B | 12 B | 125 B | 141 B |
| `counting` | 16 B | 0 | 0 B | 6 B | 10 B | 28 B | 18 B | 125 B | 135 B |
| `procedures` | 16 B | 0 | 0 B | 0 B | 16 B | 28 B | 12 B | 125 B | 141 B |
| `procedure_parameters` | 16 B | 0 | 0 B | 0 B | 16 B | 27 B | 11 B | 126 B | 142 B |
| `controller_input` | 16 B | 0 | 0 B | 0 B | 16 B | 30 B | 14 B | 123 B | 139 B |
| `sprite_support` | 16 B | 0 | 0 B | 0 B | 16 B | 26 B | 10 B | 127 B | 143 B |
| `metasprite_player` | 16 B | 0 | 0 B | 0 B | 16 B | 34 B | 18 B | 123 B | 139 B |
| `sprite_animation` | 16 B | 0 | 0 B | 0 B | 16 B | 34 B | 18 B | 123 B | 139 B |
| `palette_support` | 16 B | 0 | 0 B | 0 B | 16 B | 25 B | 9 B | 128 B | 144 B |
| `background_updates` | 16 B | 0 | 0 B | 0 B | 16 B | 25 B | 9 B | 128 B | 144 B |
| `frame_callbacks` | 16 B | 0 | 0 B | 0 B | 16 B | 25 B | 9 B | 128 B | 144 B |
| `scrolling_ppu_state` | 16 B | 0 | 0 B | 0 B | 16 B | 25 B | 9 B | 128 B | 144 B |
| `arrays` | 16 B | 1 | 1 B | 2 B | 13 B | 28 B | 15 B | 125 B | 138 B |
| `enumerations` | 16 B | 0 | 0 B | 0 B | 16 B | 26 B | 10 B | 127 B | 143 B |
| `records` | 16 B | 0 | 0 B | 0 B | 16 B | 27 B | 11 B | 126 B | 142 B |
| `gameplay_full_stack` | 16 B | 0 | 0 B | 0 B | 16 B | 33 B | 17 B | 124 B | 140 B |

No corpus de 20 programas, a soma comparativa das economias por programa é
311 bytes. Dezenove benchmarks agora reservam zero bytes de expressão; `arrays`
reserva um. `counting` mantém seis bytes de cache de laço e `arrays` mantém dois,
sem rotulá-los como temporários de expressão. O pico entre benchmarks é um; a
regressão focada prova um padrão natural de três slots e o fixture de exaustão
prova o tratamento de requisitos mais profundos.

## Regressão de geração de código

A mudança altera somente reserva de dados e relatórios de mapa. Todos os
benchmarks mantiveram tamanho de PRG, instruções e ciclos estáticos estimados.

| Benchmark | PRG código/ocupada | Instruções | Ciclos estáticos estimados |
| --- | ---: | ---: | ---: |
| `minimal` | 239/245 B | 108 | 367 |
| `counting` | 488/494 B | 216 | 700 |
| `arrays` | 382/388 B | 182 | 569 |
| `records` | 389/395 B | 196 | 605 |
| `gameplay_full_stack` | 3.350/3.356 B | 815 | 2.712 |

Em `gameplay_full_stack`, a contabilidade atual tem 17 bytes de ZP
alocados/reservados por compilador/runtime/usuário, 1.004 bytes de RAM comum de
runtime/usuário, shadow de OAM de 256 bytes, 256 bytes reservados pela pilha de
hardware, 99 bytes de ZP indisponíveis por política e 416 bytes livres visíveis
ao alocador (140 ZP + 276 comuns). Portanto, 1.277 bytes são alocados/reservados
por compilador/runtime/usuário e 1.632 bytes do espaço da CPU estão
comprometidos/reservados. As categorias mais memória livre reconciliam
exatamente os 2.048 bytes do NES.

## Verificação

A validação local passou em 475 testes automatizados não-Mesen e nos 28 testes
headless dedicados do Mesen. O corpus completo de 20 benchmarks montou e linkou,
todos os exemplos públicos foram compilados pela suíte de integração da cadeia
de ferramentas, a compilação de bytecode Python passou e `git diff --check` não
reportou erros.

## Trabalho deliberadamente adiado

Functions, valores de retorno, frames de pilha, spilling, alocador geral de
registradores, CFG/SSA/dataflow e reordenação de expressões continuam adiados.
