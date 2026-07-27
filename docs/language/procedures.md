# Procedures

Procedure declarations appear after global variables and before the main
program block. Procedures have no parameters or return values:

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

## Name resolution and calls

Calls are case-insensitive. Constants, variables, and procedures share one
global namespace. Every procedure is registered before any body is analyzed,
so a procedure may call one declared later in the source:

```pascal
procedure Start;
begin
    Initialize;
end;

procedure Initialize;
begin
    Counter := $00;
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

The basic calling convention uses the 6502 hardware stack: calls generate
`JSR` and every procedure ends with `RTS`. Procedures have global ca65 entry
labels such as `procedure_Initialize`; control-flow labels inside them use
ca65 cheap-local `@` labels. Registers are not part of the source-language
interface and are not guaranteed to be preserved.

Recursion is forbidden, and no stack frame, local variables, parameters, or
return value exist.

## Runtime restrictions

NES initialization commands remain exclusive to the main block. Using
`nes.set_background_color` or `nes.run` inside a procedure produces E3015.
