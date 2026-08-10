# Diagnósticos léxicos

[English](../../../reference/diagnostics/lexical.md) | Português (Brasil)

Diagnósticos léxicos utilizam o intervalo E1000-E1999.

## E1000 - Caractere inesperado

- **Categoria:** Lexical Analysis
- **Explicação:** O código-fonte contém um caractere que não faz parte do conjunto de tokens da linguagem.
- **Gatilho:**

  ```pascal
  program Demo; @
  ```

- **Saída esperada do compilador:**

  ```text
  E1000 demo.nsp:1:15

  Unexpected character: '@'.
  ```

- **Correção sugerida:** Remova o caractere ou substitua-o por sintaxe suportada.

## E1002 - Literal hexadecimal malformado

- **Categoria:** Lexical Analysis
- **Explicação:** O prefixo `$` não é seguido por um dígito hexadecimal.
- **Gatilho:**

  ```pascal
  Color := $;
  ```

- **Saída esperada do compilador:**

  ```text
  E1002 demo.nsp:1:10

  Hexadecimal literal has no digits after '$'.
  ```

- **Correção sugerida:** Forneça pelo menos um dígito hexadecimal, como `$00`.
