# Compilando e executando programas

[English](../../getting-started/building-and-running.md) | Português (Brasil)

## Compilação

Compile o exemplo mínimo com:

```text
python -m nes_pascal.cli examples/minimal.nsp -o build/minimal.nes
```

O repositório também contém exemplos focados para cada área implementada da linguagem:

```text
python -m nes_pascal.cli examples/arithmetic.nsp -o build/arithmetic.nes
python -m nes_pascal.cli examples/boolean_expressions.nsp -o build/boolean_expressions.nes
python -m nes_pascal.cli examples/conditionals.nsp -o build/conditionals.nes
python -m nes_pascal.cli examples/loops.nsp -o build/loops.nes
python -m nes_pascal.cli examples/counting.nsp -o build/counting.nes
python -m nes_pascal.cli examples/arrays.nsp -o build/arrays.nes
python -m nes_pascal.cli examples/enumerations.nsp -o build/enumerations.nes
python -m nes_pascal.cli examples/records.nsp -o build/records.nes
python -m nes_pascal.cli examples/procedures.nsp -o build/procedures.nes
python -m nes_pascal.cli examples/procedure_parameters.nsp -o build/procedure_parameters.nes
python -m nes_pascal.cli examples/functions.nsp -o build/functions.nes
python -m nes_pascal.cli examples/memory_layout.nsp -o build/memory_layout.nes
python -m nes_pascal.cli examples/zero_page.nsp -o build/zero_page.nes
python -m nes_pascal.cli examples/frame_synchronization.nsp -o build/frame_synchronization.nes
python -m nes_pascal.cli examples/frame_callbacks.nsp -o build/frame_callbacks.nes
python -m nes_pascal.cli examples/slow_update_callback.nsp -o build/slow_update_callback.nes
python -m nes_pascal.cli examples/controller_input.nsp -o build/controller_input.nes
python -m nes_pascal.cli examples/sprite_support.nsp -o build/sprite_support.nes --chr assets/chr_asset.chr
python -m nes_pascal.cli examples/metasprite_player.nsp -o build/metasprite_player.nes --chr assets/game.chr --metasprite assets/player_idle.json
python -m nes_pascal.cli examples/metasprite_clipping.nsp -o build/metasprite_clipping.nes --chr assets/game.chr --metasprite assets/player_idle.json
python -m nes_pascal.cli examples/sprite_animation.nsp -o build/sprite_animation.nes --chr assets/game.chr --metasprite assets/player_consolidated.json
python -m nes_pascal.cli examples/chr_asset.nsp -o build/chr_asset.nes --chr assets/chr_asset.chr
python -m nes_pascal.cli examples/palette_support.nsp -o build/palette_support.nes --chr assets/chr_asset.chr
python -m nes_pascal.cli examples/nametable_loading.nsp -o build/nametable_loading.nes --chr assets/chr_asset.chr --nametable assets/nametable_loading.nam
python -m nes_pascal.cli examples/background_updates.nsp -o build/background_updates.nes --chr assets/chr_asset.chr --nametable assets/nametable_loading.nam
python -m nes_pascal.cli examples/scrolling_ppu_state.nsp -o build/scrolling_ppu_state.nes --mirroring horizontal
python -m nes_pascal.cli examples/gameplay_full_stack.nsp -o build/gameplay_full_stack.nes --chr assets/game.chr --nametable assets/nametable_loading.nam --metasprite assets/player_consolidated.json
```

Os exemplos demonstram:

- `arithmetic.nsp`: aritmética de bytes unária e binária;
- `boolean_expressions.nsp`: comparações e operadores booleanos;
- `conditionals.nsp`: desvios simples, compostos e aninhados;
- `loops.nsp`: contagem, fluxo de controle aninhado, `break` e `continue`;
- `counting.nsp`: `inc` e `dec` com estouro circular (wrapping), laços `for`
  ascendentes e descendentes, limites exatos `$00` e `$FF` e laços aninhados;
- `arrays.nsp`: arrays fixos de bytes e booleanos, índices constantes e
  variáveis, preenchimento em laço, acumulação indexada e branches sobre
  elementos booleanos;
- `enumerations.nsp`: estados de jogo nominais, atribuições de membros,
  comparações de tipo exato e uma transição de estado determinística;
- `records.nsp`: records de layout fixo, campos enum e booleanos, arrays de
  records e indexação de campos por constantes e variáveis;
- `procedures.nsp`: resolução antecipada (forward) de procedimentos, chamadas
  aninhadas, estado global compartilhado, `JSR`/`RTS` e uma condicional dentro
  de um procedimento;
- `procedure_parameters.nsp`: parâmetros de valor tipados, cópia de argumentos
  da esquerda para a direita, valores de parâmetros locais mutáveis e chamadas
  parametrizadas aninhadas;
- `functions.nsp`: retornos tipados byte/Boolean, chamadas aninhadas,
  atribuição do resultado, temporários seguros e retorno pelo acumulador;
- `scrolling_ppu_state.nsp`: um par de rolagem (scroll) fixo diferente de zero,
  uma atualização de paleta e restauração para o par padrão `($00, $00)`;
- `memory_layout.nsp`: variáveis globais, parâmetros de procedimentos, expressões
  e um laço for alocados através do layout de memória determinístico do runtime;
- `zero_page.nsp`: temporários obrigatórios na Zero Page, globais promovidas e
  uma variável de fallback em RAM comum (não promovida);
- `frame_synchronization.nsp`: inicialização do runtime seguida por um laço de
  três quadros na thread principal sincronizado com `nes.wait_frame`.
- `frame_callbacks.nsp`: um contador de atualização na thread principal e um
  contador de VBlank na NMI, incluindo um helper seguro para VBlank validado
  transitivamente.
- `slow_update_callback.nsp`: uma atualização deliberadamente longa que cruza
  NMIs e demonstra a aglutinação (coalescing) de quadros pendentes sem chamadas
  aninhadas.
- `controller_input.nsp`: movimentação do controle 1, velocidade ao segurar A,
  alternância visual ao pressionar/soltar B, reset com Start, alternância de
  modo com Select, preparação segura do sprite 0, DMA de OAM e dois pequenos
  tiles de CHR embutidos.
- `sprite_support.nsp`: um sprite de hardware estaticamente alocado e fortemente
  tipado, posicionado pela API de shadow da OAM e transferido pelo DMA de OAM da NMI.
- `metasprite_player.nsp`: o asset de jogador fornecido pelo PNG2CHR Studio,
  movimentação em todas as oito direções do direcional (D-pad), inversão de
  orientação (flip) com âncora centralizada, seleção manual de quadro com A,
  ocultar/exibir objeto inteiro com Select e limites explícitos de jogabilidade
  que mantêm todos os componentes visíveis em todas as quatro bordas.
- `metasprite_clipping.nsp`: um laço visual lento do centro para as bordas
  esquerda, direita, superior e inferior e retorno. Cada alvo está distante o
  suficiente além da tela apenas para recortar uma linha ou coluna de componentes,
  mantendo a demonstração visível e compreensível. O estado de flip é
  explicitamente limpo em cada estágio; componentes completos de 8 por 8
  desaparecem e retornam sem estouro (wrapping).
- `sprite_animation.nsp`: um manifesto consolidado de animações idle/movimento,
  troca automática de estado, reinício explícito com o botão A, ocultar/exibir
  com Select sem pausar o tempo, orientação esquerda/direita persistente e
  movimentação no D-pad em todas as oito direções.
- `chr_asset.nsp`: inclusão de um asset CHR-ROM bruto relativo ao projeto.
- `palette_support.nsp`: dados de CHR personalizados, paletas de fundo e sprite
  inicializadas, seguido por uma atualização segura e enfileirada de paleta
  completa e individual.
- `nametable_loading.nsp`: uma nametable bruta de 1 KiB relativa ao projeto
  carregada completamente, incluindo sua tabela de atributos, antes do início
  da renderização.
- `background_updates.nsp`: escritas de tiles limitadas e repetidas, leituras
  com shadow confirmado, rejeição de estouro de tiles e atributos, cancelamento
  de pendências, limpeza explícita de estouro e uma atualização de atributos
  brutos após a inicialização do runtime.
- `gameplay_full_stack.nsp`: o exemplo full-stack que combina carregamento de
  background, entrada de controle, paletas, um jogador metasprite em movimento
  com animação e pressão combinada de RAM em um único programa.

As constantes `PlayerMinimumX`, `PlayerMaximumX`, `PlayerMinimumY` e
`PlayerMaximumY` do exemplo do jogador são específicas do asset incluído, e não
limites do renderizador. Cada quadro importado tem deslocamentos superior-esquerdo
de componentes de `-12` a `+4`, para uma extensão visível completa de `-12..+11`
ao redor da âncora. O eixo X, portanto, usa `$0C..$F4`. Os topos dos componentes
do metasprite usam Y lógico `1..232`, portanto Y usa `$0D..$E4`. O exemplo de
recorte intencionalmente não utiliza esses limites de jogabilidade.

Os exemplos de laço, contagem e parâmetros de procedimento selecionam a cor de
fundo `$21` apenas quando seus estados finais esperados são alcançados.

O atalho do `Makefile` compila o programa mínimo:

```text
make rom
```

As ROMs geradas utilizam o formato descrito em
[Plataforma-alvo](../../runtime/target-platform.md).

Cada comando também grava uma configuração gerada do ld65 ao lado da ROM usando
o sufixo `.cfg` e um relatório legível da RAM da CPU usando `.map`. O mapa
lista regiões reservadas, de runtime, do compilador, do usuário e livres, além
do endereço de cada variável e parâmetro de valor do código-fonte. Consulte
[Memória da CPU](../../runtime/cpu-memory.md).

## Assets de CHR-ROM

Configure um arquivo CHR-ROM bruto com `--chr`:

```text
python -m nes_pascal.cli examples/chr_asset.nsp -o build/chr_asset.nes --chr assets/chr_asset.chr
```

Caminhos relativos são resolvidos a partir do diretório que contém o código-fonte
`.nsp`, e não a partir do diretório de trabalho do processo do compilador. Os
componentes `.` e `..` e os separadores nativos da plataforma são suportados;
caminhos absolutos permanecem válidos. NROM atualmente requer exatamente 8192 bytes
(8 KiB). Um arquivo configurado ausente, ilegível ou com tamanho incorreto interrompe
a compilação com um diagnóstico. Quando `--chr` é omitido, o compilador gera uma
CHR-ROM vazia de 8 KiB (exceto para a demonstração fixa existente do sprite 0, que
mantém seus tiles internos).

Programas com metasprites adicionam um ou mais caminhos JSON repetíveis com `--metasprite`
e também devem configurar o banco correspondente de 8 KiB de CHR. Ambos os tipos de
caminho são resolvidos a partir do diretório do `.nsp`. Consulte
[Metasprites](../../runtime/metasprites.md) para ver o contrato de metadados, nomes
simbólicos de quadros e custo de OAM, e [Animação de sprites](../../runtime/sprite-animation.md)
para símbolos de sequência, temporização, política de repetição e custo de RAM/ROM de animação.

## Assets de nametable

Programas que utilizam `nes.load_background();` configuram um único arquivo bruto
de 1024 bytes ou um mapa de tiles de 960 bytes acompanhado por uma tabela de atributos
de 64 bytes:

```text
python -m nes_pascal.cli examples/nametable_loading.nsp -o build/nametable_loading.nes --chr assets/chr_asset.chr --nametable assets/nametable_loading.nam
python -m nes_pascal.cli game.nsp -o build/game.nes --nametable-tiles assets/screen.tiles --nametable-attributes assets/screen.attributes
```

As opções são formatos mutuamente exclusivos. As opções divididas devem aparecer juntas.
Os caminhos seguem as mesmas regras de normalização e resolução relativa ao fonte que
`--chr`. Consulte [Carregamento de fundo](../../runtime/background-loading.md) para ver o
layout bruto, comportamento de inicialização e os limites atuais de tela única.

Após `nes.run`, use `nes.set_tile`, `nes.get_tile`, `nes.set_attribute`,
`nes.clear_background_updates`, `nes.background_updates_overflowed` e
`nes.clear_background_update_overflow` conforme descrito em
[Atualizações de fundo em runtime](../../runtime/background-updates.md). No máximo
quatro bytes de tiles ou atributos são transferidos durante cada VBlank.

## Executando no Mesen

1. Gere `build/minimal.nes`.
2. Abra o Mesen.
3. Selecione **File > Open** e escolha `build/minimal.nes`.
4. A tela deve permanecer estável com a cor de fundo universal `$21`.

## Limpando arquivos gerados

Remova os artefatos de build com:

```text
make clean
```
