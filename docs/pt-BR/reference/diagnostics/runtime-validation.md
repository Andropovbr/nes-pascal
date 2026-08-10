# Diagnósticos de validação em runtime

[English](../../../reference/diagnostics/runtime-validation.md) | Português (Brasil)

Diagnósticos de validação em runtime utilizam o intervalo E6000-E6999.

## E6001 - Falha de acesso a arquivo

- **Categoria:** Runtime Validation
- **Explicação:** O driver do compilador não consegue ler seu código-fonte ou gravar um
  artefato de saída em tempo de execução.
- **Gatilho:**

  ```text
  python -m nes_pascal.cli missing.nsp -o build/missing.nes
  ```

- **Saída esperada do compilador:**

  ```text
  E6001: could not access a file: <operating-system error>
  ```

- **Correção sugerida:** Verifique o caminho, existência do arquivo e permissões do sistema de arquivos.

## E6002 - Asset de CHR-ROM não encontrado

- **Categoria:** Runtime Validation
- **Explicação:** Um caminho explicitamente configurado com `--chr` não identifica um
  arquivo existente. O diagnóstico exibe tanto o caminho original quanto o resolvido.
- **Gatilho:** Compilar com `--chr assets/missing.chr` quando esse arquivo não existir
  relativo ao diretório do arquivo-fonte.
- **Saída esperada do compilador:** `E6002` seguido pelo caminho configurado e seu caminho absoluto resolvido.
- **Correção sugerida:** Corrija o caminho ou adicione o arquivo. Omitir `--chr` é a forma
  explícita de solicitar uma CHR-ROM vazia gerada.

## E6003 - Falha de leitura de asset de CHR-ROM

- **Categoria:** Runtime Validation
- **Explicação:** O caminho configurado de CHR-ROM existe ou foi resolvido, mas o sistema
  operacional não permitiu que o compilador lesse seus bytes.
- **Gatilho:** Configurar um arquivo ilegível ou um diretório como `--chr`.
- **Saída esperada do compilador:** `E6003` seguido pelo caminho original, caminho resolvido
  e erro do sistema operacional.
- **Correção sugerida:** Selecione um arquivo comum legível e verifique suas permissões.

## E6004 - Tamanho inválido de CHR-ROM

- **Categoria:** Runtime Validation
- **Explicação:** Mapper 0 NROM atualmente aceita exatamente um banco de 8192 bytes (8 KiB) de CHR-ROM.
- **Gatilho:** Configurar um arquivo vazio ou qualquer arquivo menor ou maior que 8192 bytes.
- **Saída esperada do compilador:** `E6004` seguido pelos 8192 bytes esperados e a contagem real de bytes.
- **Correção sugerida:** Forneça um arquivo `.chr` bruto contendo exatamente 8192 bytes.

## E6005 - Configuração inválida de asset de fundo

- **Categoria:** Runtime Validation
- **Explicação:** Opções combinadas e divididas de fundo entram em conflito, uma metade de uma
  configuração dividida está ausente, ou dados de fundo foram configurados sem uma chamada correspondente
  a `nes.load_background()`.
- **Gatilho:** Usar `--nametable` com qualquer opção dividida, especificar apenas um arquivo
  dividido ou configurar dados para um programa sem o comando.
- **Saída esperada do compilador:** `E6005` explica o elemento conflitante ou ausente na configuração.
- **Correção sugerida:** Use `--nametable` sozinho, ou use ambas as opções divididas, e mantenha
  exatamente uma chamada `nes.load_background();` antes de `nes.run;`.

## E6006 - Asset de fundo não encontrado

- **Categoria:** Runtime Validation
- **Explicação:** Um caminho configurado de nametable, tile ou atributo não identifica um
  arquivo existente. Ambos os caminhos original e resolvido são exibidos.
- **Gatilho:** Configurar um arquivo ausente através de qualquer opção de nametable.
- **Saída esperada do compilador:** `E6006` inclui o caminho fornecido pelo usuário e o caminho
  resolvido relativo ao fonte.
- **Correção sugerida:** Corrija o caminho ou adicione o arquivo ausente.

## E6007 - Falha de leitura de asset de fundo

- **Categoria:** Runtime Validation
- **Explicação:** O caminho foi resolvido, mas o sistema operacional não pôde ler o arquivo
  de fundo configurado.
- **Gatilho:** Configurar um arquivo ilegível ou um diretório.
- **Saída esperada do compilador:** `E6007` inclui o caminho e o erro do sistema operacional.
- **Correção sugerida:** Selecione um arquivo comum legível e verifique permissões.

## E6008 - Tamanho inválido de asset de fundo

- **Categoria:** Runtime Validation
- **Explicação:** Dados brutos de fundo possuem um tamanho fixo nativo do hardware.
- **Gatilho:** Fornecer uma nametable combinada diferente de 1024 bytes, dados de tiles
  diferentes de 960 bytes ou dados de atributos diferentes de 64 bytes.
- **Saída esperada do compilador:** `E6008` inclui os tamanhos esperado e real.
- **Correção sugerida:** Exporte exatamente 1024 bytes combinados ou exatamente 960+64 bytes
  separados sem cabeçalhos ou metadados.

## E6009 - Asset de fundo obrigatório

- **Categoria:** Runtime Validation
- **Explicação:** O código-fonte chama `nes.load_background()`, mas nenhum byte de fundo foi configurado.
- **Gatilho:** Compilar tal programa sem nenhuma opção de nametable.
- **Saída esperada do compilador:** `E6009` identifica a configuração ausente.
- **Correção sugerida:** Passe `--nametable`, ou passe tanto `--nametable-tiles` quanto `--nametable-attributes`.

## E6010 - Configuração inválida de espelhamento

- **Categoria:** Runtime Validation
- **Explicação:** NROM atualmente suporta apenas espelhamento horizontal ou vertical estático de nametable.
- **Gatilho:** Passar qualquer outro valor para `--mirroring`.
- **Saída esperada do compilador:** `E6010` seguido pelo valor configurado.
- **Correção sugerida:** Utilize `--mirroring horizontal` ou `--mirroring vertical`.

## E6011 - Asset de metasprite não encontrado

- **Categoria:** Runtime Validation
- **Explicação:** Um caminho `--metasprite` não resolveu para um arquivo JSON existente. Caminhos
  relativos utilizam o diretório do código-fonte Pascal.
- **Gatilho:** Configurar um arquivo de metadados ausente.
- **Saída esperada do compilador:** `E6011` inclui os caminhos original e resolvido.
- **Correção sugerida:** Corrija o caminho relativo ao fonte ou adicione o arquivo.

## E6012 - Falha de leitura de asset de metasprite

- **Categoria:** Runtime Validation
- **Explicação:** O caminho de metadados foi resolvido, mas seu texto UTF-8 não pôde ser lido.
- **Gatilho:** Configurar um arquivo ou diretório ilegível.
- **Saída esperada do compilador:** `E6012` inclui o erro do sistema operacional.
- **Correção sugerida:** Forneça um arquivo JSON UTF-8 legível.

## E6013 - Metadados JSON de metasprite malformados

- **Categoria:** Runtime Validation
- **Explicação:** O arquivo configurado não é um JSON sintaticamente válido.
- **Gatilho:** Configurar um documento JSON truncado ou malformado.
- **Saída esperada do compilador:** `E6013` inclui a linha e coluna dos metadados.
- **Correção sugerida:** Corrija o JSON ou exporte-o novamente a partir do PNG2CHR Studio.

## E6014 - Formato não suportado de metadados de metasprite

- **Categoria:** Runtime Validation
- **Explicação:** O NES Pascal aceita apenas o formato `png2chr-studio-animation`.
- **Gatilho:** Definir o campo raiz `format` com outro valor.
- **Saída esperada do compilador:** `E6014` exibe os formatos real e suportado.
- **Correção sugerida:** Exporte metadados de animação do PNG2CHR Studio.

## E6015 - Versão não suportada de metadados de metasprite

- **Categoria:** Runtime Validation
- **Explicação:** A versão de esquema suportada do PNG2CHR Studio é `2`.
- **Gatilho:** Configurar metadados com um `version` raiz diferente.
- **Saída esperada do compilador:** `E6015` exibe as versões real e suportada.
- **Correção sugerida:** Reexporte utilizando a versão 2 do esquema.

## E6016 - Metadados de metasprite inválidos

- **Categoria:** Runtime Validation
- **Explicação:** Estrutura ou valores obrigatórios são inválidos, incluindo dimensões do
  quadro, deslocamentos com sinal relativos à origem, contagens de componentes, atributos,
  bits de paleta, metadados de flip, nomes de animação, durações ou política de loop.
- **Gatilho:** Omitir um campo obrigatório ou tornar inconsistentes os metadados de componentes.
- **Saída esperada do compilador:** `E6016` identifica o caminho JSON e a regra.
- **Correção sugerida:** Corrija os metadados e exporte-os novamente.

## E6017 - Dados de CHR incompatíveis com metasprite

- **Categoria:** Runtime Validation
- **Explicação:** Os metadados necessitam de um banco de 8 KiB de CHR NROM configurado e cada
  tile de componente deve caber no conjunto de tiles de sprite declarado nos metadados.
- **Gatilho:** Omitir `--chr`, configurar metadados de capacidade/tamanho incompatíveis ou
  referenciar um tile fora de `final_tile_count`.
- **Saída esperada do compilador:** `E6017` explica a divergência de CHR.
- **Correção sugerida:** Configure JSON e CHR emitidos pela mesma exportação de assets.

## E6018 - Configuração inválida de asset de metasprite

- **Categoria:** Runtime Validation
- **Explicação:** Raízes de metadados configuradas devem ter nomes únicos compatíveis com Pascal
  e o conjunto combinado pode expor no máximo 256 quadros simbólicos e 256 animações simbólicas.
- **Gatilho:** Configurar dois assets com o mesmo nome raiz ou exceder a capacidade de qualquer
  identificador.
- **Saída esperada do compilador:** `E6018` identifica a configuração conflitante.
- **Correção sugerida:** Utilize raízes de assets únicas e divida o conjunto de assets do programa.
