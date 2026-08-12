# Testando o compilador

[English](../../getting-started/testing.md) | Português (Brasil)

Execute a suíte completa com:

```text
python -m unittest discover -s tests -v
```

Ou use:

```text
make test
```

O teste de integração monta e realiza o link da ROM, validando em seguida seu cabeçalho,
mapper, bancos, vetores, dados de CHR, tamanho final, configuração de linker gerada
e mapa de memória da CPU. Testes focados no layout de memória cobrem limites físicos,
regiões reservadas, alocação determinística, esgotamento obrigatório de temporários,
fallback opcional de promoção, configurações internas malformadas e capacidade
de segmentos. Um teste de listagem do ca65 verifica opcodes de Zero Page para símbolos
promovidos e estado de runtime da NMI, além de opcodes absolutos para armazenamento
de fallback. Testes estruturais de backend verificam a preservação de registradores,
o laço de espera autoritativo baseado em contador, detecção persistente de quadros
pendentes, inicialização de renderização condicionada a VBlank e a separação de chamadas
de atualização na thread principal do callback restrito da NMI.
Testes de controle verificam a ordem serial dos bits, estados atual e anterior independentes,
argumentos em tempo de compilação, mascaramento de transição, uma leitura protegida por
quadro processado, opcodes de Zero Page, preparação de sprite fixo, setters gerais de sprites,
preservação de atributos, estado de visibilidade, inicialização e DMA de OAM e Assembly
determinístico. Testes de gerenciamento de sprites cobrem adicionalmente a posse estática
de OAM, coexistência com índices explícitos, esgotamento de 64 entradas e o setter
de posição combinada. Testes de metasprites validam o asset fornecido pelo PNG2CHR Studio,
seu contrato de deslocamento já relativo à âncora, variantes malformadas de esquema,
layouts arbitrários com sinal/esparsos/reutilizados, pivôs centralizados e não centralizados,
geometria horizontal/vertical assimétrica, preservação de limites delimitadores,
XOR de flip de componentes, posse compartilhada e esgotamento de OAM, tabelas compactas em PRG,
RAM por instância, visibilidade, ocultação em quadros mais curtos, estrutura de recorte de borda
e comportamento opcional no Mesen. Testes de animação de sprites adicionam importação simbólica
de sequências, durações padrão e sobrescritas, política de repetição (loop), conclusão de disparo
único (one-shot), estabilidade na mesma animação, reinício, avanço oculto, preservação de flip,
instâncias independentes, contagens variáveis de componentes, emissão de recursos e custos exatos
de tabelas em RAM/PRG.
Testes do toolchain são ignorados com uma mensagem explícita quando o `ca65` ou `ld65`
não estiver disponível.

Para incluir o teste opcional de comportamento no Mesen sem interface gráfica (headless), aponte
`MESEN_PATH` para o executável do emulador ou para o diretório que o contém antes de executar a suíte.
O teste compila os exemplos de comportamento, executa suas ROMs e verifica variáveis finais,
armazenamento de parâmetros de procedimento, endereços em RAM comum e promovidos quando
aplicável, progresso do contador de NMI, três iterações distintas de `nes.wait_frame`,
progresso dos callbacks de atualização e VBlank ao longo do estouro circular de 8 bits do contador
de quadros, comportamento de quadros pendentes em atualizações lentas sem chamadas aninhadas e a cor
de fundo universal. A ROM de controle também aciona ambas as portas virtuais, verifica o comportamento
de cada direção e botão, verifica a consistência da OAM e executa ao longo do estouro circular do
contador de quadros de 8 bits. A ROM de sprites verifica um sprite visível, 63 entradas ocultas,
composição de atributos e seleção de página de DMA. A ROM do jogador metasprite aciona todas as oito
direções do D-pad e valida inversão (flip) centralizada no local, seleção manual de quadro enquanto
invertido, composição de flip de origem/total, limites de jogabilidade totalmente visíveis derivados
do asset em todas as quatro bordas, estado de ocultar/mover/exibir, conversão lógica de Y, OAM de
componentes e DMA. Um cenário de teste (fixture) determinístico separado de recorte valida todas as
quatro bordas, flips horizontal, vertical e combinado, deslocamentos negativos, coordenadas sem
estouro circular, movimentação oculta e troca de quadro invertido; o exemplo de recorte voltado ao
usuário permanece deliberadamente lento o suficiente para inspeção visual. O fixture de animação de
sprites valida adicionalmente a temporização exata de 2/3/1 quadros, reinício de loop, retenção e
conclusão de quadro final em disparo único, reinício explícito, reprodução oculta, tempos de início
independentes, ocultação de slots obsoletos, persistência de flip, cancelamento de quadro manual e
isolamento de instâncias inativas. A regressão do jogador consolidado verifica que consumidores
manuais e animados emitem geometria de quadro centralizada idêntica, que seleções de idle/movimento
não reiniciam quando repetidas e que a orientação sobrevive a mudanças de estado. Uma segunda passagem
no Mesen executa o exemplo real de jogador animado em idle, movimento para a esquerda, idle voltado
para a esquerda, movimento vertical, movimento para a direita e idle voltado para a direita. O exemplo
visual de recorte também completa um ciclo inteiro centro/borda parcial sob uma verificação
automatizada de estado/OAM:

```powershell
$env:MESEN_PATH = "C:\path\to\Mesen.exe"
python -m unittest discover -s tests -v
```

O teste de comportamento é claramente ignorado quando o Mesen ou a cadeia de ferramentas cc65 não estiver disponível.

## Integração Contínua (CI)

O repositório utiliza o GitHub Actions para testes de regressão automatizados a
cada push e execução manual (`workflow_dispatch`). Todos os jobs de CI são
executados em executores pinados no `ubuntu-24.04`. A esteira é composta por
três jobs:

1. **`compiler-toolchain`**: Configura o Python e o toolchain `cc65` (`ca65` e
   `ld65`), executa a suíte completa de regressão do compilador (lexer,
   parser, análise semântica, layout de memória, diagnósticos, golden assembly e
   testes de integração de build de ROM) e gera o relatório de benchmarks do
   compilador através de `tools/measure_benchmarks.py`. O relatório gerado é
   publicado diretamente no resumo da execução do job e exportado como o artefato
   `benchmark-report`. As métricas de benchmark são atualmente observáveis e
   informativas, sem critérios de bloqueio por threshold.
2. **`mesen-runtime`**: Depende do `compiler-toolchain`, instala `ca65`/`ld65` e
   o MesenCE 2.2.1, configura `MESEN_PATH` e executa a suíte completa de testes
   de comportamento em runtime no Mesen headless.
3. **`ci-gate`**: Atua como o check autoritativo que valida se tanto
   `compiler-toolchain` quanto `mesen-runtime` foram concluídos com sucesso.

### Política de Execução Local vs CI

Durante o desenvolvimento, itere utilizando testes focados no subsistema que está sendo
modificado. Enquanto os testes de integração locais toleram a ausência de dependências
externas (`ca65`, `ld65` ou Mesen) com skips informativos, os jobs autoritativos no CI
devem obrigatoriamente instalar todas as dependências requeridas e executar todas as
asserções sem pular validações.

### Comandos Canônicos do Fluxo de Desenvolvimento

O repositório fornece alvos canônicos no `Makefile` que encapsulam os pontos de entrada padrão do Python:

| Alvo | Comando | Requisitos | Descrição |
| :--- | :--- | :--- | :--- |
| `make test` | `python -m unittest discover -s tests -v` | Python | Suíte padrão de testes de regressão local. Pula testes do Mesen quando `MESEN_PATH` não está definido. |
| `make test-all` | `make test` | Python | Alias explícito de `make test` executando a suíte completa de descoberta. |
| `make test-mesen` | `python -m unittest tests.test_integration.MesenIntegrationTests -v` | `ca65`, `ld65`, `MESEN_PATH` | Executa a suíte de testes de emulação de comportamento no Mesen headless. |
| `make benchmark` | `python tools/measure_benchmarks.py` | `ca65`, `ld65` | Executa a ferramenta de medição de recursos e padrões do compilador. |
| `make rom` | `python -m nes_pascal.cli examples/minimal.nsp -o build/minimal.nes` | `ca65`, `ld65` | Compila a ROM mínima representativa canônica. |
| `make clean` | Remove `build/`, `*.log`, `benchmark-report.md` | Python | Limpa com segurança saídas temporárias de build sem remover assets versionados. |
| `make validate` | Executa `test-all`, `benchmark`, `rom` | `ca65`, `ld65` | Validação local abrangente pré-push. Não substitui o gate autoritativo do CI. |

Para executar comandos equivalentes diretamente sem o Make:

```text
# Executar testes unitários focados durante o desenvolvimento (ex.: arrays)
python -m unittest tests.test_arrays -v

# Executar a suíte padrão de regressão do compilador
python -m unittest discover -s tests -v

# Executar a suíte de testes de runtime no Mesen (requer ca65, ld65 e MESEN_PATH)
python -m unittest tests.test_integration.MesenIntegrationTests -v

# Gerar o relatório de métricas de benchmark localmente (requer ca65 e ld65 no PATH)
python tools/measure_benchmarks.py

# Compilar a ROM mínima representativa
python -m nes_pascal.cli examples/minimal.nsp -o build/minimal.nes
```

