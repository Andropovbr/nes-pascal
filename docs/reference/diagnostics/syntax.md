# Parser and syntax diagnostics

English | [Português (Brasil)](../../pt-BR/reference/diagnostics/syntax.md)

Parser and syntax diagnostics use the E2000-E2999 range.

## E2101 - Unknown command

- **Category:** Parser / Syntax
- **Explanation:** The command name is not part of the accepted grammar.
- **Trigger:**

  ```pascal
  nes.background($21);
  ```

- **Expected compiler output:**

  ```text
  E2101 demo.nsp:1:5

  Unknown command: nes.background.
  ```

- **Suggested fix:** Use `nes.set_background_color(value);`, `nes.run;`,
  `nes.wait_frame;`, or an assignment, update, or documented control-flow
  statement.

## E2102 - Invalid syntax

- **Category:** Parser / Syntax
- **Explanation:** The token sequence does not match the grammar expected at
  that location.
- **Trigger:**

  ```pascal
  Counter := ;
  ```

- **Expected compiler output:**

  ```text
  E2102 demo.nsp:1:12

  Expected a literal, identifier, or parenthesized expression.
  ```

- **Suggested fix:** Follow the declaration and statement grammar documented
  in the [Language Guide](../../language/index.md).
