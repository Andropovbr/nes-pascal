"""Loading and validation for compiler-owned static assets."""

from __future__ import annotations

from os import PathLike
from pathlib import Path

from .diagnostics import CompilerError, DiagnosticCode, SourceLocation


NROM_CHR_ROM_SIZE = 8 * 1024
NAMETABLE_SIZE = 1024
NAMETABLE_TILE_SIZE = 960
ATTRIBUTE_TABLE_SIZE = 64
COLLISION_MAP_WIDTH = 32
COLLISION_MAP_HEIGHT = 30
COLLISION_MAP_SOURCE_SIZE = COLLISION_MAP_WIDTH * COLLISION_MAP_HEIGHT
COLLISION_MAP_PACKED_SIZE = COLLISION_MAP_SOURCE_SIZE // 8


def load_chr_rom(
    configured_path: str | PathLike[str] | None,
    source_path: Path,
    source: str,
) -> bytes | None:
    """Load one optional CHR-ROM asset relative to the source directory."""

    if configured_path is None:
        return None

    original_path = str(configured_path)
    candidate = Path(configured_path)
    if not candidate.is_absolute():
        candidate = source_path.parent / candidate
    resolved_path = candidate.resolve()
    location = SourceLocation(str(source_path), 1, 1)
    source_line = source.splitlines()[0] if source.splitlines() else ""

    try:
        chr_rom = resolved_path.read_bytes()
    except FileNotFoundError as error:
        raise CompilerError(
            DiagnosticCode.CHR_ASSET_NOT_FOUND,
            f"Configured CHR-ROM file was not found: {original_path}.\n"
            f"Resolved path: {resolved_path}",
            location,
            source_line,
            suggestion=(
                "Check the --chr path. Relative paths are resolved from the "
                "source file's directory."
            ),
        ) from error
    except OSError as error:
        raise CompilerError(
            DiagnosticCode.CHR_ASSET_READ_FAILURE,
            f"Configured CHR-ROM file cannot be read: {original_path}.\n"
            f"Resolved path: {resolved_path}\n"
            f"Operating-system error: {error}",
            location,
            source_line,
            suggestion="Check that the file is readable and is not a directory.",
        ) from error

    actual_size = len(chr_rom)
    if actual_size != NROM_CHR_ROM_SIZE:
        raise CompilerError(
            DiagnosticCode.INVALID_CHR_ROM_SIZE,
            f"Invalid CHR-ROM size for {original_path}: expected "
            f"{NROM_CHR_ROM_SIZE} bytes (8 KiB), but found {actual_size} bytes.\n"
            f"Resolved path: {resolved_path}",
            location,
            source_line,
            suggestion="Provide exactly one 8 KiB CHR-ROM bank for NROM.",
        )

    return chr_rom


def load_background_data(
    nametable_path: str | PathLike[str] | None,
    tile_path: str | PathLike[str] | None,
    attribute_path: str | PathLike[str] | None,
    source_path: Path,
    source: str,
) -> bytes | None:
    """Load one raw nametable or a tile/attribute pair beside the source."""

    has_combined = nametable_path is not None
    has_tiles = tile_path is not None
    has_attributes = attribute_path is not None
    if not (has_combined or has_tiles or has_attributes):
        return None

    if has_combined and (has_tiles or has_attributes):
        _background_configuration_error(
            source_path,
            source,
            "A combined nametable cannot be configured together with separate "
            "tile or attribute data.",
            "Use --nametable alone, or use both --nametable-tiles and "
            "--nametable-attributes.",
        )
    if has_tiles != has_attributes:
        missing = "--nametable-attributes" if has_tiles else "--nametable-tiles"
        _background_configuration_error(
            source_path,
            source,
            "Separate background data requires both tile and attribute files.",
            f"Add {missing}, or replace the separate option with --nametable.",
        )

    if nametable_path is not None:
        return _load_background_asset(
            nametable_path,
            source_path,
            source,
            asset_name="Nametable",
            option_name="--nametable",
            expected_size=NAMETABLE_SIZE,
        )

    assert tile_path is not None and attribute_path is not None
    tiles = _load_background_asset(
        tile_path,
        source_path,
        source,
        asset_name="Nametable tile data",
        option_name="--nametable-tiles",
        expected_size=NAMETABLE_TILE_SIZE,
    )
    attributes = _load_background_asset(
        attribute_path,
        source_path,
        source,
        asset_name="Attribute table data",
        option_name="--nametable-attributes",
        expected_size=ATTRIBUTE_TABLE_SIZE,
    )
    return tiles + attributes


def load_collision_map(
    configured_path: str | PathLike[str] | None,
    source_path: Path,
    source: str,
) -> bytes | None:
    """Load a 30-by-32 text map of 0/1 flags and pack it to 120 ROM bytes."""

    if configured_path is None:
        return None
    original_path = str(configured_path)
    candidate = Path(configured_path)
    if not candidate.is_absolute():
        candidate = source_path.parent / candidate
    resolved_path = candidate.resolve()
    location = SourceLocation(str(source_path), 1, 1)
    source_line = source.splitlines()[0] if source.splitlines() else ""
    try:
        text = resolved_path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise CompilerError(
            DiagnosticCode.COLLISION_ASSET_NOT_FOUND,
            f"Configured collision-map file was not found: {original_path}.\n"
            f"Resolved path: {resolved_path}",
            location,
            source_line,
            suggestion=(
                "Check the --collision-map path. Relative paths are resolved "
                "from the source file's directory."
            ),
        ) from error
    except OSError as error:
        raise CompilerError(
            DiagnosticCode.COLLISION_ASSET_READ_FAILURE,
            f"Configured collision-map file cannot be read: {original_path}.\n"
            f"Resolved path: {resolved_path}\nOperating-system error: {error}",
            location,
            source_line,
            suggestion="Select a readable raw collision-map file.",
        ) from error

    rows = text.splitlines()
    if len(rows) != COLLISION_MAP_HEIGHT:
        raise CompilerError(
            DiagnosticCode.INVALID_COLLISION_ASSET,
            f"Invalid collision-map height for {original_path}: expected "
            f"{COLLISION_MAP_HEIGHT} rows, but found {len(rows)}.\n"
            f"Resolved path: {resolved_path}",
            location,
            source_line,
            suggestion=(
                f"Provide exactly {COLLISION_MAP_HEIGHT} text rows of "
                f"{COLLISION_MAP_WIDTH} collision flags."
            ),
        )
    flags: list[int] = []
    for y, row in enumerate(rows):
        if len(row) != COLLISION_MAP_WIDTH:
            raise CompilerError(
                DiagnosticCode.INVALID_COLLISION_ASSET,
                f"Invalid collision-map width on row {y} in {original_path}: "
                f"expected {COLLISION_MAP_WIDTH} flags, but found {len(row)}.",
                location,
                source_line,
                suggestion=(
                    f"Write exactly {COLLISION_MAP_WIDTH} characters on every row."
                ),
            )
        for x, value in enumerate(row):
            if value not in "01":
                raise CompilerError(
                    DiagnosticCode.INVALID_COLLISION_ASSET,
                    f"Invalid collision value {value!r} at tile ({x}, {y}) in "
                    f"{original_path}; only 0 (passable) and 1 (solid) are supported.",
                    location,
                    source_line,
                    suggestion="Replace every collision-map entry with 0 or 1.",
                )
            flags.append(int(value))

    packed = bytearray(COLLISION_MAP_PACKED_SIZE)
    for tile_index, value in enumerate(flags):
        if value:
            packed[tile_index >> 3] |= 1 << (tile_index & 7)
    return bytes(packed)


def _load_background_asset(
    configured_path: str | PathLike[str],
    source_path: Path,
    source: str,
    *,
    asset_name: str,
    option_name: str,
    expected_size: int,
) -> bytes:
    original_path = str(configured_path)
    candidate = Path(configured_path)
    if not candidate.is_absolute():
        candidate = source_path.parent / candidate
    resolved_path = candidate.resolve()
    location = SourceLocation(str(source_path), 1, 1)
    source_line = source.splitlines()[0] if source.splitlines() else ""

    try:
        data = resolved_path.read_bytes()
    except FileNotFoundError as error:
        raise CompilerError(
            DiagnosticCode.BACKGROUND_ASSET_NOT_FOUND,
            f"Configured {asset_name.lower()} file was not found: "
            f"{original_path}.\nResolved path: {resolved_path}",
            location,
            source_line,
            suggestion=(
                f"Check the {option_name} path. Relative paths are resolved "
                "from the source file's directory."
            ),
        ) from error
    except OSError as error:
        raise CompilerError(
            DiagnosticCode.BACKGROUND_ASSET_READ_FAILURE,
            f"Configured {asset_name.lower()} file cannot be read: "
            f"{original_path}.\nResolved path: {resolved_path}\n"
            f"Operating-system error: {error}",
            location,
            source_line,
            suggestion="Check that the file is readable and is not a directory.",
        ) from error

    actual_size = len(data)
    if actual_size != expected_size:
        raise CompilerError(
            DiagnosticCode.INVALID_BACKGROUND_ASSET_SIZE,
            f"Invalid {asset_name.lower()} size for {original_path}: expected "
            f"{expected_size} bytes, but found {actual_size} bytes.\n"
            f"Resolved path: {resolved_path}",
            location,
            source_line,
            suggestion=(
                "Provide exactly 1024 bytes for a combined nametable, or "
                "exactly 960 tile bytes and 64 attribute bytes separately."
            ),
        )
    return data


def _background_configuration_error(
    source_path: Path,
    source: str,
    message: str,
    suggestion: str,
) -> None:
    source_line = source.splitlines()[0] if source.splitlines() else ""
    raise CompilerError(
        DiagnosticCode.INVALID_BACKGROUND_ASSET_CONFIGURATION,
        message,
        SourceLocation(str(source_path), 1, 1),
        source_line,
        suggestion=suggestion,
    )
