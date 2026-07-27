# Conditional statements

An `if` condition must have type `boolean`. A conditional may contain one
statement:

```pascal
if Enabled then
    Counter := $01;
```

The optional `else` branch follows Pascal semicolon placement. There is no
semicolon between the final statement of the `then` branch and `else`; one
semicolon terminates the complete conditional:

```pascal
if Enabled then
    Counter := $01
else
    Counter := $02;
```

Use `begin` and `end` for a branch containing multiple statements:

```pascal
if Enabled then
begin
    Counter := Counter + $01;
    Ready := true;
end
else
begin
    Counter := $00;
    Ready := false;
end;
```

Conditionals may be nested. An `else` without an enclosing branch block
belongs to the nearest unmatched `if`.

## Definite assignment

Definite-assignment analysis follows control flow. A variable assigned in both
branches of an `if/else` is assigned afterward. An assignment made only in the
`then` branch, or in an `if` without `else`, is not guaranteed afterward.

## Runtime restrictions

[`nes.set_background_color`](../runtime/set-background-color.md) and
[`nes.run`](../runtime/run.md) are initialization commands and must remain in
the top-level program block. Placing either command inside a conditional
produces E3009.

## Generated control flow

The backend emits a nearby relative branch followed by an absolute `JMP`.
This keeps conditional branches valid even when a branch body exceeds the
6502 relative-branch range.
