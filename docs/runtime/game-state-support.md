# Game-state support

English | [Português (Brasil)](../pt-BR/runtime/game-state-support.md)

NES Pascal game states are ordinary, explicit language-level control flow. The
recommended pattern combines a nominal enum, one global state variable,
state-entry procedures, per-frame update procedures, and one `nes.on_update`
dispatcher. There is no state keyword, hidden registry, callback table, scene
manager, or state-machine runtime.

The complete reference is
[`examples/game_state.nsp`](../../examples/game_state.nsp). Build it with:

```text
python -m nes_pascal.cli examples/game_state.nsp -o build/game_state.nes --chr assets/chr_asset.chr
```

## Represent states with an enum

```pascal
type
    GameState = (Title, Playing, Paused, GameOver);

var
    State: GameState;
```

Enums make each state readable, strongly typed, and checked at compile time.
They need no runtime metadata, and `State` occupies exactly one byte. A `byte`
with magic values would lose nominal typing without saving RAM.

The members use their declaration-order representation: `Title = $00`,
`Playing = $01`, `Paused = $02`, and `GameOver = $03`. These byte values are an
implementation detail for generated code and tests; source should use the
member names.

## Dispatch one state per frame

The registered update procedure explicitly selects one handler:

```pascal
procedure Update;
begin
    if State = Title then
    begin
        UpdateTitle;
    end
    else if State = Playing then
    begin
        UpdatePlaying;
    end
    else if State = Paused then
    begin
        UpdatePaused;
    end
    else if State = GameOver then
    begin
        UpdateGameOver;
    end;
end;
```

Only the handler selected at the start of that call runs. A transition made by
one handler cannot also execute the newly selected handler in the same frame.
The four-state dispatcher lowers to ordinary direct comparisons and branches;
the measured core is 58 PRG bytes, 24 instructions, and 79 static base cycles
when every emitted instruction is counted once. Dynamic cost depends on which
comparison succeeds. No generic dispatcher hides this cost.

Representative generated Assembly is direct and readable:

```asm
lda variable_State
cmp #$01
beq @if_then
jmp @if_else
@if_then:
jsr procedure_UpdatePlaying
```

## Separate entry from update

Use `EnterX`, `StartX`, `PauseX`, or `ResumeX` procedures for one-time setup,
and `UpdateX` procedures for per-frame work. The release convention is:

1. perform all setup and reset side effects;
2. assign `State` last;
3. return to the dispatcher.

For example, `StartGame` calls `ResetGameplay`, increments the persistent
session counter, configures the player sprite and background, and assigns
`State := Playing` last. These helpers compile through the ordinary `JSR`/`RTS`
procedure machinery. Avoid transition helpers that call each other in cycles;
the normal recursion diagnostic still applies.

## Reference lifecycle

The example implements these four observable states:

- **Title:** background color `$21`, player sprite hidden, and no gameplay
  updates. A Start press calls `StartGame`.
- **Playing:** the D-pad moves the player, while `Score` and `GameplayTicks`
  advance. The Boolean Function `ShouldEndGame()` enters `GameOver` when
  `Health` reaches zero; B provides the example's deterministic damage trigger.
  Start calls `PauseGame` before normal gameplay work.
- **Paused:** the frame loop, NMI, rendering, and controller sampling continue,
  but the handler changes no player or gameplay variables. A new Start press
  calls `ResumeGame`.
- **GameOver:** the player is hidden and normal gameplay remains stopped. A
  Start press calls `StartGame` for a new run.

Use `nes.controller_pressed` for Start transitions. It is true only on the
edge from released to held, so holding one press cannot start and immediately
pause, or pause and immediately resume. `controller_down` remains appropriate
for continuous D-pad movement.

## Explicit gameplay restart

`ResetGameplay` restores only game-owned mutable data:

| Variable | Restart value |
| --- | ---: |
| `PlayerX` | `$78` |
| `PlayerY` | `$70` |
| `Health` | `$03` |
| `Score` | `$00` |
| `GameplayTicks` | `$00` |
| `InitialRandom` | `$15`, after explicit seed `$2A` |

The example deliberately reseeds the PRNG in `ResetGameplay`, making each run
deterministic. A real game may instead omit `nes.seed_random` and continue the
current random stream; restarting gameplay never resets the PRNG implicitly.

`SessionStarts` is intentionally persistent across gameplay restarts. It is
initialized once at boot and incremented for each new run, but it is not part
of `ResetGameplay`. Real games commonly preserve high scores, options, sound
settings, and session counters while resetting player, enemy, score, timer,
spawn, animation, and gameplay-flag state.

Restart does not jump to the RESET vector, restart the ROM, snapshot or restore
RAM, or reinitialize NES hardware, PPU/controller infrastructure, compiler
runtime allocation, or persistent game data. The compiler cannot infer which
variables a game owns, so explicit user code keeps both semantics and cost
predictable.

Initialization also remains visible in source:

```pascal
begin
    SessionStarts := $00;
    ResetGameplay;
    EnterTitle;
    nes.set_background_color($21);
    nes.on_update(Update);
    nes.run;
end.
```

## Resource cost and validation

The dedicated `game_state` benchmark measures the complete sample, including
controller polling, palette queuing, one hardware sprite, and explicitly
seeded RNG:

| Metric | Measured value |
| --- | ---: |
| PRG code | 1,268 B |
| PRG occupied | 1,274 B |
| Instructions | 567 |
| Estimated static base cycles | 1,876 |
| Expression tree depth | 1 |
| Maximum live temporaries | 0 |
| Maximum source call depth | 4 |
| Source-call stack peak | 8 B |
| User variables | 8 B: 4 ZP + 4 regular RAM |
| Function-result storage | 1 B regular RAM |

Only one of those eight user bytes is the enum state. The runtime allocations
shown by the benchmark belong to existing controller, palette, sprite, and RNG
features; hidden game-state-manager RAM remains **0 B**. Programs that do not
use the example gain no code or data.

Focused compiler tests freeze direct enum comparisons, ordinary transition
calls, state assignment after setup, and the absence of a generic dispatcher.
The deterministic Mesen test executes `Title -> Playing -> Paused -> Playing ->
GameOver -> Playing`, injects distinct press/release edges, proves gameplay is
frozen while frame processing continues, verifies exact reset values, and
checks `SessionStarts = 2` after restart as evidence that the ROM was not reset.

For a larger game, keep handlers small and factor ordinary procedures by
subsystem. A chained dispatcher is intentionally the official initial pattern;
this release adds no jump table, state stack, scene lifecycle, event bus, or
dynamic state registration.
