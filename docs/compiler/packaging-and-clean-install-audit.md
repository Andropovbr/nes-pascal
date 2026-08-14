# Packaging, Distribution, and Clean-Installation Audit

English | [Português (Brasil)] — *PT-BR translation pending*

## Summary

This is an independent packaging, distribution, and clean-installation audit of
the NES Pascal compiler. Its goal is to verify that a user can obtain the
project from the repository, build and install the Python package in a clean
environment, invoke the CLI correctly, compile a valid NES Pascal program, and
understand the external `ca65`/`ld65` toolchain requirement.

The audit did not change compiler semantics, runtime behavior, packaging
configuration, CI, package structure, or CLI behavior. Only mechanical
documentation changes were made.

**Result:** the packaged compiler is functional. No P0 or P1 findings.
Three P2 findings and several P3 findings are reported below. The P2 findings
concern missing console-script entry point, incomplete installation
documentation for installed-package usage, and absent CI packaging coverage.
None of the findings block obtaining, installing, invoking, or using the
compiler today.

- **Branch:** `audit/packaging-and-clean-install`
- **Base commit (audited):** `dee2471` (`Merge pull request #32 from
  Andropovbr/chore/examples-docs-p2-hardening`), in sync with `origin/main`
- **Package version:** `0.5.8`
- **Python tested:** 3.12.3 (only interpreter available locally)
- **pip:** 26.2.1 (bootstrapped into the audit virtual environments)
- **Build frontend:** `build` 1.5.0; isolated backend `setuptools` 84.0.0
- **Toolchain:** `ca65`/`ld65` V2.18 (Ubuntu 2.19-1), present on `PATH`
- **Emulator:** Mesen (`MESEN_PATH=/usr/local/bin/mesen`), 29 runtime tests OK

---

## 1. Package metadata inventory

Source of truth: `pyproject.toml`.

| Field | Declared value |
| :--- | :--- |
| Package name | `nes-pascal` |
| Version | `0.5.8` |
| Requires-Python | `>=3.11` |
| Build backend | `setuptools.build_meta` (`setuptools>=68`) |
| Description / Summary | `Prototype Pascal compiler specialized for the NES` |
| Runtime dependencies | none declared (`Requires-Dist` absent) |
| Optional / dev dependencies | none declared |
| License metadata | none declared (setuptools auto-detects the `LICENSE` file; wheel METADATA is `Dynamic: license-file`) |
| README metadata | none declared (no `readme` key; METADATA has no Long Description) |
| Project URLs | none declared |
| Console-script / CLI entry points | none declared (no `[project.scripts]`) |
| Package discovery | `[tool.setuptools.packages.find]` include `nes_pascal*` |

The installed-wheel METADATA reflects exactly this:

```text
Metadata-Version: 2.4
Name: nes-pascal
Version: 0.5.8
Summary: Prototype Pascal compiler specialized for the NES
Requires-Python: >=3.11
License-File: LICENSE
Dynamic: license-file
```

The metadata is internally consistent (name, version, Python range, summary).
The notable gaps are the missing console-script entry point, README/long
description, license expression, and project URLs. The version `0.5.8` is a
stale milestone-era value relative to implemented features; see
[Version consistency](#10-version-consistency).

## 2. Clean virtual-environment installation

The system interpreter is `/usr/bin/python3` (3.12.3) and has neither `pip`
nor `ensurepip` (Debian/Ubuntu without the `python3-venv` package, no sudo
available). Virtual environments were created with
`python3 -m venv --without-pip` and `pip` was bootstrapped with the official
`get-pip.py` into each venv. Each venv is fully isolated in `/tmp/opencode`
with its own `site-packages`; no repository-local `PYTHONPATH`, no previously
installed dependencies, and no working-tree files were involved.

- `pip install .` from the repository (fresh venv): **OK**
  - `import nes_pascal` → version `0.5.8`; `import nes_pascal.cli` → OK
  - `pip install .` from a pristine `git archive` checkout: **OK**
- `pip install -e .` from the repository (fresh venv): **OK**
  - `python -m nes_pascal.cli --version` → `nes-pascal 0.5.8`
- `pip install <wheel>` (fresh venv): **OK**
- `pip install <sdist>` (fresh venv): **OK**

Installation does not depend on repository-local `PYTHONPATH`, pre-installed
dependencies, generated files in the working tree, or editable-install-only
behavior.

## 3. Wheel build and installation

Built with the declared backend using the standards-based frontend
(`python -m build`), installed into an isolated audit environment only (not a
runtime dependency):

```text
nes_pascal-0.5.8-py3-none-any.whl   (91,998 bytes)
```

- Wheel builds successfully.
- Filename/version are correct (`nes_pascal-0.5.8-py3-none-any.whl`).
- Installed into a fresh clean venv: import succeeds, `nes_pascal.__version__`
  is `0.5.8`.
- Installed CLI works via `python -m nes_pascal.cli`.

## 4. Source distribution audit

```text
nes_pascal-0.5.8.tar.gz   (161,048 bytes)
```

- sdist builds successfully.
- A fresh environment installs from the sdist and compiles a program
  end-to-end (see section 6).
- All runtime source modules are present in both artifacts.
- **No package-relative runtime resources exist.** The compiler has no
  templates, linker/runtime resources, configuration data, or default assets
  shipped inside the package. All assets (CHR-ROM, nametable, metasprite JSON)
  are user-supplied project files resolved relative to the `.nsp` source, so
  there is nothing that could be "present only because installation came from
  a repository checkout." An `import nes_pascal` alone is therefore a
  sufficient packaging check for this project.
- The sdist includes the top-level `tests/test_*.py` modules but not
  `tests/fixtures/`, `tests/golden/`, `tests/mesen/`, `tests/__init__.py`,
  `examples/`, or `docs/`. This is conventional and acceptable for sdists;
  none of those are required at runtime.

## 5. Installed CLI audit

From the clean wheel-installed environment (no repository context):

| Invocation | Result |
| :--- | :--- |
| `python -m nes_pascal.cli --version` | `nes-pascal 0.5.8`, exit 0 |
| `python -m nes_pascal.cli -V` | `nes-pascal 0.5.8`, exit 0 |
| `python -m nes_pascal.cli --help` | usage + option help, exit 0 |
| `python -m nes_pascal.cli` (no args) | argparse usage error, exit 2 |
| `python -m nes_pascal.cli /nonexistent.nsp -o x.nes` | file-access diagnostic, exit 1 |
| `nes-pascal --version` | **not available** — no console script is installed |

Version output matches package metadata. Diagnostics display normally on
stderr with `E`-codes and exit code 1. Invalid invocation exits with code 2.

## 6. End-to-end compile from outside the repository

A temporary project directory outside the repository
(`/tmp/opencode/nes-proj-outside`) was created containing a minimal valid
`.nsp` program. Using only the wheel-installed package, with the repository
not on the path and not the working directory:

```text
source .nsp  ->  installed NES Pascal  ->  .asm/.cfg/.map  ->  ca65  ->  ld65  ->  .nes
```

Result: **successful**. Generated `main.asm`, `main.cfg`, `main.map`,
`main.o`, and `main.nes`; the ROM is 40,976 bytes (16-byte header + 32 KiB
PRG + 8 KiB CHR) with a valid `NES\x1a` header.

**Missing-toolchain diagnostic:** with `PATH` restricted so that neither
`ca65` nor `ld65` is discoverable, the compiler stage still runs, writes the
`.asm`/`.cfg`/`.map` files, and then exits 1 with:

```text
E5001: missing toolchain component: ca65 and ld65. Install the cc65 package and try again.
```

This matches the documented E5001 behavior.

## 7. Asset path behavior after installation

Real bundled assets were copied into the temporary outside-repository project
(`chr_asset.chr`, `nametable_loading.nam`, `game.chr`, `player_idle.json`),
and project-relative paths were passed to the installed compiler:

- CHR-ROM + nametable backed program: **OK**
  (`--chr assets/chr_asset.chr --nametable assets/nametable_loading.nam`).
- Metasprite backed program: **OK**
  (`--chr assets/game.chr --metasprite assets/player_idle.json`).

User-supplied project files continue to resolve relative to the `.nsp` source
after the compiler is installed elsewhere. Nothing needs to be shipped inside
the Python package.

## 8. External dependency documentation

Documented in `docs/getting-started/prerequisites-and-installation.md`
(EN and PT-BR) and `docs/reference/diagnostics/code-generation.md`
(E5001/E5002, EN and PT-BR):

- The Python package installation does not install cc65. This is stated
  implicitly by the prerequisite list (cc65 is listed as a prerequisite, and
  "the compiler has no runtime Python dependencies outside the standard
  library").
- `ca65` and `ld65` are external toolchain dependencies required for final ROM
  generation; the E5001 diagnostic states this explicitly.
- Missing-toolchain behavior is documented: E5001 is emitted when a component
  is not on `PATH` (documented trigger: "with cc65 absent from PATH").
- `PATH` discovery is required: the CLI uses `shutil.which("ca65")` /
  `shutil.which("ld65")`.
- Commands that still work without the toolchain: the compiler stage itself
  (parse, semantic analysis, memory layout, Assembly/linker-config/memory-map
  generation). The `.asm`, `.cfg`, and `.map` outputs are written before the
  E5001 diagnostic is raised. The full ROM build does not work without the
  toolchain.

Documentation is accurate; no misleading setup instructions were found.

## 9. Package contents audit

Wheel contents (13 modules + dist-info):

```text
nes_pascal/{__init__,assets,ast,backend_ca65,builtins,cli,codegen_analysis,
diagnostics,lexer,memory_layout,metasprite_assets,parser,semantic}.py
nes_pascal-0.5.8.dist-info/{licenses/LICENSE,METADATA,WHEEL,RECORD,top_level.txt}
```

No unexpected contents in the wheel: no `tests/`, no `docs/`, no `examples/`,
no `.pyc`, no caches, no `build/` artifacts, no generated Assembly/ROMs, no
benchmark output. The LICENSE file is intentionally included.

sdist contents: the package, `pyproject.toml`, `README.md`, `LICENSE`,
generated `setup.cfg`, `nes_pascal.egg-info`, and the top-level `tests/*.py`
modules (conventional for sdists; fixtures/golden/mesen data and examples are
not included and are not required at runtime).

No large or unexpected files were found in either artifact.

## 10. Version consistency

| Source | Value |
| :--- | :--- |
| `pyproject.toml` (authoritative) | `0.5.8` |
| `nes_pascal/__init__.py` fallback | `0.5.8` |
| CLI version output | `nes-pascal 0.5.8` |
| Wheel METADATA / filename | `0.5.8` |
| sdist filename / PKG-INFO | `0.5.8` |
| README / docs version claims | none |

All values agree today. Findings:

- **P3-2a:** The package version `0.5.8` is a stale milestone-era value. The
  code implements through milestone 0.5.12 (records, expression temporaries,
  functions), while the package version still matches milestone 0.5.8. This is
  not a breakage, but the version no longer communicates implemented scope.
- **P3-2b:** `nes_pascal/__init__.py` hard-codes the `0.5.8` fallback, a
  second source of truth that can drift from `pyproject.toml`. (The
  `importlib.metadata` lookup is the primary source; the fallback duplicates
  the version.)

## 11. Python-version compatibility

- Declared range: `>=3.11`.
- Tested locally: Python 3.12.3 only (the only interpreter available; 3.11 was
  not locally testable).
- All `nes_pascal/`, `tests/`, and `tools/` modules were parsed with
  `ast.parse(feature_version=(3, 11))`: **all parse under the 3.11 grammar**,
  so no syntax newer than the declared minimum was found.
- Compatibility with 3.11 is therefore evidenced by grammar analysis only, not
  by an executed 3.11 interpreter. This limitation is reported; do not claim
  executed 3.11 compatibility from this audit.

## 12. Reproducibility / dirty-tree dependence

The working tree contained `build/` and `__pycache__/` artifacts during the
first build. A second build was run from the same tree, and a third from a
pristine `git archive` checkout:

- sdist name lists are identical across all three builds.
- Wheel name lists are identical; wheel byte size is identical
  (91,998 bytes). Wheels differ only in the ZIP container timestamp field
  (byte 11), which is expected archive metadata and not a content difference.

No dependence on stale generated files was found. (Note: `build/`,
`dist/`, `*.egg-info/`, and `__pycache__/` are already gitignored.)

## 13. Installation documentation cross-check

A new user following `docs/getting-started/prerequisites-and-installation.md`
and `docs/getting-started/first-program.md` (EN and PT-BR mirror pages):

- Supported Python versions: documented (`Python 3.11 or newer`).
- How to install NES Pascal: only "run from the repository root" / optional
  `pip install -e .` is documented. **No documented `pip install .`, wheel,
  or sdist install path.**
- How to invoke it: only `python -m nes_pascal.cli` is documented. **No
  documented `nes-pascal` console command** (which is consistent with the
  missing entry point, but the reader is never told the module invocation is
  the only public entry).
- How to obtain/use ca65 and ld65: prerequisite link to cc65 and `PATH`
  requirement are present.
- How to compile a minimal program: documented.
- Where generated files appear: documented (`build/*.asm`, `.cfg`, `.map`,
  `.o`, `.nes`).
- How to interpret a missing-toolchain error: documented (E5001).

Gap: the documentation never covers using the package after a clean install
outside the repository. This is finding **P2-2**.

## 14. CI packaging coverage

Current CI (`.github/workflows/ci.yml`) installs the project with
`pip install -e .` from the repository checkout in both jobs
(`compiler-toolchain` and `mesen-runtime`) and never builds or installs a
release artifact. Gaps:

- no wheel build;
- no sdist build;
- no install-from-wheel (or install-from-sdist) smoke test;
- no console-script smoke test (the absence of `[project.scripts]` went
  unnoticed);
- no compile-from-outside-repository test.

This is finding **P2-3**. Minimal recommended packaging smoke coverage for a
future packaging-hardening branch (not implemented during this audit):

1. build the wheel and sdist (`python -m build`);
2. install the wheel into a fresh virtual environment;
3. assert `python -m nes_pascal.cli --version` and, once an entry point
   exists, `nes-pascal --version`;
4. compile a minimal `.nsp` from a directory outside the repository using the
   installed wheel (with and without the toolchain on `PATH`).

---

## Findings classification

**P0 — released/installed compiler is unusable or produces invalid output:**
none.

**P1 — clean installation or packaged CLI materially broken:** none.
Installation succeeds from wheel, sdist, `pip install .`, and
`pip install -e .`; the packaged CLI works; end-to-end ROM builds work from
outside the repository.

**P2 — important packaging/release regression gap or misleading install
docs:**

- **P2-1 — No console-script entry point.** `pyproject.toml` declares no
  `[project.scripts]`, so `pip install` never provides a `nes-pascal` command.
  The only public entry is `python -m nes_pascal.cli`. The argparse `prog`
  name `nes-pascal` suggests an intended command that is never installed.
- **P2-2 — Installation docs do not cover installed-package usage.** The
  getting-started docs only describe running from the repository root or an
  editable install. A user with only the installed package has no documented
  install (`pip install .` / wheel) or invocation path outside the repository.
- **P2-3 — No CI packaging coverage.** CI only runs `pip install -e .` from
  the checkout. No wheel/sdist build, no install-from-artifact test, no
  console-script smoke test, no outside-repository compile test. This let
  P2-1 go undetected.

**P3 — metadata, polish, optional CI hardening:**

- **P3-1 — Metadata completeness.** No `readme`/long description, no license
  expression (only auto-detected `LICENSE` file), no `[project.urls]` in the
  wheel METADATA.
- **P3-2 — Version staleness and duplication.** Package version `0.5.8` lags
  implemented milestones 0.5.9–0.5.12, and the `0.5.8` fallback in
  `nes_pascal/__init__.py` is a second version source that can drift.
- **P3-3 — PT-BR translation.** This audit report is English-only; the
  `docs/pt-BR/` mirror index and translation-status list were not updated
  (consistent with the precedent of `diagnostic-consistency-audit.md`).
- **P3-4 — sdist test inclusion.** The sdist ships the top-level `tests/*.py`
  modules (without fixtures/golden/mesen data). Conventional and acceptable;
  listed for completeness. The wheel ships no tests.

## Recommended follow-up (separate branch, out of scope here)

1. Add `[project.scripts]` with `nes-pascal = "nes_pascal.cli:main"` and a
   corresponding smoke test.
2. Add packaging metadata: `readme`, license expression, `[project.urls]`.
3. Update getting-started documentation to cover `pip install .` / wheel
   install and installed-package invocation.
4. Add minimal CI packaging smoke coverage (wheel + sdist build,
   install-from-artifact, console-script/module smoke test, outside-repository
   compile).
5. Align the package version with implemented milestone scope and remove the
   duplicated fallback version.

## Local validation

- `make PYTHON=python3 test` — 537 tests, OK.
- `make PYTHON=python3 validate` (test-all + benchmark + rom) — exit 0.
- `make PYTHON=python3 test-mesen` with `MESEN_PATH=/usr/local/bin/mesen` —
  29 tests, OK.
- Clean-environment packaging tests were independent of the working-tree
  interpreter (fresh venvs in `/tmp/opencode`).

## CI run

The audit branch is intended to be pushed and validated by the repository's
authoritative GitHub Actions gate (`ci-gate`). See the branch push/CI result
for the final gate status.

---

## Appendix: exact versions and commands

- Interpreter: `python3` 3.12.3 (`/usr/bin/python3`), CPython.
- pip: 26.2.1 (bootstrapped via `get-pip.py` into each venv).
- Build frontend: `build` 1.5.0; isolated backend `setuptools` 84.0.0.
- Toolchain: `ca65`/`ld65` V2.18 (Ubuntu 2.19-1).
- Build: `python -m build --outdir <dir> <source-tree>`.
- Install tests: `pip install .`, `pip install -e .`,
  `pip install <wheel>`, `pip install <sdist>` in fresh venvs.
- Outside-repo compile: `python -m nes_pascal.cli main.nsp -o out/main.nes`
  from `/tmp/opencode/nes-proj-outside`.