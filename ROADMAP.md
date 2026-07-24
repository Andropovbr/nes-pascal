# nes-pascal Roadmap

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

---

# Release 0.1 — Language Foundations

Goal: compile small Pascal programs into valid NES ROMs and support basic calculations and state.

## Milestone 1 — Minimal Compiler

* [x] Parse a minimal Pascal program
* [x] Generate a valid iNES ROM
* [x] Generate NROM-256 output
* [x] Generate startup code
* [x] Generate interrupt vectors
* [x] Initialize the NES hardware
* [x] `nes.set_background_color()`
* [x] `nes.run`

## Milestone 2 — Constants and Semantic Types

* [x] Strongly typed constants
* [x] Built-in semantic type `nes_color`
* [x] Constant resolution
* [x] Duplicate declaration validation
* [x] Constant type validation
* [x] Semantic validation

## Milestone 3 — Variables

* [x] Global variables
* [x] Assignment statements
* [x] Built-in type `byte`
* [x] Built-in type `boolean`
* [x] Variable initialization through assignments
* [x] Variable type validation
* [x] RAM allocation for global variables

## Milestone 4 — Arithmetic Expressions

* [x] Numeric literals
* [x] Variable references
* [x] Constant references
* [x] Parenthesized expressions
* [x] Unary operators
* [x] Binary arithmetic operators
* [x] Addition
* [x] Subtraction
* [x] Compile-time constant folding where possible
* [x] 8-bit wraparound arithmetic

---

# Release 0.2 — Structured Programming

Goal: support the basic control-flow constructs required for game logic.

## Milestone 5 — Comparisons and Boolean Expressions

* [x] Equality operator `=`
* [x] Inequality operator `<>`
* [x] Less-than operator `<`
* [x] Greater-than operator `>`
* [x] Less-than-or-equal operator `<=`
* [x] Greater-than-or-equal operator `>=`
* [x] Boolean literals `true` and `false`
* [x] Boolean operator `not`
* [x] Boolean operator `and`
* [x] Boolean operator `or`
* [x] Short-circuit evaluation
* [x] Type validation for comparisons
* [x] Type validation for Boolean operators

## Milestone 6 — Conditional Statements

* [x] `if` statements
* [x] `if / else` statements
* [x] Nested conditionals
* [x] Compound statements inside branches
* [x] Conditional branch code generation
* [x] Long-branch handling when branch targets exceed 6502 limits

## Milestone 7 — Basic Loops

* [x] `while` loops
* [x] `repeat / until` loops
* [x] Nested loops
* [x] Loop condition validation
* [x] `break`
* [x] `continue`

## Milestone 8 — Increment and Decrement Operations

* [x] `inc(variable)`
* [x] `inc(variable, amount)`
* [x] `dec(variable)`
* [x] `dec(variable, amount)`
* [x] Optimized `INC` and `DEC` generation where possible
* [x] Wraparound behavior for `byte`
* [x] `for variable := initial_value to final_value do`
* [x] `for variable := initial_value downto final_value do`
* [x] Single statements and `begin/end` blocks
* [x] Nested `for` loops
* [x] Control variable must be `byte`
* [x] Initial and final expressions must be `byte`
* [x] Final value evaluated once before loop execution
* [x] Control variable cannot be modified inside the loop body
* [x] Correct termination at `$00` and `$FF`
* [x] Long-branch-safe ca65 generation
* [x] Definite assignment analysis for the control variable

## Milestone 9 — Procedures

* [x] Procedure declarations
* [x] Procedure calls
* [x] Procedures without parameters
* [x] Forward procedure resolution
* [x] Local labels
* [x] Nested call validation
* [x] `RTS` generation
* [x] Basic calling convention

## Milestone 10 — Procedure Parameters

* [ ] Value parameters
* [ ] `byte` parameters
* [ ] `boolean` parameters
* [ ] Parameter type checking
* [ ] Argument count validation
* [ ] Parameter storage allocation
* [ ] Define evaluation order
* [ ] Document parameter limitations
* [ ] Prevent unsupported recursion

---

# Release 0.3 — NES Runtime

Goal: provide a stable NES runtime and a frame-based execution model.

## Milestone 11 — Runtime Memory Layout

* [ ] Define compiler-managed RAM regions
* [ ] Define runtime-managed RAM regions
* [ ] Define user variable RAM regions
* [ ] Reserve OAM shadow memory
* [ ] Reserve temporary expression storage
* [ ] Generate linker configuration from compiler settings
* [ ] Detect RAM exhaustion
* [ ] Generate memory map information
* [ ] Document available CPU RAM

## Milestone 12 — Zero-Page Allocation

* [ ] Reserve zero-page runtime variables
* [ ] Allocate expression temporaries in zero page
* [ ] Allocate frequently accessed variables in zero page
* [ ] Detect zero-page exhaustion
* [ ] Generate zero-page symbols
* [ ] Prefer zero-page addressing when available
* [ ] Allow explicit zero-page variables later without breaking the ABI

## Milestone 13 — NMI and Frame Synchronization

* [ ] Install an NMI handler
* [ ] Enable NMI during VBlank
* [ ] Maintain a frame counter
* [ ] Set a frame-ready flag
* [ ] Preserve CPU registers during NMI
* [ ] Prevent unsafe PPU writes outside VBlank
* [ ] Provide `nes.wait_frame`
* [ ] Provide a stable main-loop pattern

## Milestone 14 — Frame Callbacks

* [ ] Declare an update procedure
* [ ] Register a procedure with `nes.on_update()`
* [ ] Call game update logic once per frame
* [ ] Separate game update from NMI work
* [ ] Register a VBlank procedure
* [ ] Restrict VBlank procedures to supported operations
* [ ] Detect invalid callback signatures
* [ ] Prevent multiple conflicting callbacks

## Milestone 15 — Controller Input

* [ ] Read controller port 1
* [ ] Read controller port 2
* [ ] Built-in controller button constants
* [ ] `nes.controller_down()`
* [ ] `nes.controller_pressed()`
* [ ] `nes.controller_released()`
* [ ] Store current controller state
* [ ] Store previous controller state
* [ ] Update controller state once per frame
* [ ] Validate controller index
* [ ] Support Up, Down, Left, Right, A, B, Select and Start

---

# Release 0.4 — Background Graphics

Goal: display complete static game screens and safely update background graphics.

## Milestone 16 — CHR-ROM Asset Inclusion

* [ ] Include a `.chr` file in the generated ROM
* [ ] Validate CHR-ROM size
* [ ] Require exactly 8 KiB of CHR-ROM for NROM
* [ ] Generate a default empty CHR-ROM when none is provided
* [ ] Report missing asset files
* [ ] Report invalid asset sizes
* [ ] Support project-relative asset paths

## Milestone 17 — Palette Support

* [ ] Define background palettes
* [ ] Define sprite palettes
* [ ] Upload palettes during initialization
* [ ] `nes.set_background_palette()`
* [ ] `nes.set_sprite_palette()`
* [ ] Update individual palette colors
* [ ] Validate `nes_color` values
* [ ] Queue palette changes for VBlank
* [ ] Support the universal background color

## Milestone 18 — Nametable Loading

* [ ] Include nametable data files
* [ ] Load a complete nametable during initialization
* [ ] Load attribute table data
* [ ] `nes.load_background()`
* [ ] Validate nametable asset size
* [ ] Support raw 1 KiB nametable assets
* [ ] Support separate tile and attribute data
* [ ] Disable rendering during bulk PPU uploads
* [ ] Restore rendering after initialization

## Milestone 19 — Runtime Background Updates

* [ ] `nes.set_tile(x, y, tile)`
* [ ] `nes.get_tile(x, y)` using a RAM shadow
* [ ] Queue tile updates for VBlank
* [ ] Limit updates per frame
* [ ] Detect update queue overflow
* [ ] Update attribute table entries
* [ ] `nes.set_attribute()`
* [ ] Clear pending background updates
* [ ] Document per-frame update limits

## Milestone 20 — Scrolling and PPU State

* [ ] Set horizontal scroll
* [ ] Set vertical scroll
* [ ] Reset scroll correctly after PPU writes
* [ ] Preserve PPU control state
* [ ] Preserve PPU mask state
* [ ] `nes.set_scroll(x, y)`
* [ ] Support static single-screen mirroring configurations
* [ ] Configure horizontal or vertical mirroring in the ROM header
* [ ] Default to no gameplay scrolling for the initial product scope

---

# Release 0.5 — Sprites and Gameplay

Goal: support player characters, enemies, projectiles and common single-screen game mechanics.

## Milestone 21 — Basic Sprite Support

* [ ] Reserve OAM shadow memory
* [ ] Upload OAM through DMA during VBlank
* [ ] Define a sprite data type
* [ ] Set sprite X position
* [ ] Set sprite Y position
* [ ] Set sprite tile
* [ ] Set sprite palette
* [ ] Set sprite attributes
* [ ] Hide sprites
* [ ] Show sprites
* [ ] Support horizontal flipping
* [ ] Support vertical flipping
* [ ] Support background priority

## Milestone 22 — Sprite Management API

* [ ] `nes.sprite_create()`
* [ ] `nes.sprite_set_position()`
* [ ] `nes.sprite_set_tile()`
* [ ] `nes.sprite_set_palette()`
* [ ] `nes.sprite_set_flip()`
* [ ] `nes.sprite_show()`
* [ ] `nes.sprite_hide()`
* [ ] Validate sprite indexes
* [ ] Support all 64 hardware sprites
* [ ] Hide unused sprites automatically

## Milestone 23 — Metasprites

* [ ] Define metasprite assets
* [ ] Draw metasprites composed of multiple hardware sprites
* [ ] Position metasprites using a single origin
* [ ] Hide complete metasprites
* [ ] Flip complete metasprites horizontally
* [ ] Flip complete metasprites vertically
* [ ] Clip metasprites near screen boundaries
* [ ] Handle the NES Y-coordinate offset
* [ ] Detect OAM capacity exhaustion
* [ ] Document the eight-sprites-per-scanline limitation

## Milestone 24 — Arrays

* [ ] Fixed-size global arrays
* [ ] Arrays of `byte`
* [ ] Arrays of `boolean`
* [ ] Constant array indexes
* [ ] Variable array indexes
* [ ] Array element assignment
* [ ] Array element expressions
* [ ] Index type validation
* [ ] Optional compile-time bounds checks
* [ ] Efficient indexed addressing

## Milestone 25 — Enumerations

* [ ] User-defined enumeration types
* [ ] Enumeration constants
* [ ] Enumeration variables
* [ ] Enumeration assignment validation
* [ ] Enumeration comparison
* [ ] Use enumerations for game states
* [ ] Generate byte-sized enumeration storage
* [ ] Detect duplicate enumeration members

## Milestone 26 — Records

* [ ] User-defined record types
* [ ] Byte fields
* [ ] Boolean fields
* [ ] Enumeration fields
* [ ] Record variables
* [ ] Record field access
* [ ] Record field assignment
* [ ] Record arrays
* [ ] Calculate record sizes at compile time
* [ ] Generate field offsets
* [ ] Detect unsupported recursive record definitions

## Milestone 27 — Functions

* [ ] Function declarations
* [ ] Function calls
* [ ] `byte` return values
* [ ] `boolean` return values
* [ ] Function parameters
* [ ] Return type validation
* [ ] Function calls inside expressions
* [ ] Define return-value storage
* [ ] Prevent unsupported recursion

## Milestone 28 — Collision Helpers

* [ ] Rectangle data type or collision record
* [ ] Point-versus-rectangle collision
* [ ] Rectangle-versus-rectangle collision
* [ ] Sprite bounding-box helpers
* [ ] Metasprite bounding-box helpers
* [ ] Background tile collision lookup
* [ ] Collision map assets
* [ ] `nes.collides()`
* [ ] `nes.background_collision()`
* [ ] Support configurable collision-box offsets
* [ ] Document wraparound edge cases

## Milestone 29 — Random Number Generation

* [ ] Runtime pseudo-random number generator
* [ ] Seed generator from frame and controller timing
* [ ] `nes.random_byte()`
* [ ] `nes.random_range(min, max)`
* [ ] Deterministic seed option
* [ ] Avoid severe modulo bias for small ranges
* [ ] Document deterministic behavior for testing

## Milestone 30 — Game-State Support

* [ ] Recommended state-machine pattern
* [ ] Enumeration-based game states
* [ ] Title-screen example
* [ ] Playing-state example
* [ ] Game-over-state example
* [ ] Pause-state example
* [ ] State transition helpers
* [ ] Reset gameplay variables without restarting the ROM
* [ ] Restart game with Start
* [ ] Provide a complete state-machine sample project

---

# Release 0.6 — Audio

Goal: add sound effects and music suitable for simple arcade games.

## Milestone 31 — Basic APU Sound Effects

* [ ] Initialize the NES APU
* [ ] Disable unused channels safely
* [ ] Play pulse-channel tones
* [ ] Play noise-channel effects
* [ ] Stop a sound effect
* [ ] Set sound-effect volume
* [ ] Set sound-effect pitch
* [ ] Provide predefined effect helpers
* [ ] Avoid direct conflicts with the music engine

## Milestone 32 — Audio Asset Integration

* [ ] Select an initial supported audio engine
* [ ] Include exported audio data in the ROM
* [ ] Validate audio asset files
* [ ] Generate audio symbol declarations
* [ ] Initialize the audio engine
* [ ] Update the audio engine once per frame
* [ ] Document supported export settings
* [ ] Keep DPCM disabled for the initial release

## Milestone 33 — Sound-Effect API

* [ ] `nes.play_sfx()`
* [ ] Select sound-effect channel
* [ ] Define sound-effect constants
* [ ] Stop active sound effects
* [ ] Assign effect priority
* [ ] Prevent low-priority effects from replacing critical effects
* [ ] Validate sound-effect indexes
* [ ] Provide example effects for movement, shooting, damage and scoring

## Milestone 34 — Music API

* [ ] `nes.play_music()`
* [ ] `nes.stop_music()`
* [ ] `nes.pause_music()`
* [ ] `nes.resume_music()`
* [ ] Define song constants
* [ ] Loop songs
* [ ] Change songs during gameplay
* [ ] Validate song indexes
* [ ] Preserve sound effects while music plays
* [ ] Provide title-screen and gameplay music examples

---

# Release 0.7 — Usable Game Development Product

Goal: make nes-pascal practical for building complete, simple, single-screen NES games.

## Milestone 35 — Project Configuration

* [ ] Project configuration file
* [ ] Configure source entry point
* [ ] Configure ROM name
* [ ] Configure PRG-ROM size
* [ ] Configure CHR-ROM asset
* [ ] Configure mirroring
* [ ] Configure nametable assets
* [ ] Configure palette assets
* [ ] Configure audio assets
* [ ] Configure debug or release build
* [ ] Validate unsupported mapper configurations
* [ ] Default to mapper 0

## Milestone 36 — Standard Library

* [ ] Basic numeric helper procedures
* [ ] Clamp a byte value
* [ ] Minimum and maximum helpers
* [ ] Range checks
* [ ] Absolute difference
* [ ] Coordinate helpers
* [ ] Timer helpers
* [ ] Cooldown helpers
* [ ] Animation frame helpers
* [ ] Sprite movement helpers
* [ ] Controller helpers
* [ ] Collision helpers

## Milestone 37 — Timers and Animation

* [ ] Frame timers
* [ ] Countdown timers
* [ ] Repeating timers
* [ ] Timer-expired checks
* [ ] Sprite animation state
* [ ] Animation frame duration
* [ ] Looping animations
* [ ] One-shot animations
* [ ] Animation reset
* [ ] Metasprite animation helpers

## Milestone 38 — Score and HUD Support

* [ ] Binary-coded decimal helpers or decimal conversion
* [ ] Convert byte values into decimal digits
* [ ] Draw numeric values using background tiles
* [ ] Update score during VBlank
* [ ] Draw lives
* [ ] Draw health values
* [ ] Draw counters
* [ ] Fixed-width number formatting
* [ ] Leading-zero configuration
* [ ] Example HUD implementation

## Milestone 39 — Debug Build Support

* [ ] Generate compiler debug symbols
* [ ] Generate source-to-assembly mappings
* [ ] Generate variable address maps
* [ ] Generate procedure address maps
* [ ] Generate Mesen-compatible symbol files
* [ ] Optional runtime assertions
* [ ] Optional screen-border debug indicator
* [ ] Report ROM and RAM usage
* [ ] Report zero-page usage
* [ ] Report estimated OAM usage

## Milestone 40 — Compiler Diagnostics

* [ ] Source file and line numbers in errors
* [ ] Source columns in errors
* [ ] Clear syntax error messages
* [ ] Clear semantic error messages
* [ ] Undefined identifier suggestions
* [ ] Type mismatch details
* [ ] Duplicate symbol details
* [ ] Unsupported feature diagnostics
* [ ] RAM exhaustion diagnostics
* [ ] ROM exhaustion diagnostics
* [ ] Asset validation diagnostics
* [ ] Warnings for likely gameplay mistakes

## Milestone 41 — Build Tool

* [ ] `nes-pascal build`
* [ ] `nes-pascal run`
* [ ] `nes-pascal clean`
* [ ] `nes-pascal check`
* [ ] Select emulator command
* [ ] Incremental asset rebuilding
* [ ] Debug and release build profiles
* [ ] Human-readable build summary
* [ ] Non-zero exit codes on failure
* [ ] Windows support
* [ ] Linux support

## Milestone 42 — Language Modules

* [ ] Split programs into units or modules
* [ ] Import runtime modules
* [ ] Import user modules
* [ ] Public declarations
* [ ] Private implementation details
* [ ] Module dependency resolution
* [ ] Circular dependency detection
* [ ] Separate compilation strategy
* [ ] Standard `nes` module
* [ ] Standard utility modules

## Milestone 43 — Optimization Passes

* [ ] Remove unreachable code
* [ ] Remove unused procedures
* [ ] Remove unused constants
* [ ] Fold constant expressions
* [ ] Simplify Boolean expressions
* [ ] Use immediate instructions where possible
* [ ] Use zero-page addressing where possible
* [ ] Optimize increment and decrement operations
* [ ] Eliminate redundant loads and stores
* [ ] Reuse expression temporaries
* [ ] Release-build optimization mode
* [ ] Preserve readable assembly in debug mode

## Milestone 44 — Inline Assembly

* [ ] Basic inline assembly blocks
* [ ] Reference compiler symbols from assembly
* [ ] Reference constants from assembly
* [ ] Define clobbered registers
* [ ] Prevent symbol collisions
* [ ] Restrict unsupported segment changes
* [ ] Preserve compiler runtime assumptions
* [ ] Document safe inline assembly usage
* [ ] Provide examples for advanced users

## Milestone 45 — Complete Example Games

* [ ] Player movement demo
* [ ] Sprite animation demo
* [ ] Controller edge-detection demo
* [ ] Projectile demo
* [ ] Sprite collision demo
* [ ] Background collision demo
* [ ] Sound-effects demo
* [ ] Music demo
* [ ] Title-screen and game-over demo
* [ ] Single-screen shooter
* [ ] Single-screen maze game
* [ ] Breakout-style game
* [ ] Complete commented source code
* [ ] Generated ROMs for every example

## Milestone 46 — Initial Documentation

* [ ] Installation guide
* [ ] Getting-started tutorial
* [ ] Language reference
* [ ] NES runtime reference
* [ ] Asset pipeline guide
* [ ] Graphics guide
* [ ] Controller guide
* [ ] Sprite and metasprite guide
* [ ] Collision guide
* [ ] Audio guide
* [ ] Memory model documentation
* [ ] Performance limitations
* [ ] NROM limitations
* [ ] Compiler error reference
* [ ] Complete game tutorial

## Milestone 47 — First Functional Release

* [ ] Build a complete game using only documented features
* [ ] Run correctly on Mesen
* [ ] Run correctly on at least one additional emulator
* [ ] Run correctly on real NES-compatible hardware or a flash cartridge
* [ ] Maintain stable 60 Hz gameplay on NTSC
* [ ] Support PAL timing configuration or document NTSC-only behavior
* [ ] No required manual edits to generated assembly
* [ ] No required manual linker configuration
* [ ] No required manual ROM header editing
* [ ] Stable compiler command-line interface
* [ ] Stable basic runtime API
* [ ] Publish nes-pascal v0.7.0

---

# Release 0.8 — Quality and Developer Experience

Goal: improve reliability, testing and productivity after the first functional release.

## Milestone 48 — Automated Compiler Tests

* [ ] Lexer tests
* [ ] Parser tests
* [ ] Semantic-analysis tests
* [ ] Code-generation tests
* [ ] Diagnostic tests
* [ ] Asset-validation tests
* [ ] Golden assembly tests
* [ ] Golden ROM tests
* [ ] Invalid-program tests
* [ ] Regression-test suite

## Milestone 49 — ROM Integration Tests

* [ ] Run generated ROMs automatically
* [ ] Use emulator scripting or headless execution
* [ ] Validate CPU memory values
* [ ] Validate PPU state
* [ ] Validate controller input behavior
* [ ] Validate sprite DMA
* [ ] Validate NMI timing
* [ ] Validate audio engine updates
* [ ] Capture screenshots for visual regression tests
* [ ] Detect emulator crashes and invalid opcodes

## Milestone 50 — Asset Tooling

* [ ] Convert PNG graphics into CHR data
* [ ] Validate NES palette limitations
* [ ] Deduplicate tiles
* [ ] Generate nametables
* [ ] Generate attribute tables
* [ ] Generate metasprite data
* [ ] Generate collision maps
* [ ] Preview imported assets
* [ ] Integrate conversion into the build command
* [ ] Produce actionable asset errors

## Milestone 51 — Additional Language Features

* [ ] `case` statements
* [ ] `for` loops
* [ ] Named array types
* [ ] Constant arrays
* [ ] Set-like button masks
* [ ] Bitwise `and`
* [ ] Bitwise `or`
* [ ] Bitwise `xor`
* [ ] Bitwise `not`
* [ ] Shift-left operation
* [ ] Shift-right operation
* [ ] Explicit type casts
* [ ] Compile-time `sizeof`

---

# Release 1.0 — Stable NROM Compiler

Goal: declare the mapper-0, single-screen development workflow stable.

## Milestone 52 — API Stabilization

* [ ] Review all built-in functions
* [ ] Review naming conventions
* [ ] Freeze the core language syntax
* [ ] Freeze the runtime memory layout
* [ ] Freeze the standard calling convention
* [ ] Freeze the asset formats
* [ ] Freeze the project configuration format
* [ ] Document compatibility guarantees
* [ ] Create a deprecation policy

## Milestone 53 — Production Readiness

* [ ] Build multiple complete games
* [ ] Compile medium-sized projects reliably
* [ ] Verify deterministic builds
* [ ] Verify clean builds on Windows
* [ ] Verify clean builds on Linux
* [ ] Verify ROM behavior on hardware
* [ ] Complete regression suite
* [ ] Complete documentation
* [ ] Publish downloadable compiler packages
* [ ] Publish example project templates
* [ ] Publish nes-pascal v1.0.0

---

# Post-1.0 Roadmap

These features are intentionally outside the initial single-screen NROM product scope.

## Advanced Language Features

* Local variables
* Pass-by-reference parameters
* Function and procedure overloading
* More integer types
* Signed integers
* 16-bit arithmetic
* Pointers
* Dynamic memory abstractions
* Advanced records
* Generic routines
* Compile-time metaprogramming

## Advanced NES Features

* Screen transitions
* Multidirectional scrolling
* Large levels
* Runtime CHR-RAM updates
* Sprite multiplexing
* DPCM samples
* Save data
* Battery-backed RAM
* PAL and Dendy-specific timing
* Four-player adapters

## Mapper Support

* Mapper abstraction
* UxROM
* CNROM
* AxROM
* MMC1
* MMC3
* PRG-ROM bank switching
* CHR-ROM bank switching
* Scanline IRQ support
* Mirroring control
* Additional sound chips

## Tooling

* Language Server Protocol
* Editor syntax highlighting
* Code completion
* Go-to-definition
* Integrated debugger support
* Source-level breakpoints
* Package manager
* Project templates
* Visual asset editor
* IDE integration
