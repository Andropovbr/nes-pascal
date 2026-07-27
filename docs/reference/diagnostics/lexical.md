# Lexical diagnostics

Lexical diagnostics use the E1000-E1999 range.

## E1000 - Unexpected character

- **Category:** Lexical Analysis
- **Explanation:** The source contains a character that is not part of the
  language token set.
- **Trigger:**

  ```pascal
  program Demo; @
  ```

- **Expected compiler output:**

  ```text
  E1000 demo.nsp:1:15

  Unexpected character: '@'.
  ```

- **Suggested fix:** Remove the character or replace it with supported syntax.

## E1002 - Malformed hexadecimal literal

- **Category:** Lexical Analysis
- **Explanation:** The `$` prefix is not followed by a hexadecimal digit.
- **Trigger:**

  ```pascal
  Color := $;
  ```

- **Expected compiler output:**

  ```text
  E1002 demo.nsp:1:10

  Hexadecimal literal has no digits after '$'.
  ```

- **Suggested fix:** Supply at least one hexadecimal digit, such as `$00`.
