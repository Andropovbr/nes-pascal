---
name: language-feature-check
description: Impact checklist for adding or changing an NES Pascal language feature without forgetting compiler stages, tests or public contracts.
---

For the requested feature, mark only applicable items:

- lexical tokens/keywords?
- grammar/parser?
- AST representation?
- name/scope resolution?
- type/semantic rules?
- constant evaluation?
- memory representation/layout?
- backend lowering?
- runtime helper/builtin?
- NES hardware contract?
- diagnostics and diagnostic catalog?
- positive tests?
- negative tests?
- boundary tests?
- golden Assembly?
- ca65/ld65 integration?
- Mesen runtime test?
- example program?
- canonical docs?
- translated docs maintained for that page?
- roadmap status/checklist?

Do not force every layer to change. The goal is to avoid omissions, not create boilerplate.

If public semantics are unclear, stop and route to `professor_carvalho`.
If architecture across stages is unclear, route to `seu_camilo`.
If lowering is unclear, route to `relampago_marquinhos`.
If hardware runtime behavior is unclear, route to `mestre_ppu`.
