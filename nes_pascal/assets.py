"""Loading and validation for compiler-owned static assets."""

from __future__ import annotations

from os import PathLike
from pathlib import Path

from .diagnostics import CompilerError, DiagnosticCode, SourceLocation


NROM_CHR_ROM_SIZE = 8 * 1024


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
