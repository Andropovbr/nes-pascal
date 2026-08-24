# Implementação e Medições de Geração de Números Aleatórios (0.5.14)

[English](../../compiler/random-number-generation-0.5.14.md) | Português (Brasil)

O milestone 0.5.14 adiciona um LFSR Galois de 16 bits feature-gated e três
builtins declarativos: `nes.seed_random`, `nes.random_byte` e
`nes.random_range`. Os descritores selecionam `RuntimeFeature.RANDOM` e, apenas
para ranges, `RuntimeFeature.RANDOM_RANGE`; não há caso especial por nome público
no parser ou backend.

O passo congelado é `(state >> 1) xor $B400` quando o bit baixo anterior é um.
O período máximo de 65.535 estados não nulos foi validado. A chamada avança
primeiro e retorna o novo byte baixo. Seed não nula `$SS` expande para `$SSSS`;
zero normaliza para `$ACE1`. Estado limpo zero é um marcador inativo de
auto-seed. A primeira chamada mistura um snapshot coerente de quadro/controles e
não faz reseed automático depois.

Ranges inclusivos calculam cutoff `256 mod span`, rejeitam a cauda incompleta e
reduzem bytes aceitos por subtração repetida. O custo é variável e não adiciona
divisão/módulo genéricos. Limites dinâmicos invertidos e singleton retornam o
mínimo sem avançar; limites constantes invertidos geram `E3064`.

## Benchmark

| Métrica | `random_numbers` |
| --- | ---: |
| Código PRG / ocupado | 417 / 423 B |
| Instruções | 193 |
| Ciclos estáticos-base estimados | 659 |
| RAM regular de runtime | 8 B total; 4 B de RNG |
| ZP do RNG | 0 B |
| RAM de resultado de Function | 1 B |
| RAM do usuário | 3 B |
| Máximo de temporários vivos | 0 |
| Profundidade de chamadas fonte | 1 |

O benchmark inclui byte com seed, range não potência de dois, range potência de
dois em Function e rotinas compartilhadas. A estimativa estática não representa
repetições de rejeição nem latência média/pior caso.

Todos os benchmarks anteriores preservam exatamente as métricas 0.5.13. Uma ROM
mínima não contém símbolos, rotinas, estado ou scratch de RNG.

Testes puros validam o ciclo completo, vetores, seed zero e mapeamentos uniformes
para spans 3, 5, 6, 7, 10, 100 e 255. Goldens cobrem estado, seed, passo e redução.
Duas ROMs Mesen cobrem sequência de 16 bytes, boundaries, Functions, ordem,
short-circuit, normalização e auto-seed controlado por quadro/controle atrasado.

Criptografia, entropia de hardware, valores públicos de 16 bits, distribuições,
shuffle/choice, tabelas ponderadas, streams independentes, objetos RNG, noise e
divisão/módulo genéricos permanecem fora do escopo.
