import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from nes_pascal.assets import NROM_CHR_ROM_SIZE, load_chr_rom
from nes_pascal.diagnostics import CompilerError, DiagnosticCode


SOURCE = "program AssetTest;\nbegin\n    nes.set_background_color($21);\n    nes.run;\nend.\n"


class ChrRomAssetTests(unittest.TestCase):
    def test_no_configured_asset_uses_the_backend_default(self) -> None:
        self.assertIsNone(load_chr_rom(None, Path("project/main.nsp"), SOURCE))

    def test_valid_asset_is_loaded_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project = Path(temporary_directory)
            source_path = project / "main.nsp"
            expected = bytes(range(256)) * 32
            asset_path = project / "graphics.chr"
            asset_path.write_bytes(expected)

            actual = load_chr_rom("graphics.chr", source_path, SOURCE)

        self.assertEqual(actual, expected)

    def test_relative_path_normalizes_subdirectories_and_parent_components(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project = Path(temporary_directory)
            source_path = project / "source" / "main.nsp"
            asset_path = project / "assets" / "tiles.chr"
            asset_path.parent.mkdir()
            asset_path.write_bytes(bytes(NROM_CHR_ROM_SIZE))

            previous_cwd = Path.cwd()
            unrelated_cwd = project / "elsewhere"
            unrelated_cwd.mkdir()
            try:
                os.chdir(unrelated_cwd)
                actual = load_chr_rom(
                    "../assets/./tiles.chr",
                    source_path,
                    SOURCE,
                )
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(actual, bytes(NROM_CHR_ROM_SIZE))

    def test_absolute_path_remains_supported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            asset_path = Path(temporary_directory) / "tiles.chr"
            expected = bytes([0xA5]) * NROM_CHR_ROM_SIZE
            asset_path.write_bytes(expected)

            actual = load_chr_rom(asset_path.resolve(), Path("main.nsp"), SOURCE)

        self.assertEqual(actual, expected)

    def test_missing_asset_has_stable_diagnostic_and_both_paths(self) -> None:
        source_path = Path("project/main.nsp").resolve()
        with self.assertRaises(CompilerError) as raised:
            load_chr_rom("assets/missing.chr", source_path, SOURCE)

        message = str(raised.exception)
        self.assertEqual(raised.exception.code, DiagnosticCode.CHR_ASSET_NOT_FOUND)
        self.assertIn("assets/missing.chr", message)
        self.assertIn(str((source_path.parent / "assets/missing.chr").resolve()), message)

    def test_unreadable_asset_has_stable_diagnostic(self) -> None:
        with patch.object(Path, "read_bytes", side_effect=OSError("access denied")):
            with self.assertRaises(CompilerError) as raised:
                load_chr_rom("tiles.chr", Path("project/main.nsp"), SOURCE)

        self.assertEqual(
            raised.exception.code,
            DiagnosticCode.CHR_ASSET_READ_FAILURE,
        )
        self.assertIn("access denied", str(raised.exception))

    def test_empty_small_and_large_assets_report_expected_and_actual_sizes(self) -> None:
        sizes = (0, NROM_CHR_ROM_SIZE - 1, NROM_CHR_ROM_SIZE + 1)
        with tempfile.TemporaryDirectory() as temporary_directory:
            project = Path(temporary_directory)
            source_path = project / "main.nsp"
            for size in sizes:
                with self.subTest(size=size):
                    asset_path = project / f"tiles-{size}.chr"
                    asset_path.write_bytes(bytes(size))
                    with self.assertRaises(CompilerError) as raised:
                        load_chr_rom(asset_path.name, source_path, SOURCE)

                    self.assertEqual(
                        raised.exception.code,
                        DiagnosticCode.INVALID_CHR_ROM_SIZE,
                    )
                    message = str(raised.exception)
                    self.assertIn("expected 8192 bytes", message)
                    self.assertIn(f"found {size} bytes", message)


if __name__ == "__main__":
    unittest.main()
