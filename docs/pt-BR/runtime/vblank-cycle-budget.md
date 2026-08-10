# Orçamento de ciclos de VBlank

[English](../../runtime/vblank-cycle-budget.md) | Português (Brasil)

O NES Pascal é voltado para o NES NTSC. Um VBlank tem aproximadamente 2.273 ciclos
de CPU. Essa é a janela do hardware, não uma promessa segura de que todos esses ciclos
estejam disponíveis: a NMI se inicia após a conclusão da instrução atual, o DMA de OAM
possui uma variação de paridade de um ciclo e desvios tomados podem adicionar um ciclo
de cruzamento de página. Programas devem manter uma margem em vez de consumir a estimativa
completamente.

A NMI gerada realiza o trabalho nesta ordem fixa:

1. entra na NMI, preserva A, X e Y e publica o estado do quadro;
2. envia a preparação do sprite zero legado quando presente e, em seguida, executa o
   DMA de OAM quando qualquer operação de sprite estiver incluída;
3. examina e transfere alterações enfileiradas de paleta quando chamadas de paleta
   em runtime existirem;
4. examina até quatro escritas enfileiradas de fundo quando chamadas de fundo em
   runtime existirem;
5. chama o callback opcional de VBlank do usuário;
6. envia um par de rolagem pendente completo quando `nes.set_scroll` estiver incluído;
7. redefine o latch da PPU e restaura PPUCTRL, scroll X/Y e PPUMASK;
8. restaura os registradores e retorna.

A transferência de 1 KiB de `nes.load_background()` não faz parte deste orçamento. Nem
o preenchimento correspondente com zeros gerado quando `nes.get_tile` é utilizado sem um
fundo configurado. Ambos são executados uma vez durante a inicialização no RESET enquanto
a renderização e a NMI estiverem desabilitadas.

## Custos atuais

As contagens a seguir utilizam temporizações de instruções padrão do Ricoh 2A03 e incluem
chamadas e retornos de sub-rotinas onde indicado. Elas descrevem o código gerado atual e
devem ser atualizadas quando esse código for alterado.

| Componente da NMI | Ciclos de CPU estimados |
| --- | ---: |
| Entrada de hardware, salvamento de registradores, contabilidade de quadros, restauração de registradores e `RTI` | 52 |
| Varredura de paleta sem cores marcadas (dirty) | 75 |
| Varredura de paleta com todos os oito tripletos e a cor universal marcados | 784 |
| Transmissor de fundo ignorado enquanto o cancelamento detém seu bloqueio | 19 |
| Varredura de fila de fundo sem slots publicados e sem suporte a cancelamento | 67 |
| Varredura de fila de fundo com quatro slots apenas de escrita e sem suporte a cancelamento | 203 |
| Varredura de fila de fundo com quatro tiles confirmados e sem suporte a cancelamento | 335 |
| Verificação adicional de bloqueio quando o suporte a cancelamento está incluído | 6 |
| DMA de OAM para sprites gerais, incluindo redefinição de `$2003` | 525-526 |
| Envio do sprite zero legado mais DMA de OAM | 569-570 |
| Despacho de callback de VBlank do usuário vazio (`JSR` mais `RTS`) | 12 |
| Restauração final do estado da PPU | 36 |
| Envio de rolagem incluída sem par pendente | 7 |
| Envio de rolagem incluída com um par pendente | 28 |

O máximo de paleta escreve 25 bytes de paleta: três cores independentemente visíveis
para cada uma das oito paletas mais a cor de fundo universal. Seu trabalho é limitado
porque o runtime examina nove flags fixas e não possui fila dinâmica.

Piores casos representativos, incluindo um callback de VBlank registrado e vazio, são:

| Trabalho habilitado | Estimativa usada | Restante aproximado de 2.273 |
| --- | ---: | ---: |
| Varredura de paleta limpa | 175 | 2.098 |
| Todas as cores de paleta marcadas | 884 | 1.389 |
| DMA de OAM geral e todas as cores de paleta marcadas | 1.410 | 863 |
| Quatro escritas de fundo com atualizações de shadow confirmadas | 435 | 1.838 |
| Todas as cores de paleta marcadas e quatro escritas de tiles confirmadas | 1.219 | 1.054 |
| DMA de OAM geral, todas as cores de paleta marcadas e quatro escritas de tiles confirmadas | 1.745 | 528 |

O restante deve cobrir o corpo do callback, quaisquer procedimentos que ele chame,
oscilações de temporização (jitter) e uma margem de segurança. Um programa sem callback
registrado omite o despacho de 12 ciclos. Incluir cancelamento adiciona seis ciclos a
cada linha contendo trabalho de fundo; a linha final torna-se então 1.751 usados e 522
restantes. Incluir `nes.set_scroll` adiciona sete ciclos quando nenhum par estiver
pendente ou 28 ciclos quando a NMI enviar um, reduzindo o restante correspondente nessa
quantidade. Metasprites utilizam a mesma linha de DMA de OAM geral: o layout de componentes
é calculado antes da NMI no contexto principal/atualização, portanto a contagem de componentes
não adiciona trabalho no VBlank. Programas usando o helper legado de compatibilidade
`nes.set_sprite_zero` adicionam até 44 ciclos para o envio atômico de seu registro,
reproduzindo o antigo pior caso combinado de 1.789 ciclos antes do trabalho de cancelamento
ou rolagem.

## Limites de escalabilidade

O compilador verifica se os callbacks de VBlank utilizam o subconjunto suportado e seguro
para interrupções, mas não calcula limites de laço, ciclos no grafo de chamadas nem rejeita
um callback que estoure o orçamento. Um callback estruturalmente válido ainda pode ultrapassar
o tempo do VBlank. O caminho atual de paleta totalmente marcada, quatro escritas confirmadas
de tiles e DMA de OAM geral consom cerca de 77 por cento da janela nominal antes do trabalho
útil do callback. A contribuição de fundo é limitada a quatro escritas de um byte na PPU
por quadro; requisições adicionais são rejeitadas e definem uma flag de estouro persistente.
Programas apenas para escrita omitem o trabalho de confirmação no shadow e utilizam um
máximo de 203 ciclos no transmissor, ou 209 ciclos quando o suporte a cancelamento estiver incluído.

Apenas programas contendo `nes.clear_background_updates()` incluem o bloqueio de cancelamento
de um byte e sua verificação no transmissor. Isso adiciona seis ciclos às suas varreduras
normais de fila. Quando o bloqueio é retido, a chamada retorna em 19 ciclos sem tocar no
estado da PPU ou em qualquer slot da fila. Se a NMI passou pela verificação antes que o
cancelamento adquirisse o bloqueio, a NMI conclui sua varredura limitada antes que o código
principal possa continuar; essa é a fronteira atômica de tudo-ou-nada documentada para
`nes.clear_background_updates()`. Programas que utilizam apenas inspeção ou limpeza de
estouro omitem o transmissor de fundo inteiramente.

Esse projeto é escalável apenas enquanto tarefas fixas adicionais na NMI permanecerem
explicitamente limitadas e seu pior caso combinado deixar margem. Streaming de nametables,
trabalho de animação automática na NMI, DMA de áudio ou outras transferências para a PPU
exigiriam uma revisão do orçamento central e da política de agendamento; nada disso está
implementado aqui. Os valores são exclusivos para NTSC e não reivindicam suporte à temporização PAL.

Um epílogo compartilhado restaura PPUCTRL, scroll X/Y e PPUMASK após cada transmissor de
runtime e o callback opcional do usuário. `nes.run` preserva bits enquanto habilita o padrão
atual de `$80` para PPUCTRL e `$1E` para PPUMASK; a rolagem se inicia em `($00, $00)`. Esse
custo central substitui os custos anteriores de restaurações locais duplicadas nos transmissores.
