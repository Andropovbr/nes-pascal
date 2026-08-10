# Callbacks de quadro

[English](../../runtime/frame-callbacks.md) | Português (Brasil)

O NES Pascal suporta um callback estático para a lógica normal de atualização a cada
quadro e um callback estático para trabalho restrito no VBlank:

```pascal
procedure Update;
begin
    inc(UpdateFrames);
end;

procedure VBlank;
begin
    inc(VBlankFrames);
end;

begin
    UpdateFrames := $00;
    VBlankFrames := $00;
    nes.set_background_color($21);
    nes.on_update(Update);
    nes.on_vblank(VBlank);
    nes.run;
end.
```

Ambos os registros devem ser instruções incondicionais de inicialização de nível superior
antes de `nes.run`. O argumento é um identificador direto de procedimento resolvido em
tempo de compilação, e o procedimento não deve ter parâmetros nem valor de retorno. No
máximo um callback de cada tipo é suportado. Um procedimento não pode servir a ambos os
callbacks. O registro não emite ponteiro de função, tabela de callbacks ou estado de
registro em runtime.

## Callback de atualização

O laço implícito de runtime do compilador aguarda a alteração do contador volátil de
quadros de 8 bits, chama o procedimento de atualização uma vez com `JSR` direto e, em
seguida, repete. O contador pode sofrer wrap de `$FF` para `$00`; a detecção de alteração
baseada em igualdade permanece válida. A atualização é executada no contexto principal
normal, nunca na NMI, e pode utilizar operações comuns suportadas da linguagem e
procedimentos acíclicos.

O laço estabelece `runtime_last_processed_frame` uma vez ao iniciar. Para cada iteração,
ele compara o contador autoritativo atual de quadros com esse byte persistente. Quando
diferem, ele armazena o valor mais recente do contador antes de chamar `Update`. Ele não
toma uma nova linha de base após o retorno do callback.

Isso define a política para quadros lentos:

- apenas um callback de atualização é executado por vez; chamadas nunca são concorrentes,
  aninhadas ou feitas a partir da NMI;
- uma NMI que ocorra durante `Update` permanece visível porque altera `runtime_frame_counter`
  sem alterar `runtime_last_processed_frame`;
- após o retorno de `Update`, o laço aceita imediatamente o quadro pendente mais novo em vez
  de aguardar outra NMI;
- múltiplos quadros perdidos por um callback lento são aglutinados em uma única atualização
  pendente mais recente, em vez de serem reexecutados como um grande backlog;
- o laço aguarda apenas quando os contadores atual e do último processado coincidem.

Como a sincronização utiliza um contador de 8 bits, um callback que permaneça ativo por
256 ou mais NMIs pode fazer com que o contador se iguale novamente ao valor armazenado.
Tal callback excede a janela observável de sincronização; a análise do orçamento de ciclos
está intencionalmente fora deste milestone.

Programas sem callback de atualização mantêm o laço implícito estável de espera (idle)
existente. Instruções explícitas da thread principal após `nes.run` ainda são executadas
antes do laço implícito de atualização ou de espera.

## Callback de VBlank

A NMI sempre preserva A, X e Y primeiro. Em seguida, ela incrementa `runtime_frame_counter`,
define `runtime_frame_ready`, executa o trabalho obrigatório de sprites quando habilitado,
transfere alterações enfileiradas de paleta e fundo e chama o procedimento de VBlank com
`JSR` direto. O callback e quaisquer helpers seguros terminam com `RTS`; a NMI envia um
par de rolagem pendente, executa a restauração final de estado da PPU, restaura registradores
e termina com `RTI`. Chamadas de paleta feitas pelo callback de VBlank são publicadas para
a NMI seguinte porque a transferência deste quadro já foi concluída. Essa ordenação é fixa
e determinística.

`runtime_frame_ready` é um indicador informativo de melhor esforço. A NMI o define e uma
espera de quadro na thread principal ou uma atualização aceita o limpa. Uma condição de
corrida pode tornar o indicador obsoleto, de modo que nem `nes.wait_frame` nem o laço de
callbacks o utilizam para decidir se um quadro está pendente. `runtime_frame_counter`
permanece autoritativo.

Uma vez aceito um quadro pendente, o runtime copia o estado atual dos controles para o estado
anterior e lê as portas 1 e 2 exatamente uma vez antes de chamar `Update`. A abstração de
consulta protegida é compartilhada com `nes.wait_frame`; consulte [Entrada de controle](controller-input.md).

O código de VBlank é intencionalmente conservador. O compilador valida transitivamente cada
procedimento alcançável. O subconjunto suportado é:

- atribuições escalares cujas expressões não necessitam de temporários compartilhados do compilador;
- `inc(Target)` e `dec(Target)` sem quantidade;
- instruções `if` com condições livres de temporários e ramos seguros;
- chamadas a procedimentos sem parâmetros cujos grafos de chamada completos satisfaçam as mesmas regras;
- chamadas de paleta com valores livres de temporários; estas preparam a transferência limitada de runtime do quadro seguinte;
- `nes.set_scroll` com valores de bytes livres de temporários; o par é enviado pela restauração final de estado na mesma NMI.

Expressões aritméticas e de comparação, quantidades em updates, todos os laços,
`nes.wait_frame`, `nes.run`, comandos de registro, chamadas parametrizadas, recursão e
chamadas para o callback de atualização são rejeitados. Entradas de VBlank devem ser
atribuídas antes que `nes.run` habilite a NMI. O compilador valida a segurança estrutural,
mas não rejeita callbacks por contagem estimada de ciclos. O transmissor fixo de paleta é um
trabalho limitado pertencente ao runtime; o código do usuário deve caber dentro do
[Orçamento de ciclos de VBlank](vblank-cycle-budget.md) restante. Não há fila genérica de
eventos ou comandos da PPU.

`nes.wait_frame` também é rejeitado dentro de um callback de atualização porque comandos
de runtime não podem aparecer em procedimentos. Registrar um procedimento para atualização
e VBlank simultaneamente é rejeitado com E3025: os dois contextos de execução possuem
regras de segurança distintas e compartilhar um ponto de entrada seria ambíguo.
