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

## Milestone 42 — Units and the `uses` Clause

- [ ] Add `unit`, `interface`, `implementation` and `uses`
- [ ] Parse units and `uses` clauses
- [ ] Allow one source file per unit
- [ ] Resolve built-in and user units
- [ ] Resolve project source directories
- [ ] Detect missing and duplicate units
- [ ] Support public interface declarations
- [ ] Support private implementation declarations
- [ ] Support qualified identifiers
- [ ] Support unqualified identifiers when unambiguous
- [ ] Detect ambiguous imported symbols
- [ ] Generate collision-free unit-qualified assembly symbols
- [ ] Include imported files in dependency tracking
- [ ] Add multi-file fixtures and golden assembly tests
- [ ] Document the initial unit syntax and limitations

## Milestone 43 — Unit Dependency and Initialization Model

- [ ] Build a directed unit dependency graph
- [ ] Separate interface and implementation dependencies
- [ ] Resolve dependencies transitively
- [ ] Detect direct and indirect cycles
- [ ] Report the complete dependency cycle
- [ ] Topologically sort units
- [ ] Compile and emit each unit once
- [ ] Define deterministic initialization order
- [ ] Execute dependencies before dependents
- [ ] Execute all unit initialization before the program body
- [ ] Separate runtime initialization from user initialization
- [ ] Parse but initially reject unsupported finalization blocks
- [ ] Add diamond, chain and cycle tests
- [ ] Expose the graph to later bank-placement tooling

## Milestone 44 — Unit-Aware Semantic Analysis

- [ ] Symbol table per unit
- [ ] Separate interface and implementation scopes
- [ ] Qualified and unqualified lookup
- [ ] Local declarations override imports
- [ ] Ambiguity detection
- [ ] Cross-unit type, constant, variable and routine resolution
- [ ] Interface/implementation signature validation
- [ ] Missing and duplicate implementation diagnostics
- [ ] Cross-unit recursion detection
- [ ] Cross-unit defined-assignment analysis
- [ ] Cross-unit call graph
- [ ] Declaration and use-site diagnostics
- [ ] Semantic regression tests

## Milestone 45 — Unit-Aware Code Generation

- [ ] Stable assembly prefix per unit
- [ ] Private-symbol mangling
- [ ] Unique local labels
- [ ] Cross-unit `JSR` and data references
- [ ] Unit initialization procedures
- [ ] Master initialization routine
- [ ] Deterministic unit ordering
- [ ] Group generated assembly by unit
- [ ] Preserve source mappings
- [ ] Unit-qualified debugger symbols
- [ ] ca65 and ld65 validation
- [ ] Multi-unit ROM tests in Mesen

## Milestone 46 — Unit Documentation and Examples

- [ ] Unit syntax reference
- [ ] `uses` documentation
- [ ] Public and private visibility
- [ ] Qualified identifier behavior
- [ ] Source lookup and filename conventions
- [ ] Dependency and initialization order
- [ ] Circular-dependency restrictions
- [ ] Built-in units
- [ ] Unit-related diagnostics
- [ ] Recommended project structure
- [ ] Two-unit and realistic game examples
- [ ] Migration guide from single-file projects

## Milestone 47 — Optimization Passes

- [ ] Remove unreachable code
- [ ] Remove unused procedures and constants
- [ ] Fold constant expressions
- [ ] Simplify Boolean expressions
- [ ] Use immediate and zero-page instructions
- [ ] Optimize increment and decrement
- [ ] Eliminate redundant loads and stores
- [ ] Reuse expression temporaries
- [ ] Preserve readable debug assembly

## Milestone 48 — Inline Assembly

- [ ] Inline assembly blocks
- [ ] Reference compiler symbols and constants
- [ ] Declare clobbered registers
- [ ] Prevent symbol collisions
- [ ] Restrict unsupported segment changes
- [ ] Preserve runtime assumptions
- [ ] Document safe usage
- [ ] Provide advanced examples

## Milestone 49 — Complete Example Games

- [ ] Player movement demo
- [ ] Sprite animation demo
- [ ] Controller edge-detection demo
- [ ] Projectile and collision demos
- [ ] Background collision demo
- [ ] Sound and music demos
- [ ] Title and game-over demo
- [ ] Single-screen shooter
- [ ] Single-screen maze game
- [ ] Breakout-style game
- [ ] Commented source and generated ROMs

## Milestone 50 — Initial Documentation

- [ ] Installation and getting-started guides
- [ ] Language and runtime references
- [ ] Asset pipeline guide
- [ ] Graphics, controller, sprite and collision guides
- [ ] Audio guide
- [ ] Memory model
- [ ] Performance and NROM limitations
- [ ] Error reference
- [ ] Complete game tutorial

## Milestone 51 — Automated Compiler Tests

- [ ] Lexer, parser and semantic tests
- [ ] Code-generation tests
- [ ] Diagnostic tests
- [ ] Asset-validation tests
- [ ] Golden assembly and ROM tests
- [ ] Invalid-program fixtures
- [ ] Regression suite

## Milestone 52 — ROM Integration Tests

- [ ] Automated emulator execution
- [ ] CPU RAM and PPU validation
- [ ] Controller behavior tests
- [ ] Sprite DMA tests
- [ ] NMI timing tests
- [ ] Audio update tests
- [ ] Screenshot regression tests
- [ ] Invalid-opcode and crash detection

## Milestone 53 — Asset Tooling

- [ ] PNG-to-CHR conversion
- [ ] NES palette validation
- [ ] Tile deduplication
- [ ] Nametable generation
- [ ] Attribute generation
- [ ] Metasprite generation
- [ ] Collision-map generation
- [ ] Asset previews
- [ ] Build integration
- [ ] Actionable diagnostics

## Milestone 54 — Additional Language Features

- [ ] `case` statements
- [ ] Named array types
- [ ] Constant arrays
- [ ] Button-mask sets
- [ ] Bitwise operators
- [ ] Shift operations
- [ ] Explicit casts
- [ ] Compile-time `sizeof`

## Milestone 55 — API Stabilization

- [ ] Review built-in functions and naming
- [ ] Freeze core syntax
- [ ] Freeze runtime memory layout
- [ ] Freeze the calling convention
- [ ] Freeze asset and project formats
- [ ] Document compatibility guarantees
- [ ] Create a deprecation policy

## Milestone 56 — Production Readiness

- [ ] Build multiple complete games
- [ ] Compile medium projects reliably
- [ ] Verify deterministic builds
- [ ] Verify Windows and Linux installs
- [ ] Verify ROMs on hardware
- [ ] Complete regression suite and documentation
- [ ] Publish packages and templates

## Milestone 57 — Release 1.0

- [ ] Build a complete game using only documented features
- [ ] Run correctly in Mesen and another emulator
- [ ] Run correctly on hardware or a flash cartridge
- [ ] Maintain stable NTSC gameplay
- [ ] Document PAL support or NTSC-only behavior
- [ ] Require no manual generated-assembly edits
- [ ] Require no manual linker or header edits
- [ ] Stabilize the CLI and runtime API
- [ ] Publish `nes-pascal 1.0.0`

---

# Release 1.1 — Graphics and Asset Pipeline

Goal: make background construction practical through integrated conversion, symbolic tiles and metatiles.

## Milestone 58 — Asset Declaration Syntax

- [ ] Declare CHR, nametable, palette, metasprite and collision assets
- [ ] Resolve project-relative paths
- [ ] Normalize Windows and Linux paths
- [ ] Detect missing, duplicate and unsupported assets
- [ ] Associate declarations with source locations
- [ ] Track assets as build dependencies
- [ ] Document supported formats

## Milestone 59 — Integrated PNG-to-CHR Conversion

- [ ] Accept indexed, RGB and RGBA PNG files
- [ ] Validate dimensions and four-color tile limits
- [ ] Report invalid tile coordinates and colors
- [ ] Convert tiles into NES 2bpp format
- [ ] Preserve deterministic ordering
- [ ] Deduplicate identical and optionally flipped tiles
- [ ] Emit tile-index mappings
- [ ] Append multiple assets
- [ ] Detect CHR overflow
- [ ] Pad to 8 KiB
- [ ] Report used and free CHR tiles

## Milestone 60 — Tile Symbol Generation

- [ ] Generate Pascal constants for imported tiles
- [ ] Support explicit and generated names
- [ ] Namespace symbols per asset
- [ ] Detect collisions
- [ ] Use symbols in background and sprite APIs
- [ ] Generate assembly and debugger symbols
- [ ] Produce a tile-symbol map
- [ ] Document index-stability limitations

## Milestone 61 — Metatile Definitions

- [ ] Define 2×2 tile metatiles
- [ ] Store four tile indexes and one palette
- [ ] Generate metatile identifiers
- [ ] Validate tile and palette references
- [ ] Support generated and hand-authored definitions
- [ ] Generate compact ROM tables
- [ ] Report ROM usage

## Milestone 62 — Metatile Rendering API

- [ ] `nes.set_metatile()`
- [ ] `nes.get_metatile()`
- [ ] Expand metatiles into nametable writes
- [ ] Update the correct attribute quadrant
- [ ] Queue atomic updates for VBlank
- [ ] Validate coordinates and IDs
- [ ] Detect queue overflow
- [ ] Support immediate rendering with rendering disabled
- [ ] Redraw rectangular metatile regions

## Milestone 63 — Metatile Maps

- [ ] Define metatile map assets
- [ ] Support one-screen maps
- [ ] Store width and height
- [ ] Generate compact map and palette data
- [ ] `nes.load_metatile_map()`
- [ ] Expand into nametable and attributes
- [ ] Validate dimensions and references
- [ ] Generate map symbols and usage reports
- [ ] Provide editor-export examples

## Milestone 64 — Attribute Table Abstraction

- [ ] Calculate addresses and quadrants
- [ ] Maintain attribute RAM shadows
- [ ] Modify quadrants without corrupting neighbors
- [ ] Synchronize all background APIs
- [ ] Detect shadow mismatches in debug builds
- [ ] Test quadrants and screen edges

## Milestone 65 — Graphics Asset Validation Suite

- [ ] PNG conversion tests
- [ ] Invalid dimension and color tests
- [ ] CHR overflow tests
- [ ] Deduplication tests
- [ ] Symbol generation tests
- [ ] Metatile and attribute tests
- [ ] Golden CHR and nametable outputs
- [ ] Visual regression ROMs
- [ ] Deterministic output verification

---

# Release 1.2 — Advanced Sprites, Animation and Collision

Goal: provide higher-level entity rendering, animation and collision systems.

## Milestone 66 — Sprite Handle Abstraction

- [ ] Stable sprite-handle type
- [ ] Separate logical handles from OAM indexes
- [ ] Automatic allocation and release
- [ ] Exhaustion and invalid-handle detection
- [ ] Hide released sprites
- [ ] Store logical state in RAM
- [ ] Synchronize with OAM shadow
- [ ] Preserve low-level indexed access

## Milestone 67 — Declarative Metasprite Assets

- [ ] Define component offsets, tile and attributes
- [ ] Support flip metadata
- [ ] Generate metasprite identifiers
- [ ] Validate tiles and component count
- [ ] Calculate visual and collision bounds
- [ ] Allow collision-box overrides
- [ ] Generate compact ROM tables
- [ ] Import a documented external format where practical

## Milestone 68 — Metasprite Runtime Manager

- [ ] Create and destroy instances
- [ ] Assign assets
- [ ] Position, flip, show and hide
- [ ] Expand instances into OAM
- [ ] Clip offscreen components
- [ ] Define deterministic render order
- [ ] Support logical priority
- [ ] Detect and report OAM overflow
- [ ] Hide unused OAM entries

## Milestone 69 — Sprite Animation Assets

- [ ] Define clips and frames
- [ ] Associate frames with metasprites
- [ ] Define frame durations
- [ ] Looping, one-shot and hold-last behavior
- [ ] Transition behavior
- [ ] Generate identifiers
- [ ] Validate references and durations
- [ ] Generate compact tables

## Milestone 70 — Sprite Animation Runtime

- [ ] Play, restart, stop, pause and resume
- [ ] Change animation safely
- [ ] Advance once per frame
- [ ] Query current animation and frame
- [ ] Detect completion
- [ ] Playback speed controls
- [ ] Global animation divisor
- [ ] Directional-animation helpers
- [ ] Deterministic frame-skipping behavior

## Milestone 71 — Collision Shape Definitions

- [ ] Point and rectangle shapes
- [ ] Multiple hitboxes
- [ ] Hurtboxes and attack boxes
- [ ] Origin-relative offsets
- [ ] Generated shape assets
- [ ] Enable and disable individual shapes
- [ ] Default metasprite shapes and runtime overrides
- [ ] Document edge and wraparound conventions

## Milestone 72 — Advanced Entity Collision

- [ ] Point/rectangle and rectangle/rectangle tests
- [ ] Multiple-shape tests
- [ ] Collision layers and masks
- [ ] Return colliding shape IDs and side information
- [ ] Ignore inactive entities
- [ ] Screen and world bounds
- [ ] Projectile and enemy helpers
- [ ] Prevent duplicate reports
- [ ] Deterministic iteration order
- [ ] Debug visualization metadata

## Milestone 73 — Background Collision Maps

- [ ] Collision values per metatile
- [ ] Solid, hazard and trigger classes
- [ ] Directional flags and one-way platforms
- [ ] Generate collision maps
- [ ] Pixel and metatile queries
- [ ] Rectangle-versus-background tests
- [ ] Return direction and metatile ID
- [ ] Consistent boundary behavior

## Milestone 74 — Movement and Resolution Helpers

- [ ] Bounded movement
- [ ] Axis-separated background resolution
- [ ] Fixed-point positions and velocity
- [ ] Acceleration, friction and gravity
- [ ] Jump velocity
- [ ] Grounded and wall-contact state
- [ ] Top-down helpers
- [ ] Simple platform helpers
- [ ] Document tunneling and velocity limits

## Milestone 75 — Sprite Flicker Management

- [ ] Detect scanlines over eight sprites
- [ ] Optional OAM rotation
- [ ] Rotate logical priority
- [ ] Pin critical sprites
- [ ] Allow disabling
- [ ] Report scanline pressure
- [ ] Stress-test ROMs
- [ ] Verify emulator and hardware behavior

---

# Release 1.3 — Scrolling and Larger NROM Worlds

Goal: support playfields larger than one screen within NROM limits.

## Milestone 76 — Camera Abstraction

- [ ] Camera X and Y independent from entities
- [ ] World-to-screen and screen-to-world conversion
- [ ] Camera bounds
- [ ] Follow targets with margins and dead zones
- [ ] Lock one axis
- [ ] Expose camera state
- [ ] Document coordinate limits

## Milestone 77 — 16-bit Integer Foundations

- [ ] Unsigned 16-bit type
- [ ] Variables, constants and assignment
- [ ] Comparisons, addition and subtraction
- [ ] Increment and decrement
- [ ] Byte widening and explicit narrowing
- [ ] Wraparound behavior
- [ ] Little-endian storage
- [ ] Two-byte temporaries
- [ ] Optimizations for constant high bytes
- [ ] Debugger support and tests

## Milestone 78 — Multi-Nametable Support

- [ ] Track visible and offscreen nametables
- [ ] Horizontal and vertical mirroring
- [ ] Reject unsupported configurations
- [ ] Calculate nametable addresses from world coordinates
- [ ] Attribute shadows per nametable
- [ ] Load offscreen data
- [ ] Cross nametable boundaries
- [ ] Preserve PPU latch state
- [ ] Boundary tests

## Milestone 79 — Scrolling Update Queue

- [ ] Dedicated PPU scrolling queue
- [ ] Queue rows, columns and attributes
- [ ] Calculate VBlank cost
- [ ] Enforce safe budgets
- [ ] Defer excess work
- [ ] Prioritize visible edges
- [ ] Detect queue lag
- [ ] Integrate palette and OAM costs
- [ ] Stress tests and documented limits

## Milestone 80 — Horizontal Scrolling

- [ ] Scroll left and right
- [ ] Detect tile and metatile crossings
- [ ] Load new columns and attributes
- [ ] Update collision position
- [ ] Subpixel movement
- [ ] Optional looping and bounded maps
- [ ] Prevent seams
- [ ] Clip offscreen sprites
- [ ] Complete example

## Milestone 81 — Vertical Scrolling

- [ ] Scroll up and down
- [ ] Detect row and metatile crossings
- [ ] Load new rows and attributes
- [ ] Update collision position
- [ ] Optional looping and bounded maps
- [ ] Handle vertical nametable transitions
- [ ] Document mapper-0 limitations
- [ ] Complete example

## Milestone 82 — Two-Axis Scrolling

- [ ] Simultaneous horizontal and vertical movement
- [ ] Edge-update ordering
- [ ] Avoid duplicate corner updates
- [ ] Correct corner attributes
- [ ] Detect budget overruns
- [ ] Define maximum diagonal speed
- [ ] Camera clamping
- [ ] Stress tests and debug visualization
- [ ] Top-down example

## Milestone 83 — Compressed Map Data

- [ ] Simple 6502-friendly compression
- [ ] Run-length encoding
- [ ] Repeated metatile sequences
- [ ] Build-time compression
- [ ] Full-map and edge decompression
- [ ] Compression statistics
- [ ] Raw fallback
- [ ] Malformed-data detection
- [ ] Bounded temporary storage
- [ ] Cycle-cost measurement

## Milestone 84 — Room and Screen System

- [ ] Named rooms
- [ ] Map, collision and palette association
- [ ] Entrance points and exits
- [ ] Room loading with rendering disabled
- [ ] Direct and fade transitions
- [ ] Persistent room state
- [ ] Per-room initialization and update callbacks
- [ ] Reference validation
- [ ] Multi-room example

## Milestone 85 — Scrolling Test and Profiling Suite

- [ ] Camera and 16-bit tests
- [ ] Nametable boundary tests
- [ ] Row, column and attribute tests
- [ ] Horizontal, vertical and two-axis regression ROMs
- [ ] Compression tests
- [ ] Worst-case VBlank measurement
- [ ] Cycle reports
- [ ] PPU-write validation
- [ ] Emulator and hardware verification

---

# Release 1.4 — Complete Audio Support

Goal: provide a complete music and sound-effect workflow while preserving NROM compatibility.

## Milestone 86 — Audio Engine Selection and Abstraction

- [ ] Select and version the official engine
- [ ] Isolate engine-specific assembly
- [ ] Define initialization and update entry points
- [ ] Define RAM, zero-page and ROM requirements
- [ ] Define supported APU channels
- [ ] Define SFX/music sharing behavior
- [ ] Preserve future engine replacement
- [ ] Add licensing and compatibility tests

## Milestone 87 — Audio Project Import

- [ ] Define supported FamiStudio exports
- [ ] Import music, SFX and symbols
- [ ] Detect missing and mismatched exports
- [ ] Reject unsupported configurations
- [ ] Detect DPCM when disabled
- [ ] Generate Pascal song and SFX constants
- [ ] Include data automatically
- [ ] Track build dependencies
- [ ] Report ROM usage
- [ ] End-to-end example

## Milestone 88 — Music Playback Runtime

- [ ] Play, stop, pause, resume and restart
- [ ] Change and query songs
- [ ] Looping and non-looping behavior
- [ ] Song completion when supported
- [ ] Volume and fades
- [ ] Exactly one update per frame
- [ ] Duplicate-update prevention
- [ ] NTSC timing documentation
- [ ] PAL support or explicit limitation

## Milestone 89 — Sound-Effect Playback Runtime

- [ ] Play and stop effects
- [ ] Stop all effects
- [ ] Priorities
- [ ] Automatic and explicit channel selection
- [ ] Simultaneous effects within engine limits
- [ ] Defined no-channel behavior
- [ ] Preserve music state
- [ ] Document channel conflicts
- [ ] Arcade effect examples

## Milestone 90 — DPCM Support

- [ ] Optional DPCM
- [ ] Validate sample format, alignment and address range
- [ ] Reserve linker region
- [ ] Detect overlap
- [ ] Generate sample identifiers
- [ ] Playback API
- [ ] Controller-read mitigation
- [ ] ROM usage reports
- [ ] DPCM test ROM
- [ ] Preserve non-DPCM builds

## Milestone 91 — Audio Diagnostics and Profiling

- [ ] RAM, zero-page and ROM reports
- [ ] Music, SFX and DPCM sizes
- [ ] Channel contention warnings
- [ ] Detect missing frame updates
- [ ] Measure update cycle cost
- [ ] Stress tests
- [ ] Emulator and hardware verification
- [ ] Document known differences

---

# Release 1.5 — NROM Tooling, Optimization and Consolidation

Goal: make the complete NROM workflow efficient, maintainable and ready to serve as the stable base for mapper support.

## Milestone 92 — Unified Project Manifest

- [ ] Stabilize the manifest format
- [ ] Project metadata and sources
- [ ] Graphics, map and audio assets
- [ ] Mirroring and region
- [ ] Debug and release profiles
- [ ] Output and emulator configuration
- [ ] Optional DPCM
- [ ] Unknown-field and conflict validation
- [ ] Schema versioning
- [ ] Editor-validation schema
- [ ] Preserve 1.x compatibility

## Milestone 93 — Project Templates

- [ ] Empty NROM template
- [ ] Single-screen arcade template
- [ ] Top-down and platform templates
- [ ] Horizontal-scrolling template
- [ ] Multi-room template
- [ ] Audio template
- [ ] Commented sources and placeholder assets
- [ ] `nes-pascal new`
- [ ] Safe project-name and overwrite behavior
- [ ] CI builds for all templates

## Milestone 94 — Build Cache and Incremental Compilation

- [ ] Hash sources, assets and configuration
- [ ] Cache parsing and converted assets
- [ ] Rebuild affected outputs only
- [ ] Compiler-version invalidation
- [ ] Forced clean builds
- [ ] Corruption detection
- [ ] Byte-identical cached and clean outputs
- [ ] Cache reports and tests

## Milestone 95 — ROM and RAM Usage Reports

- [ ] PRG code, constants, maps, audio and runtime sizes
- [ ] Free PRG space
- [ ] CHR usage
- [ ] Global RAM and zero-page usage
- [ ] OAM and update-buffer usage
- [ ] Group by module, procedure and asset
- [ ] Human-readable and JSON reports
- [ ] Contributor-focused overflow diagnostics

## Milestone 96 — Call Graph and Dependency Reports

- [ ] Procedure call graph
- [ ] Unit dependency graph
- [ ] Callback and interrupt roots
- [ ] Unreachable and recursive procedures
- [ ] Runtime dependencies
- [ ] Estimated procedure sizes
- [ ] Temporary-storage requirements
- [ ] Standard graph export
- [ ] Prepare for bank allocation

## Milestone 97 — Improved Optimization Pipeline

- [ ] Explicit intermediate representation
- [ ] Basic blocks and control-flow graphs
- [ ] Constant propagation
- [ ] Constant branch folding
- [ ] Unreachable block removal
- [ ] Dead-store removal
- [ ] Redundant load/store elimination
- [ ] Increment combination
- [ ] Zero-page instruction selection
- [ ] Comparison and Boolean optimization
- [ ] Temporary reuse
- [ ] Optional optimization remarks
- [ ] Regression verification

## Milestone 98 — Procedure Inlining

- [ ] Explicit inline marker
- [ ] Automatic small-procedure inlining
- [ ] Preserve evaluation order
- [ ] Rename local labels
- [ ] Update source mappings
- [ ] Estimate size impact
- [ ] Configurable limits
- [ ] Optimization remarks
- [ ] Nested and callback tests

## Milestone 99 — Data Layout Optimization

- [ ] Group related constants and tables
- [ ] Alignment support
- [ ] Hot-data placement
- [ ] Page-crossing analysis and warnings
- [ ] Segment hints without raw linker syntax
- [ ] Protect vectors and runtime data
- [ ] Detailed data-layout maps
- [ ] Prepare mapper-aware metadata
- [ ] Deterministic output

## Milestone 100 — Source-Level Debug Information

- [ ] Map source lines to addresses
- [ ] Map procedures to ROM ranges
- [ ] Map variables and constants
- [ ] Map labels to source constructs
- [ ] Mesen-compatible output
- [ ] Preserve mappings after optimization and inlining
- [ ] Mark runtime-generated code
- [ ] Include asset, metasprite, animation, room and map symbols
- [ ] Automated validation
- [ ] Debugger setup guide

## Milestone 101 — Runtime Debug Overlay

- [ ] Optional debug overlay
- [ ] Frame overrun indicator
- [ ] OAM and dropped-sprite data
- [ ] PPU queue usage
- [ ] Room and camera state
- [ ] Registered game-state values
- [ ] Controller toggle
- [ ] Compile out of release builds
- [ ] Preserve game PPU state
- [ ] Document costs

## Milestone 102 — Runtime Assertions

- [ ] `assert()`
- [ ] Preserve source locations
- [ ] Safe stop behavior
- [ ] Failure identifiers
- [ ] Screen and RAM failure reporting
- [ ] Emulator-readable state
- [ ] Compile out of release builds
- [ ] Runtime subsystem assertions
- [ ] Hardware behavior documentation

## Milestone 103 — Headless Emulator Test Runner

- [ ] Select a supported emulator workflow
- [ ] Launch ROMs automatically
- [ ] Run configured frame counts
- [ ] Inject controller input
- [ ] Read RAM
- [ ] Detect invalid opcodes, lockups and assertions
- [ ] Capture and compare screenshots
- [ ] Machine-readable results
- [ ] CI integration
- [ ] Windows and Linux support

## Milestone 104 — Static Performance Analysis

- [ ] Estimate procedure cycles where possible
- [ ] Detect unbounded frame loops
- [ ] Warn about expensive NMI operations
- [ ] Validate PPU access contexts
- [ ] Estimate PPU, metasprite and collision costs
- [ ] Warn about nested entity loops
- [ ] Identify 16-bit hot-path and page-crossing risks
- [ ] Separate guarantees from heuristics
- [ ] Document limitations

## Milestone 105 — Standard Library Consolidation

- [ ] Review naming
- [ ] Separate low-level and high-level APIs
- [ ] Stable namespaces
- [ ] Remove redundancy
- [ ] Deprecation and migration diagnostics
- [ ] Standardize coordinates, timers, collisions and handles
- [ ] Standardize callbacks
- [ ] Document side effects and NMI restrictions
- [ ] Freeze the 1.x standard-library surface

## Milestone 106 — NROM Showcase Game

- [ ] Complete documented game
- [ ] Title, gameplay, pause and game-over
- [ ] Multiple rooms or scrolling
- [ ] Animated metasprites
- [ ] Background and entity collision
- [ ] Projectiles, score and HUD
- [ ] Sound effects and music
- [ ] Restart flow
- [ ] Commented source
- [ ] Memory and performance measurements
- [ ] Stable frame rate
- [ ] Multi-emulator and hardware verification
- [ ] Publish ROM and source

## Milestone 107 — 1.x Compatibility and Migration Tests

- [ ] Compile fixtures for all 1.x releases
- [ ] Verify deprecated API diagnostics
- [ ] Verify manifest migrations
- [ ] Preserve language, ABI and calling-convention guarantees
- [ ] Preserve deterministic builds
- [ ] Historical project fixtures
- [ ] Document intentional breaks
- [ ] Automated migrations where practical

## Milestone 108 — Final NROM Documentation Set

- [ ] Complete language and runtime references
- [ ] Graphics pipeline, metatiles and metasprites
- [ ] Animations and collision
- [ ] Scrolling, rooms and 16-bit coordinates
- [ ] Audio and DPCM
- [ ] Optimization and debugging
- [ ] Headless testing
- [ ] Performance and hardware pitfalls
- [ ] Complete game tutorial
- [ ] Migration and troubleshooting guides

## Milestone 109 — Final NROM Release

- [ ] Complete required 1.x milestones
- [ ] Build the showcase
- [ ] Pass compiler, ROM and visual tests
- [ ] Verify deterministic release builds
- [ ] Verify clean Windows and Linux installations
- [ ] Verify emulator integrations
- [ ] Verify hardware execution
- [ ] Review and freeze public APIs
- [ ] Freeze the NROM runtime ABI
- [ ] Publish notes, migrations, packages, templates and showcase
- [ ] Tag the final NROM-focused 1.x release
- [ ] Begin 2.0 without breaking 1.x guarantees

---

# Release 2.0 — UxROM and Explicit PRG Banking

Goal: expand beyond the 32 KiB PRG-ROM limit with explicit PRG-ROM bank management.

Planned areas:

- UxROM mapper support
- Fixed and switchable PRG-ROM banks
- Explicit code-bank placement
- Explicit data-bank placement
- Far calls
- Bank-safe callbacks
- Bank-switching runtime
- Bank-aware linker generation
- Bank overflow diagnostics
- Initial bank usage reports

---

# Release 2.x — Automatic Bank Organization

Goal: let the compiler analyze and distribute code and data across UxROM banks.

Planned areas:

- Bank-aware call graph
- Automatic procedure placement
- Automatic constant and asset placement
- Fixed-bank residency analysis
- Bank-switch minimization
- Cross-bank call trampolines
- Bank pressure reports
- Placement hints and overrides
- Deterministic bank layout
- Incremental and whole-program bank optimization

---

# Release 3.0 — MMC1

Goal: support larger games with PRG banking, CHR banking and configurable mirroring.

Planned areas:

- MMC1 register protocol
- PRG banking modes
- CHR-ROM banking
- Runtime mirroring control
- PRG-RAM
- Save-game foundations
- Mapper-aware asset placement
- Mapper-aware linker generation
- Safe NMI and bank-switch interactions

---

# Release 3.x — Larger MMC1 Games

Planned areas:

- Save games
- Larger maps and room sets
- CHR asset groups
- Automatic CHR-bank allocation
- Mapper-aware graphics pipelines
- Persistent world state
- More advanced scrolling engines
- MMC1-specific diagnostics and profiling

---

# Release 4.0 — MMC3 and Advanced Engines

Goal: support scanline IRQs and more advanced rendering architectures.

Planned areas:

- MMC3 PRG and CHR banking
- Scanline IRQ support
- Split-screen rendering
- Fixed status bars
- Advanced scrolling
- CHR animation through banking
- IRQ-safe callbacks
- Mapper-specific runtime scheduling
- Advanced bank placement
- Larger engine-oriented project templates
