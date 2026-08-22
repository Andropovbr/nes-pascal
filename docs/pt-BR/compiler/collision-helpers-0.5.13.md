# Implementação e Medições dos Helpers de Colisão (0.5.13)

[English](../../compiler/collision-helpers-0.5.13.md) | Português (Brasil)

O marco 0.5.13 adiciona colisões leves e apenas consultivas sobre a
infraestrutura existente de records, builtins, sprites, metasprites, funções e
assets. `nes_rect` é um `RecordType` canônico predefinido, não um novo escalar.
As chamadas resolvem para `BuiltinId` estáveis com hooks semânticos, emissores
de backend e dependências de runtime explícitos.

## Lowering e memória

Ponto/retângulo e retângulo/retângulo carregam endereços diretos por um
ponteiro Zero Page de dois bytes ativado por recurso. Dez bytes compartilhados
de RAM comum guardam dois retângulos e um ponto/instância. Os validadores usam
fim alargado com carry: fim lógico 256 é válido; fim maior e área zero retornam
false. A sobreposição compara distâncias unsigned entre inícios, tornando mero
toque uma não colisão sem aritmética com wrap.
Entradas escalares sensíveis a chamadas reutilizam o alocador de expressões
quando uma função posterior pode executar outra consulta; referências diretas
a records continuam operandos sem temporário.

Bounds de sprite reutilizam X da OAM e o cache existente de Y lógico. Bounds de
metasprite usam quatro bytes imutáveis por frame, vindos de `collision_box` ou
dos extremos dos componentes calculados em compilação. Flips transformam os
offsets ao redor da âncora já estabelecida. Não há lista de colliders,
descritor por entidade, heap, resposta física ou varredura geométrica em
runtime.

Assets de fundo entram como 32 flags texto em cada uma de 30 linhas. O
compilador valida e compacta em 120 bytes PRG. A consulta deriva diretamente
dos pixels um índice compactado 0..119, soma ao rótulo ROM por um ponteiro ZP
de 16 bits e testa uma tabela de máscaras de 8 bytes. Índices lógicos acima de
255 funcionam sem aritmética pública de 16 bits. Esse caminho não seleciona
`BACKGROUND_GET_TILE` nem aloca seu shadow de 960 bytes.

## Benchmarks

| Benchmark | Código/ocupado PRG | Instruções | Ciclos-base estáticos | ZP alocada/reservada | Runtime/usuário comum | OAM | Temporários máximos | Payload do mapa |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `collision_rectangles` | 1.907/1.913 B | 760 | 2.510 | 17 B | 110 B | 256 B | 0 | 0 B |
| `collision_background` | 476/482 B | 161 | 530 | 11 B | 10 B | 0 B | 0 | 120 B |

O workload de retângulos inclui ponto/retângulo, AABB, bounds de sprite e
metasprite, dependências já existentes do runtime de sprites e records do
usuário. O workload de fundo inclui quatro consultas, dois bytes de scratch,
os símbolos do ponteiro, payload de 120 bytes e tabela de máscaras de 8 bytes.

Os 21 workloads anteriores preservam exatamente suas medições de PRG,
instruções, ciclos, RAM, Zero Page e pressão de temporários da 0.5.12.
`gameplay_full_stack` continua com 3.350 B de código PRG, 3.356 B ocupados,
profundidade 1, zero temporários vivos, 815 instruções e 2.712 ciclos-base
estáticos estimados. Um programa mínimo não contém símbolos, rotinas ou dados
de colisão.

Testes focados cobrem registro declarativo, tipo nominal, gating, custos exatos,
assets inválidos, metadata custom/fallback e flips, independência do shadow e
Assembly golden seletivo. Um ROM determinístico no Mesen cobre bordas, área
zero, wrap, fim exato 256, bounds de sprite/metasprite, interação com funções e
curto-circuito, limites de tiles, Y fora da tela e índice lógico 641.

A validação local final passou em todos os 558 testes automatizados sem pulos
ou falhas, incluindo os 30 testes Mesen headless dedicados. O corpus completo
de 23 benchmarks foi montado e linkado, e o smoke build da ROM mínima concluiu
com o compilador na versão 0.5.13.

## Adiado deliberadamente

Física, resposta à colisão, mapas mutáveis, coordenadas de mundo/rolagem,
escalares signed públicos, coordenadas públicas de 16 bits, slopes, círculos,
polígonos, colisão contínua, pathfinding, partição espacial, ECS e registro
automático de colliders ficam fora deste marco.
