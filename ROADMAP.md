# nes-pascal Roadmap

## Philosophy

The compiler evolves through small, testable milestones.
Each milestone should produce a working compiler capable of generating a valid NES ROM.

---

## Milestone 1
- [x] Minimal compiler
- [x] Generate a valid NROM ROM
- [x] `nes.set_background_color()`
- [x] `nes.run`

---

## Milestone 2
- [x] Strongly typed constants
- [x] Built-in semantic type `nes_color`
- [x] Constant resolution
- [x] Semantic validation

---

## Milestone 3
- [x] Variables
- [x] Assignment
- [x] `byte`
- [x] `boolean`

---

## Milestone 4
- [ ] Arithmetic expressions
- [ ] Unary operators
- [ ] Binary operators

---

## Milestone 5
- [ ] IF / ELSE
- [ ] Boolean expressions

---

## Milestone 6
- [ ] Procedures
- [ ] Parameters
- [ ] Calling convention

---

## Milestone 7
- [ ] Controller input

---

## Milestone 8
- [ ] Sprite support

---

## Milestone 9
- [ ] NMI
- [ ] VBlank callbacks

---

## Future

- Zero-page allocation
- Optimization passes
- Bank switching
- Audio
- Inline Assembly
- User-defined types
