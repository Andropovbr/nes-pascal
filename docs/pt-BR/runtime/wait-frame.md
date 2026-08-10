# `nes.wait_frame`

[English](../../runtime/wait-frame.md) | Português (Brasil)

`nes.wait_frame` bloqueia a thread principal até que o contador de quadros da NMI
pertencente ao runtime seja alterado:

```pascal
nes.run;
while Running do
begin
    nes.wait_frame;
    inc(Frames);
end;
```

O comando deve ser executado após a chamada incondicional de nível superior `nes.run`.
Ele pode aparecer em laços e condicionais do bloco principal. Ele não pode aparecer
dentro de um procedimento neste milestone; fazer isso produz E3015. Executá-lo antes
de `nes.run` aguardaria para sempre porque a NMI ainda estaria desabilitada, de modo que
o compilador reporta E3017.

## Contrato de sincronização

O tratador de NMI incrementa `runtime_frame_counter`, um contador volátil de 8 bits,
uma vez por NMI. `nes.wait_frame` faz a amostragem desse byte e aguarda até que seu
valor mude. O contador sofre wrap módulo 256 e permanece como o sinal autoritativo;
o byte separado `runtime_frame_ready` é apenas um indicador informativo de melhor esforço.
A NMI define o indicador e uma espera concluída na thread principal o limpa, mas condições
de corrida são permitidas porque nenhuma decisão de sincronização o lê.

A NMI preserva A, X, Y, o status do processador através do protocolo de interrupção e
o equilíbrio da pilha. Ela pode chamar o único callback de VBlank estaticamente registrado
e validado após a contabilidade de quadros. Ela não executa lógica de atualização nem
processa uma fila genérica de comandos da PPU.

Após observar o novo valor do contador, `nes.wait_frame` atualiza ambas as portas de
controle através da mesma rotina de consulta protegida utilizada pelo laço de callbacks.
Isso disponibiliza o estado atualizado de [`controller_down`, `controller_pressed` e
`controller_released`](controller-input.md) para laços principais explícitos sem consultar
um quadro processado duas vezes. O comando em si não realiza escritas na PPU. Operações de
PPU em runtime sensíveis à renderização devem ser executadas no VBlank.
