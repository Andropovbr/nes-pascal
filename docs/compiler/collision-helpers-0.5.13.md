# Collision Helpers Implementation and Measurements (0.5.13)

English | [Português (Brasil)](../pt-BR/compiler/collision-helpers-0.5.13.md)

Milestone 0.5.13 adds lightweight, query-only collision support on top of the
existing record, builtin, sprite, metasprite, function, and asset
infrastructure. `nes_rect` is a canonical predefined `RecordType`, not a new
scalar. Collision calls resolve to stable `BuiltinId` values with explicit
semantic hooks, backend emitters, and runtime dependencies.

## Lowering and memory

Point/rectangle and rectangle/rectangle calls load direct record addresses
through one feature-gated two-byte Zero Page pointer. Ten shared regular-RAM
bytes hold two rectangles and a point/instance input. Runtime validators use
carry-aware widened ends: logical end 256 is valid, larger ends and zero-area
boxes return false. Axis overlap uses unsigned start distances, so edge touch
is non-overlap without wrapped arithmetic.
Call-sensitive scalar inputs reuse the scoped expression allocator when a later
user function could execute another collision query; direct record references
remain zero-temporary operands.

Sprite bounds reuse the OAM X byte and existing logical-Y cache. Metasprite
bounds use four immutable per-frame bytes generated from either
`collision_box` metadata or compile-time component extents. Whole-object flips
transform metadata offsets around the established logical anchor. No active
collider list, per-entity descriptor, heap allocation, physics response, or
runtime geometry scan exists.

Background assets enter as 30 rows of 32 text flags. The compiler validates
and packs them into 120 PRG bytes. Runtime lookup derives a 0..119 packed byte
index directly from screen pixels, adds it to the ROM label through a 16-bit
Zero Page pointer, and tests an 8-byte mask table. Logical tile indexes above
255 are therefore covered without adding public 16-bit arithmetic. This path
does not select `BACKGROUND_GET_TILE` and never allocates its 960-byte shadow.

## Benchmarks

| Benchmark | PRG code/occupied | Instructions | Static base cycles | ZP allocated/reserved | Regular runtime/user | OAM | Max live temporaries | Collision-map payload |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `collision_rectangles` | 1,907/1,913 B | 760 | 2,510 | 17 B | 110 B | 256 B | 0 | 0 B |
| `collision_background` | 476/482 B | 161 | 530 | 11 B | 10 B | 0 B | 0 | 120 B |

The rectangle workload includes point/rect, rect/rect, individual sprite
bounds, metasprite bounds, their existing sprite runtime dependencies, and
user records/results. The background workload includes four queries, two
collision scratch bytes, the pointer symbols, 120 payload bytes, and the
shared 8-byte mask table.

All 21 pre-existing workloads retain their exact 0.5.12 PRG, instruction,
cycle, RAM, Zero Page, and temporary-pressure measurements. In particular,
`gameplay_full_stack` remains 3,350 B PRG code, 3,356 B occupied, tree depth 1,
zero live expression temporaries, 815 instructions, and 2,712 estimated static
base cycles. A minimal program contains no collision symbols, routines, or
data.

Focused compiler tests cover registry metadata, nominal record typing,
feature selection, exact RAM/ZP costs, malformed map assets, metasprite
metadata fallback/custom boxes, flip transforms, shadow independence, and
selective golden Assembly. A deterministic Mesen ROM covers point/rect,
rect/rect, edge touch, zero size, wraparound, exact-end-256, sprite bounds,
normal/flipped custom metasprite bounds, function/short-circuit interaction,
tile boundaries, out-of-screen Y, and logical map index 641.

Final local validation passed all 558 automated tests with no skips or
failures, including all 30 dedicated headless Mesen tests. The complete
23-program benchmark corpus assembled and linked, and the minimal ROM smoke
build completed with compiler version 0.5.13.

## Deliberately deferred

Physics, collision response, mutable collision maps, scrolling/world
coordinates, signed public scalar arithmetic, 16-bit public coordinates,
slopes, circles, polygons, continuous collision, pathfinding, spatial
partitioning, ECS integration, and automatic collider registration remain
outside this milestone.
