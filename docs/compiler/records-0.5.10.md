# Record Implementation and Measurements (0.5.10)

English | [Português (Brasil)](../pt-BR/compiler/records-0.5.10.md)

Milestone 0.5.10 adds nominal, fixed-layout records as compiler metadata and
contiguous static storage. `RecordType` retains the name, ordered typed fields,
zero-based offsets, total size, and nominal identity. Parsed and resolved field
reads/writes remain explicit through semantic analysis, temporary analysis,
memory layout, benchmark reporting, and ca65 generation.

## Layout and lowering

- `byte`, `boolean`, and enum fields each occupy one byte with no padding.
- Standalone records and arrays of records are allocated contiguously in regular
  RAM and are excluded from automatic Zero Page promotion.
- A standalone or constant-index field becomes a direct symbol-plus-offset
  operand. A 4-byte record at index 2 uses `base + 8` before its field offset.
- Variable record-array indexes are multiplied by the compile-time record size:
  powers of two use `asl`; other sizes use local repeated addition. No generic
  multiplication runtime or permanent temporary is linked.
- Indexed writes evaluate the index first and preserve the scaled offset on the
  hardware stack across right-hand-side evaluation.
- Variable access is rejected when a selected field's maximum scaled offset can
  exceed 255. Constant indexes remain direct ca65 address expressions.

Representative lowering is:

```asm
    lda #$20
    sta variable_Player

    lda variable_Index
    asl a
    asl a
    clc
    adc #$01
    tax
    lda variable_Enemies,x
```

## Records benchmark

The `records` workload uses a 4-byte entity, a four-element entity array,
standalone record fields, enum and Boolean fields, constant/variable indexes,
field reads and writes, arithmetic, and an enum-field branch.

| Metric | Result |
| --- | ---: |
| PRG code | 389 B |
| PRG occupied | 395 B |
| Instructions | 196 |
| Estimated static base cycles | 605 |
| Expression tree depth | 2 |
| Maximum live expression temporaries | 0 |
| Fixed temporary pool reservation | 16 B |
| Temporaries/cache actually required | 0 B |
| Record storage | 20 B regular RAM |
| Other regular user storage | 1 B |
| Automatically promoted scalar storage | 2 B ZP |
| ZP benchmark allocated/reserved | 27 B |
| ZP allocator-visible free | 126 B |
| Regular allocator-visible free | 1,511 B |
| Runtime features | None |

The record array contributes 16 bytes and the standalone record 4 bytes. The
index and result scalars follow the existing promotion policy; no record,
field, descriptor, scaling cache, or runtime helper consumes Zero Page.

All 19 pre-existing benchmark workloads retain their previous PRG, instruction,
cycle, RAM, Zero Page, and temporary-pressure metrics. Programs without records
emit no record-specific storage, code, metadata, or runtime feature.

Final local validation passed 486 automated tests and the dedicated 27-test
Mesen runtime suite. The public records example assembled and linked as a valid
NROM image, and the complete benchmark corpus reconciled its 2 KiB RAM totals.

## Deliberately deferred

Nested and anonymous records, whole-record assignment/equality, record
parameters and returns, references, pointers, packed/variant records, methods,
constructors, destructors, RTTI, runtime bounds checks, multidimensional arrays,
a multiplication runtime, and temporary allocator redesign remain outside this
milestone.
