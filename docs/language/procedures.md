# Procedures

English | [Português (Brasil)](..\pt-BR\language\procedures.md)

Procedure declarations appear after global variables and before the main
program block. A parameterless procedure omits parentheses:

```pascal
procedure Initialize;
begin
    Counter := $00;
end;
```

A call is the procedure name followed by a semicolon:

```pascal
begin
    Initialize;
    nes.set_background_color($21);
    nes.run;
end.
```

## Value parameters

Procedures may declare one or more value parameters. Each parameter declares
one name and uses either `byte` or `boolean`; semicolons separate parameters:

```pascal
procedure Initialize(Start: byte; Enabled: boolean);
begin
    Counter := Start;
    RenderingEnabled := Enabled;
end;
```

Calls place comma-separated argument expressions in parentheses:

```pascal
Initialize($01 + $02, true);
```

The number and types of arguments must exactly match the declaration. E3016
reports an incorrect argument count, E4004 reports an incompatible argument
type, and E4005 rejects parameter types other than `byte` and `boolean`.
Empty parentheses are not valid: write `Reset;` rather than `Reset();` for a
parameterless declaration or call.

Arguments are evaluated from left to right and copied into one-byte,
procedure-specific RAM slots before `JSR`. A value parameter is initialized
on entry and may be assigned or updated inside its procedure. Such changes
modify only the procedure's copy; there is no pass-by-reference mode.

Parameter names are case-insensitive and must be unique within their
procedure. They may be reused by different procedures, but they cannot shadow
a global constant, variable, or procedure name in the current milestone.

## Name resolution and calls

Calls are case-insensitive. Constants, variables, and procedures share one
global namespace. Parameters form procedure-specific local scopes. Every
procedure signature is registered before any body is analyzed, so a procedure
may call one declared later in the source:

```pascal
procedure Start(Value: byte);
begin
    Initialize(Value);
end;

procedure Initialize(Value: byte);
begin
    Counter := Value;
end;
```

Procedures may call other procedures to any acyclic depth. E3013 reports an
unknown call. E3014 rejects both direct and indirect recursion.

## Global state and definite assignment

All variables are global. Semantic analysis computes the variables each
procedure requires on entry and those it definitely assigns. A call is
rejected with E3008 when a required global variable is not assigned. Variables
definitely assigned by a procedure are available to following statements in
the caller. Conditional and loop assignment rules remain conservative across
procedure boundaries.

## Calling convention

The basic calling convention uses the 6502 hardware stack: calls store each
argument in its static parameter slot, generate `JSR`, and every procedure
ends with `RTS`. Parameters use labels such as
`parameter_Initialize_Value`. Procedures have global ca65 entry labels such
as `procedure_Initialize`; control-flow labels inside them use ca65 cheap-local
`@` labels. Registers are not part of the source-language interface and are
not guaranteed to be preserved.

Static parameter storage is safe because direct and indirect recursion remain
forbidden. No stack frame, general local variables, reference parameters, or
return value exists.

## Runtime restrictions

`nes.run`, `nes.wait_frame`, and registration commands remain exclusive to the
main block. Palette calls, including `nes.set_background_color`, are allowed in
procedures and stage changes for VBlank. Callback registration inside a
procedure produces E3022. Parameterless procedures may be registered as the
update or VBlank callback under the rules in
[Frame callbacks](../runtime/frame-callbacks.md).
