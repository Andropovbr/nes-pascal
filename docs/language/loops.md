# Loops

NES Pascal supports `while`, `repeat`/`until`, and ascending or descending
`for` loops. Loops may be nested.

## `while`

`while` checks a `boolean` condition before each iteration:

```pascal
while Counter < Limit do
    Counter := Counter + $01;
```

A compound body uses `begin` and `end`:

```pascal
while Running do
begin
    Counter := Counter + $01;
    Running := Counter < Limit;
end;
```

## `repeat` / `until`

`repeat` executes its body before checking its `boolean` condition, so the
body runs at least once:

```pascal
repeat
    Counter := Counter - $01;
until Counter = $00;
```

## `for`

An ascending `for` loop includes both bounds:

```pascal
for Index := $00 to $03 do
    inc(Total);
```

A descending loop uses `downto`:

```pascal
for Index := $03 downto $00 do
begin
    inc(Total, $02);
end;
```

The control variable, initial expression, and final expression must all have
type `byte`. The compiler assigns the initial value before evaluating and
caching the final value. The final expression is evaluated exactly once. The
body may be a single statement or a `begin`/`end` block, and `for` loops may be
nested.

The control variable is definitely assigned after the loop, even when the
initial range is empty, because initialization occurs before the first range
check. A non-empty loop that completes normally leaves it at the final value;
an empty range leaves it at the initialized value. Assigning the control
variable, applying `inc` or `dec` to it, or reusing it as a nested loop's
control variable produces E3012.

Endpoint checks occur before increment or decrement, so `$FF` for `to` and
`$00` for `downto` terminate without wrapping into another iteration.

## `break` and `continue`

`break` exits the nearest enclosing loop. `continue` transfers control to the
nearest loop's next condition check. In a `for` loop, `continue` advances to
the next control-variable value.

```pascal
while Counter < Limit do
begin
    Counter := Counter + $01;
    if Counter = SkipValue then
        continue;
    if Counter = StopValue then
        break;
end;
```

Using either statement outside a loop produces E3010. In nested loops,
`break` and `continue` always target the innermost loop.

## Definite assignment

Definite-assignment analysis is intentionally conservative. Assignments made
only inside a loop are not considered guaranteed after the loop because a
`while` body may not execute and loop control may skip statements. Assign
values before entering a loop when they are needed afterward or in a `repeat`
condition.

The `for` control variable is the exception: its initialization is guaranteed
before the first range check.

## Runtime restrictions

NES initialization commands cannot be placed inside loops. Doing so produces
E3011. Loops execute only during startup before `nes.run`; they are not
frame-based loops and cannot implement timed gameplay behavior.

## Generated control flow

The backend uses absolute jumps for loop back edges and exits, with relative
branches targeting only nearby labels. Large and nested loop bodies therefore
do not depend on the 6502 relative-branch range. The same nearby-branch and
absolute-jump pattern keeps large `for` bodies valid.
