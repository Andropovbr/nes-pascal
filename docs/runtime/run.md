# `nes.run`

`nes.run` completes initial configuration and keeps the program running:

```pascal
nes.run;
```

It must:

- appear exactly once;
- be the final statement in the main program block;
- remain outside conditionals, loops, and procedures.

No statement may appear after it because control transfers to the runtime's
stable main loop. During the transition, the runtime completes the supported
initial configuration and enables rendering.

The stable loop is not a frame-based execution model. The runtime does not yet
provide per-frame callbacks or timed gameplay behavior.
