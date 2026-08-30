# NES Pascal multi-agent kit

Cross-runtime layout:

```text
AGENTS.md
GEMINI.md

.agents/
  roles/
    compiler-architect.md
    language-semantics-reviewer.md
    backend-6502-reviewer.md
    nes-runtime-reviewer.md
    implementation-worker.md
    final-reviewer.md
  skills/
    caveman/
    compiler-test-check/
    language-feature-check/
    golden-assembly-check/
    diagnostic-check/
    compiler-benchmark/
    nes-compiler-runtime-check/
    roadmap-milestone-check/

.codex/
  config.toml
  agents/
    seu-camilo.toml
    professor-carvalho.toml
    relampago-marquinhos.toml
    mestre-ppu.toml
    ze-da-oficina.toml
    fiscal.toml

.gemini/
  agents/
    seu-camilo.md
    professor-carvalho.md
    relampago-marquinhos.md
    mestre-ppu.md
    ze-da-oficina.md
    fiscal.md
```

## Design

One canonical policy, shared provider-neutral roles, shared deterministic skills, thin runtime adapters.

The default implementation/review path is intentionally cheap:

`lead -> ze_da_oficina -> focused checks -> fiscal`

Expensive specialists are read-only and are invoked only for unresolved decisions:

- `professor_carvalho`: public language semantics;
- `seu_camilo`: compiler architecture;
- `relampago_marquinhos`: 6502 backend/codegen/performance;
- `mestre_ppu`: NES runtime/hardware.

Do not spawn specialists merely because a task touches their domain.

See `MIGRATION.md` before copying over an existing setup.
