# `nes.run`

[English](../../runtime/run.md) | Português (Brasil)

`nes.run` conclui a inicialização e inicia a fase de runtime sincronizada por quadros:

```pascal
nes.run;
```

Ela deve:

- aparecer exatamente uma vez;
- permanecer fora de condicionais, laços e procedimentos.

O runtime aguarda o VBlank e habilita a NMI, a renderização de fundo, a renderização
de sprites e ambos os bits de renderização dos oito pixels mais à esquerda através de
shadows de PPUCTRL e PPUMASK pertencentes ao compilador. O estado normal habilitado de
PPUMASK, portanto, adiciona `$1E` enquanto preserva bits não relacionados do shadow.
O conteúdo nas posições X `$00..$07` fica visível por padrão; nenhuma configuração
pública de máscara é fornecida atualmente. Shadows de rolagem mantêm seus padrões
zerados `($00, $00)` a menos que [`nes.set_scroll`](scrolling-and-ppu-state.md) prepare
um novo par. O estado pertencente ao runtime e as escritas de inicialização na PPU
estão concluídos antes que a NMI seja habilitada.

Quando presente, [`nes.load_background()`](background-loading.md) realiza sua transferência
completa de 1 KiB para a PPU anteriormente na sequência de inicialização com a renderização
desabilitada. `nes.run` permanece como o ponto único que habilita a renderização após o
término de todas as transferências de inicialização.

Instruções após `nes.run` são executadas na thread principal. Um laço pode chamar
[`nes.wait_frame`](wait-frame.md) para avançar uma vez por NMI. Programas existentes que
terminam com `nes.run` continuam válidos: o compilador emite um laço estável implícito
de espera (idle) após o bloco principal quando nenhum callback de atualização estiver registrado.
Chamadas de paleta após `nes.run` preparam valores publicados atomicamente na RAM do
runtime; o transmissor da NMI os consome antes de qualquer callback de VBlank do usuário.

Quando [`nes.on_update`](frame-callbacks.md) registra um callback, o laço implícito
registra uma linha de base inicial persistente de quadros, aguarda até que o contador
volátil seja diferente, armazena o valor observado mais recente, chama o procedimento
de atualização uma vez com `JSR` direto e repete. Um quadro que chega durante uma
atualização lenta, portanto, permanece pendente e é processado imediatamente após o
retorno do callback. Backlogs são aglutinados para o quadro mais novo em vez de serem
reexecutados. Antes de cada callback aceito, o runtime principal atualiza ambas as portas
de controle uma vez. A lógica de atualização permanece no contexto principal normal. Um
callback de VBlank registrado separadamente é executado na NMI.
