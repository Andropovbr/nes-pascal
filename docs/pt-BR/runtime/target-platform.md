# Plataforma-alvo

[English](../../runtime/target-platform.md) | Português (Brasil)

O NES Pascal gera código Assembly compatível com o ca65 para a CPU Ricoh 2A03 e
utiliza apenas instruções do 6502. Ele não gera C intermediário nem utiliza instruções
exclusivas do 65C02.

## Formato da ROM

Os programas gerados são direcionados a sistemas NES NTSC com mapper 0, NROM-256:

- um cabeçalho iNES explícito;
- 32 KiB de PRG-ROM;
- um banco de 8 KiB de CHR-ROM, contendo um arquivo bruto `.chr` configurado sem alterações,
  preenchido com zeros por padrão, ou contendo dois tiles internos quando o suporte fixo ao
  sprite 0 é utilizado sem um asset configurado;
- vetores NMI, RESET e IRQ.

O cabeçalho iNES tem como padrão o espelhamento horizontal de nametables. Passe
`--mirroring vertical` para espelhamento vertical; apenas essas duas escolhas estáticas
de NROM são suportadas.

A imagem de saída possui 40.976 bytes: um cabeçalho iNES de 16 bytes, 32 KiB de PRG-ROM
e 8 KiB de CHR-ROM.

## Comportamento de inicialização

O caminho de RESET desabilita interrupções, inicializa a pilha e a RAM pertencente ao
runtime, e aguarda a estabilização da PPU. Escritas de paleta na inicialização permanecem
seguras enquanto a renderização estiver desabilitada. Uma nametable configurada é copiada
para `$2000-$23FF` durante essa fase de renderização desabilitada. `nes.run` aguarda o
VBlank antes de habilitar a NMI e a renderização.

Cada NMI preserva A, X, Y e o equilíbrio da pilha, incrementa um contador volátil de
quadros de 8 bits e define um byte informativo de quadro pronto. Se registrado, um callback
restrito de VBlank é executado via `JSR` direto; seu procedimento termina com `RTS`.
A NMI então restaura o estado da PPU pertencente ao compilador, restaura os registradores
e executa o `RTI` final. A lógica comum de atualização é executada apenas na thread principal.
Seu byte persistente do último quadro processado preserva uma NMI pendente ao longo de callbacks
lentos e aglutina o backlog mais antigo. A thread principal consulta as portas de controle
padrão uma vez antes de cada atualização processada. Quando o suporte a sprites é incluído,
a NMI transfere o shadow completo de OAM alinhado a página por DMA; o helper legado e fixo
do sprite 0 primeiro envia seu registro completo de preparação. A geometria de metasprites é
composta nesse shadow no contexto principal/atualização; a NMI não realiza cálculos de layout.
Não há fila genérica de comandos da PPU, sistema de animação automática, remapeamento de
controles ou áudio.

## Memória

O NES expõe 2 KiB de RAM física interna da CPU em `$0000-$07FF`. O intervalo `$0800-$1FFF`
contém espelhos, não armazenamento adicional. A Zero Page possui regiões separadas de
runtime, temporários do compilador, futuras declarações explícitas e promoção automática.
Variáveis globais frequentemente referenciadas podem ser promovidas de forma conservadora;
parâmetros e variáveis em fallback utilizam RAM comum. Consulte [Memória da CPU](cpu-memory.md)
para a política determinística completa.

A CHR-ROM normalmente é vazia. Um arquivo bruto de exatamente 8192 bytes pode ser selecionado
com a opção `--chr` do compilador; caminhos relativos utilizam o diretório do arquivo-fonte.
O exemplo de controles embute condicionalmente dois tiles internos de 8x8 do jogador quando
nenhum arquivo é selecionado. Bytes configurados de CHR ocupam o segmento de CHR existente
uma vez e não são convertidos nem modificados. JSON de metasprites configurado é analisado
apenas pelo compilador. Sua geometria compacta de componentes é emitida na PRG-ROM, enquanto
os gráficos dos tiles referenciados permanecem no único banco de CHR configurado.

Uma nametable completa de 1024 bytes pode ser embutida na PRG-ROM e transferida para a
nametable 0 da PPU. Ela contém 960 índices de tiles seguidos pela tabela de atributos de
64 bytes. O compilador também aceita essas duas partes como arquivos separados e as concatena
sem conversão. Consulte [Carregamento de fundo](background-loading.md).

O Assembly gerado é intencionalmente legível e inclui comentários que identificam a origem
dos blocos gerados. O backend não é uma game engine genérica.
