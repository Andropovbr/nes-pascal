# Funções 0.5.12

[English](../../compiler/functions-0.5.12.md) | Português (Brasil)

A milestone 0.5.12 adiciona funções de usuário tipadas sobre o alocador de
temporários com escopo introduzido na 0.5.11. Ela não adiciona variáveis locais,
frames de pilha em runtime, recursão, retornos agregados, retornos antecipados ou
otimizações.

## Contrato implementado

- Declarações podem ser intercaladas com procedimentos antes do bloco principal.
- Parâmetros e valores de retorno suportam apenas `byte` e `boolean`.
- Declarações sem parâmetros omitem a lista; toda chamada usa parênteses.
- Atribuir o nome da função define seu resultado. A análise de atribuição
  definitiva exige um resultado em todo caminho que alcança o epílogo.
- Chamadas de função são resolvidas como expressões de valor e podem ser
  aninhadas em argumentos, aritmética, comparações, condições e expressões
  Booleanas de curto-circuito.
- Recursão direta, indireta e mista de procedimento/função é rejeitada.

## ABI e propriedade de memória

Os parâmetros de função mantêm a ABI de procedimento: um byte estático
determinístico de RAM regular por parâmetro por valor. Cada função também possui
um byte de resultado do compilador em RAM regular em `FUNCTION_RESULTS`. O
epílogo carrega esse byte no acumulador 6502 e retorna com `RTS`:

```asm
function_Add:
    ; body assigns function_result_Add
    lda function_result_Add ; return value in A
    rts
```

Não existe janela fixa compartilhada de retorno nem reserva de resultado em Zero
Page. Programas sem funções não emitem bytes de resultado, segmento
`FUNCTION_RESULTS` ou corpos de função. Endereços de retorno comuns de `JSR`
usam a pilha de hardware; o relatório de benchmarks informa a profundidade máxima
de chamada de origem e seu pico de endereço de retorno de dois bytes por chamada
separadamente da RAM comprometida.

A profundidade de chamada de origem é limitada em tempo de compilação para que os
endereços de retorno permaneçam dentro da pilha de hardware reservada de 256
bytes: com dois bytes por `JSR` ativo e dez bytes reservados para frames de `JSR`
de runtime e folga de NMI, a profundidade máxima suportada de chamada de origem é
123. Cadeias acíclicas mais profundas são rejeitadas com `E5007`; recursão é
rejeitada antes, com `E3014`.

A ABI chamável trata `A`, `X`, `Y` e as flags do processador como destruídos pelo
chamador; não existem registradores preservados pela função chamada. `A` contém o
resultado escalar no retorno, e carregar o resultado Booleano canônico também
deixa a flag zero válida para um branch direto. O ponteiro da pilha de hardware é
balanceado em cada `JSR`/`RTS`; temporários de expressão gerenciados pelo
compilador e bytes estáticos de parâmetro/resultado são os únicos locais de valor
preservados prometidos por esta milestone.

## Segurança de chamadas aninhadas

A análise de temporários reproduz todo o grafo de chamadas acíclico de origem.
Cada chamável recebe uma base determinística igual ao número máximo de slots de
expressão do chamador vivos em sua entrada. A geração de backend arrenda esse
prefixo enquanto reduz o corpo do chamável, de modo que temporários da função
chamada não podem se sobrepor a valores suspensos do chamador.

Os argumentos são avaliados da esquerda para a direita. Quando um argumento
posterior contém uma chamada de função, um resultado anterior é arrendado no pool
de expressões até que todos os argumentos estejam prontos; somente então ele é
copiado para o byte de parâmetro estático da função chamada. Isso também impede
que uma chamada aninhada à mesma função sobrescreva parâmetros parcialmente
preparados de uma chamada externa.

A ordem Booleana de curto-circuito permanece da esquerda para a direita. Nós de
aritmética binária e de comparação mantêm a regra de redução estabelecida:
operandos diretos à direita são consumidos após o lado esquerdo, enquanto um lado
direito que exige avaliação é avaliado e preservado antes do lado esquerdo.

O golden de pressão focado mantém o slot 0 na expressão principal, entra em
`Middle` na base 1 e entra em `Leaf` na base 2; `Leaf` então arrenda o slot 2 para
um pico verificado de três bytes simultaneamente vivos. A profundidade de chamada
de origem é dois, de modo que o pico correspondente de endereço de retorno é de
quatro bytes na pilha de hardware.

| Componente estático da ABI | Custo |
| --- | ---: |
| Resultado declarado por função | 1 B de RAM regular |
| Epílogo de função (`LDA abs` + `RTS`) | 4 B de PRG, 2 instruções |
| Transferência de chamada (`JSR`) | 3 B de PRG, 1 instrução |
| Endereço de retorno de origem ativo | 2 B na pilha de hardware |
| Valor de expressão suspenso | 1 byte de ZP com escopo enquanto vivo |

A avaliação de argumentos e o código do corpo de resultado são adicionais e
dependem da origem. Chamadas aninhadas não adicionam janela fixa de retorno nem
sobrecarga de frame de software.

## Benchmark

A entrada dedicada `functions` do corpus compila `examples/functions.nsp`,
incluindo um resultado de função passado diretamente a um procedimento, e mede:

| Métrica | Valor verificado |
| --- | ---: |
| Código PRG / ocupado | 365 B / 371 B |
| Instruções / ciclos-base estáticos estimados | 158 / 560 |
| Profundidade da árvore de expressão / máximo de temporários vivos | 2 / 1 |
| Profundidade máxima de chamada de origem / pico de endereço de retorno JSR | 2 / 4 B |
| Armazenamento de resultado de função | 3 B de RAM regular do compilador |
| Alocação regular de runtime + usuário | 11 B |
| RAM regular livre visível ao alocador | 1.522 B |
| Zero Page livre visível ao alocador | 142 B |
| Memória livre total visível ao alocador | 1.664 B |
| Compilador/runtime/usuário alocado ou reservado | 25 B |
| Espaço de endereço de CPU total comprometido/reservado | 384 B |

Todos os números de PRG, instruções, ciclos, RAM, Zero Page e pressão de
temporários dos benchmarks pré-existentes permanecem inalterados. Em particular,
`gameplay_full_stack` permanece com 3.350 B de código PRG, 3.356 B de PRG
ocupado, profundidade de expressão 1, zero temporários vivos, 815 instruções e
2.712 ciclos-base estáticos estimados.

## Cobertura de regressão

`tests/test_functions.py` cobre sintaxe, resolução tipada, chamadas diretas e
aninhadas, resultados definitivos (incluindo efeitos de curto-circuito
condicionais), diagnósticos canônicos, ciclos de recursão, propriedade explícita
de memória, custo zero sem funções, interação com builtins, três slots de
temporários simultaneamente vivos e goldens focados de ABI.
`tests/fixtures/runtime/functions.nsp` mais `tests/mesen/verify_functions.lua`
verificam segurança de parâmetros estáticos aninhados, argumentos da esquerda
para a direita, aritmética complexa primeiro à direita, comparações, normalização
Booleana, efeitos colaterais de curto-circuito, interação procedimento/função e
wrap-around de 8 bits em um ROM montado. A contabilidade de benchmarks tem uma
asserção focada para os três bytes de resultado regular de propriedade do
compilador e a reconciliação exata de 2 KiB.

A validação local final passou em todos os 524 testes automatizados, incluindo
todos os 29 testes Mesen headless dedicados. O corpus completo de benchmarks de
21 programas e todos os exemplos públicos foram montados e linkados com sucesso.