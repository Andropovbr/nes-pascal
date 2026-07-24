# Compiler Diagnostics

Diagnostic codes are part of the compiler's public API. Once retired, a code
must never be assigned to a different diagnostic. Future diagnostics must use
the range reserved for their category.

## Diagnostic Code Ranges

| Range | Category |
| --- | --- |
| E1000-E1999 | Lexical Analysis |
| E2000-E2999 | Parser / Syntax |
| E3000-E3999 | Semantic Analysis |
| E4000-E4999 | Type System |
| E5000-E5999 | Code Generation |
| E6000-E6999 | Runtime Validation |
| W1000-W1999 | Warnings |
| I1000-I1999 | Informational Messages |

## Diagnostic Index

| Code | Category | Description |
| --- | --- | --- |
| E1000 | Lexical Analysis | Unexpected character |
| E1002 | Lexical Analysis | Malformed hexadecimal literal |
| E2101 | Parser / Syntax | Unknown command |
| E2102 | Parser / Syntax | Invalid syntax |
| E3001 | Semantic Analysis | Missing `nes.run` |
| E3002 | Semantic Analysis | Statement after `nes.run` |
| E3003 | Semantic Analysis | Invalid background-color call count |
| E3004 | Semantic Analysis | Duplicate symbol |
| E3005 | Semantic Analysis | Unknown identifier |
| E3006 | Semantic Analysis | Assignment to constant |
| E3007 | Semantic Analysis | Unknown assignment target |
| E3008 | Semantic Analysis | Variable read before assignment |
| E4001 | Type System | Unknown type |
| E4002 | Type System | Invalid `nes_color` value |
| E4003 | Type System | Invalid `byte` value |
| E4004 | Type System | Incompatible types |
| E5001 | Code Generation | Missing toolchain |
| E5002 | Code Generation | Toolchain failure |
| E6001 | Runtime Validation | File access failure |

## Lexical Analysis (E1000-E1999)

### E1000 - Unexpected character

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

### E1002 - Malformed hexadecimal literal

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

## Semantic Analysis (E3000-E3999)

### E3001 - Missing `nes.run`

- **Category:** Semantic Analysis
- **Explanation:** A valid program must finish with exactly one `nes.run`
  statement.
- **Trigger:**

  ```pascal
  begin
      nes.set_background_color($21);
  end.
  ```

- **Expected compiler output:**

  ```text
  E3001 demo.nsp:4:1

  The program must end with nes.run.
  ```

- **Suggested fix:** Add `nes.run;` as the final statement.

### E3002 - Statement after `nes.run`

- **Category:** Semantic Analysis
- **Explanation:** `nes.run` transfers control to the stable main loop, so no
  later statement can execute.
- **Trigger:**

  ```pascal
  nes.run;
  Counter := $01;
  ```

- **Expected compiler output:**

  ```text
  E3002 demo.nsp:2:1

  No statement may appear after nes.run.
  ```

- **Suggested fix:** Move `nes.run;` to the end of the block.

### E3003 - Invalid background-color call count

- **Category:** Semantic Analysis
- **Explanation:** The current milestone requires exactly one call to
  `nes.set_background_color`.
- **Trigger:**

  ```pascal
  begin
      nes.run;
  end.
  ```

- **Expected compiler output:**

  ```text
  E3003 demo.nsp:3:1

  The program must set the background color exactly once.
  ```

- **Suggested fix:** Add one `nes.set_background_color(value);` call before
  `nes.run`.

### E3004 - Duplicate symbol

- **Category:** Semantic Analysis
- **Explanation:** Constants and variables share a case-insensitive namespace.
- **Trigger:**

  ```pascal
  var
      Color: byte;
      COLOR: byte;
  ```

- **Expected compiler output:**

  ```text
  E3004 demo.nsp:3:5

  Symbol COLOR is already declared.
  ```

- **Suggested fix:** Give every constant and variable a unique name.

### E3005 - Unknown identifier

- **Category:** Semantic Analysis
- **Explanation:** A value expression references a name that has not been
  declared.
- **Trigger:**

  ```pascal
  Counter := Missing;
  ```

- **Expected compiler output:**

  ```text
  E3005 demo.nsp:1:12

  Unknown identifier: Missing.
  ```

- **Suggested fix:** Declare the referenced constant or variable before use.

### E3006 - Assignment to constant

- **Category:** Semantic Analysis
- **Explanation:** Constants cannot be modified after declaration.
- **Trigger:**

  ```pascal
  Maximum := $10;
  ```

- **Expected compiler output:**

  ```text
  E3006 demo.nsp:1:1

  Cannot assign to constant Maximum.
  ```

- **Suggested fix:** Assign the value to a variable instead.

### E3007 - Unknown assignment target

- **Category:** Semantic Analysis
- **Explanation:** The left side of an assignment is not a declared variable.
- **Trigger:**

  ```pascal
  Missing := $01;
  ```

- **Expected compiler output:**

  ```text
  E3007 demo.nsp:1:1

  Unknown variable: Missing.
  ```

- **Suggested fix:** Declare the target in the `var` section.

### E3008 - Variable read before assignment

- **Category:** Semantic Analysis
- **Explanation:** A variable value is read before an earlier statement
  assigns it.
- **Trigger:**

  ```pascal
  var
      BackgroundColor: nes_color;
  begin
      nes.set_background_color(BackgroundColor);
  ```

- **Expected compiler output:**

  ```text
  E3008 demo.nsp:4:30

  Variable BackgroundColor is read before it is assigned.

      nes.set_background_color(BackgroundColor);
                               ^^^^^^^^^^^^^^^
  ```

- **Suggested fix:** Assign the variable before reading it.

## Type System (E4000-E4999)

### E4001 - Unknown type

- **Category:** Type System
- **Explanation:** A declaration names a type not provided by the current
  language.
- **Trigger:**

  ```pascal
  Counter: word;
  ```

- **Expected compiler output:**

  ```text
  E4001 demo.nsp:1:10

  Unknown type: word.
  ```

- **Suggested fix:** Use `nes_color`, `byte`, or `boolean`.

### E4002 - Invalid `nes_color` value

- **Category:** Type System
- **Explanation:** `nes_color` values are limited to the NES palette range
  `$00..$3F`.
- **Trigger:**

  ```pascal
  BackgroundColor := $80;
  ```

- **Expected compiler output:**

  ```text
  E4002 demo.nsp:1:20

  Value $80 is not valid for type nes_color.

  Allowed range: $00..$3F.
  ```

- **Suggested fix:** Use a hexadecimal value from `$00` through `$3F`.

### E4003 - Invalid `byte` value

- **Category:** Type System
- **Explanation:** A `byte` occupies one byte and cannot represent values above
  `$FF`.
- **Trigger:**

  ```pascal
  Counter := $100;
  ```

- **Expected compiler output:**

  ```text
  E4003 demo.nsp:1:12

  Value $100 is not valid for type byte.

  Allowed range: $00..$FF.
  ```

- **Suggested fix:** Use a hexadecimal value from `$00` through `$FF`.

### E4004 - Incompatible types

- **Category:** Type System
- **Explanation:** Assignments and intrinsic arguments require exact type
  matches. Numeric-to-boolean and other implicit conversions are forbidden.
  Arithmetic expressions and their operands must have type `byte`.
- **Trigger:**

  ```pascal
  Counter := Active;
  ```

- **Expected compiler output:**

  ```text
  E4004 demo.nsp:1:12

  Cannot assign a value of type boolean to variable Counter of type byte.

  The source and target types must match.
  ```

- **Suggested fix:** Use a source value with exactly the target type. Use
  `true` or `false` for a boolean literal, and use arithmetic only with
  `byte` values.

## Parser / Syntax (E2000-E2999)

### E2101 - Unknown command

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

- **Suggested fix:** Use `nes.set_background_color(value);`, `nes.run;`, or an
  assignment.

### E2102 - Invalid syntax

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
  in `LANGUAGE.md`.

## Code Generation (E5000-E5999)

### E5001 - Missing toolchain

- **Category:** Code Generation
- **Explanation:** ca65 or ld65 cannot be found, so the compiler cannot produce
  a ROM.
- **Trigger:**

  ```text
  python -m nes_pascal.cli examples/minimal.nsp -o build/minimal.nes
  ```

  with cc65 absent from `PATH`.

- **Expected compiler output:**

  ```text
  E5001: missing toolchain component: ca65 and ld65.
  ```

- **Suggested fix:** Install cc65 and add ca65 and ld65 to `PATH`.

### E5002 - Toolchain failure

- **Category:** Code Generation
- **Explanation:** ca65 or ld65 returned a nonzero exit status.
- **Trigger:**

  ```text
  ca65 or ld65 rejects its generated input
  ```

- **Expected compiler output:**

  ```text
  E5002: ca65 failed.

  <tool output>
  ```

- **Suggested fix:** Read the included tool output and correct the underlying
  Assembly or linker configuration problem.

## Runtime Validation (E6000-E6999)

### E6001 - File access failure

- **Category:** Runtime Validation
- **Explanation:** The compiler driver cannot read its source or write an
  output artifact at runtime.
- **Trigger:**

  ```text
  python -m nes_pascal.cli missing.nsp -o build/missing.nes
  ```

- **Expected compiler output:**

  ```text
  E6001: could not access a file: <operating-system error>
  ```

- **Suggested fix:** Check the path, file existence, and filesystem
  permissions.

## Warnings (W1000-W1999)

This range is reserved for future non-fatal compiler warnings. The compiler
currently emits no warnings.

## Informational Messages (I1000-I1999)

This range is reserved for future informational diagnostics. The compiler
currently emits no informational messages.
