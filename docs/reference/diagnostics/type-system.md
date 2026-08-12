# Type-system diagnostics

English | [Português (Brasil)](../../pt-BR/reference/diagnostics/type-system.md)

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

- **Suggested fix:** Use `nes_color`, `byte`, `boolean`, `sprite`, or
  `metasprite`.

## E4002 - Invalid `nes_color` value

- **Category:** Type System
- **Explanation:** `nes_color` values are limited to the NES palette range
  `$00..$3F` in declarations, assignments, and every palette API.
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
  only `byte` and `boolean`. Although `nes_color`, `sprite`, and `metasprite`
  remain valid global types, they cannot be used for a parameter yet.
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

## E4007 - Invalid palette argument type

- **Category:** Type System
- **Explanation:** Palette and color indexes require compile-time `byte`
  values, while color arguments require `nes_color`. No implicit conversions
  are performed.
- **Trigger:** Pass a Boolean index or a `byte` variable as a palette color.
- **Expected compiler output:** `E4007` identifies the argument, actual type,
  and required type.
- **Suggested fix:** Use a `byte` constant for indexes and an assigned
  `nes_color` value for colors.

## E4008 - Invalid `sprite` value

- **Category:** Type System
- **Explanation:** A `sprite` is a strongly typed hardware OAM index and must
  select one of the NES's 64 entries.
- **Trigger:** Compile
  `tests/fixtures/diagnostics/invalid_sprite_value.nsp`, or declare or assign
  a `sprite` value above `$3F`.
- **Expected compiler output:** `E4008` identifies the invalid literal and the
  supported `$00..$3F` range.
- **Suggested fix:** Use a sprite index from `$00` through `$3F`.

## E4009 - Invalid `metasprite` value

- **Category:** Type System
- **Explanation:** A `metasprite` is an opaque static instance identity. A
  hexadecimal number is not a metasprite instance or symbolic frame.
- **Trigger:** Compile
  `tests/fixtures/diagnostics/invalid_metasprite_value.nsp`, which assigns a
  hexadecimal literal to a `metasprite` variable.
- **Expected compiler output:** `E4009` rejects the literal without converting
  it to an instance identity.
- **Suggested fix:** Assign the result of
  `nes.metasprite_create(imported.frame)` to the variable.

## E4010 - Invalid array element type

- **Category:** Type System
- **Explanation:** Fixed arrays currently support only `byte` and `boolean`
  elements.
- **Trigger:** Declare `array[$00..$03] of nes_color`.
- **Suggested fix:** Use `byte` or `boolean` as the element type.

## E4011 - Invalid array index type

- **Category:** Type System
- **Explanation:** An array index must be a strict `byte` expression.
- **Trigger:** Index an array with a `boolean` value.
- **Suggested fix:** Use an assigned `byte` variable, literal, constant, or
  arithmetic expression.

## E4012 - Array index out of bounds

- **Category:** Type System
- **Explanation:** A compile-time-known index is outside the array's inclusive
  declared range.
- **Trigger:** Read or write `Values[$08]` when `Values` is declared as
  `array[$00..$07] of byte`.
- **Suggested fix:** Use a constant index inside the declared bounds. Variable
  indexes remain the program's runtime responsibility.

## E4013 - Invalid array usage

- **Category:** Type System
- **Explanation:** A scalar was indexed, or an array was used or assigned as a
  whole scalar value.
- **Trigger:** Compile `Counter[$00] := $01` or `Counter := Values`.
- **Suggested fix:** Index a declared array and read or write one element.

## E4014 - Invalid array bounds

- **Category:** Type System
- **Explanation:** Arrays use a zero-based byte range with lower bound `$00`
  and upper bound no greater than `$FF`.
- **Trigger:** Declare `array[$01..$04] of byte`.
- **Suggested fix:** Declare a range such as `array[$00..$03] of byte`.
