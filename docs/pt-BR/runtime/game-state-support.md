# Suporte a estados de jogo

[English](../../runtime/game-state-support.md) | Português (Brasil)

Estados de jogo em NES Pascal são fluxo de controle comum, explícito e no nível
da linguagem. O padrão recomendado combina uma enumeração nominal, uma variável
global de estado, procedimentos de entrada, procedimentos de atualização por
quadro e um dispatcher registrado com `nes.on_update`. Não há palavra-chave de
estado, registro oculto, tabela de callbacks, gerenciador de cenas ou runtime de
máquina de estados.

A referência completa é
[`examples/game_state.nsp`](../../../examples/game_state.nsp). Compile-a com:

```text
python -m nes_pascal.cli examples/game_state.nsp -o build/game_state.nes --chr assets/chr_asset.chr
```

## Represente estados com uma enumeração

```pascal
type
    GameState = (Title, Playing, Paused, GameOver);

var
    State: GameState;
```

Enumerações tornam cada estado legível, fortemente tipado e verificado em tempo
de compilação. Elas não exigem metadados em runtime, e `State` ocupa exatamente
um byte. Um `byte` com números mágicos perderia a tipagem nominal sem economizar
RAM.

Os membros usam a representação pela ordem de declaração: `Title = $00`,
`Playing = $01`, `Paused = $02` e `GameOver = $03`. Esses bytes são detalhes da
geração de código e dos testes; o fonte deve usar os nomes dos membros.

## Despache um estado por quadro

O procedimento de atualização registrado seleciona explicitamente um handler:

```pascal
procedure Update;
begin
    if State = Title then
    begin
        UpdateTitle;
    end
    else if State = Playing then
    begin
        UpdatePlaying;
    end
    else if State = Paused then
    begin
        UpdatePaused;
    end
    else if State = GameOver then
    begin
        UpdateGameOver;
    end;
end;
```

Somente o handler selecionado no início da chamada executa. Uma transição feita
por ele não executa também o novo handler no mesmo quadro. O dispatcher de
quatro estados baixa para comparações e branches diretos; o núcleo medido ocupa
58 bytes de PRG, 24 instruções e 79 ciclos-base estáticos quando cada instrução
emitida é contada uma vez. O custo dinâmico depende da comparação que tiver
sucesso. Nenhum dispatcher genérico esconde esse custo.

O Assembly representativo é direto:

```asm
lda variable_State
cmp #$01
beq @if_then
jmp @if_else
@if_then:
jsr procedure_UpdatePlaying
```

## Separe entrada de atualização

Use procedimentos `EnterX`, `StartX`, `PauseX` ou `ResumeX` para configuração
executada uma vez, e `UpdateX` para trabalho por quadro. A convenção da release
é:

1. executar todos os efeitos de configuração e reset;
2. atribuir `State` por último;
3. retornar ao dispatcher.

Por exemplo, `StartGame` chama `ResetGameplay`, incrementa o contador persistente
de sessões, configura o sprite e o fundo, e atribui `State := Playing` por
último. Esses helpers usam a mecânica comum `JSR`/`RTS`. Evite ciclos entre
helpers de transição; o diagnóstico normal de recursão continua valendo.

## Ciclo de vida da referência

O exemplo implementa quatro estados observáveis:

- **Title:** fundo `$21`, sprite do jogador oculto e sem atualização de gameplay.
  Um pressionamento de Start chama `StartGame`.
- **Playing:** o direcional move o jogador, enquanto `Score` e `GameplayTicks`
  avançam. A Function booleana `ShouldEndGame()` entra em `GameOver` quando
  `Health` chega a zero; B é o gatilho determinístico de dano do exemplo. Start
  chama `PauseGame` antes do trabalho normal de gameplay.
- **Paused:** laço de quadros, NMI, renderização e leitura de controles continuam,
  mas o handler não altera variáveis do jogador ou do gameplay. Um novo
  pressionamento de Start chama `ResumeGame`.
- **GameOver:** o jogador fica oculto e o gameplay normal permanece parado.
  Start chama `StartGame` para uma nova partida.

Use `nes.controller_pressed` nas transições com Start. Ele é verdadeiro somente
na borda de solto para pressionado; manter um botão pressionado não pode iniciar
e pausar imediatamente, nem pausar e retomar imediatamente. `controller_down`
continua apropriado para movimento contínuo.

## Reinício explícito do gameplay

`ResetGameplay` restaura somente dados mutáveis pertencentes ao jogo:

| Variável | Valor após reinício |
| --- | ---: |
| `PlayerX` | `$78` |
| `PlayerY` | `$70` |
| `Health` | `$03` |
| `Score` | `$00` |
| `GameplayTicks` | `$00` |
| `InitialRandom` | `$15`, após seed explícita `$2A` |

O exemplo reinicializa o PRNG explicitamente em `ResetGameplay`, tornando cada
partida determinística. Um jogo real pode omitir `nes.seed_random` e continuar
o stream atual; reiniciar gameplay nunca reinicializa o PRNG implicitamente.

`SessionStarts` persiste de propósito entre reinícios. Ela é inicializada uma
vez no boot e incrementada a cada partida, mas não pertence a `ResetGameplay`.
Jogos reais normalmente preservam recordes, opções, som e contadores de sessão,
enquanto reiniciam jogador, inimigos, pontuação, timers, spawns, animações e
flags de gameplay.

Reiniciar não salta para o vetor RESET, não reinicia a ROM, não captura ou
restaura snapshots de RAM e não reinicializa hardware do NES, infraestrutura
de PPU/controles, alocação do runtime do compilador ou dados persistentes do
jogo. O compilador não sabe quais variáveis pertencem ao gameplay; código de
usuário explícito mantém semântica e custo previsíveis.

A inicialização também permanece visível no fonte:

```pascal
begin
    SessionStarts := $00;
    ResetGameplay;
    EnterTitle;
    nes.set_background_color($21);
    nes.on_update(Update);
    nes.run;
end.
```

## Custo e validação

O benchmark `game_state` mede o exemplo completo, incluindo controles, fila de
paleta, um sprite de hardware e RNG com seed explícita:

| Métrica | Valor medido |
| --- | ---: |
| Código PRG | 1.268 B |
| PRG ocupado | 1.274 B |
| Instruções | 567 |
| Ciclos-base estáticos estimados | 1.876 |
| Profundidade da árvore de expressão | 1 |
| Máximo de temporários vivos | 0 |
| Profundidade máxima de chamadas do fonte | 4 |
| Pico da pilha de chamadas do fonte | 8 B |
| Variáveis de usuário | 8 B: 4 ZP + 4 RAM regular |
| Armazenamento do resultado de Function | 1 B em RAM regular |

Somente um desses oito bytes de usuário é o estado enum. As alocações de
runtime pertencem aos recursos existentes de controles, paleta, sprites e RNG;
RAM oculta de gerenciador de estados permanece em **0 B**. Programas que não
usam o exemplo não recebem código ou dados adicionais.

Testes focados congelam comparações diretas de enum, chamadas comuns dos
helpers, atribuição do estado depois da configuração e ausência de dispatcher
genérico. O teste Mesen determinístico executa `Title -> Playing -> Paused ->
Playing -> GameOver -> Playing`, injeta bordas distintas de pressionar/soltar,
prova que gameplay fica congelado enquanto quadros continuam, verifica os
valores exatos do reset e confirma `SessionStarts = 2` após o reinício como
evidência de que a ROM não foi reiniciada.

Em jogos maiores, mantenha handlers pequenos e extraia subsistemas em
procedimentos comuns. O dispatcher encadeado é deliberadamente o padrão inicial
oficial; esta release não adiciona jump table, pilha de estados, ciclo de vida de
cenas, event bus ou registro dinâmico de estados.
