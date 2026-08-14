# Diagnósticos do compilador

[English](../../../reference/diagnostics/index.md) | Português (Brasil)

Códigos de diagnóstico fazem parte da API pública do compilador. Uma vez aposentado,
um código nunca deve ser atribuído a um diagnóstico diferente. Futuros diagnósticos
devem utilizar o intervalo reservado para a sua categoria.

## Intervalos de códigos de diagnóstico

| Intervalo | Categoria | Detalhes |
| --- | --- | --- |
| E1000-E1999 | Lexical Analysis | [Diagnósticos léxicos](lexical.md) |
| E2000-E2999 | Parser / Syntax | [Diagnósticos de sintaxe](syntax.md) |
| E3000-E3999 | Semantic Analysis | [Diagnósticos semânticos](semantic.md) |
| E4000-E4999 | Type System | [Diagnósticos do sistema de tipos](type-system.md) |
| E5000-E5999 | Code Generation | [Diagnósticos de geração de código](code-generation.md) |
| E6000-E6999 | Runtime Validation | [Diagnósticos de validação em runtime](runtime-validation.md) |
| W1000-W1999 | Warnings | Reservado; nenhum aviso é emitido |
| I1000-I1999 | Informational Messages | Reservado; nenhuma mensagem informativa é emitida |

## Índice de diagnósticos

| Código | Categoria | Descrição |
| --- | --- | --- |
| [E1000](lexical.md) | Lexical Analysis | Caractere inesperado |
| [E1002](lexical.md) | Lexical Analysis | Literal hexadecimal malformado |
| [E2101](syntax.md) | Parser / Syntax | Comando desconhecido |
| [E2102](syntax.md) | Parser / Syntax | Sintaxe inválida |
| [E3001](semantic.md) | Semantic Analysis | `nes.run` ausente |
| [E3002](semantic.md) | Semantic Analysis | Instrução após `nes.run` |
| [E3003](semantic.md) | Semantic Analysis | Contagem inválida de chamadas de cor de fundo |
| [E3004](semantic.md) | Semantic Analysis | Símbolo duplicado |
| [E3005](semantic.md) | Semantic Analysis | Identificador desconhecido |
| [E3006](semantic.md) | Semantic Analysis | Atribuição a constante |
| [E3007](semantic.md) | Semantic Analysis | Alvo de atribuição desconhecido |
| [E3008](semantic.md) | Semantic Analysis | Variável lida antes da atribuição |
| [E3009](semantic.md) | Semantic Analysis | Comando de runtime dentro de condicional |
| [E3010](semantic.md) | Semantic Analysis | Controle de laço fora de laço |
| [E3011](semantic.md) | Semantic Analysis | Comando de runtime dentro de laço |
| [E3012](semantic.md) | Semantic Analysis | Modificação da variável de controle do for |
| [E3013](semantic.md) | Semantic Analysis | Procedimento desconhecido |
| [E3014](semantic.md) | Semantic Analysis | Ciclo recursivo entre rotinas |
| [E3015](semantic.md) | Semantic Analysis | Comando de runtime dentro de procedimento |
| [E3016](semantic.md) | Semantic Analysis | Contagem incorreta de argumentos de procedimento |
| [E3017](semantic.md) | Semantic Analysis | Espera de quadro antes do início do runtime |
| [E3018](semantic.md) | Semantic Analysis | Procedimento de callback desconhecido |
| [E3019](semantic.md) | Semantic Analysis | Assinatura de callback inválida |
| [E3020](semantic.md) | Semantic Analysis | Callback de atualização duplicado |
| [E3021](semantic.md) | Semantic Analysis | Callback de VBlank duplicado |
| [E3022](semantic.md) | Semantic Analysis | Contexto de registro de callback inválido |
| [E3023](semantic.md) | Semantic Analysis | Operação não segura para VBlank |
| [E3024](semantic.md) | Semantic Analysis | Grafo de chamadas de callback inválido |
| [E3025](semantic.md) | Semantic Analysis | Registro conflitante de callbacks |
| [E3026](semantic.md) | Semantic Analysis | Índice de controle inválido |
| [E3027](semantic.md) | Semantic Analysis | Índice dinâmico de controle |
| [E3028](semantic.md) | Semantic Analysis | Botão de controle inválido |
| [E3029](semantic.md) | Semantic Analysis | Contagem inválida de argumentos de controle |
| [E3030](semantic.md) | Semantic Analysis | Contagem inválida de argumentos do sprite zero |
| [E3031](semantic.md) | Semantic Analysis | Índice de paleta de fundo inválido |
| [E3032](semantic.md) | Semantic Analysis | Índice de paleta de sprite inválido |
| [E3033](semantic.md) | Semantic Analysis | Índice de cor de paleta inválido |
| [E3034](semantic.md) | Semantic Analysis | Contagem inválida de argumentos de paleta |
| [E3035](semantic.md) | Semantic Analysis | Contagem inválida de argumentos de carga de fundo |
| [E3036](semantic.md) | Semantic Analysis | Carga de fundo após início do runtime |
| [E3037](semantic.md) | Semantic Analysis | Carga duplicada de fundo |
| [E3038](semantic.md) | Semantic Analysis | Contagem inválida de argumentos de set-tile |
| [E3039](semantic.md) | Semantic Analysis | Contagem inválida de argumentos de get-tile |
| [E3040](semantic.md) | Semantic Analysis | Contagem inválida de argumentos de set-attribute |
| [E3041](semantic.md) | Semantic Analysis | Contagem inválida de argumentos de clear-background-updates |
| [E3042](semantic.md) | Semantic Analysis | Coordenada de tile inválida |
| [E3043](semantic.md) | Semantic Analysis | Coordenada de atributo inválida |
| [E3044](semantic.md) | Semantic Analysis | Contagem inválida de argumentos de consulta de estouro de fundo |
| [E3045](semantic.md) | Semantic Analysis | Contagem inválida de argumentos de limpeza de estouro de fundo |
| [E3046](semantic.md) | Semantic Analysis | Contagem inválida de argumentos de set-scroll |
| [E3047](semantic.md) | Semantic Analysis | Contagem inválida de argumentos da API de sprites |
| [E3048](semantic.md) | Semantic Analysis | Paleta de sprite de hardware inválida |
| [E3049](semantic.md) | Semantic Analysis | Contagem inválida de argumentos de sprite-create |
| [E3050](semantic.md) | Semantic Analysis | Capacidade de sprites de hardware na OAM esgotada |
| [E3051](semantic.md) | Semantic Analysis | Importação de metasprite inválida |
| [E3052](semantic.md) | Semantic Analysis | Importação duplicada de metasprite |
| [E3053](semantic.md) | Semantic Analysis | Criação de metasprite inválida |
| [E3054](semantic.md) | Semantic Analysis | Contagem inválida de argumentos da API de metasprites |
| [E3055](semantic.md) | Semantic Analysis | Quadro de metasprite incompatível |
| [E3056](semantic.md) | Semantic Analysis | Animação de metasprite inválida |
| [E3057](semantic.md) | Semantic Analysis | Contexto de builtin inválido |
| [E3058](semantic.md) | Semantic Analysis | Contagem inválida de argumentos de builtin |
| [E3059](semantic.md) | Semantic Analysis | Função desconhecida |
| [E3060](semantic.md) | Semantic Analysis | Contagem incorreta de argumentos de função |
| [E3061](semantic.md) | Semantic Analysis | Função usada como instrução |
| [E3062](semantic.md) | Semantic Analysis | Procedimento usado como expressão |
| [E3063](semantic.md) | Semantic Analysis | Resultado de função indefinido |
| [E4001](type-system.md) | Type System | Tipo desconhecido |
| [E4002](type-system.md) | Type System | Valor inválido para `nes_color` |
| [E4003](type-system.md) | Type System | Valor inválido para `byte` |
| [E4004](type-system.md) | Type System | Tipos incompatíveis |
| [E4005](type-system.md) | Type System | Tipo de parâmetro não suportado |
| [E4006](type-system.md) | Type System | Tipo de argumento de controle inválido |
| [E4007](type-system.md) | Type System | Tipo de argumento de paleta inválido |
| [E4008](type-system.md) | Type System | Valor inválido para `sprite` |
| [E4009](type-system.md) | Type System | Valor inválido para `metasprite` |
| [E4010](type-system.md) | Type System | Tipo de elemento de array inválido |
| [E4011](type-system.md) | Type System | Tipo de índice de array inválido |
| [E4012](type-system.md) | Type System | Índice de array fora dos limites |
| [E4013](type-system.md) | Type System | Uso inválido de array |
| [E4014](type-system.md) | Type System | Limites de array inválidos |
| [E4015](type-system.md) | Type System | Membro de enumeração duplicado |
| [E4016](type-system.md) | Type System | Membros de enumeração em excesso |
| [E4017](type-system.md) | Type System | Comparação de enumeração inválida |
| [E4018](type-system.md) | Type System | Membro de enumeração desconhecido |
| [E4019](type-system.md) | Type System | Campo duplicado em record |
| [E4020](type-system.md) | Type System | Campo de record desconhecido |
| [E4021](type-system.md) | Type System | Acesso a campo em valor que não é record |
| [E4022](type-system.md) | Type System | Tipo de campo de record não suportado |
| [E4023](type-system.md) | Type System | Definição recursiva de record |
| [E4024](type-system.md) | Type System | Layout ou offset indexado de record inválido |
| [E4025](type-system.md) | Type System | Uso inválido de record |
| [E4026](type-system.md) | Type System | Tipo de retorno de função não suportado |
| [E5001](code-generation.md) | Code Generation | Toolchain ausente |
| [E5002](code-generation.md) | Code Generation | Falha no toolchain |
| [E5003](code-generation.md) | Code Generation | RAM do usuário esgotada |
| [E5004](code-generation.md) | Code Generation | RAM temporária esgotada |
| [E5005](code-generation.md) | Code Generation | Layout de memória inválido |
| [E5006](code-generation.md) | Code Generation | Estouro de segmento de RAM |
| [E6001](runtime-validation.md) | Runtime Validation | Falha de acesso a arquivo |
| [E6002](runtime-validation.md) | Runtime Validation | Asset de CHR-ROM não encontrado |
| [E6003](runtime-validation.md) | Runtime Validation | Falha de leitura de asset de CHR-ROM |
| [E6004](runtime-validation.md) | Runtime Validation | Tamanho inválido de CHR-ROM |
| [E6005](runtime-validation.md) | Runtime Validation | Configuração inválida de asset de fundo |
| [E6006](runtime-validation.md) | Runtime Validation | Asset de fundo não encontrado |
| [E6007](runtime-validation.md) | Runtime Validation | Falha de leitura de asset de fundo |
| [E6008](runtime-validation.md) | Runtime Validation | Tamanho inválido de asset de fundo |
| [E6009](runtime-validation.md) | Runtime Validation | Asset de fundo obrigatório |
| [E6010](runtime-validation.md) | Runtime Validation | Configuração inválida de espelhamento |
| [E6011](runtime-validation.md) | Runtime Validation | Asset de metasprite não encontrado |
| [E6012](runtime-validation.md) | Runtime Validation | Falha de leitura de asset de metasprite |
| [E6013](runtime-validation.md) | Runtime Validation | Metadados JSON de metasprite malformados |
| [E6014](runtime-validation.md) | Runtime Validation | Formato não suportado de metadados de metasprite |
| [E6015](runtime-validation.md) | Runtime Validation | Versão não suportada de metadados de metasprite |
| [E6016](runtime-validation.md) | Runtime Validation | Metadados de metasprite inválidos |
| [E6017](runtime-validation.md) | Runtime Validation | Dados de CHR incompatíveis com metasprite |
| [E6018](runtime-validation.md) | Runtime Validation | Configuração inválida de asset de metasprite |

## Avisos (Warnings)

O intervalo W1000-W1999 é reservado para futuros avisos não fatais do compilador. O
compilador atualmente não emite avisos.

## Mensagens informativas

O intervalo I1000-I1999 é reservado para futuras mensagens diagnósticas informativas. O
compilador atualmente não emite mensagens informativas.
