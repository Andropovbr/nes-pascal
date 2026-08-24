# Números Aleatórios

[English](../../runtime/random-numbers.md) | Português (Brasil)

NES Pascal fornece um PRNG pequeno e determinístico para gameplay. Ele é
adequado para comportamento de inimigos, seleção de spawns, loot, variação
visual e escolhas procedurais. Ele **não é criptograficamente seguro** e não é
uma fonte de entropia.

## API

```pascal
nes.seed_random($2A);
Value := nes.random_byte();
EnemyX := nes.random_range($08, $F7);
```

- `nes.seed_random(seed: byte)` seleciona um fluxo reproduzível. Uma semente
  não nula `$SS` mapeia para o estado interno `$SSSS`; `$00` mapeia para `$ACE1`.
- `nes.random_byte(): byte` avança o estado exatamente uma vez e retorna o byte
  baixo do novo estado.
- `nes.random_range(minimum: byte, maximum: byte): byte` usa limites inclusivos
  `[minimum, maximum]`. Limites iguais retornam o byte sem avançar. Um mínimo
  dinâmico maior que o máximo retorna o mínimo sem avançar; limites constantes
  invertidos geram `E3064`. `$00..$FF` avança uma vez e retorna um byte comum.

O gerador é um LFSR Galois de 16 bits com deslocamento para a direita e máscara
XOR `$B400`. Todos os estados não nulos formam um ciclo de 65.535 estados. O
estado zero é absorvente e nunca é ativado. Em RAM limpa, `$0000` significa
apenas “auto-seed pendente”; a primeira chamada o substitui por um estado não
nulo derivado de timing antes do passo.

Algoritmo, mapeamento de seed, convenção de passo antes da saída e sequência são
um contrato de compatibilidade. A seed `$2A` começa em `$15, $8A, $45, $A2,
$D1, $E8, $74, $BA, ...`. Mudanças futuras devem ser documentadas explicitamente.

## Seed automático e determinístico

Sem `nes.seed_random`, a primeira chamada captura o contador de quadros da NMI.
Se APIs de controle já estiverem vinculadas, ela também aplica XOR aos estados
atuais dos controles 1 e 2. O byte misturado recebe XOR `$E1` no estado baixo e
`$AC` no alto, garantindo um par não nulo. Isso produz variação simples de
timing, não entropia verdadeira.

A mistura automática ocorre uma única vez antes do primeiro passo. Quadros e
entradas posteriores não alteram um fluxo ativo. `nes.seed_random` instala um
estado não nulo, desativa implicitamente a mistura automática e garante que a
mesma seed e ordem de chamadas produzam a mesma saída. Endereços de ROM, layout
de código, RAM não inicializada e timing do host não participam.

## Redução limitada e timing

Para um span `N`, o runtime rejeita bytes abaixo de `256 mod N` e reduz o domínio
restante por subtrações repetidas. Isso evita o viés de `random_byte() mod N`
sem adicionar divisão/módulo genéricos. Spans que dividem 256 têm cutoff zero; o
domínio completo de 256 bytes usa um caminho direto.

Rejection sampling tem tempo variável. Um LFSR válido eventualmente aceita para
todo span, mas código com orçamento rígido deve considerar novas tentativas. O
helper usa dois bytes de RAM regular para span e cutoff.

## Chamadas, callbacks e memória

Chamadas aleatórias têm efeito colateral e não são duplicadas, removidas ou
reordenadas. Argumentos de função e short-circuit Booleano continuam da esquerda
para a direita. Aritmética complexa mantém a ordem existente: um operando direito
não direto é avaliado antes do esquerdo. Um operando Booleano pulado não avança o
PRNG.

Chamadas RNG em caminhos de callback VBlank geram `E3023`; use inicialização,
código principal, Functions ou o callback de update.

Programas sem RNG não emitem código nem alocam RAM/ZP de RNG. `random_byte` ou
`seed_random` usa exatamente 2 bytes de RAM regular e zero bytes de ZP.
`random_range` acrescenta 2 bytes regulares de scratch. Não há heap nem pool de
temporários específico de RNG.

Consulte [o exemplo de números aleatórios](../../../examples/random_numbers.nsp).
