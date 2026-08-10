# Runtime do NES

[English](../../runtime/index.md) | Português (Brasil)

O runtime implementado fornece uma pequena sequência de inicialização e um
tratador de NMI pertencente ao runtime para um programa NROM NTSC. Suas APIs
de quadros e controles são:

- [`nes.set_background_color`](set-background-color.md) define a cor de fundo
  universal da paleta do NES;
- [APIs de paleta](palettes.md) configuram quatro paletas de fundo e quatro
  paletas de sprites e enfileiram alterações de runtime para o VBlank;
- [`nes.load_background`](background-loading.md) transfere uma nametable bruta
  configurada e sua tabela de atributos durante a inicialização;
- [APIs de atualização de fundo](background-updates.md) mantêm opcionalmente um
  shadow de tiles confirmados e enfileiram no máximo quatro escritas de tiles
  ou atributos para cada VBlank;
- [`nes.run`](run.md) conclui a inicialização, habilita a NMI e a renderização no
  VBlank, e inicia a fase de runtime sincronizada por quadros;
- [`nes.set_scroll`](scrolling-and-ppu-state.md) prepara atomicamente um par fixo
  de rolagem horizontal e vertical para a restauração final da NMI;
- [`nes.wait_frame`](wait-frame.md) aguarda a alteração do contador volátil de
  quadros da NMI;
- [`nes.on_update`](frame-callbacks.md) registra estaticamente um procedimento sem
  parâmetros para o laço de quadros da thread principal;
- [`nes.on_vblank`](frame-callbacks.md) registra estaticamente um procedimento restrito
  e sem parâmetros para trabalho no VBlank da NMI;
- [`nes.controller_down`, `nes.controller_pressed` e `nes.controller_released`](controller-input.md)
  consultam o estado estável dos controles padrão 1 e 2;
- [Primitivas de sprites de hardware](sprites.md) mantêm 64 entradas de OAM em um
  shadow de CPU alinhado a página e as transferem via DMA de OAM na NMI;
- [Metasprites](metasprites.md) compilam metadados de quadros do PNG2CHR Studio em
  listas de componentes residentes em PRG com uma posição lógica e posse compartilhada de OAM;
- [Animação de sprites](sprite-animation.md) avança sequências simbólicas de quadros
  de metasprites na thread principal sincronizada por quadros;
- `nes.set_sprite_zero` é o helper fixo de preparação de OAM, exclusivo para exemplos,
  descrito na documentação de controles; ele permanece como um helper de compatibilidade.

`nes.load_background()` e comandos diretos de paleta de inicialização devem ficar antes
de `nes.run`; chamadas de paleta em procedimentos ou após `nes.run` são enfileiradas.
`nes.wait_frame` pode aparecer em laços e condicionais do bloco principal após `nes.run`,
mas não em procedimentos. O único código de usuário executado pela NMI é o callback
único de VBlank estaticamente validado, quando registrado.

Consulte [Orçamento de ciclos de VBlank](vblank-cycle-budget.md) para os custos atuais de
pior caso do runtime, margem disponível para callbacks e limites de escalabilidade.

Consulte [Plataforma-alvo](target-platform.md) para o formato da ROM gerada e comportamento
de inicialização do hardware. Consulte [Memória da CPU](cpu-memory.md) para o limite físico
de RAM, regiões reservadas, capacidade do usuário e o relatório gerado de mapa de memória.
