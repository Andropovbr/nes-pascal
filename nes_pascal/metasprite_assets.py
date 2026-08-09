"""PNG2CHR Studio metasprite metadata loading and compile-time validation."""

from __future__ import annotations

import json
from os import PathLike
from pathlib import Path
import re
from typing import Any

from .ast import (
    MetaspriteAsset,
    MetaspriteComponent,
    MetaspriteFrame,
)
from .diagnostics import CompilerError, DiagnosticCode, SourceLocation


SUPPORTED_FORMAT = "png2chr-studio-animation"
SUPPORTED_VERSION = 2
NES_SPRITE_TILE_CAPACITY = 256
NES_TILE_BYTES = 16
IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


def load_metasprite_assets(
    configured_paths: tuple[str | PathLike[str], ...],
    source_path: Path,
    source: str,
    chr_rom: bytes | None,
) -> tuple[MetaspriteAsset, ...]:
    """Load configured metadata files relative to the Pascal source."""

    if not configured_paths:
        return ()
    if chr_rom is None:
        _error(
            source_path,
            source,
            DiagnosticCode.INCOMPATIBLE_METASPRITE_CHR,
            "Metasprite metadata was configured without a CHR-ROM asset.",
            "Pass --chr with the 8 KiB CHR bank referenced by the metadata.",
        )

    assert chr_rom is not None
    chr_tile_capacity = min(
        NES_SPRITE_TILE_CAPACITY,
        len(chr_rom) // NES_TILE_BYTES,
    )
    assets: list[MetaspriteAsset] = []
    names: set[str] = set()
    next_frame_id = 0
    for configured_path in configured_paths:
        asset, next_frame_id = _load_one_asset(
            configured_path,
            source_path,
            source,
            chr_tile_capacity,
            next_frame_id,
        )
        normalized = asset.name.lower()
        if normalized in names:
            _error(
                source_path,
                source,
                DiagnosticCode.INVALID_METASPRITE_CONFIGURATION,
                f"Metasprite asset name {asset.name} is configured more than once.",
                "Give every configured metadata asset a unique root name.",
            )
        names.add(normalized)
        assets.append(asset)
    return tuple(assets)


def _load_one_asset(
    configured_path: str | PathLike[str],
    source_path: Path,
    source: str,
    chr_tile_capacity: int,
    first_frame_id: int,
) -> tuple[MetaspriteAsset, int]:
    original_path = str(configured_path)
    candidate = Path(configured_path)
    if not candidate.is_absolute():
        candidate = source_path.parent / candidate
    resolved_path = candidate.resolve()
    try:
        text = resolved_path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        _error(
            source_path,
            source,
            DiagnosticCode.METASPRITE_ASSET_NOT_FOUND,
            f"Configured metasprite metadata was not found: {original_path}.\n"
            f"Resolved path: {resolved_path}",
            "Check the --metasprite path. Relative paths use the source directory.",
            cause=error,
        )
    except (OSError, UnicodeError) as error:
        _error(
            source_path,
            source,
            DiagnosticCode.METASPRITE_ASSET_READ_FAILURE,
            f"Configured metasprite metadata cannot be read: {original_path}.\n"
            f"Resolved path: {resolved_path}\nError: {error}",
            "Provide a readable UTF-8 JSON metadata file.",
            cause=error,
        )

    try:
        document = json.loads(text)
    except json.JSONDecodeError as error:
        _error(
            source_path,
            source,
            DiagnosticCode.MALFORMED_METASPRITE_METADATA,
            f"Malformed metasprite JSON in {original_path} at metadata "
            f"line {error.lineno}, column {error.colno}: {error.msg}.",
            "Correct the JSON syntax and export the metadata again.",
            cause=error,
        )

    root = _mapping(document, "$", source_path, source)
    format_name = _string(root, "format", "$", source_path, source)
    if format_name != SUPPORTED_FORMAT:
        _error(
            source_path,
            source,
            DiagnosticCode.UNSUPPORTED_METASPRITE_FORMAT,
            f"Unsupported metasprite metadata format {format_name!r}; expected "
            f"{SUPPORTED_FORMAT!r}.",
            "Export PNG2CHR Studio animation metadata in the supported format.",
        )
    version = _integer(root, "version", "$", source_path, source)
    if version != SUPPORTED_VERSION:
        _error(
            source_path,
            source,
            DiagnosticCode.UNSUPPORTED_METASPRITE_VERSION,
            f"Unsupported metasprite metadata version {version}; expected "
            f"version {SUPPORTED_VERSION}.",
            "Re-export with the supported PNG2CHR Studio metadata version.",
        )

    asset_name = _identifier(
        _string(root, "name", "$", source_path, source),
        "$.name",
        source_path,
        source,
    ).lower()
    source_metadata = _mapping_field(root, "source", "$", source_path, source)
    if (
        _integer(source_metadata, "tile_width", "$.source", source_path, source)
        != 8
        or _integer(
            source_metadata,
            "tile_height",
            "$.source",
            source_path,
            source,
        )
        != 8
    ):
        _invalid(
            source_path,
            source,
            "$.source.tile_width/tile_height must describe 8x8 NES sprites.",
        )

    chr_metadata = _mapping_field(root, "chr", "$", source_path, source)
    declared_capacity = _integer(
        chr_metadata,
        "capacity_tiles",
        "$.chr",
        source_path,
        source,
    )
    final_tile_count = _integer(
        chr_metadata,
        "final_tile_count",
        "$.chr",
        source_path,
        source,
    )
    final_size = _integer(
        chr_metadata,
        "final_size_bytes",
        "$.chr",
        source_path,
        source,
    )
    if declared_capacity != NES_SPRITE_TILE_CAPACITY or final_size != 8192:
        _error(
            source_path,
            source,
            DiagnosticCode.INCOMPATIBLE_METASPRITE_CHR,
            "Metasprite metadata must target one 256-tile sprite pattern table "
            "inside an 8 KiB NROM CHR bank.",
            "Export for 8x8 NES sprites with capacity_tiles 256 and an "
            "8192-byte final CHR bank.",
        )
    if not 0 <= final_tile_count <= chr_tile_capacity:
        _error(
            source_path,
            source,
            DiagnosticCode.INCOMPATIBLE_METASPRITE_CHR,
            f"Metadata declares {final_tile_count} final tiles, but the current "
            f"sprite CHR table supports {chr_tile_capacity}.",
            "Use metadata and --chr data produced for the same NROM bank.",
        )

    flags = _mapping_field(root, "attribute_flags", "$", source_path, source)
    expected_flags = {
        "flip_horizontal": 0x40,
        "flip_vertical": 0x80,
        "palette_mask": 0x03,
    }
    for field, expected in expected_flags.items():
        actual = _integer(flags, field, "$.attribute_flags", source_path, source)
        if actual != expected:
            _invalid(
                source_path,
                source,
                f"$.attribute_flags.{field} must be {expected}, not {actual}.",
            )

    origin = _mapping_field(root, "origin", "$", source_path, source)
    origin_x = _integer(origin, "x", "$.origin", source_path, source)
    origin_y = _integer(origin, "y", "$.origin", source_path, source)
    animations = _list_field(root, "animations", "$", source_path, source)
    if not animations:
        _invalid(source_path, source, "$.animations must contain at least one animation.")

    frames: list[MetaspriteFrame] = []
    animation_names: set[str] = set()
    frame_id = first_frame_id
    for animation_index, animation_value in enumerate(animations):
        animation_path = f"$.animations[{animation_index}]"
        animation = _mapping(animation_value, animation_path, source_path, source)
        animation_name = _identifier(
            _string(animation, "name", animation_path, source_path, source),
            f"{animation_path}.name",
            source_path,
            source,
        ).lower()
        if animation_name in animation_names:
            _invalid(
                source_path,
                source,
                f"{animation_path}.name duplicates animation {animation_name!r}.",
            )
        animation_names.add(animation_name)
        frame_values = _list_field(
            animation,
            "frames",
            animation_path,
            source_path,
            source,
        )
        if not frame_values:
            _invalid(
                source_path,
                source,
                f"{animation_path}.frames must contain at least one frame.",
            )
        for animation_frame_index, frame_value in enumerate(frame_values):
            if frame_id > 0xFF:
                _error(
                    source_path,
                    source,
                    DiagnosticCode.INVALID_METASPRITE_CONFIGURATION,
                    "Configured metasprite assets exceed 256 symbolic frames.",
                    "Reduce the configured frame set for this NROM program.",
                )
            frame_path = f"{animation_path}.frames[{animation_frame_index}]"
            frame = _mapping(frame_value, frame_path, source_path, source)
            width = _positive_byte(frame, "width", frame_path, source_path, source)
            height = _positive_byte(frame, "height", frame_path, source_path, source)
            sprite_values = _list_field(
                frame,
                "sprites",
                frame_path,
                source_path,
                source,
            )
            if len(sprite_values) > 64:
                _invalid(
                    source_path,
                    source,
                    f"{frame_path}.sprites contains {len(sprite_values)} components; "
                    "one NES frame can use at most 64.",
                )
            components = tuple(
                _component(
                    component_value,
                    f"{frame_path}.sprites[{component_index}]",
                    final_tile_count,
                    source_path,
                    source,
                )
                for component_index, component_value in enumerate(sprite_values)
            )
            frames.append(
                MetaspriteFrame(
                    frame_id,
                    f"{asset_name}.{animation_name}_{animation_frame_index}",
                    asset_name,
                    animation_name,
                    animation_frame_index,
                    width,
                    height,
                    origin_x,
                    origin_y,
                    components,
                )
            )
            frame_id += 1
    return MetaspriteAsset(asset_name, original_path, tuple(frames)), frame_id


def _component(
    value: Any,
    path: str,
    final_tile_count: int,
    source_path: Path,
    source: str,
) -> MetaspriteComponent:
    component = _mapping(value, path, source_path, source)
    # PNG2CHR Studio exports these as signed offsets from the configured
    # top-level origin. The origin has already been subtracted by the producer;
    # subtracting it again here would move every non-zero-anchor metasprite.
    x_offset = _integer(component, "x", path, source_path, source)
    y_offset = _integer(component, "y", path, source_path, source)
    for name, offset in (("x", x_offset), ("y", y_offset)):
        flipped = -offset - 8
        if not -128 <= offset <= 127 or not -128 <= flipped <= 127:
            _invalid(
                source_path,
                source,
                f"{path}.{name} produces offset {offset}; both the original and "
                "8-pixel flipped offset must fit signed 8-bit range.",
            )
    tile = _integer(component, "tile", path, source_path, source)
    if not 0 <= tile < final_tile_count:
        _error(
            source_path,
            source,
            DiagnosticCode.INCOMPATIBLE_METASPRITE_CHR,
            f"{path}.tile is {tile}, outside metadata CHR tiles "
            f"0..{max(0, final_tile_count - 1)}.",
            "Re-export the metadata and CHR bank together.",
        )
    attributes = _integer(component, "attributes", path, source_path, source)
    if not 0 <= attributes <= 0xFF:
        _invalid(source_path, source, f"{path}.attributes must be $00..$FF.")
    palette = _integer(component, "palette", path, source_path, source)
    if not 0 <= palette <= 3 or attributes & 0x03 != palette:
        _invalid(
            source_path,
            source,
            f"{path}.palette must be 0..3 and equal attributes bits 0-1.",
        )
    horizontal_flip = _boolean(
        component,
        "horizontal_flip",
        path,
        source_path,
        source,
    )
    vertical_flip = _boolean(
        component,
        "vertical_flip",
        path,
        source_path,
        source,
    )
    if horizontal_flip != bool(attributes & 0x40):
        _invalid(
            source_path,
            source,
            f"{path}.horizontal_flip disagrees with attributes bit 6.",
        )
    if vertical_flip != bool(attributes & 0x80):
        _invalid(
            source_path,
            source,
            f"{path}.vertical_flip disagrees with attributes bit 7.",
        )
    return MetaspriteComponent(x_offset, y_offset, tile, attributes)


def _mapping(
    value: Any,
    path: str,
    source_path: Path,
    source: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        _invalid(source_path, source, f"{path} must be a JSON object.")
    return value


def _mapping_field(
    value: dict[str, Any],
    field: str,
    path: str,
    source_path: Path,
    source: str,
) -> dict[str, Any]:
    return _mapping(
        _required(value, field, path, source_path, source),
        f"{path}.{field}",
        source_path,
        source,
    )


def _list_field(
    value: dict[str, Any],
    field: str,
    path: str,
    source_path: Path,
    source: str,
) -> list[Any]:
    result = _required(value, field, path, source_path, source)
    if not isinstance(result, list):
        _invalid(source_path, source, f"{path}.{field} must be a JSON array.")
    return result


def _string(
    value: dict[str, Any],
    field: str,
    path: str,
    source_path: Path,
    source: str,
) -> str:
    result = _required(value, field, path, source_path, source)
    if not isinstance(result, str) or not result:
        _invalid(source_path, source, f"{path}.{field} must be a non-empty string.")
    return result


def _integer(
    value: dict[str, Any],
    field: str,
    path: str,
    source_path: Path,
    source: str,
) -> int:
    result = _required(value, field, path, source_path, source)
    if isinstance(result, bool) or not isinstance(result, int):
        _invalid(source_path, source, f"{path}.{field} must be an integer.")
    return result


def _positive_byte(
    value: dict[str, Any],
    field: str,
    path: str,
    source_path: Path,
    source: str,
) -> int:
    result = _integer(value, field, path, source_path, source)
    if not 1 <= result <= 0xFF:
        _invalid(source_path, source, f"{path}.{field} must be in 1..255.")
    return result


def _boolean(
    value: dict[str, Any],
    field: str,
    path: str,
    source_path: Path,
    source: str,
) -> bool:
    result = _required(value, field, path, source_path, source)
    if not isinstance(result, bool):
        _invalid(source_path, source, f"{path}.{field} must be boolean.")
    return result


def _required(
    value: dict[str, Any],
    field: str,
    path: str,
    source_path: Path,
    source: str,
) -> Any:
    if field not in value:
        _invalid(source_path, source, f"Missing required field {path}.{field}.")
    return value[field]


def _identifier(
    value: str,
    path: str,
    source_path: Path,
    source: str,
) -> str:
    if IDENTIFIER_PATTERN.fullmatch(value) is None:
        _invalid(
            source_path,
            source,
            f"{path} must be a Pascal-compatible identifier, not {value!r}.",
        )
    return value


def _invalid(source_path: Path, source: str, message: str) -> None:
    _error(
        source_path,
        source,
        DiagnosticCode.INVALID_METASPRITE_METADATA,
        message,
        "Correct the PNG2CHR Studio metadata and export it again.",
    )


def _error(
    source_path: Path,
    source: str,
    code: DiagnosticCode,
    message: str,
    suggestion: str,
    *,
    cause: Exception | None = None,
) -> None:
    error = CompilerError(
        code,
        message,
        SourceLocation(str(source_path), 1, 1),
        source.splitlines()[0] if source.splitlines() else "",
        suggestion=suggestion,
    )
    if cause is None:
        raise error
    raise error from cause
