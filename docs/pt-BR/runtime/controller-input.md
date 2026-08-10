# Entrada de controle

[English](../../runtime/controller-input.md) | Português (Brasil)

O NES Pascal lê os controles padrão conectados às portas 1 e 2. A entrada é amostrada
pelo runtime principal fora da NMI exatamente uma vez para cada quadro processado. O
contador de quadros permanece como a fonte autoritativa de sincronização.

## Constantes de botões

As oito constantes embutidas de `byte` utilizam o mesmo layout estável que os bytes
de estado do runtime:

| Constante | Máscara | Posição serial |
| --- | --- | --- |
| `nes.button_a` | `$01` | 1 |
| `nes.button_b` | `$02` | 2 |
| `nes.button_select` | `$04` | 3 |
| `nes.button_start` | `$08` | 4 |
| `nes.button_up` | `$10` | 5 |
| `nes.button_down` | `$20` | 6 |
| `nes.button_left` | `$40` | 7 |
| `nes.button_right` | `$80` | 8 |

Direções simultâneas e opostas são armazenadas exatamente como o controle as relata.
O runtime não filtra combinações.

## Consultas

Cada consulta retorna um valor `boolean` canônico. O argumento de controle deve ser o
valor hexadecimal direto `$01` ou `$02`, ou uma constante `byte` declarada em tempo
de compilação com um desses valores. Índices dinâmicos de controle não são suportados.

```pascal
if nes.controller_down($01, nes.button_right) then
    inc(PlayerX);

if nes.controller_pressed($01, nes.button_start) then
    PlayerX := $78;

if nes.controller_released($01, nes.button_b) then
    PlayerTile := $01;
```

O segundo argumento deve ser exatamente uma constante embutida de botão. Máscaras
arbitrárias e expressões de botões são intencionalmente rejeitadas.

- `nes.controller_down` é verdadeiro enquanto o estado atual contiver o botão.
- `nes.controller_pressed` é verdadeiro quando o bit estiver definido no estado atual
  e limpo no estado anterior.
- `nes.controller_released` é verdadeiro quando o bit estiver limpo no estado atual
  e definido no estado anterior.

Os estados atual e anterior são estáveis por todo o quadro processado, de modo que
consultas repetidas retornam resultados consistentes. `pressed` e `released` descrevem
transições entre quadros processados, não eventos brutos de NMI. Atualizações lentas
aglutinam quadros perdidos e comparam a consulta mais recente com a última consulta
processada em vez de reexecutar um backlog de entrada.

## Ordem no runtime

Para um callback de atualização registrado, a ordem no runtime principal é:

```text
aguarda até que runtime_frame_counter seja diferente de runtime_last_processed_frame
aceita o quadro pendente mais recente
copia os estados atuais dos controles para os estados anteriores
trava e lê as portas $4016 e $4017
chama o callback de atualização
```

`nes.wait_frame` chama a mesma abstração idempotente de atualização de controles após
observar um novo quadro. `runtime_controller_polled_frame` impede que as portas sejam
amostradas duas vezes se dois caminhos de runtime se referirem ao mesmo quadro processado.
Um byte separado `runtime_controller_poll_valid` garante que a RAM limpa não seja confundida
com um quadro já processado quando o primeiro valor de contador aceito for `$00`. A
leitura de controles nunca é chamada a partir da NMI ou de um callback de VBlank.

## Protocolo de hardware e limitação

O leitor interno escreve `$01` e depois `$00` em `$4016`, em seguida lê oito bits seriais
de `$4016` e `$4017` em paralelo. A rotina é isolada para que um futuro milestone de
áudio possa substituí-la sem alterar a API do Pascal.

Este primeiro leitor não é seguro para DMC. A reprodução de amostras DMC pode excluir
ciclos de leitura de controle no hardware do NES, portanto uma leitura repetida ou outro
algoritmo seguro para DMC deve substituí-lo antes que o áudio DMC seja habilitado.

## Sprite do exemplo de controle

[`examples/controller_input.nsp`](../../../examples/controller_input.nsp) utiliza um helper
fixo `nes.set_sprite_zero(x, y, tile, attributes)` exclusivamente para tornar o milestone de
controles visível. O helper invalida um registro de preparação de cinco bytes, escreve todos
os quatro campos do sprite e o publica. A NMI envia apenas um registro completo para
`runtime_oam_shadow` antes do DMA de OAM.

Este helper suporta apenas o sprite de hardware 0. Não é uma API de alocação, gerenciamento,
animação, colisão ou metasprites. Seus dois tiles de 8x8 do jogador são embutidos na CHR-ROM
apenas quando o helper é utilizado. Novos programas devem utilizar as
[primitivas gerais de sprites de hardware](sprites.md); o helper fixo permanece para
compatibilidade com esse exemplo focado de controles.
