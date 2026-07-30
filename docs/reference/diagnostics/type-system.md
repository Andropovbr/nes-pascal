# Type-system diagnostics

Type-system diagnostics use the E4000-E4999 range.

## E4001 - Unknown type

- **Category:** Type System
- **Explanation:** A declaration names a type not provided by the implemented
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

## E4002 - Invalid `nes_color` value

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

## E4003 - Invalid `byte` value

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

## E4004 - Incompatible types

- **Category:** Type System
- **Explanation:** Assignments and intrinsic arguments require exact type
  matches. Numeric-to-boolean and other implicit conversions are forbidden.
  Arithmetic expressions and their operands must have type `byte`. Comparison
  operands must follow the comparison operator's type rules, and Boolean
  operators require `boolean` operands. Increment/decrement targets and
  amounts, plus `for` control variables and bounds, must have type `byte`.
  Procedure arguments must exactly match their corresponding `byte` or
  `boolean` parameter types.
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
  `true` or `false` for a boolean literal, and use arithmetic only with `byte`
  values. Compare matching types, and use `not`, `and`, and `or` only with
  `boolean` values.

## E4005 - Unsupported parameter type

- **Category:** Type System
- **Explanation:** The current value-parameter calling convention supports
  only `byte` and `boolean`. Although `nes_color` remains a valid type for
  constants and global variables, it cannot be used for a parameter yet.
- **Trigger:**

  ```pascal
  procedure SetColor(Color: nes_color);
  begin
  end;
  ```

- **Expected compiler output:**

  ```text
  E4005 demo.nsp:1:27

  Type nes_color is not supported for procedure parameters.
  ```

- **Suggested fix:** Declare the value parameter as `byte` or `boolean`, or
  keep an `nes_color` value in global state.

## E4006 - Invalid controller argument type

- **Category:** Type System
- **Explanation:** The controller index and button arguments describe
  compile-time byte values. Boolean values cannot select a port or button.
- **Trigger:** `nes.controller_down(true, nes.button_a)` or a boolean button
  argument.
- **Expected compiler output:** `E4006` identifies the argument and its actual
  type.
- **Suggested fix:** Pass `$01` or `$02` as the controller and exactly one
  `nes.button_*` constant as the button.
