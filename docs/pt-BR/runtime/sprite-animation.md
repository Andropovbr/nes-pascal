# Animação de sprites

[English](../../runtime/sprite-animation.md) | Português (Brasil)

A animação de sprites seleciona quadros ordenados de metasprites automaticamente
na thread principal. Ela reutiliza a reserva estática de OAM, posição, visibilidade,
recorte e estado de flip de todo o objeto do metasprite; a animação nunca aloca
ou libera sprites de hardware em tempo de execução.

A organização em camadas é deliberadamente unidirecional:

```text
asset JSON
    -> quadros de metasprite imutáveis, validados e relativos à origem
    -> animações armazenam apenas IDs de quadros ordenados e durações
    -> estado mutável de reprodução seleciona um ID de quadro
    -> o renderizador de metasprite existente expande aquele quadro para a OAM
```

Animações não possuem, copiam, normalizam ou reinterpretam geometria de componentes,
origem, pivô, limites, posicionamento de flip ou recorte. Um quadro selecionado manualmente
e o mesmo quadro selecionado através de uma animação são o mesmo registro de quadro
imutável e emitem bytes idênticos de componentes.

## Símbolos do asset e metadados

Cada animação importada do PNG2CHR Studio expõe um símbolo em tempo de compilação
chamado `<asset>.<animacao>`. Quadros individuais mantêm seus nomes existentes
`<asset>.<animacao>_<indice>`:

```pascal
nes.import_metasprite(player);
Player := nes.metasprite_create(player.movement_right_0);
nes.metasprite_set_animation(Player, player.movement_right);
```

O objeto de animação versão 2 suportado aceita:

- `default_frame_duration`: duração opcional de 1 a 255 quadros lógicos do jogo;
  metadados de compatibilidade que a omitem utilizam 1;
- `frames[].duration`: sobrescrita opcional por quadro de 1 a 255;
- `loop`: política booleana opcional de reprodução, com padrão `true`.

O NES Pascal não infere o comportamento de disparo único (one-shot) a partir do nome,
tipo ou direção da animação. Defina `"loop": false` explicitamente para uma sequência
one-shot. Sequências vazias, durações zero, campos de animação não suportados, nomes
duplicados, valores não booleanos de loop e mais de 255 quadros em uma única animação
produzem E6016. O programa configurado combinado pode expor no máximo 256 símbolos de
quadros e 256 símbolos de animação.

O objeto `source` raiz é proveniência de ferramentas. O NES Pascal não abre nem
requer seu caminho PNG; a compilação utiliza os metadados de animação/quadro e o banco
de CHR configurado separadamente. O manifesto consolidado do jogador fornecido foi
explicitamente reancorado em `(12,12)`, com deslocamentos de componentes já relativos
àquele pivô centralizado. A saída anexada do exportador utilizava `(0,0)` mais
coordenadas brutas `0/8/16`, o que descreve intencionalmente um pivô de canto sob o
contrato da versão 2 e produziria um flip em estilo dobradiça. O compilador não tenta
adivinhar silenciosamente um pivô centralizado porque pivôs não centralizados são válidos.

Este jogador expõe `player.idle` e `player.movement_right`. Sua sequência espelhada
gerada `movement_left` é omitida porque não contém arte única; o flip horizontal de
todo o metasprite seleciona a orientação. Os jogos continuam livres para importar animações
distintas para esquerda/direita quando os artistas fornecerem quadros distintos.

## API pública

```pascal
nes.metasprite_set_animation(Player, player.movement_right);
nes.metasprite_restart_animation(Player);
Finished := nes.metasprite_animation_finished(Player);
```

`nes.metasprite_set_animation` inicia uma animação compatível diferente em seu
primeiro quadro com a duração completa do primeiro quadro. Atribuir a animação já
ativa é uma operação nula (no-op) e não reinicia seu temporizador. Isso torna seguro
para um procedimento de atualização selecionar a animação desejada a cada quadro.

`nes.metasprite_restart_animation` reinicia a animação ativa selecionada no quadro zero.
Ela não faz nada antes que uma animação tenha sido selecionada.

`nes.metasprite_animation_finished` retorna `true` apenas após uma animação one-shot
ter consumido a duração completa de seu quadro final. O quadro final permanece selecionado.
Ela retorna `false` para animações em loop ativas, instâncias inativas e animações
one-shot reiniciadas.

Símbolos de animação são valores exclusivos do compilador. Eles não podem ser armazenados
em variáveis, declarados como tipos públicos, convertidos de bytes ou computados em
tempo de execução. E3056 rejeita uma animação não simbólica ou um emparelhamento de outro
asset conhecido estaticamente. Quando uma variável `metasprite` opaca impede essa prova,
o runtime verifica o ID do asset e ignora com segurança um emparelhamento incompatível.

## Regras de temporização e interação

O runtime avança cada animação ativa uma vez para cada quadro lógico do jogo aceito
pelo laço principal sincronizado por quadros. Uma duração `D`, portanto, mantém seu
quadro selecionado por exatamente `D` quadros lógicos do jogo. O avanço é executado após
a leitura dos controles e antes do procedimento registrado `nes.on_update`, nunca na NMI.
Se uma atualização lenta cruzar múltiplas NMIs, a política existente de aglutinação
para o quadro mais novo se aplica; a animação não reexecuta um backlog.

Alterar quadros reexecuta automaticamente o renderizador de metasprites existente. Quadros
podem ter contagens e layouts de componentes diferentes. Quaisquer slots reservados de OAM
não mais utilizados são ocultados, enquanto posição, visibilidade e flips horizontal/vertical
de todo o objeto permanecem inalterados.

Ocultar um metasprite afeta apenas a publicação na OAM: seu temporizador de animação continua
avançando. Exibi-lo posteriormente renderiza o quadro então atual. A seleção manual com
`nes.metasprite_set_frame` desabilita deliberadamente a reprodução automática; chame
`nes.metasprite_set_animation` para iniciá-la novamente.

## Custo de ROM e RAM

Metadados de animação são dados imutáveis na PRG-ROM. Cada animação incluída adiciona
cinco bytes de tabela (ponteiro de sequência baixo/alto, contagem de quadros, flag de loop
e ID do asset) mais dois bytes por quadro de animação (ID do quadro e duração). A geometria
existente dos componentes do quadro é referenciada por ID e não é duplicada. Rotinas de
runtime de animação são incluídas apenas quando uma operação de animação ou consulta de
conclusão for utilizada.

Metasprites estáticos mantêm o custo de RAM do milestone 0.5.3 de quatro bytes comuns
por instância mais oito bytes compartilhados de rascunho do renderizador. Um programa
utilizando animação adiciona quatro bytes comuns por instância: animação selecionada,
índice do quadro de animação, temporizador e flags de reprodução. Seu custo total em RAM
comum para metasprites é, portanto, de `8N + 8` bytes. Os dois ponteiros compartilhados de
dois bytes do renderizador na Zero Page e a reserva de OAM não aumentam.

## Exemplo

Compile o jogador animado fornecido com:

```text
python -m nes_pascal.cli examples/sprite_animation.nsp -o build/sprite_animation.nes --chr assets/game.chr --metasprite assets/player_consolidated.json
```

O D-pad movimenta em todas as oito direções. Atualizações parado selecionam `player.idle`;
atualizações em movimento selecionam `player.movement_right`. O flip horizontal é o estado
independente de orientação, de modo que parar ou mover-se verticalmente preserva a última
orientação esquerda/direita. Repetir qualquer uma das seleções de animação a cada atualização
não a reinicia. O botão A reinicia a reprodução explicitamente, e Select oculta ou exibe
o jogador sem pausar sua animação.
