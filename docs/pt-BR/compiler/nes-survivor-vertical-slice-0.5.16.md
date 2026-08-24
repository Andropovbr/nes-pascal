# Vertical Slice de NES Survivor — 0.5.16

[English](../../compiler/nes-survivor-vertical-slice-0.5.16.md) | Português (Brasil)

O marco 0.5.16 valida a linguagem e o runtime existentes do NES Pascal como um
único sistema de gameplay. Ele adiciona um vertical slice duradouro de NES
Survivor; não altera alocação do compilador, não implementa otimização e não
adiciona recurso de linguagem.

## Referência congelada

A base de comparação é a branch `main` de
[`Andropovbr/nes-survivor`](https://github.com/Andropovbr/nes-survivor),
congelada em 24/08/2026 no commit:

```text
af433de5ad5705d756e9f4cb9ff800fc91b6261c
```

O SHA foi resolvido no remoto oficial antes da inspeção. O checkout da
referência permaneceu somente leitura; uma cópia isolada foi usada para
verificar mapa e ROM. Builds e testes do NES Pascal nunca acessam a rede.

O workload mantido é
[`examples/nes_survivor/nes_survivor_vertical_slice.nsp`](../../../examples/nes_survivor/nes_survivor_vertical_slice.nsp).
Todos os inputs ficam no diretório `assets/` ao lado dele.

## Descobertas do fluxo de assets (Asset Workflow Findings)

| Input local | Fonte na referência congelada | SHA-256 | Papel |
| --- | --- | --- | --- |
| `assets/game.chr` | `assets/game.chr` mais `src/chr.s` | `285c4879a83641e45debc34e6c5ea889a8552e423cf0e24df88efcad7c7185e2` | composição CHR exata de 8 KiB extraída da ROM congelada |
| `assets/arena_blank.nam` | fixture de integração do NES Pascal | `30a0c265f473bc034386a7d6c3f42b81ada1da6bccb03393602c2c240947896a` | tile map estático com 960 bytes `$15` e 64 atributos zerados |
| `assets/player.json` | `assets/png2chr-studio/nes_survivor.p2c.json`, `src/soldier_animation_data.c` | `a356e0d070e13ecae915ec356ec041e087506b92ae215b8e73705b0aba3a25a9` | adaptador idle/walking do Soldier |
| `assets/sword.json` | mesmo projeto e `src/weapon_sword.c` | `bc1c7b22533b8db9b9f18fdfe7e29c47afbcc385be816c18c13c4c102d7f5715` | adaptador da espada de dois tiles |
| `assets/bat.json` | mesmo projeto e `src/bat_animation_data.c` | `dacc6edbc988dafa6e33ef29cebd157f2592b23fb959da872d1eeef954d273ca` | adaptador de dois quadros do Bat |
| `assets/gem.json` | mesmo projeto e `src/xp_gem.c` | `698b781aa3df5305689cf1a35c95c6e79e209cc52e000efcde31b4b03ef14ab9` | adaptador da gema de um tile |

O `assets/game.chr` fonte da referência tem SHA-256
`86d7033d970b090a01ac46c3ef42c469abbe58a719df0e02eee27a4b518a2c99`.
Seus primeiros 4 KiB fornecem a tabela de sprites; a segunda metade não é
copiada para a ROM. O `src/chr.s` congelado gera a fonte de background. Portanto,
o `game.chr` local é o banco CHR final exato extraído da ROM de referência
verificada, e não uma cópia inalterada do asset fonte.

Os quatro JSONs são adaptadores mínimos e determinísticos para o contrato já
suportado `png2chr-studio-animation` versão 2. Eles preservam tiles, atributos,
duração e geometria da referência, mas separam as quatro entidades. A separação
evita que cada Bat ou gema reserve sete componentes, pois o NES Pascal
dimensiona uma instância pelo maior quadro de seu asset.

Para auditar ou recriar os inputs:

1. faça checkout do SHA congelado fora deste repositório;
2. valide o hash do `assets/game.chr` fonte, monte a referência congelada e
   extraia seu banco CHR final de 8 KiB (ou monte a composição equivalente de
   `src/chr.s`); valide o hash local da tabela;
3. inspecione as cinco animações em
   `assets/png2chr-studio/nes_survivor.p2c.json` e as tabelas C citadas;
4. emita uma raiz de metadados versão 2 por entidade, mantendo tiles e atributos;
5. gere `arena_blank.nam` com 960 bytes `$15` seguidos de 64 bytes `$00`;
6. rode `python -m unittest tests.test_nes_survivor_vertical_slice -v` para
   validar CHR, tiles ocupados, geometria, orçamento OAM e snapshot estrutural.

O projeto nativo do PNG2CHR Studio e o input atual do compilador não são o mesmo
formato de intercâmbio. Remover esse adaptador manual pertence ao marco 0.5.17.

## Descobertas de CHR e pattern tables (CHR and Pattern-Table Findings)

O `assets/game.chr` original **não** contém o alfabeto do pattern table 1: seus
4 KiB finais estão vazios. A referência obtém os glifos de dados `font_tile`
inline em `src/chr.s`. Esse fonte copia apenas os primeiros 4 KiB de
`assets/game.chr`, emite as letras maiúsculas e completa o restante da tabela 1
com zeros. Assim, a ROM C/Assembly contém 21 tiles de sprite e 18 glifos de
background preenchidos.

O `assets/game.chr` congelado no NES Pascal reproduz byte a byte a composição
CHR final da ROM de referência. Nenhum tile foi redesenhado ou movido. A
inspeção em runtime corrigiu uma premissa anterior da documentação: em Playing,
o `PPUCTRL` autoritativo é `$80`. Os bits 3 e 4 estão zerados, portanto sprites
e background selecionam o pattern table `$0000-$0FFF`. A fonte permanece em
`$1000-$1FFF`, mas este recorte não a seleciona nem renderiza.

| Índices CHR | Uso neste workload |
| --- | --- |
| `$00-$07` | quadros do Soldier/jogador |
| `$08-$09` | espada vertical |
| `$0A-$0D` | dois quadros de voo do Bat |
| `$0E-$13` | tiles do skeleton da referência, mantidos mas não usados |
| `$14` | gema de XP |
| `$15-$FF` na tabela de sprites | vazios |
| tiles de background `$41-$45`, `$47-$49`, `$4D-$50`, `$52-$56`, `$59` | glifos maiúsculos gerados por `src/chr.s` |
| demais tiles da tabela de background | vazios |

O NES Pascal preserva a organização da CHR, mas ainda não possui o pequeno
loader direto de texto por tela da referência. Incluir a fila geral atual de
updates de background reservaria 995 bytes de RAM regular, acima dos 918 bytes
livres neste workload. O fallback seguro distingue Title, Playing, dano e
GameOver por cores universais e mostra o emblema central de sete sprites no
Title. Os glifos continuam congelados na CHR para proveniência exata e validação
futura do fluxo de telas; este recorte não os renderiza.

### Correção do background da arena

A ROM 0.5.16 original repetia um padrão de tile por toda a arena. A inspeção da
ROM sem alterações no Mesen confirmou a causa completa:

- Playing restaurava `PPUCTRL=$80` e `PPUMASK=$1E`; o background selecionava o
  pattern table 0, não o 1;
- nenhum background estático estava configurado, então RESET não inicializava a
  nametable 0;
- no Mesen, posições representativas da nametable e dos atributos continham
  `$00`, embora a VRAM de power-on do NES real não seja garantida;
- o valor `$00` da nametable selecionava o tile `$00` do pattern table 0, cujos
  16 bytes congelados contêm gráficos não vazios do Soldier;
- o tile `$00` do pattern table 1 era vazio, mas essa tabela não estava ativa.

O problema não era restauração de paleta nem scroll obsoleto. Era a combinação
de nametable não inicializada, seleção real da tabela 0 e tile `$00` não vazio.

A correção focada adiciona `arena_blank.nam` e chama o comando existente
`nes.load_background()` uma vez antes de `nes.run`. As 960 posições usam `$15`,
o primeiro tile vazio depois da arte preenchida da tabela 0, e os 64 atributos
usam `$00`. O upload ocorre com rendering desativado, eliminando dependência da
VRAM de power-on. O dano altera apenas a cor universal; depois do countdown
exato de dez updates, o preto volta sobre a nametable vazia. O restart reutiliza
o mesmo estado determinístico da PPU.

Não há custo persistente de RAM, Zero Page, runtime feature, fila ou shadow. O
PRG aumenta 1.083 bytes: 1.024 bytes da nametable e 59 bytes do upload único. A
inicialização emitida adiciona 25 instruções e 76 ciclos-base estáticos, sem
executar no loop de gameplay.

## Vertical slice implementado

O programa combina:

- enums `GameState`, `EnemyState` e `GemState`;
- arrays fixos de 12 records `Enemy` de quatro bytes e oito records
  `ExperienceGem` de três bytes;
- Functions tipadas para estado ativo e colisões retangulares;
- movimento em oito direções, com opostos cancelados por eixo;
- animação idle de um quadro e walking de dois, preservando facing horizontal;
- espada automática ativa por 12 quadros a cada período de 60;
- 12 Bats animados simultâneos, spawn nas bordas via RNG e perseguição de um
  pixel a cada três updates;
- colisão espada/Bat alternada por paridade, morte e criação de gema;
- uma colisão rotativa de coleta por update e contador de XP observável;
- contato Bat/jogador rotativo, cinco HP, 30 updates de invulnerabilidade e
  flash vermelho de dez updates no lugar de áudio;
- estados visíveis Title, Playing e GameOver, com Start iniciando e reiniciando
  a sessão sem reset da ROM.

O gameplay é representativo, não um port linha a linha. Ele mantém tamanhos de
pool, período do ataque, dano, período de spawn, arte e pico OAM da referência.

## Propriedade OAM

| Pool | Instâncias | Sprites por instância | Pico reservado/visível |
| --- | ---: | ---: | ---: |
| Jogador | 1 | 7 | 7 |
| Espada | 1 | 2 | 2 |
| Bats | 12 | 2 | 24 |
| Gemas | 8 | 1 | 8 |
| **Total** | **22 metasprites** | — | **41/64** |

O último slot é `$28` (decimal 40), restando 23 entradas. O cenário Mesen deixa
as 41 visíveis ao mesmo tempo e confere a contagem exata. Assim como a
referência, não há rotação de prioridade por scanline.

## Saída medida do NES Pascal

O benchmark chama-se `nes_survivor_vertical_slice`.

| Métrica de código | Valor verificado |
| --- | ---: |
| Código PRG | 6.991 B |
| PRG ocupado, incluindo vetores | 6.997 B |
| Header iNES | 16 B |
| CHR-ROM | 8.192 B |
| Linhas de Assembly gerado | 5.003 |
| Instruções geradas | 2.678 |
| Soma estática de ciclos-base | 8.175 |
| Profundidade máxima da árvore de expressão | 2 |
| Temporários de expressão vivos máximos | 0 |
| Profundidade máxima de chamadas do usuário | 5 |
| Uso máximo da return stack do usuário | 10 B |

Os 8.175 ciclos são a soma do estimador sobre o stream estático inteiro, não um
caminho de quadro. O custo dinâmico é validado no Mesen.

### Inspeção do código gerado

O ca65 gerado foi inspecionado em `UpdatePlayer`, `UpdateSword`,
`UpdateEnemies`, nos dois loops de colisão, em `UpdateGems` e no dispatch de
estados. O índice do record `Enemy` de quatro bytes vira dois `ASL`; o índice da
gema de três bytes usa um pequeno loop de soma. Cada acesso de campo recalcula o
offset escalado, e o dispatch de handles de metasprite vira duas cadeias de
branches. Os helpers compartilhados de colisão, RNG, animação e metasprite são
chamados, não duplicados.

Não há pressão de temporários de expressão, mas o scanner registra 31
materializações booleanas canônicas, 22 candidatos `CMP #$00` redundantes e
quatro round trips store/load. Junto ao escalonamento repetido de records, são
oportunidades medidas de codegen, não otimizações introduzidas neste marco.

### Contabilidade de RAM da CPU

| Métrica de memória | Bytes |
| --- | ---: |
| Símbolos de runtime na Zero Page | 15 |
| Caches do compilador na Zero Page | 7 |
| Variáveis do usuário promovidas à Zero Page | 32 |
| Temporários de expressão necessários na Zero Page | 0 |
| **Zero Page alocada/reservada pelo workload** | **54** |
| Zero Page indisponível por política | 97 |
| **Zero Page livre visível ao alocador** | **105** |
| Alocação regular de runtime | 243 |
| Resultados de Functions do compilador | 3 |
| Alocação regular do usuário | 116 |
| **Alocação não-ZP regular/runtime/usuário** | **362** |
| Shadow OAM | 256 |
| Reserva da página da pilha de hardware | 256 |
| **RAM regular livre visível ao alocador** | **918** |
| **Memória livre total visível ao alocador** | **1.023** |
| **Alocado/reservado por compilador/runtime/usuário** | **672** |
| **Espaço de endereços total comprometido/reservado** | **1.025** |

```text
1.025 comprometidos/reservados + 1.023 livres = 2.048 bytes
```

Os 97 bytes de política não são consumo do programa. A página de hardware de
256 bytes é reserva, não ocupação dinâmica comprovada da pilha.

### Stress em runtime

O cenário headless chega a 12 Bats e oito gemas, mantém 41 sprites por 120
quadros de vídeo e observava 107 updates antes deste follow-up e 106 depois:
aproximadamente 53 updates por segundo numa linha do tempo NTSC de 60 Hz. Não
há crash, freeze, opcode
inválido ou corrupção OAM; o runtime continua processando o estado mais novo.

Esse resultado é registrado como gap de performance. O teste exige pelo menos
100 updates em 120 quadros para impedir regressão material silenciosa.

## Comparação com a referência C/Assembly

| Área | Referência congelada | Vertical slice NES Pascal |
| --- | --- | --- |
| PRG ocupado | 8.403 B | 6.997 B |
| Pico OAM | 41/64 | 41/64 |
| Pool de inimigos | 12 Bats | 12 Bats |
| Pool de gemas | 8; excesso condensado | 8; excesso omitido |
| Movimento do jogador | 1 px/eixo/update | igual |
| Movimento do Bat | média Q4 de 0,375 px/eixo/update | 1 px a cada 3 updates, cerca de 0,333 |
| Ataque | 12 quadros a cada 60 | igual |
| Dano | cinco HP, cooldown 30, ruído APU | cinco HP, cooldown 30, flash vermelho 10 |
| Telas | PresentedBy + Title textual | Title por cor/emblema |
| Reinício | GameOver -> Title -> Playing | GameOver -> Playing |
| Stress cheio | 1.735/1.735 updates após baseline | 106/120 com 41 sprites |

Os tamanhos PRG não são um duelo de compiladores: a ROM C inclui fonte/textos,
suporte cc65, separação, condensação de drops e comportamento fora do recorte.
A referência não perfilou ciclos de gameplay separadamente; seu caminho NMI
normal é documentado em cerca de 590 ciclos.

A maior diferença está no renderer. A referência compartilha animação dos Bats
e usa um renderer especializado de dois sprites. O NES Pascal usa 22 instâncias
genéricas, cada uma com estado de animação/runtime. Essa generalidade explica
boa parte da perda no pior caso.

## Gaps expostos

| Classificação | Comportamento necessário / limitação atual | Workaround e custo | Usado? | Ação recomendada |
| --- | --- | --- | :---: | --- |
| **LANGUAGE GAP** | Coleções e parâmetros de callables não carregam handles opacos de metasprite. | Declarar 20 handles e selecioná-los por dois procedimentos de dispatch; adiciona fonte e branches gerados. | Sim | Avaliar arrays/parâmetros com propriedade estática em Additional Language Features. |
| **ERGONOMICS/BOILERPLATE GAP** | Não há locais, inicialização integral de record ou `inc`/`dec` de campo indexado. | Usar variáveis de trabalho compartilhadas e reset/update campo a campo; contribui para as 664 linhas. | Sim | Tratar somente em trabalho de linguagem separado. |
| **RUNTIME GAP** | Não há loader pequeno de texto por tela; a fila geral de background reserva 995 B e não cabe nos 918 B restantes. | Preservar a fonte na CHR, mas renderizar cores de estado e emblema; telas textuais são omitidas. | Sim | Medir um caminho de tela estática menor em trabalho futuro de footprint. |
| **RUNTIME GAP** | Não há rotação por scanline nem renderer bulk de entidades. | Manter propriedade estática e aceitar possível flicker acima de oito sprites por scanline. | Sim | Medir qualquer API bulk/rotação antes de adotá-la. |
| **ASSET GAP** | O projeto nativo do PNG2CHR Studio não é o schema versão 2 do compilador. | Manter quatro adapters congelados; custa transformação e sincronização manuais. | Sim | Resolver intercâmbio/versionamento canônico em 0.5.17. |
| **CODEGEN/PERFORMANCE GAP** | Estado genérico por metasprite e escalonamento repetido de arrays de records reduzem o update rate no pico. | Manter APIs genéricas e exigir o piso de 100/120 em torno do resultado medido de 106/120; sem alterar o otimizador. | Sim | Preservar o workload para medir backend estruturado e footprint. |
| **TEST/TOOLING GAP** | O benchmark não integra profiler de ciclos dinâmicos exatos. | Separar métricas estáticas de instruções/ciclos da vazão determinística no Mesen; ciclos exatos por frame ficam desconhecidos. | Sim | Adicionar profiling apenas em marco dedicado de tooling/benchmark. |

### Linguagem e ergonomia

- Arrays não aceitam handles opacos `sprite`/`metasprite`, e parâmetros de
  callable não aceitam esses tipos. O exemplo declara 20 handles de pool e os
  escolhe por dois procedimentos explícitos.
- Não há variáveis locais nem inicialização do record inteiro. Variáveis de
  trabalho globais e reset campo a campo aumentam o exemplo para 664 linhas.
- `inc`/`dec` não operam em campos de records indexados.

Suporte a coleções e parâmetros de handles foi registrado em Additional
Language Features.

### Runtime e performance

- A animação/renderização genérica por instância perde 14 de 120 updates no
  pico de 41 sprites; o renderer especializado da referência não perde updates
  em seu cenário longo.
- O estado de animação se repete 22 vezes, embora os Bats possam compartilhar
  frame/timer cosmético.
- Não há rotação por scanline, primitiva de pool ou renderer bulk. Uma nova API
  só deve existir depois de medição.

Os marcos futuros de backend estruturado, benchmarks de otimização e footprint
do runtime agora preservam explicitamente este workload. Nenhuma otimização foi
feita em 0.5.16.

### Assets e telas

- O `.p2c.json` nativo não é consumido diretamente; 0.5.17 cobre intercâmbio e
  adapters.
- A CHR congelada inclui a fonte gerada da referência, mas a fila geral atual
  de updates de background não cabe na RAM restante deste workload; por isso o
  recorte usa cores e um emblema em vez de texto.
- Separação dos Bats e condensação com pool de gemas cheio continuam políticas
  exclusivas da referência.

## Validação

O marco adiciona testes focados de assets, golden estrutural, benchmark,
toolchain e Mesen. A linha de base local final é de 591 testes automatizados,
incluindo os 34 testes Mesen headless dedicados, além do corpus completo de
benchmarks e do smoke build de ROM. O resultado do CI autoritativo é registrado
com a branch/commit do marco, não inferido da execução local.
