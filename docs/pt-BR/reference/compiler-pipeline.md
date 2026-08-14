# Pipeline do compilador

[English](../../reference/compiler-pipeline.md) | Português (Brasil)

O pipeline do compilador é deliberadamente separado:

```text
.nsp source + optional CHR-ROM, metasprite JSON, and nametable assets
  -> lexer
  -> parser
  -> AST
  -> semantic validation, name resolution, and type checking
  -> resolved AST
  -> validated CPU memory layout
  -> ca65 backend
  -> ca65
  -> ld65
  -> ROM
```

## Componentes

- `lexer.py` produz tokens com informações de linha e coluna;
- `parser.py` valida a gramática e constrói a AST analisada em `ast.py`;
- `semantic.py` valida declarações, resolve referências e chamadas de
  procedimento/função, verifica tipos e resultados, rejeita ciclos recursivos,
  aplica atribuição definitiva interprocedural e valida
  intrínsecos de controles e o grafo completo de chamadas de callbacks de VBlank.
  Ele também constrói a posse compartilhada determinística de OAM por slot antes de
  resolver expressões estáticas de `nes.sprite_create()` e `nes.metasprite_create(frame)`;
- `assets.py` resolve caminhos configurados a partir do diretório do código-fonte e
  valida contagens de bytes de CHR-ROM bruta, nametable combinada e tiles/atributos divididos;
- `metasprite_assets.py` valida metadados de animação versão 2 do PNG2CHR Studio, consome
  suas coordenadas de componentes com sinal já relativas à origem sem uma segunda subtração,
  e retém a geometria do quadro mais metadados de sequência simbólica, duração e repetição;
- `codegen_analysis.py` calcula tempos de vida de expressões, bases de
  temporários seguras entre chamadas, profundidade e caches do compilador;
- `memory_layout.py` gerencia intervalos de RAM física, alocação, verificações de limites
  e sobreposição, armazenamento obrigatório na Zero Page, promoção opcional conservadora,
  fallback em RAM comum, geração de configuração do ld65 e o mapa de memória legível por humanos;
- `backend_ca65.py` gera Assembly legível e comentado a partir de valores resolvidos utilizando
  os símbolos de runtime, temporários e do usuário já alocados, e emite cópias de argumentos
  da esquerda para a direita antes de chamadas de procedimentos/funções e
  retorna funções em `A`. Ele também gerencia a
  transferência de nametable na inicialização, o tratador mínimo de NMI, a transição segura
  de runtime no VBlank, a sequência de espera do contador de quadros, o estado persistente do
  último quadro processado, o leitor serial isolado de controles, a consulta protegida de
  controles, a fila limitada de fundo, o shadow de tiles confirmados, o shadow de OAM alinhado
  a página, helpers de sprites individuais, composição e recorte de metasprites orientados por
  tabelas, temporização de animação de metasprites na thread principal, DMA de OAM e chamadas
  estáticas diretas de callbacks;
- `cli.py` grava o Assembly, a configuração gerada do linker `.cfg` e o relatório de memória da
  CPU `.map` antes de coordenar o ca65 e o ld65.

A configuração do linker é gerada a partir do mesmo objeto de layout imutável utilizado
pelo backend e pelo gerador do mapa. Não existe um arquivo de linker estático de NROM mantido
separadamente ou cálculo duplicado de endereços de RAM.

O texto-fonte não é traduzido diretamente para Assembly com substituição de strings. O
compilador utiliza nós explícitos de AST analisados e resolvidos entre a análise sintática
e a geração de código.

Erros comuns do código-fonte são exibidos sem rastreamento de pilha (stack trace) do Python
e incluem código de erro, arquivo, linha, coluna, trecho do fonte e dica de correção quando útil.
Consulte a [referência de diagnósticos](diagnostics/index.md).
