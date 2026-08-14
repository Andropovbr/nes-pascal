# Diagnósticos de geração de código

[English](../../../reference/diagnostics/code-generation.md) | Português (Brasil)

Diagnósticos de geração de código utilizam o intervalo E5000-E5999.

## E5001 - Toolchain ausente

- **Categoria:** Code Generation
- **Explicação:** ca65 ou ld65 não puderam ser encontrados, portanto o compilador não
  pode produzir uma ROM.
- **Gatilho:**

  ```text
  python -m nes_pascal.cli examples/minimal.nsp -o build/minimal.nes
  ```

  com o cc65 ausente no `PATH`.

- **Saída esperada do compilador:**

  ```text
  E5001: missing toolchain component: ca65 and ld65.
  ```

- **Correção sugerida:** Instale o cc65 e adicione o ca65 e ld65 ao `PATH`.

## E5002 - Falha no toolchain

- **Categoria:** Code Generation
- **Explicação:** ca65 ou ld65 retornou um status de saída diferente de zero.
- **Gatilho:**

  ```text
  ca65 ou ld65 rejeita sua entrada gerada
  ```

- **Saída esperada do compilador:**

  ```text
  E5002: ca65 failed.

  <tool output>
  ```

- **Correção sugerida:** Leia a saída da ferramenta incluída e corrija o problema
  subjacente de Assembly ou configuração do linker.

## E5003 - RAM do usuário esgotada

- **Categoria:** Code Generation
- **Explicação:** Uma variável global ou slot de parâmetro de valor de procedimento
  não cabe na região de RAM do usuário. O diagnóstico identifica o símbolo, quantidade
  de bytes solicitada, quantidade de bytes disponível e a declaração de origem.
- **Gatilho:** Declarar variáveis e parâmetros de um byte não promovidos suficientes
  para exceder a região de usuário comum `$0300-$07FF`. A fonte de regressão focada é
  `tests/fixtures/diagnostics/user_ram_exhausted.nsp`, utilizada com um layout interno
  de teste deliberadamente restrito.
- **Saída esperada do compilador:**

  ```text
  E5003 program.nsp:5:5

  User RAM cannot allocate Second: requested 1 byte, but 0 bytes remain in User RAM.
  ```

- **Correção sugerida:** Reduza o número de variáveis ou parâmetros. A promoção
  automática é opcional e não pode ser forçada para ocultar o esgotamento da RAM comum.

## E5004 - RAM temporária esgotada

- **Categoria:** Code Generation
- **Explicação:** A avaliação de expressões e limites de laço for em cache requerem
  mais bytes do que o pool obrigatório de 16 bytes do compilador na Zero Page. O
  armazenamento obrigatório nunca toma emprestado do espaço opcional de promoção automática.
- **Gatilho:** Compilar `tests/fixtures/diagnostics/temporary_ram_exhausted.nsp`, cuja
  expressão aninhada necessita de 17 bytes temporários.
- **Saída esperada do compilador:**

  ```text
  E5004 temporary_ram_exhausted.nsp:1:1

  Expression and loop code requires 17 temporary bytes, but the Zero Page temporaries region has only 16 bytes available.
  ```

- **Correção sugerida:** Simplifique expressões aninhadas ou laços. O espaço de promoção
  opcional não pode atender às alocações obrigatórias do compilador.

## E5005 - Layout de memória inválido

- **Categoria:** Code Generation
- **Explicação:** Configurações internas do compilador descrevem um layout de RAM impossível
  ou não suportado, como partições da Zero Page excedendo `$00FF`, reservas sobrepostas, uma
  região além de `$07FF` ou um shadow de OAM não alinhado a página.
- **Gatilho:** Trata-se de um diagnóstico de configuração interna. Testes constroem
  `MemoryLayoutSettings` malformados; nenhuma opção pública de CLI altera esses valores.
- **Saída esperada do compilador:**

  ```text
  E5005 <input>:1:1

  The OAM shadow region must start on a 256-byte page boundary.
  ```

- **Correção sugerida:** Restaure os padrões suportados de memória NROM.

## E5006 - Estouro de segmento de RAM

- **Categoria:** Code Generation
- **Explicação:** Os bytes emitidos para um segmento de Assembly excedem a região
  atribuída àquele segmento. Isso é verificado antes da execução do ca65 ou ld65.
- **Gatilho:** Isso indica uma divergência interna do compilador. Testes injetam um
  segmento gerado superdimensionado em um layout de outra forma válido.
- **Saída esperada do compilador:**

  ```text
  E5006 <input>:1:1

  Generated segment for User RAM requires 1281 bytes, but its RAM region contains 1280 bytes.
  ```

- **Correção sugerida:** Corrija a alocação ou geração de segmentos do compilador; alterar
  o código-fonte do usuário não deve ser necessário para uma divergência interna.

## E5007 - Profundidade de chamadas de pilha de hardware esgotada

- **Categoria:** Code Generation
- **Explicação:** A profundidade máxima estaticamente conhecida de chamadas
  aninhadas de procedimentos/funções consumiria mais da pilha de hardware de
  256 bytes do 6502 (`$0100-$01FF`) do que a ABI permite. Cada `JSR` ativo
  reserva dois bytes para o endereço de retorno; a capacidade restante mantém 10
  bytes para frames de `JSR` do runtime e folga de NMI, portanto a profundidade
  máxima suportada de chamadas de fonte é 123. Recursão é rejeitada antes com
  `E3014`, então este diagnóstico só ocorre para cadeias de chamadas acíclicas
  longas.
- **Gatilho:** Um programa cuja profundidade máxima de chamadas aninhadas
  excede 123. O limite é exercitado programaticamente em `tests/test_functions.py`
  (124 funções encadeadas pelo caminho mais profundo emitem este diagnóstico).
- **Saída esperada do compilador:**

  ```text
  E5007 <input>:1:1

  Callable nesting depth of 124 exceeds the supported maximum of 123. Each nested procedure or function call consumes two bytes of the 256-byte NES hardware stack for its JSR return address, and 10 bytes are reserved for runtime and NMI stack usage.
  ```

- **Correção sugerida:** Reduza o comprimento das cadeias de chamadas. Recursão
  não é suportada; divida cadeias longas de procedimentos e funções que chamam
  umas às outras em uma estrutura mais achatada.
