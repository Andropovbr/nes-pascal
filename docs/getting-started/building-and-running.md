# Building and running programs

## Compilation

Compile the minimal example with:

```text
python -m nes_pascal.cli examples/minimal.nsp -o build/minimal.nes
```

The repository also contains focused examples for each implemented language
area:

```text
python -m nes_pascal.cli examples/arithmetic.nsp -o build/arithmetic.nes
python -m nes_pascal.cli examples/boolean_expressions.nsp -o build/boolean_expressions.nes
python -m nes_pascal.cli examples/conditionals.nsp -o build/conditionals.nes
python -m nes_pascal.cli examples/loops.nsp -o build/loops.nes
python -m nes_pascal.cli examples/counting.nsp -o build/counting.nes
python -m nes_pascal.cli examples/procedures.nsp -o build/procedures.nes
python -m nes_pascal.cli examples/procedure_parameters.nsp -o build/procedure_parameters.nes
python -m nes_pascal.cli examples/memory_layout.nsp -o build/memory_layout.nes
```

The examples demonstrate:

- `arithmetic.nsp`: unary and binary byte arithmetic;
- `boolean_expressions.nsp`: comparisons and Boolean operators;
- `conditionals.nsp`: simple, compound, and nested branches;
- `loops.nsp`: counting, nested control flow, `break`, and `continue`;
- `counting.nsp`: wrapping `inc` and `dec`, ascending and descending `for`
  loops, exact `$00` and `$FF` endpoints, and nested loops;
- `procedures.nsp`: forward procedure resolution, nested calls, shared global
  state, `JSR`/`RTS`, and a conditional inside a procedure;
- `procedure_parameters.nsp`: typed value parameters, left-to-right argument
  copies, mutable local parameter values, and nested parameterized calls;
- `memory_layout.nsp`: globals, procedure parameters, expressions, and a
  for-loop allocated through the deterministic runtime memory layout.

The loop, counting, and procedure-parameter examples select background color
`$21` only when their expected final states are reached.

The `Makefile` shortcut builds the minimal program:

```text
make rom
```

Generated ROMs use the format described in
[Target platform](../runtime/target-platform.md).

Each command also writes a generated ld65 configuration beside the ROM using
the `.cfg` suffix and a human-readable CPU RAM report using `.map`. The map
lists reserved, runtime, compiler, user, and free regions plus the address of
every source variable and value parameter. See [CPU memory](../runtime/cpu-memory.md).

## Running in Mesen

1. Generate `build/minimal.nes`.
2. Open Mesen.
3. Select **File > Open** and choose `build/minimal.nes`.
4. The display should remain stable with universal background color `$21`.

## Cleaning generated files

Remove build artifacts with:

```text
make clean
```
