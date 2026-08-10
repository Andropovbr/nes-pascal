# Diagnósticos do analisador e de sintaxe

[English](../../../reference/diagnostics/syntax.md) | Português (Brasil)

Diagnósticos do analisador e de sintaxe utilizam o intervalo E2000-E2999.

## E2101 - Comando desconhecido

- **Categoria:** Parser / Syntax
- **Explicação:** O nome do comando não faz parte da gramática aceita.
- **Gatilho:**

  ```pascal
  nes.background($21);
  ```

- **Saída esperada do compilador:**

  ```text
  E2101 demo.nsp:1:5

  Unknown command: nes.background.
  ```

- **Correção sugerida:** Utilize `nes.set_background_color(value);`, `nes.run;`,
  `nes.wait_frame;`, ou uma instrução de atribuição, atualização ou de controle de fluxo documentada.

## E2102 - Sintaxe inválida

- **Categoria:** Parser / Syntax
- **Explicação:** A sequência de tokens não corresponde à gramática esperada naquele local.
- **Gatilho:**

  ```pascal
  Counter := ;
  ```

- **Saída esperada do compilador:**

  ```text
  E2102 demo.nsp:1:12

  Expected a literal, identifier, or parenthesized expression.
  ```

- **Correção sugerida:** Siga a gramática de declarações e instruções documentada no
  [Guia da Linguagem](../../language/index.md).
