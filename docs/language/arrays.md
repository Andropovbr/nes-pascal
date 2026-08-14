# Arrays

English | [Português (Brasil)](../pt-BR/language/arrays.md)

NES Pascal supports fixed-size, one-dimensional global arrays. Arrays are
compiler-managed static storage: there is no heap, descriptor, length field,
runtime allocator, or generic array runtime.

## Declaration

Array bounds use the language's hexadecimal byte literals:

```pascal
var
    Values: array[$00..$0F] of byte;
    Flags: array[$00..$07] of boolean;
```

The lower bound is always `$00`. The inclusive upper bound may be `$00`
through `$FF`, so one declaration contains between 1 and 256 elements. Only
`byte`, `boolean`, and declared [record](records.md) elements are supported.
Arrays may be declared only in the global `var` section; they cannot be
constants, local variables, parameters, or return values.

Each scalar element occupies one byte. Boolean elements use the same canonical
storage as scalar booleans: `false` is `$00` and `true` is `$01`. Boolean
arrays are not bit-packed. Consequently:

- `array[$00..$0F] of byte` consumes exactly 16 bytes of RAM;
- `array[$00..$07] of boolean` consumes exactly 8 bytes of RAM.

A record element occupies its record's compile-time size. Field access folds
or calculates `index * record size + field offset`; see
[Records](records.md) for the addressing and offset limits.

The compiler allocates each array as one deterministic, contiguous regular-RAM
range and shows that range and type in the generated memory map. Arrays are not
automatically promoted to Zero Page.

## Reading and writing elements

An array element is a typed expression with the array's element type:

```pascal
Values[$00] := $10;
Values[Index] := Counter + $01;
Counter := Values[Index] + $01;

Flags[$00] := true;
if Flags[Index] then
    Counter := Counter + $01;
```

The index must have type `byte`; `boolean` indexes and implicit conversions are
rejected. Assignments also require an exact element-type match.

An indexed assignment evaluates its index before its value. For a variable
index, the backend preserves that index on the hardware stack while evaluating
the value, then uses native 6502 indexed addressing. This does not reserve an
array-specific Zero Page byte.

As with scalar variables, reading an array before any preceding element
assignment is rejected by definite-assignment analysis. The compiler does not
attempt per-element initialization proofs; a program remains responsible for
assigning every element it later reads.

## Bounds checks and addressing

A constant index, including a byte constant expression that the compiler can
evaluate, is checked against the declared bounds at compile time. A known
out-of-range access produces E4012. The element address is then computed at
compile time, for example:

```asm
    lda variable_Values + 3
```

A non-constant byte index is not checked at runtime. It normally uses native
absolute indexed addressing:

```asm
    lda variable_Index
    tax
    lda variable_Values,x
```

Programs must ensure that variable indexes stay inside the declared range.
There is no runtime bounds metadata or generated bounds-checking routine.

## Current limitations

Dynamic, open, multidimensional, local, parameter, returned, enum-element, and
bit-packed arrays are not supported. Arrays cannot be assigned or compared as
whole values, and no pointer or slicing operations exist.
