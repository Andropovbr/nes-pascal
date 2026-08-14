# Functions

English | [Português (Brasil)](../pt-BR/language/functions.md)

Functions are named, statically allocated routines that return one `byte` or
`boolean` value. Declarations appear with procedures after the global `var`
section and before the main block.

```pascal
function Add(Left: byte; Right: byte): byte;
begin
    Add := Left + Right;
end;

function Ready(Value: byte): boolean;
begin
    Ready := Value >= $10;
end;
```

Parameters are value parameters of type `byte` or `boolean`. A parameterless
declaration omits the parameter list:

```pascal
function CurrentScore: byte;
begin
    CurrentScore := Score;
end;
```

Every call uses parentheses, including a parameterless call:

```pascal
Score := Add(CurrentScore(), $01);
Enabled := Ready(Score);
```

The function name is its result target. It must be assigned a value of the
declared return type on every path that reaches the end of the body. There is
no early `return` statement. A function result may be read only after an
assignment in the same body.

## Evaluation order

Function arguments are evaluated from left to right. `and` and `or` also keep
their documented left-to-right short-circuit behavior, so a function call in a
skipped operand does not execute.

Binary arithmetic and comparisons preserve the existing NES Pascal lowering
order. A simple literal or direct-memory right operand is consumed after the
left operand. When the right operand itself requires evaluation, it is
evaluated first and preserved while the left operand is evaluated. Therefore,
in `LeftCall() - RightCall()`, `RightCall()` executes first.

## Calling convention and limits

Parameters use the same static regular-RAM convention as procedures. A return
value is loaded into the 6502 accumulator (`A`) immediately before `RTS`.
Each declared function receives one explicit regular-RAM backing byte for its
result; programs without functions allocate no result bytes, function segment,
or function code.

Calls may clobber `A`, `X`, `Y`, and processor flags. No general-purpose
register is callee-saved; only compiler-managed temporary storage and the
static parameter/result locations carry values across a call. `JSR` return
addresses use the reserved hardware stack, which is balanced again by `RTS`.

The compiler analyzes the complete acyclic call graph. Caller-owned expression
temporaries remain leased across nested calls, and an earlier argument is
preserved when a later argument can call a function. This prevents nested calls
from aliasing either the expression pool or static parameter slots.

Direct recursion, indirect function recursion, and mixed procedure/function
cycles are rejected with `E3014`. Functions have no local variable section,
runtime stack frame, reference parameters, default arguments, overloads, or
aggregate return values. Functions cannot be registered as frame callbacks.

See [the functions example](../../examples/functions.nsp).
