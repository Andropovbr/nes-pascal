# Infraestrutura de Builtins / Intrínsecos

[English](../../compiler/builtin-infrastructure.md) | Português (Brasil)

O milestone 0.5.6 fornece às chamadas comuns `nes.*` um pipeline unificado em tempo de compilação:

```text
source call
  -> BuiltinCall(public name, arguments, source position)
  -> registry lookup and signature validation
  -> optional semantic hook
  -> ResolvedBuiltinCall(BuiltinId, resolved arguments)
  -> descriptor runtime dependencies
  -> BackendEmitter dispatch
  -> direct ca65 code
```

Esta infraestrutura existe apenas no compilador. As ROMs geradas não contêm tabela
de busca de builtins, despacho dinâmico ou indireção adicional em tempo de execução.

## Registro e identidade resolvida

`nes_pascal/builtins.py` contém um registro estático e imutável indexado tanto pelo
nome público quanto por `BuiltinId`. Cada `BuiltinDescriptor` registra:

- nome público e identidade estável;
- tipo de instrução (statement) ou valor (value);
- tipos de parâmetros e tipo de retorno opcional;
- identidade do hook semântico;
- dependências de recursos de runtime, incluindo dependências que se aplicam apenas
  a escritas de paleta enfileiradas;
- identidade do emissor do backend;
- diagnóstico de contagem de argumentos e texto de correção;
- a sintaxe excepcional de instrução direta utilizada por `nes.wait_frame`.

O analisador sintático (parser) não constrói famílias de nós específicas para cada operação.
Ele preserva o nome qualificado, argumentos e local da chamada em `BuiltinCall`. A análise
semântica resolve esse nome exatamente uma vez e armazena `BuiltinId` em `ResolvedBuiltinCall`;
o layout de memória e a geração de código nunca analisam o nome público novamente.

A validação genérica de assinatura verifica contexto, contagem de argumentos e tipos exatos.
Os casos de `SemanticHook` retêm verificações que não podem ser expressas por uma tupla de tipos,
incluindo constantes de controle, limites de paleta/índice, limites de coordenadas de fundo,
alocação estática de sprites, quadros e animações simbólicos de metasprites e posse entre assets.

A detecção de recursos de memória coleta recursivamente valores `RuntimeFeature` a partir
dos descritores resolvidos. Uma entrada não utilizada no registro não consome RAM nem código.
Em particular, `nes.get_tile()` requisita o shadow de 960 bytes de fundo confirmado, enquanto
operações apenas de escrita de tiles e atributos não o requisitam. Descritores de sprites e
metasprites requisitam suporte a OAM apenas quando utilizados.

O backend do ca65 utiliza mapas centralizados de `BackendEmitter` para builtins de instrução
e de valor. Helpers em grupo ainda expressam sequências específicas do hardware, mas o
despacho é baseado na identidade resolvida do emissor em vez de classes de AST ou casamento
de strings com o nome público.

## Inventário de construções

| Classificação | Construções existentes | Representação |
| --- | --- | --- |
| Instruções comuns de fundo | `nes.set_background_color`, `nes.set_tile`, `nes.set_attribute`, `nes.clear_background_updates`, `nes.clear_background_update_overflow` | `BuiltinCall` / `ResolvedBuiltinCall` |
| Instruções comuns de paleta | `nes.set_background_palette`, `nes.set_sprite_palette`, `nes.set_background_palette_color`, `nes.set_sprite_palette_color` | `BuiltinCall` / `ResolvedBuiltinCall` |
| Instruções comuns de quadro/rolagem | `nes.wait_frame`, `nes.set_scroll` | `BuiltinCall` / `ResolvedBuiltinCall` |
| Instruções comuns de sprites | `nes.set_sprite_zero`, `nes.sprite_set_position`, `nes.sprite_set_x`, `nes.sprite_set_y`, `nes.sprite_set_tile`, `nes.sprite_set_palette`, `nes.sprite_set_attributes`, `nes.sprite_hide`, `nes.sprite_show`, `nes.sprite_set_flip_horizontal`, `nes.sprite_set_flip_vertical`, `nes.sprite_set_behind_background` | `BuiltinCall` / `ResolvedBuiltinCall` |
| Instruções comuns de metasprites/animação | `nes.metasprite_set_position`, `nes.metasprite_set_frame`, `nes.metasprite_set_animation`, `nes.metasprite_restart_animation`, `nes.metasprite_hide`, `nes.metasprite_show`, `nes.metasprite_set_flip_horizontal`, `nes.metasprite_set_flip_vertical` | `BuiltinCall` / `ResolvedBuiltinCall` |
| Builtins comuns de valor | `nes.controller_down`, `nes.controller_pressed`, `nes.controller_released`, `nes.sprite_create`, `nes.metasprite_create`, `nes.metasprite_animation_finished`, `nes.get_tile`, `nes.background_updates_overflowed` | `BuiltinCall` / `ResolvedBuiltinCall` |
| Construção de asset em tempo de compilação | `nes.import_metasprite` | Especializada: valida a identidade do asset configurado e não gera chamada em runtime |
| Construção de asset de fundo em tempo de compilação | `nes.load_background` | Especializada: coordena dados de nametable configurados e ordem pré-renderização no programa |
| Construções de callback/estrutura do programa | `nes.on_update`, `nes.on_vblank` | Especializada: registra identidades de procedimento e valida grafos de chamada |
| Estrutura de início de runtime | `nes.run` | Especializada: fronteira de fase exclusiva de nível superior, não uma chamada comum |

Nomes qualificados de botões de controle como `nes.button_a` até `nes.button_right` são
constantes tipadas em tempo de compilação, não builtins chamáveis.

## Adicionando um builtin comum

Uma API comum futura deve exigir apenas:

1. um descritor de registro com um novo `BuiltinId`, assinatura, dependências de `RuntimeFeature` e `BackendEmitter`;
2. um caminho semântico genérico existente, ou um `SemanticHook` focado quando a assinatura não puder expressar uma restrição em tempo de compilação;
3. um helper emissor no backend ou uma entrada intencional em um emissor agrupado existente;
4. testes positivos, negativos, de isolamento de recursos e de comportamento gerado;
5. documentação sincronizada da linguagem e da API.

Não adicione uma nova classe de AST analisado, classe de AST resolvido, ramo no analisador sintático
ou caso de `isinstance` no layout de memória para um builtin comum. Mantenha uma construção
especializada apenas quando ela alterar a estrutura do programa, configuração de assets do
compilador ou topologia de callbacks.

## Tamanho da refatoração e compatibilidade

A migração substituiu 18 classes de nós comuns analisados e 17 classes de nós comuns resolvidos
por uma classe analisada e uma resolvida. Também removeu de `ast.py` os enums de despacho de
controles, operações de sprites, operações de metasprites e tipos de paleta na AST.

O corpus de benchmark da versão 0.5.5 permanece como a linha de base de compatibilidade. Os
resultados representativos a seguir são idênticos antes e depois da refatoração:

| Benchmark | PRG ocupada | Instruções | ZP alocada/reservada | Não-ZP alocada | Recursos vinculados representativos |
| --- | ---: | ---: | ---: | ---: | --- |
| `minimal` | 245 -> 245 B | 108 -> 108 | 25 -> 25 B | 7 -> 7 B | apenas runtime mínimo |
| `controller_input` | 895 -> 895 B | 404 -> 404 | 30 -> 30 B | 265 -> 265 B | consulta de controle, sprite zero legado, OAM |
| `sprite_support` | 589 -> 589 B | 273 -> 273 | 26 -> 26 B | 326 -> 326 B | API de sprites e OAM |
| `metasprite_player` | 1.443 -> 1.443 B | 551 -> 551 | 34 -> 34 B | 272 -> 272 B | API de metasprites, consulta de controle, OAM |
| `sprite_animation` | 2.013 -> 2.013 B | 675 -> 675 | 34 -> 34 B | 276 -> 276 B | animação de metasprite e OAM |
| `background_updates` | 2.172 -> 2.172 B | 522 -> 522 | 25 -> 25 B | 995 -> 995 B | fila, estado de estouro, shadow de tiles confirmados |
| `gameplay_full_stack` | 3.484 -> 3.484 B | 874 -> 874 | 33 -> 33 B | 1.260 -> 1.260 B | recursos combinados de controles, paleta, rolagem, OAM, animação e fundo |

Aqui, Zero Page significa Zero Page alocada pelo benchmark ou reservada pelo compilador;
não-ZP inclui alocação comum de runtime/usuário mais qualquer shadow de OAM. As definições
completas de contabilidade permanecem na auditoria de otimização da versão 0.5.5.
