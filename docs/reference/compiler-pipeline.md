# Compiler pipeline

The compiler pipeline is deliberately separated:

```text
.nsp source + optional CHR-ROM and nametable assets
  -> lexer
  -> parser
  -> AST
  -> semantic validation, name resolution, and type checking
  -> resolved AST
  -> validated CPU memory layout
  -> ca65 backend
  -> ca65
  -> ld65
  -> ROM
```

## Components

- `lexer.py` produces tokens with line and column information;
- `parser.py` validates grammar and builds the parsed AST in `ast.py`;
- `semantic.py` validates declarations, resolves references and procedure
  calls, checks exact types, enforces interprocedural definite assignment, and
  validates controller intrinsics and the complete VBlank callback call graph.
  It also builds deterministic per-slot OAM ownership before resolving static
  `nes.sprite_create()` expressions;
- `assets.py` resolves configured paths from the source directory and validates
  raw CHR-ROM, combined nametable, and split tile/attribute byte counts;
- `memory_layout.py` owns physical RAM ranges, allocation, bounds and overlap
  checks, mandatory Zero Page storage, conservative optional promotion,
  regular-RAM fallback, ld65 configuration generation, and the human-readable
  memory map;
- `backend_ca65.py` generates readable, commented Assembly from resolved
  values using the already allocated runtime, temporary, and user symbols, and
  emits left-to-right argument copies before procedure calls. It also owns the
  initialization nametable upload, minimal NMI handler, VBlank-safe runtime
  transition, frame-counter wait sequence, persistent last-processed frame
  state, isolated serial controller reader, guarded controller polling, bounded
  background queue, confirmed tile shadow, page-aligned OAM shadow, sprite
  property helpers, OAM DMA, and direct static callback calls;
- `cli.py` writes Assembly, the generated `.cfg` linker configuration, and the
  `.map` CPU memory report before coordinating ca65 and ld65.

The linker configuration is generated from the same immutable layout object
used by the backend and map writer. There is no separately maintained static
NROM linker file or duplicate RAM-address calculation.

Source text is not translated directly to Assembly with string replacement.
The compiler uses explicit parsed and resolved AST nodes between parsing and
code generation.

Ordinary source errors are displayed without a Python stack trace and include
an error code, file, line, column, source excerpt, and correction hint when
useful. See the [diagnostics reference](diagnostics/index.md).
