# Semantic diagnostics

Semantic-analysis diagnostics use the E3000-E3999 range.

## E3001 - Missing `nes.run`

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

## E3002 - Statement after `nes.run`

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

## E3003 - Invalid background-color call count

- **Category:** Semantic Analysis
- **Explanation:** A valid program requires exactly one call to
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

## E3004 - Duplicate symbol

- **Category:** Semantic Analysis
- **Explanation:** Constants, variables, and procedures share a
  case-insensitive namespace. Parameter names are case-insensitive within a
  procedure and cannot shadow a global symbol.
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

- **Suggested fix:** Use a unique name in the current scope. Rename a
  parameter if it duplicates another parameter or a global symbol.

## E3005 - Unknown identifier

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

## E3006 - Assignment to constant

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

## E3007 - Unknown assignment target

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

## E3008 - Variable read before assignment

- **Category:** Semantic Analysis
- **Explanation:** A variable value is read before an earlier statement
  assigns it, or a procedure is called before the globals it requires have
  been assigned.
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

- **Suggested fix:** Assign the variable before reading it or before calling a
  procedure that requires it.

## E3009 - Runtime command inside conditional

- **Category:** Semantic Analysis
- **Explanation:** NES initialization commands must execute exactly once in
  the top-level program block. `nes.set_background_color` and `nes.run` cannot
  be placed on a conditional execution path.
- **Trigger:**

  ```pascal
  if Enabled then
      nes.run;
  ```

- **Expected compiler output:**

  ```text
  E3009 demo.nsp:2:5

  nes.run cannot appear inside a conditional branch.
  ```

- **Suggested fix:** Move the NES runtime command out of the conditional and
  place it in the top-level program block.

## E3010 - Loop control outside loop

- **Category:** Semantic Analysis
- **Explanation:** `break` and `continue` require an enclosing `while`,
  `repeat`, or `for` loop that provides their control-flow target.
- **Trigger:**

  ```pascal
  begin
      break;
  end.
  ```

- **Expected compiler output:**

  ```text
  E3010 demo.nsp:2:5

  break can appear only inside a loop.
  ```

- **Suggested fix:** Move the statement inside a loop or remove it.

## E3011 - Runtime command inside loop

- **Category:** Semantic Analysis
- **Explanation:** NES initialization commands must execute exactly once.
  `nes.set_background_color` and `nes.run` cannot be repeated by a loop.
- **Trigger:**

  ```pascal
  while Running do
      nes.run;
  ```

- **Expected compiler output:**

  ```text
  E3011 demo.nsp:2:5

  nes.run cannot appear inside a loop body.
  ```

- **Suggested fix:** Move the NES runtime command out of the loop and into the
  top-level program block.

## E3012 - For control variable modification

- **Category:** Semantic Analysis
- **Explanation:** A `for` loop owns its control variable while its body is
  executing. Assigning it, updating it with `inc` or `dec`, or reusing it as
  the control variable of a nested `for` would make loop termination
  unpredictable.
- **Trigger:**

  ```pascal
  for Index := $00 to $03 do
      Index := $01;
  ```

- **Expected compiler output:**

  ```text
  E3012 demo.nsp:2:5

  For control variable Index cannot be modified inside its loop body.
  ```

- **Suggested fix:** Remove the modification, use a different variable in the
  body, or update the control variable after the loop.

## E3013 - Unknown procedure

- **Category:** Semantic Analysis
- **Explanation:** A bare procedure call must resolve to a declared procedure.
  All procedure declarations appear before the main program block, but their
  relative order does not restrict calls.
- **Trigger:**

  ```pascal
  begin
      Missing;
  end.
  ```

- **Expected compiler output:**

  ```text
  E3013 demo.nsp:2:5

  Unknown procedure: Missing.
  ```

- **Suggested fix:** Declare the procedure before the main program block or
  correct the call's spelling.

## E3014 - Recursive procedure call

- **Category:** Semantic Analysis
- **Explanation:** The calling convention supports nested acyclic calls but
  does not support direct or indirect recursion.
- **Trigger:**

  ```pascal
  procedure Again;
  begin
      Again;
  end;
  ```

- **Expected compiler output:**

  ```text
  E3014 demo.nsp:4:5

  Recursive procedure call involving Again is not supported.
  ```

- **Suggested fix:** Remove the recursive call cycle and express the repeated
  work with a supported loop.

## E3015 - Runtime command inside procedure

- **Category:** Semantic Analysis
- **Explanation:** `nes.set_background_color` and `nes.run` belong to the main
  initialization sequence and must execute exactly once. They cannot be hidden
  behind a procedure call.
- **Trigger:**

  ```pascal
  procedure StartRuntime;
  begin
      nes.run;
  end;
  ```

- **Expected compiler output:**

  ```text
  E3015 demo.nsp:4:5

  nes.run cannot appear inside a procedure.
  ```

- **Suggested fix:** Move the runtime command to the main program block.

## E3016 - Incorrect procedure argument count

- **Category:** Semantic Analysis
- **Explanation:** Every procedure call must provide exactly one argument for
  each declared value parameter. Parameterless procedures continue to use a
  bare call without parentheses.
- **Trigger:**

  ```pascal
  procedure Initialize(Value: byte);
  begin
  end;

  begin
      Initialize;
  end.
  ```

- **Expected compiler output:**

  ```text
  E3016 demo.nsp:7:5

  Procedure Initialize expects 1 argument(s), but 0 were provided.
  ```

- **Suggested fix:** Pass exactly the declared number of arguments, in the
  same order as the parameters.
