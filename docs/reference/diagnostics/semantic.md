# Semantic diagnostics

English | [Português (Brasil)](..\..\pt-BR\reference\diagnostics\semantic.md)

Semantic-analysis diagnostics use the E3000-E3999 range.

## E3001 - Missing `nes.run`

- **Category:** Semantic Analysis
- **Explanation:** A valid program must start the runtime with exactly one
  unconditional top-level `nes.run` statement.
- **Trigger:**

  ```pascal
  begin
      nes.set_background_color($21);
  end.
  ```

- **Expected compiler output:**

  ```text
  E3001 demo.nsp:4:1

  The program must start the runtime with nes.run.
  ```

- **Suggested fix:** Add one top-level `nes.run;` after initialization and
  before any `nes.wait_frame` statement.

## E3002 - Statement after `nes.run`

- **Category:** Semantic Analysis
- **Explanation:** Ordinary main-thread statements, including queued palette
  updates, may follow `nes.run`, but additional `nes.run` calls may not.
- **Trigger:**

  ```pascal
  nes.run;
  nes.run;
  ```

- **Expected compiler output:**

  ```text
  E3002 demo.nsp:2:1

  nes.run may appear only once.
  ```

- **Suggested fix:** Remove the duplicate `nes.run` call.

## E3003 - Invalid background-color call count

- **Category:** Semantic Analysis
- **Explanation:** A valid program requires exactly one initialization call to
  `nes.set_background_color` before `nes.run`. Later queued calls are allowed.
- **Trigger:**

  ```pascal
  begin
      nes.run;
  end.
  ```

- **Expected compiler output:**

  ```text
  E3003 demo.nsp:3:1

  The program must set its initial background color exactly once.
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
- **Explanation:** `nes.run` must execute exactly once in the top-level program
  block and cannot be placed on a conditional execution path. Palette calls
  are allowed and queue changes after runtime starts.
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
- **Explanation:** `nes.run` must execute exactly once and cannot be repeated
  by a loop. Palette calls are allowed and queue changes after runtime starts.
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
- **Explanation:** `nes.run` belongs to the main initialization sequence and
  `nes.wait_frame` depends on the main block's known runtime phase. Palette
  calls are allowed in procedures and publish changes for VBlank.
- **Trigger:**

  ```pascal
  procedure WaitInsideProcedure;
  begin
      nes.wait_frame;
  end;
  ```

- **Expected compiler output:**

  ```text
  E3015 demo.nsp:4:5

  nes.wait_frame cannot appear inside a procedure.
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

## E3017 - Frame wait before runtime start

- **Category:** Semantic Analysis
- **Explanation:** `nes.wait_frame` observes a counter changed by NMI. Before
  `nes.run`, NMI is disabled and the wait could never complete.
- **Trigger:** Compile
  `tests/fixtures/diagnostics/frame_wait_before_run.nsp`, or write:

  ```pascal
  nes.set_background_color($21);
  nes.wait_frame;
  nes.run;
  ```

- **Expected compiler output:**

  ```text
  E3017 frame_wait_before_run.nsp:4:5

  nes.wait_frame cannot execute before nes.run starts NMI.
  ```

- **Suggested fix:** Move `nes.wait_frame` and its containing frame loop after
  the unconditional top-level `nes.run` call.

## E3018 - Unknown callback procedure

- **Category:** Semantic Analysis
- **Explanation:** A callback registration names a procedure that is not
  declared.
- **Trigger:** `nes.on_update(Missing);`
- **Expected compiler output:**

  ```text
  E3018 demo.nsp:4:19

  Unknown callback procedure: Missing.
  ```

- **Suggested fix:** Declare a parameterless procedure before the main block
  or correct the identifier.

## E3019 - Invalid callback signature

- **Category:** Semantic Analysis
- **Explanation:** Update and VBlank callbacks must be parameterless
  procedures with no return value.
- **Trigger:** Register `procedure Update(Value: byte);` with
  `nes.on_update(Update);`.
- **Expected compiler output:** `E3019` followed by `Callback procedure Update
  must not have parameters.`
- **Suggested fix:** Use a procedure declared without a parameter list.

## E3020 - Duplicate update callback

- **Category:** Semantic Analysis
- **Explanation:** Only one static update callback may be registered.
- **Trigger:** Place two `nes.on_update(...)` statements in initialization.
- **Expected compiler output:** `E3020` followed by `Only one update callback
  may be registered.`
- **Suggested fix:** Keep one update registration and dispatch explicitly from
  that procedure when necessary.

## E3021 - Duplicate VBlank callback

- **Category:** Semantic Analysis
- **Explanation:** Only one static VBlank callback may be registered.
- **Trigger:** Place two `nes.on_vblank(...)` statements in initialization.
- **Expected compiler output:** `E3021` followed by `Only one VBlank callback
  may be registered.`
- **Suggested fix:** Keep one VBlank registration and call only safe,
  parameterless helpers from it.

## E3022 - Invalid callback registration context

- **Category:** Semantic Analysis
- **Explanation:** Registration is compile-time initialization, not a runtime
  operation. It must be unconditional, top-level, and before `nes.run`.
- **Trigger:** Put `nes.on_update(Update);` in an `if`, loop, procedure, or
  after `nes.run`.
- **Expected compiler output:** `E3022` followed by a callback registration
  context explanation.
- **Suggested fix:** Move the registration to unconditional top-level
  initialization before `nes.run`.

## E3023 - VBlank-unsafe operation

- **Category:** Semantic Analysis
- **Explanation:** A VBlank callback or reachable helper contains an
  unbounded operation or uses shared non-reentrant compiler temporary storage.
- **Trigger:** Use `while`, `repeat`, `for`, arithmetic, a comparison,
  `nes.wait_frame`, or another unsupported statement on the VBlank call path.
- **Expected compiler output:** `E3023` identifies the unsafe operation and
  the procedure path that reaches it.
- **Suggested fix:** Restrict VBlank code to temporary-free scalar
  assignments, simple `inc`/`dec`, safe conditionals, palette staging calls
  with temporary-free values, and validated helpers.

## E3024 - Invalid callback call graph

- **Category:** Semantic Analysis
- **Explanation:** A VBlank callback reaches update logic or a parameterized
  procedure. Such a call is not part of the conservative interrupt-safe
  subset.
- **Trigger:** Call the registered update callback or a procedure with value
  parameters from a VBlank callback or reachable helper.
- **Expected compiler output:** `E3024` identifies the invalid call edge.
- **Suggested fix:** Keep update logic outside NMI and use only parameterless,
  transitively VBlank-safe helpers.

## E3025 - Conflicting callback registration

- **Category:** Semantic Analysis
- **Explanation:** One procedure cannot be registered for both main-thread
  update and NMI VBlank contexts in this milestone.
- **Trigger:** Register `Both` with both `nes.on_update(Both);` and
  `nes.on_vblank(Both);`.
- **Expected compiler output:** `E3025` followed by `Procedure Both cannot be
  registered as both update and VBlank callbacks.`
- **Suggested fix:** Declare separate parameterless procedures for the two
  execution contexts.

## E3026 - Invalid controller index

- **Category:** Semantic Analysis
- **Explanation:** Standard controller queries support only ports 1 and 2.
- **Trigger:** `nes.controller_down($03, nes.button_a)` or index `$00`.
- **Expected compiler output:** `E3026` identifies the invalid constant.
- **Suggested fix:** Pass `$01`, `$02`, or a declared `byte` constant with one
  of those values.

## E3027 - Dynamic controller index

- **Category:** Semantic Analysis
- **Explanation:** The controller index must be selected at compile time so
  code generation can use one fixed runtime state byte.
- **Trigger:** Pass a variable or expression as the first controller-query
  argument.
- **Expected compiler output:** `E3027` followed by `requires a compile-time
  controller index`.
- **Suggested fix:** Use `$01`, `$02`, or a direct declared `byte` constant.

## E3028 - Invalid controller button

- **Category:** Semantic Analysis
- **Explanation:** A controller query accepts exactly one standard
  `nes.button_*` constant, not a literal, user constant, expression, or unknown
  button name.
- **Trigger:** `nes.controller_down($01, nes.button_fire)`.
- **Expected compiler output:** `E3028` identifies the invalid button.
- **Suggested fix:** Use A, B, Select, Start, Up, Down, Left, or Right through
  its documented built-in constant.

## E3029 - Invalid controller argument count

- **Category:** Semantic Analysis
- **Explanation:** Each controller query requires one controller index and one
  button constant.
- **Trigger:** Omit either argument or provide an extra argument.
- **Expected compiler output:** `E3029` reports the provided count.
- **Suggested fix:** Use a call such as
  `nes.controller_pressed($01, nes.button_start)`.

## E3030 - Invalid sprite-zero argument count

- **Category:** Semantic Analysis
- **Explanation:** The fixed controller-example sprite helper requires X, Y,
  tile, and attributes values.
- **Trigger:** Call `nes.set_sprite_zero` with other than four arguments.
- **Expected compiler output:** `E3030` reports the provided count.
- **Suggested fix:** Pass exactly four `byte` expressions. This helper is not a
  general sprite API.

## E3031 - Invalid background palette index

- **Category:** Semantic Analysis
- **Explanation:** A background palette index must be a compile-time `byte`
  value from `$00` through `$03`.
- **Trigger:** Pass `$04` or a dynamic expression to
  `nes.set_background_palette` or its individual-color form.
- **Expected compiler output:** `E3031` identifies the invalid index and API.
- **Suggested fix:** Use `$00..$03` or a `byte` constant in that range.

## E3032 - Invalid sprite palette index

- **Category:** Semantic Analysis
- **Explanation:** A sprite palette index must be a compile-time `byte` value
  from `$00` through `$03`.
- **Trigger:** Pass `$04` or a dynamic expression to `nes.set_sprite_palette`
  or its individual-color form.
- **Expected compiler output:** `E3032` identifies the invalid index and API.
- **Suggested fix:** Use `$00..$03` or a `byte` constant in that range.

## E3033 - Invalid palette color index

- **Category:** Semantic Analysis
- **Explanation:** Individual palette updates select color `$00..$03` at
  compile time.
- **Trigger:** Pass color index `$04` or a dynamic expression.
- **Expected compiler output:** `E3033` identifies the invalid color index.
- **Suggested fix:** Use `$00..$03` or a `byte` constant in that range.

## E3034 - Invalid palette argument count

- **Category:** Semantic Analysis
- **Explanation:** Full palette calls require one index and four colors;
  individual calls require palette index, color index, and color.
- **Trigger:** Omit an argument or provide an extra argument.
- **Expected compiler output:** `E3034` reports the expected and actual count.
- **Suggested fix:** Use the documented five- or three-argument signature.

## E3035 - Invalid background-load argument count

- **Category:** Semantic Analysis
- **Explanation:** `nes.load_background()` selects the background configured
  by compiler options and therefore takes no source-language arguments.
- **Trigger:** `nes.load_background($00);`
- **Expected compiler output:** `E3035` reports the provided argument count.
- **Suggested fix:** Call `nes.load_background();` without arguments.

## E3036 - Background load after runtime start

- **Category:** Semantic Analysis
- **Explanation:** A full 1 KiB nametable upload is initialization-only and
  cannot run after `nes.run` enables rendering.
- **Trigger:** Place `nes.load_background();` after `nes.run;`.
- **Expected compiler output:** `E3036` identifies the unsafe command.
- **Suggested fix:** Move the load to unconditional top-level initialization
  before `nes.run;`.

## E3037 - Duplicate background load

- **Category:** Semantic Analysis
- **Explanation:** The current NROM program supports one static background
  load into nametable 0.
- **Trigger:** Call `nes.load_background();` twice in the main block.
- **Expected compiler output:** `E3037` points to the second call.
- **Suggested fix:** Keep one initialization call and one configured asset.

## E3038 - Invalid set-tile argument count

- **Category:** Semantic Analysis
- **Explanation:** `nes.set_tile` requires tile X, tile Y, and tile index.
- **Trigger:** Compile
  `tests/fixtures/diagnostics/set_tile_argument_count.nsp`, or omit or add an
  argument to `nes.set_tile`.
- **Expected compiler output:** `E3038` reports the expected and actual count.
- **Suggested fix:** Call `nes.set_tile(x, y, tile)` with three `byte` values.

## E3039 - Invalid get-tile argument count

- **Category:** Semantic Analysis
- **Explanation:** `nes.get_tile` requires tile X and tile Y.
- **Trigger:** Compile
  `tests/fixtures/diagnostics/get_tile_argument_count.nsp`, or omit or add an
  argument to `nes.get_tile`.
- **Expected compiler output:** `E3039` reports the expected and actual count.
- **Suggested fix:** Call `nes.get_tile(x, y)` with two `byte` values.

## E3040 - Invalid set-attribute argument count

- **Category:** Semantic Analysis
- **Explanation:** `nes.set_attribute` requires attribute X, attribute Y, and
  one raw attribute byte.
- **Trigger:** Compile
  `tests/fixtures/diagnostics/set_attribute_argument_count.nsp`.
- **Expected compiler output:** `E3040` reports the expected and actual count.
- **Suggested fix:** Call `nes.set_attribute(x, y, value)` with three `byte`
  values.

## E3041 - Invalid clear-background-updates argument count

- **Category:** Semantic Analysis
- **Explanation:** `nes.clear_background_updates()` takes no arguments.
- **Trigger:** Compile
  `tests/fixtures/diagnostics/clear_background_updates_argument_count.nsp`.
- **Expected compiler output:** `E3041` reports the provided count.
- **Suggested fix:** Call `nes.clear_background_updates();` without arguments.

## E3042 - Invalid tile coordinate

- **Category:** Semantic Analysis
- **Explanation:** A direct literal or constant tile coordinate is outside
  nametable 0's logical 32-by-30 tile area.
- **Trigger:** Compile
  `tests/fixtures/diagnostics/invalid_tile_coordinate.nsp`, use X above 31, or
  use Y above 29 in `nes.set_tile` or `nes.get_tile`.
- **Expected compiler output:** `E3042` identifies the coordinate and valid
  range.
- **Suggested fix:** Use X from 0 through 31 and Y from 0 through 29. Dynamic
  coordinates are checked by the runtime.

## E3043 - Invalid attribute coordinate

- **Category:** Semantic Analysis
- **Explanation:** A direct literal or constant attribute coordinate is outside
  the hardware 8-by-8 attribute-entry grid for nametable 0.
- **Trigger:** Compile
  `tests/fixtures/diagnostics/invalid_attribute_coordinate.nsp`, use X above 7,
  or use Y above 7 in `nes.set_attribute`.
- **Expected compiler output:** `E3043` identifies the coordinate and valid
  range.
- **Suggested fix:** Use X and Y from 0 through 7. Dynamic coordinates are
  checked by the runtime.

## E3044 - Invalid background-overflow query argument count

- **Category:** Semantic Analysis
- **Explanation:** `nes.background_updates_overflowed()` reads one fixed
  runtime flag and takes no arguments.
- **Trigger:** Compile
  `tests/fixtures/diagnostics/background_updates_overflowed_argument_count.nsp`.
- **Expected compiler output:** `E3044` reports the provided count.
- **Suggested fix:** Call `nes.background_updates_overflowed()` without
  arguments and use its `boolean` result.

## E3045 - Invalid background-overflow clear argument count

- **Category:** Semantic Analysis
- **Explanation:** `nes.clear_background_update_overflow()` clears one fixed
  runtime flag and takes no arguments.
- **Trigger:** Compile
  `tests/fixtures/diagnostics/clear_background_update_overflow_argument_count.nsp`.
- **Expected compiler output:** `E3045` reports the provided count.
- **Suggested fix:** Call `nes.clear_background_update_overflow();` without
  arguments.
## E3046 - Invalid set-scroll argument count

- **Category:** Semantic Analysis
- **Explanation:** `nes.set_scroll` requires exactly two arguments: horizontal
  scroll and vertical scroll.
- **Trigger:** Call `nes.set_scroll` with fewer or more than two arguments.
- **Expected compiler output:** `E3046` followed by the expected and actual
  argument counts.
- **Suggested fix:** Pass exactly two `byte` values, for example
  `nes.set_scroll($08, $04);`.

## E3047 - Invalid sprite API argument count

- **Category:** Semantic Analysis
- **Explanation:** Sprite property setters require a `sprite` index and one
  property value. `nes.sprite_hide` and `nes.sprite_show` require only the
  sprite index.
- **Trigger:** Compile
  `tests/fixtures/diagnostics/sprite_argument_count.nsp`, or omit or add an
  argument to a `nes.sprite_*` statement.
- **Expected compiler output:** `E3047` reports the command's expected and
  actual argument counts.
- **Suggested fix:** Pass exactly the arguments documented for the sprite API.

## E3048 - Invalid hardware sprite palette

- **Category:** Semantic Analysis
- **Explanation:** OAM attribute bits 0-1 select one of four sprite palettes.
  A direct literal or constant passed to `nes.sprite_set_palette` must be in
  `$00..$03`.
- **Trigger:** Compile
  `tests/fixtures/diagnostics/invalid_sprite_palette.nsp`, or pass `$04` or
  greater as a compile-time palette value.
- **Expected compiler output:** `E3048` identifies the value and valid range.
- **Suggested fix:** Use sprite palette `$00`, `$01`, `$02`, or `$03`.

## E3049 - Invalid sprite-create argument count

- **Category:** Semantic Analysis
- **Explanation:** `nes.sprite_create()` is a parameterless compile-time OAM
  reservation expression.
- **Trigger:** Compile
  `tests/fixtures/diagnostics/sprite_create_argument_count.nsp` or pass any
  argument to `nes.sprite_create`.
- **Expected compiler output:** `E3049` reports that zero arguments were
  expected and identifies the provided count.
- **Suggested fix:** Call `nes.sprite_create()` with empty parentheses.

## E3050 - OAM hardware-sprite capacity exhausted

- **Category:** Semantic Analysis
- **Explanation:** Explicit individual-sprite reservations, distinct
  `nes.sprite_create()` sites, and statically owned metasprite components share
  the NES's fixed 64-entry OAM capacity. Static allocation cannot reserve
  another non-conflicting entry or component group.
- **Trigger:** Compile
  `tests/fixtures/diagnostics/sprite_capacity_exhausted.nsp` or otherwise
  reserve all 64 indexes before another creation site.
- **Expected compiler output:** `E3050` identifies the creation site that
  cannot receive an OAM entry.
- **Suggested fix:** Remove an individual sprite reservation, sprite creation
  site, or metasprite instance. Allocation never wraps, aliases an owner,
  truncates a metasprite, or returns a sentinel.

## E3051 - Invalid metasprite import

- **Category:** Semantic Analysis
- **Explanation:** A compile-time metasprite import must be a direct top-level
  statement before `nes.run`, must name one asset configured with
  `--metasprite`, and every configured asset must be imported.
- **Trigger:** Compile `tests/fixtures/diagnostics/invalid_metasprite_import.nsp`
  without configuring its `player` metadata, nest the import, or move it after
  runtime startup.
- **Expected compiler output:** `E3051` identifies the invalid import or the
  configured asset that lacks an import statement.
- **Suggested fix:** Configure the JSON and write
  `nes.import_metasprite(player);` directly in the main block before
  `nes.run;`.

## E3052 - Duplicate metasprite import

- **Category:** Semantic Analysis
- **Explanation:** One configured asset root may be imported exactly once.
- **Trigger:** Compile
  `tests/fixtures/diagnostics/duplicate_metasprite_import.nsp` with the player
  asset configured.
- **Expected compiler output:** `E3052` identifies the second import.
- **Suggested fix:** Keep one top-level import for each asset root.

## E3053 - Invalid metasprite creation

- **Category:** Semantic Analysis
- **Explanation:** `nes.metasprite_create` requires exactly one imported,
  symbolic frame such as `player.idle_0`. The creation site has a persistent
  static identity and is not a heap allocation.
- **Trigger:** Compile
  `tests/fixtures/diagnostics/invalid_metasprite_create.nsp` or call the
  intrinsic without one symbolic frame.
- **Expected compiler output:** `E3053` explains the invalid creation form.
- **Suggested fix:** Import the asset and pass one frame symbol.

## E3054 - Invalid metasprite API argument count

- **Category:** Semantic Analysis
- **Explanation:** Position takes a metasprite and two bytes; frame and flip
  setters and animation selection take a metasprite and one value; hide/show,
  animation restart, and animation completion queries take one metasprite.
- **Trigger:** Compile
  `tests/fixtures/diagnostics/metasprite_argument_count.nsp`.
- **Expected compiler output:** `E3054` reports the expected and actual counts.
- **Suggested fix:** Pass exactly the arguments documented by the metasprite
  API.

## E3055 - Incompatible metasprite frame

- **Category:** Semantic Analysis
- **Explanation:** A metasprite instance owns OAM capacity for all frames in
  its creation asset. A frame from another asset cannot be selected safely.
- **Trigger:** Compile
  `tests/fixtures/diagnostics/incompatible_metasprite_frame.nsp` with both
  referenced assets configured.
- **Expected compiler output:** `E3055` names the instance and frame assets.
- **Suggested fix:** Select a frame from the same asset used at creation.

## E3056 - Invalid metasprite animation

- **Category:** Semantic Analysis
- **Explanation:** `nes.metasprite_set_animation` requires one imported,
  symbolic animation belonging to the instance's creation asset. Animation
  names are compiler-only symbols and cannot be replaced with numeric values.
- **Trigger:** Compile
  `tests/fixtures/diagnostics/invalid_metasprite_animation.nsp`, or pass a
  statically known animation from another asset.
- **Expected compiler output:** `E3056` identifies the non-symbolic or
  incompatible animation selection.
- **Suggested fix:** Pass a symbol such as `player.movement_right` from the
  same imported asset used by `nes.metasprite_create`.

## E3057 - Invalid builtin context

- **Category:** Semantic Analysis
- **Explanation:** Ordinary builtins are registered as either standalone
  statements or value-producing expressions. A statement builtin cannot be
  assigned or nested in an expression, and a value builtin cannot be used as
  a standalone statement.
- **Trigger:** Compile
  `tests/fixtures/diagnostics/invalid_builtin_context.nsp`, or write
  `nes.sprite_create();` as a standalone statement.
- **Expected compiler output:** `E3057` names the builtin and its registered
  context.
- **Suggested fix:** Use statement builtins directly and consume value builtin
  results in a type-compatible expression.

## E3058 - Invalid builtin argument count

- **Category:** Semantic Analysis
- **Explanation:** The centralized builtin signature requires a fixed number
  of arguments. Builtins with an existing operation-specific count diagnostic
  retain that code; `E3058` covers ordinary signatures that did not previously
  have a dedicated diagnostic.
- **Trigger:** Compile
  `tests/fixtures/diagnostics/invalid_builtin_argument_count.nsp`.
- **Expected compiler output:** `E3058` reports the expected and provided
  argument counts.
- **Suggested fix:** Pass exactly the arguments documented for the builtin.
