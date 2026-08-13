import os
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from nes_pascal.assets import (
    ATTRIBUTE_TABLE_SIZE,
    NAMETABLE_SIZE,
    NAMETABLE_TILE_SIZE,
    load_background_data,
)
from nes_pascal.ast import LoadBackground, ResolvedLoadBackground
from nes_pascal.backend_ca65 import generate
from nes_pascal.cli import build_argument_parser, compile_source
from nes_pascal.diagnostics import CompilerError, DiagnosticCode
from nes_pascal.memory_layout import build_memory_layout
from nes_pascal.parser import parse
from nes_pascal.semantic import analyze


SOURCE = """program Background;
begin
    nes.load_background();
    nes.set_background_color($0F);
    nes.run;
end.
"""


def analyze_source(source: str = SOURCE, filename: str = "background.nsp"):
    return analyze(parse(source, filename), source, filename)


class NametableAssetTests(unittest.TestCase):
    def test_no_configuration_returns_no_background_data(self) -> None:
        self.assertIsNone(
            load_background_data(None, None, None, Path("main.nsp"), SOURCE)
        )

    def test_valid_combined_nametable_is_loaded_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project = Path(temporary_directory)
            expected = bytes(range(256)) * 4
            (project / "screen.nam").write_bytes(expected)

            actual = load_background_data(
                "screen.nam",
                None,
                None,
                project / "main.nsp",
                SOURCE,
            )

        self.assertEqual(actual, expected)

    def test_separate_tile_and_attribute_files_are_concatenated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project = Path(temporary_directory)
            tiles = bytes((index % 256 for index in range(NAMETABLE_TILE_SIZE)))
            attributes = bytes([0xE4]) * ATTRIBUTE_TABLE_SIZE
            (project / "tiles.bin").write_bytes(tiles)
            (project / "attributes.bin").write_bytes(attributes)

            actual = load_background_data(
                None,
                "tiles.bin",
                "attributes.bin",
                project / "main.nsp",
                SOURCE,
            )

        self.assertEqual(actual, tiles + attributes)

    def test_absolute_nametable_path_remains_supported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            asset_path = Path(temporary_directory) / "screen.nam"
            expected = bytes([0xA5]) * NAMETABLE_SIZE
            asset_path.write_bytes(expected)

            actual = load_background_data(
                asset_path.resolve(),
                None,
                None,
                Path("main.nsp"),
                SOURCE,
            )

        self.assertEqual(actual, expected)

    def test_relative_paths_ignore_process_working_directory_and_normalize(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project = Path(temporary_directory)
            source_path = project / "source" / "main.nsp"
            source_path.parent.mkdir()
            asset_path = project / "assets" / "screens" / "main.nam"
            asset_path.parent.mkdir(parents=True)
            expected = bytes([0x23]) * NAMETABLE_SIZE
            asset_path.write_bytes(expected)
            unrelated = project / "elsewhere"
            unrelated.mkdir()
            previous_cwd = Path.cwd()
            try:
                os.chdir(unrelated)
                actual = load_background_data(
                    "../assets/./screens/../screens/main.nam",
                    None,
                    None,
                    source_path,
                    SOURCE,
                )
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(actual, expected)

    def test_missing_and_unreadable_files_have_stable_diagnostics(self) -> None:
        source_path = Path("project/main.nsp").resolve()
        with self.assertRaises(CompilerError) as missing:
            load_background_data(
                "assets/missing.nam",
                None,
                None,
                source_path,
                SOURCE,
            )
        self.assertEqual(
            missing.exception.code,
            DiagnosticCode.BACKGROUND_ASSET_NOT_FOUND,
        )
        self.assertIn("assets/missing.nam", str(missing.exception))
        self.assertIn(
            str((source_path.parent / "assets/missing.nam").resolve()),
            str(missing.exception),
        )

        with patch.object(Path, "read_bytes", side_effect=OSError("access denied")):
            with self.assertRaises(CompilerError) as unreadable:
                load_background_data(
                    "screen.nam",
                    None,
                    None,
                    source_path,
                    SOURCE,
                )
        self.assertEqual(
            unreadable.exception.code,
            DiagnosticCode.BACKGROUND_ASSET_READ_FAILURE,
        )
        self.assertIn("access denied", str(unreadable.exception))

    def test_invalid_combined_tile_and_attribute_sizes_report_actual_size(self) -> None:
        cases = (
            ("nametable", 0, NAMETABLE_SIZE),
            ("nametable", NAMETABLE_SIZE - 1, NAMETABLE_SIZE),
            ("nametable", NAMETABLE_SIZE + 1, NAMETABLE_SIZE),
            ("tiles", NAMETABLE_TILE_SIZE - 1, NAMETABLE_TILE_SIZE),
            ("attributes", ATTRIBUTE_TABLE_SIZE + 1, ATTRIBUTE_TABLE_SIZE),
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            project = Path(temporary_directory)
            for kind, actual_size, expected_size in cases:
                with self.subTest(kind=kind, actual_size=actual_size):
                    nametable = tiles = attributes = None
                    if kind == "nametable":
                        nametable = project / "screen.nam"
                        nametable.write_bytes(bytes(actual_size))
                    else:
                        tiles = project / "tiles.bin"
                        attributes = project / "attributes.bin"
                        tiles.write_bytes(
                            bytes(
                                actual_size
                                if kind == "tiles"
                                else NAMETABLE_TILE_SIZE
                            )
                        )
                        attributes.write_bytes(
                            bytes(
                                actual_size
                                if kind == "attributes"
                                else ATTRIBUTE_TABLE_SIZE
                            )
                        )
                    with self.assertRaises(CompilerError) as raised:
                        load_background_data(
                            nametable,
                            tiles,
                            attributes,
                            project / "main.nsp",
                            SOURCE,
                        )
                    self.assertEqual(
                        raised.exception.code,
                        DiagnosticCode.INVALID_BACKGROUND_ASSET_SIZE,
                    )
                    message = str(raised.exception)
                    self.assertIn(f"expected {expected_size} bytes", message)
                    self.assertIn(f"found {actual_size} bytes", message)

    def test_conflicting_or_incomplete_configuration_is_rejected(self) -> None:
        cases = (
            ("screen.nam", "tiles.bin", "attributes.bin"),
            (None, "tiles.bin", None),
            (None, None, "attributes.bin"),
        )
        for nametable, tiles, attributes in cases:
            with self.subTest(
                nametable=nametable,
                tiles=tiles,
                attributes=attributes,
            ):
                with self.assertRaises(CompilerError) as raised:
                    load_background_data(
                        nametable,
                        tiles,
                        attributes,
                        Path("main.nsp"),
                        SOURCE,
                    )
                self.assertEqual(
                    raised.exception.code,
                    DiagnosticCode.INVALID_BACKGROUND_ASSET_CONFIGURATION,
                )


class NametableLanguageTests(unittest.TestCase):
    def test_parser_and_semantic_model_zero_argument_background_load(self) -> None:
        parsed = parse(SOURCE)
        self.assertIsInstance(parsed.statements[0], LoadBackground)
        self.assertEqual(parsed.statements[0].arguments, ())

        resolved = analyze_source()
        self.assertIsInstance(resolved.statements[0], ResolvedLoadBackground)

    def test_command_line_exposes_combined_and_split_configuration(self) -> None:
        parser = build_argument_parser()
        combined = parser.parse_args(
            ["main.nsp", "-o", "main.nes", "--nametable", "screen.nam"]
        )
        self.assertEqual(combined.nametable, "screen.nam")
        split = parser.parse_args(
            [
                "main.nsp",
                "-o",
                "main.nes",
                "--nametable-tiles",
                "tiles.bin",
                "--nametable-attributes",
                "attributes.bin",
            ]
        )
        self.assertEqual(split.nametable_tiles, "tiles.bin")
        self.assertEqual(split.nametable_attributes, "attributes.bin")

    def test_command_line_version_flag_reports_version(self) -> None:
        import io
        from contextlib import redirect_stdout
        from nes_pascal import __version__

        parser = build_argument_parser()
        buffer = io.StringIO()
        with redirect_stdout(buffer), self.assertRaises(SystemExit) as context:
            parser.parse_args(["--version"])
        self.assertEqual(context.exception.code, 0)
        self.assertIn(f"nes-pascal {__version__}", buffer.getvalue())

    def test_invalid_source_forms_have_stable_diagnostics(self) -> None:
        fixtures = {
            "invalid_background_load_argument_count.nsp": "E3035",
            "background_load_after_run.nsp": "E3036",
            "duplicate_background_load.nsp": "E3037",
        }
        directory = Path(__file__).resolve().parent / "fixtures" / "diagnostics"
        for filename, expected_code in fixtures.items():
            with self.subTest(filename=filename):
                path = directory / filename
                source = path.read_text(encoding="utf-8")
                with self.assertRaises(CompilerError) as raised:
                    analyze_source(source, str(path))
                self.assertEqual(raised.exception.code, expected_code)

    def test_source_command_and_asset_configuration_must_match(self) -> None:
        without_command = """program NoLoad;
begin
    nes.set_background_color($0F);
    nes.run;
end.
"""
        with tempfile.TemporaryDirectory() as temporary_directory:
            project = Path(temporary_directory)
            load_source = project / "load.nsp"
            load_source.write_text(SOURCE, encoding="utf-8")
            with self.assertRaises(CompilerError) as missing:
                compile_source(load_source, project / "load.nes")
            self.assertEqual(
                missing.exception.code,
                DiagnosticCode.BACKGROUND_ASSET_REQUIRED,
            )

            no_load_source = project / "no-load.nsp"
            no_load_source.write_text(without_command, encoding="utf-8")
            (project / "screen.nam").write_bytes(bytes(NAMETABLE_SIZE))
            with self.assertRaises(CompilerError) as unused:
                compile_source(
                    no_load_source,
                    project / "no-load.nes",
                    nametable_path="screen.nam",
                )
            self.assertEqual(
                unused.exception.code,
                DiagnosticCode.INVALID_BACKGROUND_ASSET_CONFIGURATION,
            )

    def test_dynamic_contexts_keep_existing_runtime_diagnostics(self) -> None:
        cases = (
            (
                """program P;
begin
    if true then nes.load_background();
    nes.set_background_color($0F);
    nes.run;
end.
""",
                "E3009",
            ),
            (
                """program P;
procedure Load;
begin
    nes.load_background();
end;
begin
    nes.set_background_color($0F);
    nes.run;
end.
""",
                "E3015",
            ),
        )
        for source, expected_code in cases:
            with self.subTest(expected_code=expected_code):
                with self.assertRaises(CompilerError) as raised:
                    analyze_source(source)
                self.assertEqual(raised.exception.code, expected_code)


class NametableBackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = bytes(range(256)) * 4
        cls.program = analyze_source()
        cls.layout = build_memory_layout(cls.program)
        cls.assembly = generate(
            cls.program,
            cls.layout,
            background_data=cls.data,
        )

    def test_upload_targets_complete_nametable_zero_with_rendering_disabled(self) -> None:
        upload = self.assembly.split("; Source: nes.load_background()", 1)[1]
        upload = upload.split("; Source: nes.set_background_color", 1)[0]
        self.assertIn("sta $2001", upload)
        self.assertIn("lda #$20\n    sta $2006", upload)
        self.assertIn("lda #$00\n    sta $2006", upload)
        self.assertEqual(upload.count("sta $2007"), 4)
        for page in range(4):
            self.assertIn(f"@upload_background_page_{page}:", upload)
        self.assertLess(
            self.assembly.index("; Source: nes.load_background()"),
            self.assembly.index("; Source: nes.run"),
        )

    def test_normal_rendering_enables_the_background_left_edge(self) -> None:
        run = self.assembly.split("; Source: nes.run", 1)[1]
        self.assertIn(
            "lda runtime_ppumask_shadow\n"
            "    ora #$1E\n"
            "    sta runtime_ppumask_shadow ; preserve bits and enable rendering\n"
            "    sta $2001",
            run,
        )

    def test_asset_bytes_are_embedded_unchanged_exactly_once(self) -> None:
        self.assertEqual(self.assembly.count("background_nametable_data:"), 1)
        storage = self.assembly.split("background_nametable_data:", 1)[1]
        storage = storage.split('.segment "VECTORS"', 1)[0]
        emitted = bytes(int(value, 16) for value in re.findall(r"\$([0-9A-F]{2})", storage))
        self.assertEqual(emitted, self.data)

    def test_assembly_is_deterministic(self) -> None:
        second = generate(
            analyze_source(),
            build_memory_layout(analyze_source()),
            background_data=self.data,
        )
        self.assertEqual(second, self.assembly)


if __name__ == "__main__":
    unittest.main()
