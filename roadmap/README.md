# NES Pascal roadmap

This index is the canonical source for roadmap navigation and milestone
progression. Do not infer the current or next milestone from numbering alone.

## Current roadmap state

- **Current release:** Release 0.3 — NES Runtime
- **Last completed milestone:** [`0.3.2 — Zero-Page Allocation`](0.md#zero-page-allocation)
- **Next milestone:** [`0.3.3 — NMI and Frame Synchronization`](0.md#nmi-and-frame-synchronization)
- **Next milestone file:** [Version 0 roadmap](0.md#nmi-and-frame-synchronization)

## Philosophy

The compiler evolves through small, testable milestones.

Each milestone must produce a working compiler capable of generating a valid NES ROM.

The initial product scope is intentionally limited to:

* NROM games
* 32 KiB PRG-ROM
* 8 KiB CHR-ROM
* No bank switching
* No additional sound chips
* Single-screen games
* Simple arcade-style gameplay
* One or two controllers
* Backgrounds, sprites, collision detection, sound effects and music

Features outside this scope may be introduced after the first usable release.

## Major-version roadmaps

1. [Version 0](0.md) — Releases 0.1 through 0.8
2. [Version 1](1.md) — Release 1.0
3. [Version 2](2.md) — no formal release milestones currently defined
4. [Version 3](3.md) — no formal release milestones currently defined
5. [Future roadmap](future.md) — post-1.0 areas without release-scoped milestones

## Milestone progression

- Read this index before beginning milestone work.
- Use the explicit current and next milestone declarations above.
- Open the linked major-version file and implement only the requested milestone.
- A partially completed later milestone does not become the next milestone unless
  this index explicitly identifies it.
- After completing a milestone, update its checklist and status in the
  major-version file, then update the current, last-completed, and next entries
  in this index.
- Do not silently add work to later milestones, remove planned work, or move work
  between releases. Propose those changes separately.

## Milestone identifier stability

- Milestone numbering is scoped to its release.
- The milestone title and its lowercase kebab-case Markdown anchor are the stable
  identity.
- Do not rely on historical global milestone numbers.
- Planned milestones may be renumbered within their release when necessary.
- Completed milestones are stable history and must not be renumbered, reordered,
  moved, or have their scope changed without explicit user approval.
- The `Formerly` metadata preserves the historical global number during the
  migration.

## Adding or reorganizing planned milestones

- Add a milestone to the appropriate release in the corresponding major-version
  file.
- Give it the next release-scoped identifier for its current position.
- Choose a unique title whose generated Markdown anchor is lowercase kebab-case.
- Update this index when the current or next milestone changes.
- When planned milestones are reorganized, update their identifiers and links but
  preserve their titles, checklist content, and release boundaries unless a
  separate scope change is explicitly approved.
- Never reorganize completed milestones without explicit user approval.
