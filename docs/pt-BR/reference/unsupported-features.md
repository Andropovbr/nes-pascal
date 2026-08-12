# Recursos não suportados

[English](../../reference/unsupported-features.md) | Português (Brasil)

Esta página lista limites importantes da linguagem, runtime e plataforma-alvo
atualmente implementados. O trabalho planejado é acompanhado no
[roadmap do projeto](../../../roadmap/README.md); um item não marcado no roadmap não faz
parte da linguagem suportada.

## Limitações da linguagem

- `nes_color`, `byte`, `boolean`, `sprite` e `metasprite` são os únicos tipos embutidos.
- Declarações `type` e tipos definidos pelo usuário não são suportados.
- Constantes não podem se referir a outras constantes, e inicializadores de constantes
  não podem conter expressões.
- Inferência de tipos e conversões implícitas não são suportadas.
- A aritmética é limitada a operandos `byte` com `+` e `-` unários, `+` e `-` binários
  e parênteses.
- Multiplicação e divisão não são suportadas.
- Igualdade e desigualdade exigem tipos correspondentes; comparações ordenadas são
  limitadas a `byte`.
- Expressões booleanas suportam apenas `not`, `and` e `or`.
- `case`, records, funções gerais, strings em tempo de execução e Assembly inline
  não são suportados. Arrays são limitados a arrays globais unidimensionais de
  tamanho fixo com elementos `byte` ou `boolean`. Um pequeno conjunto fixo de expressões de consulta embutidas e os
  intrínsecos estaticamente resolvidos `nes.sprite_create()` e `nes.metasprite_create(frame)`
  são suportados.
- Parâmetros de procedimentos são limitados a valores `byte` e `boolean`. Não há parâmetros
  por referência, valores padrão, valores de retorno ou variáveis locais gerais.
- Chamadas de procedimentos podem ser aninhadas, mas não podem ser recursivas.
- Memória dinâmica e orientação a objetos não são suportadas.

## Limitações de instruções e execução

- As instruções são limitadas a atribuição, `inc` e `dec`, `if`/`else`, laços suportados,
  `break`, `continue`, chamadas de procedimentos, as APIs de paleta, `nes.load_background`,
  `nes.set_background_color`, `nes.set_scroll`, as primitivas de sprites de hardware `nes.sprite_*`,
  `nes.import_metasprite` em tempo de compilação e as primitivas `nes.metasprite_*`, `nes.run`,
  `nes.wait_frame`, `nes.on_update`, `nes.on_vblank` e o helper fixo do exemplo de controles `nes.set_sprite_zero`.
- Ramos condicionais e corpos de laços podem conter instruções suportadas, mas `nes.run` e o
  registro de callbacks permanecem exclusivos de nível superior. Chamadas de paleta em fluxo
  de controle de runtime ou procedimentos são preparadas para o VBlank.
- Laços sincronizados por quadros e callbacks de atualização são executados na thread principal.
  A NMI pode invocar apenas um callback de VBlank estaticamente registrado e transitivamente validado.
- `for` suporta apenas variáveis de controle e limites do tipo `byte`. Uma variável de controle
  não pode ser modificada dentro do corpo do seu laço.

## Limitações de runtime e plataforma-alvo

- A promoção automática para a Zero Page é limitada à política determinística de variáveis
  globais. Declarações explícitas na Zero Page não estão implementadas.
- Apenas NES NTSC, mapper 0, 32 KiB de PRG-ROM e 8 KiB de CHR-ROM são suportados.
- Um único arquivo de CHR-ROM bruto de exatamente 8 KiB é suportado. CHR-RAM, múltiplos
  arquivos ou bancos, conversão de gráficos, compressão e atualizações de CHR em runtime não são suportados.
- Uma única nametable bruta de 1 KiB para a nametable 0 é suportada durante a inicialização,
  seja combinada ou como 960 bytes de tiles mais 64 bytes de atributos, seguida por no máximo
  quatro atualizações enfileiradas de bytes de tiles ou atributos brutos por quadro. Múltiplas
  telas, nametables geradas, seleção alternativa de nametable, sistemas de jogabilidade com
  rolagem e streaming não são suportados. Um par fixo de rolagem pode ser preparado com `nes.set_scroll`.
- Controles padrão 1 e 2 são suportados sem remapeamento, Four Score, dispositivos de expansão,
  bufferização, combos, turbo ou leituras repetidas seguras para DMC.
- Primitivas de sprites de hardware suportam todas as 64 entradas de OAM, campos individuais,
  atributos de paleta/flip/prioridade, ocultar/exibir determinístico, alocação estática individual
  e DMA de OAM na NMI. Metasprites suportam layouts arbitrários de componentes com posse estática,
  seleção manual de quadros, posição do objeto inteiro, visibilidade, flip, recorte de sprites de
  hardware e sequências automáticas de quadros em repetição ou disparo único. Criação/destruição
  em runtime, velocidade variável de reprodução, interpolação (blending) de animações, colisão,
  multiplexação/flicker de sprites, ordenação e mitigação de estouro de scanlines não são suportados.
  `nes.set_sprite_zero` permanece como um helper legado de compatibilidade.
- O registro de callbacks é estático. Há apenas um callback de cada tipo, sem parâmetros, valores
  de retorno, prioridades, listas, remoção, chamadas indiretas, callbacks de IRQ ou tratadores de
  interrupção pertencentes ao usuário.
- Não há fila genérica de comandos da PPU. Alterações de paleta em runtime utilizam um shadow fixo
  e transmissor limitado no VBlank; outras escritas na PPU em tempo de renderização permanecem não suportadas.
- O compilador não fornece uma game engine ou uma passagem geral de otimização; a promoção na
  Zero Page é uma política fixa de alocação, não um otimizador de pontos críticos.
