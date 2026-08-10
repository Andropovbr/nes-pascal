# Metasprites

[English](../../runtime/metasprites.md) | Português (Brasil)

Um metasprite é um objeto lógico composto por uma lista arbitrária de sprites
de hardware 8 por 8 do NES. Um valor `metasprite` identifica a instância lógica;
não é um índice de OAM, e índices de componentes nunca são expostos ao código-fonte.
Metasprites e [valores `sprite`](sprites.md) gerenciados individualmente escrevem
no mesmo shadow de OAM e compartilham o mesmo limite físico de 64 sprites de hardware.

## Importação e criação

Metadados do PNG2CHR Studio são configurados no momento do build e importados pelo
seu `name` raiz:

```text
python -m nes_pascal.cli examples/metasprite_player.nsp -o build/metasprite_player.nes --chr assets/game.chr --metasprite assets/player_idle.json
```

```pascal
var
    Player: metasprite;

begin
    nes.import_metasprite(player);
    Player := nes.metasprite_create(player.idle_0);
end;
```

`--metasprite` é repetível. Caminhos relativos de JSON e CHR são resolvidos a partir
do diretório do código-fonte Pascal. `nes.import_metasprite` é uma instrução de nível
superior em tempo de compilação e deve preceder `nes.run`. Ela não abre um arquivo no NES.
Símbolos de quadros utilizam `<asset>.<animacao>_<quadro-base-zero>`, portanto os seis
quadros idle anexados são `player.idle_0` até `player.idle_5`.

Cada local sintaticamente distinto de `nes.metasprite_create(frame)` é uma instância
estática persistente. A criação se inicia oculta com o quadro selecionado e posição
zerada. Não há heap, destruição ou busca de nomes em tempo de execução.

## API pública

```pascal
nes.metasprite_set_position(Player, X, Y);
nes.metasprite_set_frame(Player, player.idle_2);
nes.metasprite_set_animation(Player, player.idle);
nes.metasprite_restart_animation(Player);
nes.metasprite_set_flip_horizontal(Player, true);
nes.metasprite_set_flip_vertical(Player, false);
nes.metasprite_hide(Player);
nes.metasprite_show(Player);
```

Posição recebe dois valores `byte`, setters de flip recebem `boolean`, e a seleção
de quadro requer um quadro simbólico do asset de criação da instância. Alterar um
quadro preserva posição, visibilidade e flips de todo o objeto. Se o novo quadro
possuir menos componentes, as entradas reservadas não utilizadas permanecem ocultas.
Alterar posição ou quadro enquanto oculto não exibe a instância. E3055 rejeita um
quadro de outro asset quando a identidade da instância é conhecida diretamente na
compilação. Como variáveis `metasprite` comuns são identidades opacas de um byte, o
runtime também verifica IDs de assets e ignora com segurança um emparelhamento
dinâmico incompatível em vez de ler além da capacidade reservada.

Seleção de animação, temporização automática, repetição (loop), conclusão em disparo
único (one-shot), reinício e a interação com seleção manual de quadros estão documentados
em [Animação de sprites](sprite-animation.md).

## Metadados suportados

O compilador aceita metadados do PNG2CHR Studio `png2chr-studio-animation` versão 2.
Ele valida a estrutura exigida de objetos/arrays, tamanho de tile de origem 8 por 8,
dimensões do quadro, origem dos metadados, contagem de componentes, coordenadas com
sinal, intervalo de tiles, byte de atributos, bits de paleta, booleanos de flip,
capacidade declarada de 256 tiles e declaração de 8 KiB de CHR NROM.

Cada quadro é armazenado como uma lista de componentes. Layouts podem ser retangulares,
esparsos, assimétricos ou utilizar deslocamentos negativos relativos à origem. Índices
de CHR repetidos e não contíguos permanecem inalterados. Apenas entradas no array `sprites`
de cada quadro consom OAM, de modo que tiles de origem omitidos/transparentes não a consomem.
A ordem dos componentes é preservada.

Existe uma única representação imutável de quadro. Seleção manual de quadro e
[animação de sprites](sprite-animation.md) referenciam os mesmos IDs de quadros e as
mesmas listas de componentes; o estado de animação nunca cria uma segunda geometria,
pivô, flip ou caminho de recorte.

O PNG2CHR Studio versão 2 define a `origin` raiz como a âncora lógica configurada nas
coordenadas de pixels do quadro de origem. Ele subtrai essa âncora durante a exportação,
de modo que cada valor `animations[].frames[].sprites[].x/y` já é um deslocamento com sinal
a partir da âncora. O NES Pascal consome esses deslocamentos diretamente; ele não subtrai
`origin` novamente.

Campos de ferramentas como coordenadas na imagem de origem, linha/coluna do tile de
origem, rótulos de reutilização e estatísticas de conversão permanecem apenas no
compilador. Durações de animação e política de repetição tornam-se tabelas PRG compactas
e imutáveis. Gráficos de tiles permanecem exclusivamente na CHR-ROM; não são copiados para PRG.

Os metadados atualmente declaram uma capacidade de tiles e contagem final de tiles,
mas não identificam de forma inequívoca a qual pattern table de 4 KiB do NES os índices
se destinam. O NES Pascal utiliza o banco NROM CHR configurado e valida o intervalo de
tiles de um byte para sprites, mas não pode provar que arquivos JSON e CHR com nomes
diferentes vieram da mesma exportação. Um contrato futuro do PNG2CHR Studio deve adicionar
uma identidade explícita de pattern table/banco e preferencialmente um hash do conteúdo
de CHR. Os metadados anexados indicam `player.chr` enquanto o arquivo compatível fornecido
é `game.chr`; o compilador, portanto, não trata o nome de arquivo de saída das ferramentas
como identidade.

## Origem do quadro, âncora lógica e posição

Coordenadas do quadro de origem utilizam o canto superior esquerdo da imagem como `(0, 0)`.
`width` e `height` do quadro descrevem essa extensão de origem e são retidos para
representação em tempo de compilação e futuros trabalhos com caixas delimitadoras
(bounding boxes). Eles não implicam uma grade retangular de componentes e não são
copiados para a RAM em runtime.

A `origin` nos metadados raiz seleciona um ponto nesse sistema de coordenadas de origem
tanto como âncora lógica quanto como pivô de flip de todo o metasprite. O PNG2CHR Studio
exporta uma célula de origem em `(source_x, source_y)` como:

```text
component.x = source_x - origin.x
component.y = source_y - origin.y
```

O NES Pascal armazena `component.x/y` inalterados como `dx/dy` com sinal.
`nes.metasprite_set_position(M, x, y)` posiciona a âncora na coordenada lógica da tela
`(x, y)`, de modo que X/Y lógicos sempre identificam o mesmo ponto do objeto independentemente
do quadro ou estado de flip. Uma origem `(0, 0)` deliberadamente utiliza o canto superior
esquerdo do quadro de origem como âncora. Uma origem dentro ou fora de um quadro pode
representar os pés de um personagem, o centro de uma nave, efeitos assimétricos ou objetos
em dobradiça (hinge).

A origem do quadro de origem, a âncora lógica e o pivô de flip são conceitos distintos,
mas a versão 2 necessita de apenas uma `origin` declarada: o `(0, 0)` do quadro de origem
é fixo, enquanto a `origin` configurada é tanto âncora quanto pivô. Um campo `pivot` separado
é desnecessário a menos que um formato de asset futuro necessite de flip em torno de um
ponto diferente da posição lógica.

### Compatibilidade com assets iniciais da versão 0.5.3

O PNG2CHR Studio já utilizava o contrato acima quando emitia o esquema na versão 2. O
importador inicial do NES Pascal 0.5.3 tratava incorretamente `sprites[].x/y` como coordenadas
de origem e subtraía `origin` uma segunda vez. Isso era invisível para assets `(0, 0)`, mas
incorreto para qualquer âncora diferente de zero. O importador agora segue o contrato existente
do produtor; não há alteração de esquema nem modo de compatibilidade para a subtração dupla incorreta.

Metadados `(0, 0)` existentes permanecem determinísticos e mantêm seu comportamento de
flip no canto superior esquerdo (estilo dobradiça). O NES Pascal nunca adivinha um centro a
partir de largura ou altura do quadro. Para centralizar um quadro 24 por 24, reexporte com
`origin: {"x": 12, "y": 12}`; os deslocamentos de componentes correspondentes tornam-se
`-12`, `-4` e `4`. Alterar apenas `origin` sem reexportar os deslocamentos de componentes
não satisfaz o contrato do formato. O fixture de jogador fornecido foi reancorado dessa forma.

## Inversão (flip) de todo o metasprite

O flip espelha cada componente 8 por 8 em torno da âncora lógica, não em torno de um
retângulo inferido de largura/altura. Para a coordenada lógica `L` e deslocamento com
sinal superior-esquerdo `d`, o posicionamento é:

```text
não invertido: component_top_left = L + d
invertido:     component_top_left = L - d - 8
```

De forma equivalente, o deslocamento invertido é `d' = -d - 8`. O 8 adicional compensa a
largura ou altura do componente. O flip horizontal aplica XOR no bit 6 de atributos da
OAM; o flip vertical aplica XOR no bit 7. O XOR preserva bits não relacionados de paleta
e prioridade e combina corretamente o flip do objeto inteiro com um componente já invertido pelo asset.

Um pivô centralizado preserva o intervalo delimitador visível correspondente enquanto
espelha o posicionamento assimétrico e a orientação dos tiles dentro dele. Um pivô
deliberadamente não centralizado mantém X/Y lógicos estáveis, mas pode deslocar o
intervalo delimitador visível, o que é o comportamento esperado de dobradiça. O runtime
não altera X/Y lógicos em nenhum dos casos.

## Posse de OAM e custo

O compilador determina a maior contagem de componentes entre todos os quadros no asset
de uma instância e reserva essa quantidade de entradas livres. Reservas explícitas
individuais são processadas primeiro, depois locais de `nes.sprite_create()`, e em seguida
locais de criação de metasprites na ordem do código-fonte. Entradas de metasprites podem
ser não contíguas e são registradas como proprietárias do tipo `metasprite_component`. A
instância resolvida mapeia privadamente posições de componentes para esses índices de OAM.

Se o total compartilhado exceder 64, E3050 interrompe a compilação. A alocação nunca sofre
wrap, sobrescreve outro proprietário, trunca um quadro ou retorna um sentinela inválido.
Esse máximo fixo permite que animações automáticas alternem entre quadros de tamanhos
diferentes sem alocação de OAM em tempo de execução.

Cada instância utiliza quatro bytes mutáveis de RAM comum: X lógico, Y lógico, ID do quadro
selecionado e flags de visibilidade/flip. O suporte a metasprites também inclui oito bytes
de rascunho compartilhados em RAM comum e dois ponteiros de dois bytes compartilhados na
Zero Page. Tabelas imutáveis em PRG contêm:

- ponteiros baixo/alto de quadros e um ID de asset por quadro;
- para cada quadro, uma contagem de componentes seguida por quatro bytes por componente:
  deslocamento X com sinal, deslocamento Y com sinal, tile, atributos;
- ponteiros baixo/alto de tabelas de slots e um ID de asset por instância;
- para cada instância, uma contagem de slots reservados seguida por seus índices internos de OAM.

Largura, altura e origem não ocupam bytes em tabelas de ROM porque os deslocamentos de
componentes exportados já codificam a geometria relativa à âncora.

Programas utilizando [animação de sprites](sprite-animation.md) adicionam quatro bytes
mutáveis por instância e tabelas compactas de sequência de animação na PRG-ROM. Programas
que utilizam apenas operações estáticas de quadros mantêm os custos acima e não incluem
o estado ou rotinas de animação.

## Visibilidade, recorte e Y do NES

Exibir renderiza cada componente ativo a partir do estado atual. Ocultar escreve `$FF`
no byte Y de cada slot detido. Renderizar um quadro menor oculta os slots restantes.

A adição de coordenadas possui sinal e é verificada antes de escrever na OAM. Um componente
é exibido apenas quando todo o tile 8 por 8 for representável: canto superior esquerdo X
`0..248` e topo lógico Y `1..232`. Qualquer elemento além do limite esquerdo, direito,
superior ou inferior é ocultado como um sprite de hardware inteiro; a aritmética nunca
causa wrap para a borda oposta. Caminhos de deslocamento positivo e negativo verificam
novamente os limites finais direito/inferior. Recorte em nível de pixel não está implementado.

O Y do metasprite é uma coordenada de topo lógico da tela. Para um componente visível, o
runtime escreve `OAM Y = topo lógico - 1` exatamente uma vez, correspondendo à convenção
de Y de sprites do NES. O topo lógico 0 seria codificado como `$FF`, que este runtime
reserva como sentinela oculto, de modo que esse componente é recortado.

Isso difere intencionalmente da API de baixo nível de sprites individuais: `nes.sprite_set_y`
aceita e armazena o byte Y bruto da OAM sem subtrair um, enquanto o posicionamento de
metasprites aceita uma âncora lógica de tela e realiza a conversão por componente. O
comportamento existente de Y e ocultar/exibir de sprites individuais permanece inalterado.

O trabalho de layout de metasprites é executado na inicialização, no código principal
ou em `nes.on_update`, nunca na NMI. A NMI continua transferindo o shadow completo alinhado
a página através de um único DMA de OAM.

## Limite de scanlines do hardware

A capacidade de 64 entradas de OAM não é o único limite de sprites. A PPU do NES renderiza
no máximo oito sprites de hardware em uma mesma scanline. Um metasprite largo, ou vários
objetos compartilhando scanlines, podem apresentar desaparecimento de sprites (dropout)
mesmo quando a posse total de OAM for válida. O NES Pascal não ordena sprites, não rotaciona
a prioridade na OAM, não equilibra scanlines nem implementa mitigação de flicker. A animação
não altera esse limite do hardware.
