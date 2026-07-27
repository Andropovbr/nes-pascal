# Increment and decrement

`inc` and `dec` update an initialized `byte` variable. The one-argument forms
add or subtract one:

```pascal
inc(Counter);
dec(Counter);
```

An optional `byte` expression specifies the amount:

```pascal
inc(Counter, Step);
dec(Counter, Step + $01);
```

Updates wrap modulo 256, like other `byte` arithmetic. Incrementing `$FF`
produces `$00`; decrementing `$00` produces `$FF`. The one-argument forms
generate the 6502 `INC` and `DEC` instructions directly.

The target must already be assigned because an update reads its previous
value. The target and optional amount must have type `byte`; incompatible uses
produce E4004.

An initialized `byte` value parameter may be used as the target. The update
changes only the procedure's local parameter copy.

A `for` loop's control variable cannot be changed with `inc` or `dec` inside
that loop body. See [`for` loops](loops.md#for).
