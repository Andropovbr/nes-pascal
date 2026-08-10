# Assignments

English | [Português (Brasil)](..\pt-BR\language\assignments.md)

Assignment uses `:=`:

```pascal
BackgroundColor := $21;
Counter := $FF;
Enabled := true;
```

The right-hand side may be:

- a hexadecimal literal;
- `true` or `false`;
- a constant reference;
- a previously assigned variable reference;
- a `byte` arithmetic expression;
- a comparison or Boolean expression whose result is `boolean`.

Both sides must have exactly the same type. There are no implicit conversions.
Reading a variable before an earlier assignment is a compilation error.
Constants cannot be assignment targets.

Value parameters are initialized local copies and may also be assignment
targets inside their declaring procedure. Assigning a parameter does not
modify the caller's argument.

Definite-assignment analysis follows structured control flow. The detailed
rules for branches, loops, and procedure calls are documented with those
constructs.

Assignment diagnostics preserve the earliest primary error:

- E4002 reports a `nes_color` value outside `$00..$3F`;
- E4004 reports incompatible source and target types, including hexadecimal
  literals assigned to `boolean`;
- E3008 reports a variable read before assignment.

Whole-program checks such as E3003 run only after statement-level semantic
analysis succeeds. See the
[diagnostics reference](../reference/diagnostics/index.md) for the complete
index, explanations, examples, and suggested fixes.

Initialized `byte` variables can also be changed with
[`inc` and `dec`](increment-and-decrement.md).
