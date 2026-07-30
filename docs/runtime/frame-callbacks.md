# Frame callbacks

NES Pascal supports one static callback for normal per-frame update logic and
one static callback for restricted VBlank work:

```pascal
procedure Update;
begin
    inc(UpdateFrames);
end;

procedure VBlank;
begin
    inc(VBlankFrames);
end;

begin
    UpdateFrames := $00;
    VBlankFrames := $00;
    nes.set_background_color($21);
    nes.on_update(Update);
    nes.on_vblank(VBlank);
    nes.run;
end.
```

Both registrations must be unconditional top-level initialization statements
before `nes.run`. The argument is a direct procedure identifier resolved at
compile time, and the procedure must have no parameters or return value. At
most one callback of each kind is supported. A procedure cannot serve as both
callbacks. Registration emits no function pointer, callback table, or runtime
registration state.

## Update callback

The compiler's implicit runtime loop waits for the volatile 8-bit frame
counter to change, calls the update procedure once with direct `JSR`, then
repeats. The counter may wrap from `$FF` to `$00`; equality-based change
detection remains valid. Update executes in normal main context, never in NMI,
and may use ordinary supported language operations and acyclic procedures.

The loop establishes `runtime_last_processed_frame` once when it starts. For
each iteration it compares the current authoritative frame counter with that
persistent byte. When they differ, it stores the newest counter value before
calling `Update`. It does not take a fresh baseline after the callback returns.

This defines the slow-frame policy:

- only one update callback runs at a time; calls are never concurrent, nested,
  or made from NMI;
- an NMI that occurs during `Update` remains visible because it changes
  `runtime_frame_counter` without changing `runtime_last_processed_frame`;
- after `Update` returns, the loop immediately accepts the newest pending
  frame instead of waiting for another NMI;
- several frames missed by one slow callback are coalesced into one newest
  pending update rather than replayed as a large backlog;
- the loop waits only when the current and last-processed counters match.

Because synchronization uses an 8-bit counter, a callback that remains active
for 256 or more NMIs can make the counter equal the stored value again. Such a
callback exceeds the observable synchronization window; cycle-budget analysis
is intentionally outside this milestone.

Programs without an update callback retain the existing implicit stable idle
loop. Explicit main-thread statements after `nes.run` still execute before the
implicit update or idle loop.

## VBlank callback

NMI always preserves A, X, and Y first. It then increments
`runtime_frame_counter`, sets the advisory `runtime_frame_ready` byte, and
calls the VBlank procedure with direct `JSR`. The callback and any safe helper
end with `RTS`; NMI restores registers and ends with `RTI`. This ordering is
fixed and deterministic.

`runtime_frame_ready` is a best-effort advisory latch. NMI sets it, and a
main-thread frame wait or accepted update clears it. A race may make the latch
stale, so neither `nes.wait_frame` nor the callback loop uses it to decide
whether a frame is pending. `runtime_frame_counter` remains authoritative.

Once a pending frame is accepted, the runtime copies current controller state
to previous state and reads ports 1 and 2 exactly once before calling `Update`.
The guarded polling abstraction is shared with `nes.wait_frame`; see
[Controller input](controller-input.md).

VBlank code is intentionally conservative. The compiler transitively validates
every reachable procedure. The supported subset is:

- scalar assignments whose expressions need no shared compiler temporary;
- `inc(Target)` and `dec(Target)` without an amount;
- `if` statements with temporary-free conditions and safe branches;
- calls to parameterless procedures whose complete call graphs satisfy the
  same rules.

Arithmetic and comparison expressions, update amounts, all loops,
`nes.wait_frame`, `nes.run`, registration commands, parameterized calls,
recursion, and calls into the update callback are rejected. VBlank inputs must
be assigned before `nes.run` enables NMI. This milestone performs no cycle
budget analysis and provides no generic event or PPU command queue.

`nes.wait_frame` is also rejected inside an update callback because runtime
commands cannot appear in procedures. Registering one procedure for both
update and VBlank is rejected with E3025: the two execution contexts have
different safety rules and sharing one entry point would be ambiguous.
