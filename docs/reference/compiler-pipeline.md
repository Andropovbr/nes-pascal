# Compiler pipeline

The compiler pipeline is deliberately separated:

```text
.nsp source
  -> lexer
  -> parser
  -> AST
  -> semantic validation, name resolution, and type checking
  -> resolved AST
  -> ca65 backend
  -> ca65
  -> ld65
  -> ROM
```

## Components

- `lexer.py` produces tokens with line and column information;
- `parser.py` validates grammar and builds the parsed AST in `ast.py`;
- `semantic.py` validates declarations, resolves references and procedure
  calls, checks exact types, and enforces interprocedural definite assignment;
- `backend_ca65.py` generates readable, commented Assembly from resolved
  values, allocates variables and value-parameter slots in regular CPU RAM,
  and emits left-to-right argument copies before procedure calls;
- `cli.py` writes Assembly and coordinates ca65 and ld65;
- `nrom.cfg` defines the 32 KiB PRG and 8 KiB CHR NROM layout.

Source text is not translated directly to Assembly with string replacement.
The compiler uses explicit parsed and resolved AST nodes between parsing and
code generation.

Ordinary source errors are displayed without a Python stack trace and include
an error code, file, line, column, source excerpt, and correction hint when
useful. See the [diagnostics reference](diagnostics/index.md).
