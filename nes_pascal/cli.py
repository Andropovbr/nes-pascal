"""Command-line interface for the NES Pascal compiler."""

import argparse
from dataclasses import replace
from pathlib import Path
import shutil
import subprocess
import sys

from .assets import load_background_data, load_chr_rom
from .ast import ResolvedLoadBackground
from .backend_ca65 import generate
from .diagnostics import CompilerError, DiagnosticCode, SourceLocation
from .memory_layout import (
    DEFAULT_MEMORY_LAYOUT_SETTINGS,
    MemoryLayoutSettings,
    build_memory_layout,
    generate_linker_config,
    generate_memory_map,
)
from .parser import parse
from .semantic import analyze


class ToolchainError(Exception):
    pass


def compile_source(
    source_path: Path,
    output_path: Path,
    memory_settings: MemoryLayoutSettings = DEFAULT_MEMORY_LAYOUT_SETTINGS,
    chr_path: str | Path | None = None,
    nametable_path: str | Path | None = None,
    nametable_tiles_path: str | Path | None = None,
    nametable_attributes_path: str | Path | None = None,
    mirroring: str | None = None,
) -> tuple[Path, Path]:
    source_path = source_path.resolve()
    output_path = output_path.resolve()
    source = source_path.read_text(encoding="utf-8")
    if mirroring is not None:
        normalized_mirroring = mirroring.lower()
        if normalized_mirroring not in ("horizontal", "vertical"):
            raise CompilerError(
                DiagnosticCode.INVALID_MIRRORING_CONFIGURATION,
                f"Invalid mirroring configuration: {mirroring}.",
                SourceLocation(str(source_path), 1, 1),
                source.splitlines()[0] if source.splitlines() else "",
                suggestion="Use --mirroring horizontal or --mirroring vertical.",
            )
        memory_settings = replace(
            memory_settings,
            horizontal_mirroring=normalized_mirroring == "horizontal",
        )
    program = parse(source, str(source_path))
    resolved_program = analyze(program, source, str(source_path))
    chr_rom = load_chr_rom(chr_path, source_path, source)
    background_data = load_background_data(
        nametable_path,
        nametable_tiles_path,
        nametable_attributes_path,
        source_path,
        source,
    )
    has_background_load = any(
        isinstance(statement, ResolvedLoadBackground)
        for statement in resolved_program.statements
    )
    if has_background_load and background_data is None:
        raise CompilerError(
            DiagnosticCode.BACKGROUND_ASSET_REQUIRED,
            "nes.load_background() requires configured nametable data.",
            SourceLocation(str(source_path), 1, 1),
            source.splitlines()[0] if source.splitlines() else "",
            suggestion=(
                "Pass --nametable with one 1024-byte file, or pass both "
                "--nametable-tiles and --nametable-attributes."
            ),
        )
    if background_data is not None and not has_background_load:
        raise CompilerError(
            DiagnosticCode.INVALID_BACKGROUND_ASSET_CONFIGURATION,
            "Background data was configured, but the program does not call "
            "nes.load_background().",
            SourceLocation(str(source_path), 1, 1),
            source.splitlines()[0] if source.splitlines() else "",
            suggestion="Add one nes.load_background(); call before nes.run;.",
        )
    layout = build_memory_layout(
        resolved_program,
        memory_settings,
        source=source,
        filename=str(source_path),
    )
    assembly = generate(
        resolved_program,
        layout,
        chr_rom=chr_rom,
        background_data=background_data,
    )
    linker_config = generate_linker_config(layout)
    memory_map = generate_memory_map(layout)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    assembly_path = output_path.with_suffix(".asm")
    config_path = output_path.with_suffix(".cfg")
    memory_map_path = output_path.with_suffix(".map")
    object_path = output_path.with_suffix(".o")
    assembly_path.write_text(assembly, encoding="utf-8", newline="\n")
    config_path.write_text(linker_config, encoding="utf-8", newline="\n")
    memory_map_path.write_text(memory_map, encoding="utf-8", newline="\n")

    ca65 = shutil.which("ca65")
    ld65 = shutil.which("ld65")
    missing = [name for name, path in (("ca65", ca65), ("ld65", ld65)) if path is None]
    if missing:
        names = " and ".join(missing)
        raise ToolchainError(
            f"{DiagnosticCode.MISSING_TOOLCHAIN}: "
            f"missing toolchain component: {names}. "
            "Install the cc65 package and try again."
        )

    _run_tool([ca65, str(assembly_path), "-o", str(object_path)], "ca65")
    _run_tool(
        [
            ld65,
            "-C",
            str(config_path),
            str(object_path),
            "-o",
            str(output_path),
        ],
        "ld65",
    )
    return assembly_path, output_path


def _run_tool(command: list[str], tool_name: str) -> None:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise ToolchainError(
            f"{DiagnosticCode.TOOLCHAIN_FAILURE}: {tool_name} failed.\n\n{detail}"
        )


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nes-pascal",
        description="Compile the current NES Pascal subset to an NROM image.",
    )
    parser.add_argument("source", type=Path, help=".nsp source file")
    parser.add_argument("-o", "--output", required=True, type=Path, help=".nes ROM")
    parser.add_argument(
        "--chr",
        type=str,
        help="8 KiB .chr asset; relative paths use the source file directory",
    )
    parser.add_argument(
        "--nametable",
        type=str,
        help="1 KiB raw nametable; relative paths use the source file directory",
    )
    parser.add_argument(
        "--nametable-tiles",
        type=str,
        help="960-byte tile map used with --nametable-attributes",
    )
    parser.add_argument(
        "--nametable-attributes",
        type=str,
        help="64-byte attribute table used with --nametable-tiles",
    )
    parser.add_argument(
        "--mirroring",
        type=str,
        default="horizontal",
        help="static nametable mirroring: horizontal (default) or vertical",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_argument_parser().parse_args(argv)
    try:
        assembly_path, rom_path = compile_source(
            arguments.source,
            arguments.output,
            chr_path=arguments.chr,
            nametable_path=arguments.nametable,
            nametable_tiles_path=arguments.nametable_tiles,
            nametable_attributes_path=arguments.nametable_attributes,
            mirroring=arguments.mirroring,
        )
    except (CompilerError, ToolchainError) as error:
        print(error, file=sys.stderr)
        return 1
    except OSError as error:
        print(
            f"{DiagnosticCode.FILE_ACCESS_FAILURE}: "
            f"could not access a file: {error}",
            file=sys.stderr,
        )
        return 1
    print(f"Assembly: {assembly_path}")
    print(f"Linker configuration: {rom_path.with_suffix('.cfg')}")
    print(f"Memory map: {rom_path.with_suffix('.map')}")
    print(f"ROM: {rom_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
