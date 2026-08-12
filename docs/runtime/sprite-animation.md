# Sprite animation

English | [Português (Brasil)](../pt-BR/runtime/sprite-animation.md)

Sprite animation selects ordered metasprite frames automatically on the main
thread. It reuses the metasprite's static OAM reservation, position,
visibility, clipping, and whole-object flip state; animation never allocates
or frees hardware sprites at runtime.

The layering is deliberately one-way:

```text
asset JSON
    -> validated, origin-relative immutable metasprite frames
    -> animations store only ordered frame IDs and durations
    -> mutable playback state selects one frame ID
    -> the existing metasprite renderer expands that frame into OAM
```

Animations do not own, copy, normalize, or reinterpret component geometry,
origin, pivot, bounds, flip placement, or clipping. A frame selected manually
and the same frame selected through an animation are the same immutable frame
record and emit identical component bytes.

## Asset symbols and metadata

Each imported PNG2CHR Studio animation exposes one compile-time symbol named
`<asset>.<animation>`. Individual frames keep their existing
`<asset>.<animation>_<index>` names:

```pascal
nes.import_metasprite(player);
Player := nes.metasprite_create(player.movement_right_0);
nes.metasprite_set_animation(Player, player.movement_right);
```

The supported version-2 animation object accepts:

- `default_frame_duration`: optional duration from 1 through 255 logical game
  frames; compatibility metadata that omits it uses 1;
- `frames[].duration`: optional per-frame override from 1 through 255;
- `loop`: optional Boolean playback policy, defaulting to `true`.

NES Pascal does not infer one-shot behavior from an animation name, type, or
direction. Set `"loop": false` explicitly for a one-shot sequence. Empty
sequences, zero durations, unsupported animation fields, duplicate names,
non-Boolean loop values, and more than 255 frames in one animation produce
E6016. The combined configured program may expose at most 256 frame symbols
and 256 animation symbols.

The root `source` object is tooling provenance. NES Pascal does not open or
require its PNG path; compilation uses the animation/frame metadata and the
separately configured CHR bank. The bundled consolidated player manifest is
explicitly reanchored at `(12,12)`, with component offsets already relative to
that centered pivot. The attached exporter output used `(0,0)` plus raw
`0/8/16` coordinates, which intentionally describes a corner pivot under the
version-2 contract and would produce a hinge-like flip. The compiler does not
silently guess a centered pivot because non-centered pivots are valid.

This player exposes `player.idle` and `player.movement_right`. Its generated
mirrored `movement_left` sequence is omitted because it contains no unique
artwork; horizontal whole-metasprite flip selects facing. Games remain free to
import distinct left/right animations when artists provide distinct frames.

## Public API

```pascal
nes.metasprite_set_animation(Player, player.movement_right);
nes.metasprite_restart_animation(Player);
Finished := nes.metasprite_animation_finished(Player);
```

`nes.metasprite_set_animation` starts a different compatible animation at its
first frame with the full first-frame duration. Assigning the already-active
animation is a no-op and does not restart its timer. This makes it safe for an
update procedure to select the desired animation every frame.

`nes.metasprite_restart_animation` restarts the selected active animation at
frame zero. It does nothing before an animation has been selected.

`nes.metasprite_animation_finished` returns `true` only after a one-shot
animation has consumed the complete duration of its final frame. The final
frame remains selected. It returns `false` for active looping animations,
inactive instances, and restarted one-shot animations.

Animation symbols are compiler-only values. They cannot be stored in
variables, declared as public types, converted from bytes, or computed at
runtime. E3056 rejects a non-symbolic animation or a statically known
cross-asset pairing. When an opaque `metasprite` variable prevents that proof,
the runtime verifies the asset ID and safely ignores an incompatible pairing.

## Timing and interaction rules

The runtime advances every active animation once for each logical game frame
accepted by the frame-synchronized main loop. A duration of `D` therefore
keeps its frame selected for exactly `D` logical game frames. Advancement runs
after controller polling and before the registered `nes.on_update` procedure,
never in NMI. If a slow update crosses multiple NMIs, the existing newest-frame
coalescing policy applies; animation does not replay a backlog.

Changing frames automatically reruns the existing metasprite renderer. Frames
may have different component counts and layouts. Any no-longer-used reserved
OAM slots are hidden, while position, visibility, and horizontal/vertical
whole-object flips remain unchanged.

Hiding a metasprite affects OAM publication only: its animation timer continues
to advance. Showing it later renders the then-current frame. Manual
`nes.metasprite_set_frame` selection deliberately disables automatic playback;
call `nes.metasprite_set_animation` to start it again.

## ROM and RAM cost

Animation metadata is immutable PRG-ROM data. Each linked animation adds five
table bytes (low/high sequence pointer, frame count, loop flag, and asset ID)
plus two bytes per animation frame (frame ID and duration). Existing frame
component geometry is referenced by ID and is not duplicated. Animation
runtime routines are feature-linked only when an animation operation or
completion query is used.

Static metasprites retain the milestone-0.5.3 RAM cost of four regular bytes
per instance plus eight shared renderer scratch bytes. An animation-using
program adds four regular bytes per instance: selected animation, animation
frame index, timer, and playback flags. Its total metasprite regular-RAM cost
is therefore `8N + 8` bytes. The two shared two-byte Zero Page renderer
pointers and the OAM reservation do not grow.

## Example

Build the supplied animated player with:

```text
python -m nes_pascal.cli examples/sprite_animation.nsp -o build/sprite_animation.nes --chr assets/game.chr --metasprite assets/player_consolidated.json
```

The D-pad moves in all eight directions. Stationary updates select
`player.idle`; moving updates select `player.movement_right`. Horizontal flip
is the independent facing state, so stopping or moving vertically preserves
the last left/right orientation. Repeating either animation selection every
update does not restart it. A explicitly restarts playback, and Select hides
or shows the player without pausing its animation.
