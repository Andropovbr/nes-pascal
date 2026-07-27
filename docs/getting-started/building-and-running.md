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
```

The examples demonstrate:

- `arithmetic.nsp`: unary and binary byte arithmetic;
- `boolean_expressions.nsp`: comparisons and Boolean operators;
- `conditionals.nsp`: simple, compound, and nested branches;
- `loops.nsp`: counting, nested control flow, `break`, and `continue`;
- `counting.nsp`: wrapping `inc` and `dec`, ascending and descending `for`
  loops, exact `$00` and `$FF` endpoints, and nested loops;
- `procedures.nsp`: forward procedure resolution, nested calls, shared global
  state, `JSR`/`RTS`, and a conditional inside a procedure.

The loop example selects background color `$21` when its expected final state
is reached. The counting example does the same only when all expected counter
values are reached.

The `Makefile` shortcut builds the minimal program:

```text
make rom
```

Generated ROMs use the format described in
[Target platform](../runtime/target-platform.md).

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
