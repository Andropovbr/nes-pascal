import copy
from dataclasses import replace
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from nes_pascal.ast import (
    MetaspriteAsset,
    MetaspriteComponent,
    MetaspriteFrame,
    OamOwnerKind,
    ResolvedAssignment,
    ResolvedBuiltinCall,
)
from nes_pascal.builtins import BuiltinId
from nes_pascal.backend_ca65 import generate
from nes_pascal.cli import compile_source
from nes_pascal.diagnostics import CompilerError, DiagnosticCode
from nes_pascal.memory_layout import build_memory_layout
from nes_pascal.metasprite_assets import load_metasprite_assets
from nes_pascal.parser import parse
from nes_pascal.semantic import analyze


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "metasprite_player.nsp"
METADATA = ROOT / "examples" / "assets" / "player_idle.json"
CHR = ROOT / "examples" / "assets" / "game.chr"
SOURCE = "program MetaspriteTest;\nbegin\n    nes.set_background_color($0F);\n    nes.run;\nend.\n"


def load_reference_asset() -> MetaspriteAsset:
    return load_metasprite_assets(
        (METADATA,),
        EXAMPLE,
        EXAMPLE.read_text(encoding="utf-8"),
        CHR.read_bytes(),
    )[0]


def resolve(source: str, assets: tuple[MetaspriteAsset, ...]):
    return analyze(
        parse(source, "metasprite_test.nsp"),
        source,
        "metasprite_test.nsp",
        metasprite_assets=assets,
    )


def program(body: str, declarations: str = "    Player: metasprite;\n") -> str:
    variable_section = f"var\n{declarations}" if declarations else ""
    return f"""program MetaspriteTest;
{variable_section}
begin
    nes.import_metasprite(player);
    {body}
    nes.set_background_color($0F);
    nes.run;
end.
"""


def synthetic_document() -> dict:
    return {
        "format": "png2chr-studio-animation",
        "version": 2,
        "name": "shape",
        "source": {"tile_width": 8, "tile_height": 8},
        "chr": {
            "capacity_tiles": 256,
            "final_tile_count": 8,
            "final_size_bytes": 8192,
        },
        "attribute_flags": {
            "flip_horizontal": 0x40,
            "flip_vertical": 0x80,
            "palette_mask": 0x03,
        },
        "origin": {"x": 10, "y": 20},
        "animations": [
            {
                "name": "pose",
                "frames": [
                    {
                        "width": 31,
                        "height": 29,
                        "sprites": [
                            {
                                "x": -8,
                                "y": -8,
                                "tile": 7,
                                "attributes": 0x41,
                                "palette": 1,
                                "horizontal_flip": True,
                                "vertical_flip": False,
                            },
                            {
                                "x": 8,
                                "y": 8,
                                "tile": 2,
                                "attributes": 0,
                                "palette": 0,
                                "horizontal_flip": False,
                                "vertical_flip": False,
                            },
                            {
                                "x": 0,
                                "y": 0,
                                "tile": 7,
                                "attributes": 0,
                                "palette": 0,
                                "horizontal_flip": False,
                                "vertical_flip": False,
                            },
                        ],
                    }
                ],
            }
        ],
    }


def load_temporary_document(document: object) -> tuple[MetaspriteAsset, ...]:
    with tempfile.TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        source_path = root / "main.nsp"
        metadata_path = root / "shape.json"
        metadata_path.write_text(json.dumps(document), encoding="utf-8")
        return load_metasprite_assets(
            ("shape.json",), source_path, SOURCE, bytes(8192)
        )


def transformed_components(
    frame: MetaspriteFrame,
    logical_x: int,
    logical_y: int,
    *,
    horizontal_flip: bool = False,
    vertical_flip: bool = False,
) -> list[tuple[int, int, int]]:
    geometry = []
    for component in frame.components:
        x_offset = (
            -component.x_offset - 8
            if horizontal_flip
            else component.x_offset
        )
        y_offset = (
            -component.y_offset - 8
            if vertical_flip
            else component.y_offset
        )
        attributes = component.attributes
        if horizontal_flip:
            attributes ^= 0x40
        if vertical_flip:
            attributes ^= 0x80
        geometry.append((logical_x + x_offset, logical_y + y_offset, attributes))
    return geometry


def bounding_ranges(
    geometry: list[tuple[int, int, int]],
) -> tuple[tuple[int, int], tuple[int, int]]:
    return (
        (min(x for x, _, _ in geometry), max(x + 8 for x, _, _ in geometry)),
        (min(y for _, y, _ in geometry), max(y + 8 for _, y, _ in geometry)),
    )


class MetaspriteAssetTests(unittest.TestCase):
    def test_attached_png2chr_metadata_is_a_regression_fixture(self) -> None:
        asset = load_reference_asset()
        self.assertEqual(asset.name, "player")
        self.assertEqual(len(asset.frames), 6)
        self.assertEqual(
            [(frame.width, frame.height) for frame in asset.frames],
            [(24, 24)] * 6,
        )
        self.assertEqual([len(frame.components) for frame in asset.frames], [7] * 6)
        first = asset.frames[0]
        self.assertEqual(
            [(item.x_offset, item.y_offset) for item in first.components],
            [
                (-4, -12),
                (4, -12),
                (-4, -4),
                (4, -4),
                (-12, 4),
                (-4, 4),
                (4, 4),
            ],
        )
        self.assertEqual([item.tile for item in first.components[:2]], [0, 0])
        self.assertEqual(first.components[1].attributes & 0x40, 0x40)
        self.assertEqual(len(first.components), 9 - 2)

    def test_arbitrary_sparse_signed_and_reused_components_are_preserved(self) -> None:
        frame = load_temporary_document(synthetic_document())[0].frames[0]
        self.assertEqual((frame.width, frame.height), (31, 29))
        self.assertEqual((frame.origin_x, frame.origin_y), (10, 20))
        self.assertEqual(
            frame.components,
            (
                MetaspriteComponent(-8, -8, 7, 0x41),
                MetaspriteComponent(8, 8, 2, 0),
                MetaspriteComponent(0, 0, 7, 0),
            ),
        )

    def test_png2chr_offsets_are_not_shifted_by_the_declared_origin_twice(self) -> None:
        document = synthetic_document()
        document["origin"] = {"x": 37, "y": -19}
        frame = load_temporary_document(document)[0].frames[0]
        self.assertEqual((frame.origin_x, frame.origin_y), (37, -19))
        self.assertEqual(
            [(item.x_offset, item.y_offset) for item in frame.components],
            [(-8, -8), (8, 8), (0, 0)],
        )

    def test_centered_24_by_24_pivot_preserves_both_bounding_ranges(self) -> None:
        frame = load_reference_asset().frames[0]
        normal = transformed_components(frame, 112, 104)
        horizontal = transformed_components(
            frame, 112, 104, horizontal_flip=True
        )
        vertical = transformed_components(frame, 112, 104, vertical_flip=True)
        self.assertEqual(bounding_ranges(normal)[0], (100, 124))
        self.assertEqual(bounding_ranges(horizontal)[0], (100, 124))
        self.assertEqual(bounding_ranges(normal)[1], (92, 116))
        self.assertEqual(bounding_ranges(vertical)[1], (92, 116))

    def test_player_example_bounds_keep_every_frame_visible_at_all_edges(self) -> None:
        asset = load_reference_asset()
        source = EXAMPLE.read_text(encoding="utf-8")
        parsed = parse(source, str(EXAMPLE))
        constants = {
            declaration.name: declaration.value.value
            for declaration in parsed.constants
        }

        horizontal_bounds = []
        vertical_bounds = []
        for frame in asset.frames:
            for flipped in (False, True):
                geometry = transformed_components(
                    frame,
                    0,
                    0,
                    horizontal_flip=flipped,
                    vertical_flip=flipped,
                )
                horizontal_bounds.append(bounding_ranges(geometry)[0])
                vertical_bounds.append(bounding_ranges(geometry)[1])

        minimum_x_offset = min(bounds[0] for bounds in horizontal_bounds)
        maximum_x_offset = max(bounds[1] for bounds in horizontal_bounds)
        minimum_y_offset = min(bounds[0] for bounds in vertical_bounds)
        maximum_y_offset = max(bounds[1] for bounds in vertical_bounds)
        expected = {
            "PlayerMinimumX": -minimum_x_offset,
            "PlayerMaximumX": 256 - maximum_x_offset,
            "PlayerMinimumY": 1 - minimum_y_offset,
            "PlayerMaximumY": 240 - maximum_y_offset,
        }
        self.assertEqual(
            expected,
            {
                "PlayerMinimumX": 0x0C,
                "PlayerMaximumX": 0xF4,
                "PlayerMinimumY": 0x0D,
                "PlayerMaximumY": 0xE4,
            },
        )
        self.assertEqual(
            {name: constants[name] for name in expected},
            expected,
        )

        for comparison in (
            "if PlayerX > PlayerMinimumX then",
            "if PlayerX < PlayerMaximumX then",
            "if PlayerY > PlayerMinimumY then",
            "if PlayerY < PlayerMaximumY then",
        ):
            self.assertIn(comparison, source)
        for frame in asset.frames:
            for horizontal_flip in (False, True):
                for x in (expected["PlayerMinimumX"], expected["PlayerMaximumX"]):
                    geometry = transformed_components(
                        frame,
                        x,
                        expected["PlayerMinimumY"],
                        horizontal_flip=horizontal_flip,
                    )
                    self.assertTrue(all(0 <= left <= 248 for left, _, _ in geometry))
                for vertical_flip in (False, True):
                    for y in (
                        expected["PlayerMinimumY"],
                        expected["PlayerMaximumY"],
                    ):
                        geometry = transformed_components(
                            frame,
                            expected["PlayerMinimumX"],
                            y,
                            horizontal_flip=horizontal_flip,
                            vertical_flip=vertical_flip,
                        )
                        self.assertTrue(all(1 <= top <= 232 for _, top, _ in geometry))

    def test_asymmetric_layout_mirrors_positions_and_xors_component_flips(self) -> None:
        frame = load_temporary_document(synthetic_document())[0].frames[0]
        normal = transformed_components(frame, 80, 96)
        horizontal = transformed_components(
            frame, 80, 96, horizontal_flip=True
        )
        vertical = transformed_components(frame, 80, 96, vertical_flip=True)
        both = transformed_components(
            frame,
            80,
            96,
            horizontal_flip=True,
            vertical_flip=True,
        )
        self.assertEqual(normal, [(72, 88, 0x41), (88, 104, 0), (80, 96, 0)])
        self.assertEqual(horizontal, [(80, 88, 0x01), (64, 104, 0x40), (72, 96, 0x40)])
        self.assertEqual(vertical, [(72, 96, 0xC1), (88, 80, 0x80), (80, 88, 0x80)])
        self.assertEqual(both, [(80, 96, 0x81), (64, 80, 0xC0), (72, 88, 0xC0)])

    def test_explicit_non_centered_pivot_preserves_intentional_hinge_motion(self) -> None:
        document = synthetic_document()
        document["origin"] = {"x": 0, "y": 0}
        sprites = document["animations"][0]["frames"][0]["sprites"]
        for sprite, x in zip(sprites, (0, 8, 16), strict=True):
            sprite["x"] = x
            sprite["y"] = 0
        frame = load_temporary_document(document)[0].frames[0]
        normal = transformed_components(frame, 100, 80)
        flipped = transformed_components(frame, 100, 80, horizontal_flip=True)
        self.assertEqual(bounding_ranges(normal)[0], (100, 124))
        self.assertEqual(bounding_ranges(flipped)[0], (76, 100))
        self.assertEqual([x for x, _, _ in flipped], [92, 84, 76])

    def test_metadata_failures_have_stable_actionable_diagnostics(self) -> None:
        cases = []
        unsupported_format = synthetic_document()
        unsupported_format["format"] = "other"
        cases.append((unsupported_format, DiagnosticCode.UNSUPPORTED_METASPRITE_FORMAT))
        unsupported_version = synthetic_document()
        unsupported_version["version"] = 99
        cases.append((unsupported_version, DiagnosticCode.UNSUPPORTED_METASPRITE_VERSION))
        missing = synthetic_document()
        del missing["origin"]
        cases.append((missing, DiagnosticCode.INVALID_METASPRITE_METADATA))
        for field, value in (("tile", 8), ("attributes", 256), ("palette", 4), ("x", 300)):
            invalid = copy.deepcopy(synthetic_document())
            component = invalid["animations"][0]["frames"][0]["sprites"][0]
            component[field] = value
            cases.append(
                (
                    invalid,
                    DiagnosticCode.INCOMPATIBLE_METASPRITE_CHR
                    if field == "tile"
                    else DiagnosticCode.INVALID_METASPRITE_METADATA,
                )
            )
        for field in ("horizontal_flip", "vertical_flip"):
            invalid = copy.deepcopy(synthetic_document())
            component = invalid["animations"][0]["frames"][0]["sprites"][0]
            component[field] = not component[field]
            cases.append((invalid, DiagnosticCode.INVALID_METASPRITE_METADATA))
        for document, expected in cases:
            with self.subTest(expected=expected, document=document):
                with self.assertRaises(CompilerError) as raised:
                    load_temporary_document(document)
                self.assertEqual(raised.exception.code, expected)
                self.assertIn("\n\n", str(raised.exception))

    def test_malformed_missing_and_chr_incompatible_assets_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source_path = root / "main.nsp"
            malformed = root / "bad.json"
            malformed.write_text("{", encoding="utf-8")
            with self.assertRaises(CompilerError) as raised:
                load_metasprite_assets((malformed,), source_path, SOURCE, bytes(8192))
            self.assertEqual(
                raised.exception.code, DiagnosticCode.MALFORMED_METASPRITE_METADATA
            )
            with self.assertRaises(CompilerError) as raised:
                load_metasprite_assets(("missing.json",), source_path, SOURCE, bytes(8192))
            self.assertEqual(raised.exception.code, DiagnosticCode.METASPRITE_ASSET_NOT_FOUND)
            with self.assertRaises(CompilerError) as raised:
                load_metasprite_assets((METADATA,), source_path, SOURCE, None)
            self.assertEqual(raised.exception.code, DiagnosticCode.INCOMPATIBLE_METASPRITE_CHR)

    def test_unreadable_metadata_is_not_confused_with_missing_asset(self) -> None:
        cases = (
            (OSError("access denied"), "access denied"),
            (
                UnicodeDecodeError(
                    "utf-8", b"\xff\xfe", 0, 1, "invalid start byte"
                ),
                "invalid start byte",
            ),
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source_path = root / "main.nsp"
            for error, fragment in cases:
                with self.subTest(error=error):
                    with patch.object(Path, "read_text", side_effect=error):
                        with self.assertRaises(CompilerError) as raised:
                            load_metasprite_assets(
                                ("shape.json",), source_path, SOURCE, bytes(8192)
                            )
                    message = str(raised.exception)
                    self.assertEqual(
                        raised.exception.code,
                        DiagnosticCode.METASPRITE_ASSET_READ_FAILURE,
                    )
                    self.assertIn("shape.json", message)
                    self.assertIn(str((root / "shape.json").resolve()), message)
                    self.assertIn(fragment, message)
                    self.assertNotIn("was not found", message)

    def test_duplicate_configured_asset_roots_are_rejected(self) -> None:
        with self.assertRaises(CompilerError) as raised:
            load_metasprite_assets(
                (METADATA, METADATA), EXAMPLE, SOURCE, CHR.read_bytes()
            )
        self.assertEqual(
            raised.exception.code,
            DiagnosticCode.INVALID_METASPRITE_CONFIGURATION,
        )


class MetaspriteSemanticAndOwnershipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.asset = load_reference_asset()

    def test_create_returns_a_persistent_metasprite_instance(self) -> None:
        resolved = resolve(
            program("Player := nes.metasprite_create(player.idle_0);"),
            (self.asset,),
        )
        assignment = next(
            statement
            for statement in resolved.statements
            if isinstance(statement, ResolvedAssignment)
        )
        self.assertIsInstance(assignment.value, ResolvedBuiltinCall)
        self.assertIs(assignment.value.builtin, BuiltinId.METASPRITE_CREATE)
        self.assertEqual(
            [argument.value for argument in assignment.value.arguments],
            [0, 0],
        )
        self.assertEqual(resolved.metasprite_instances[0].oam_indexes, tuple(range(7)))

    def test_individual_and_metasprite_reservations_share_one_pool(self) -> None:
        source = """program MixedOwnership;
const
    ReservedZero: sprite = $00;
var
    Individual: sprite;
    Player: metasprite;
begin
    nes.import_metasprite(player);
    Individual := nes.sprite_create();
    Player := nes.metasprite_create(player.idle_0);
    nes.set_background_color($0F);
    nes.run;
end.
"""
        resolved = resolve(source, (self.asset,))
        ownership = [(item.index, item.owner) for item in resolved.oam_reservations]
        self.assertEqual(
            ownership,
            [(0, OamOwnerKind.INDIVIDUAL_EXPLICIT), (1, OamOwnerKind.INDIVIDUAL_CREATED)]
            + [(index, OamOwnerKind.METASPRITE_COMPONENT) for index in range(2, 9)],
        )
        meta = resolved.oam_reservations[2:]
        self.assertEqual([item.owner_index for item in meta], [0] * 7)
        self.assertEqual([item.component_index for item in meta], list(range(7)))

    def test_exact_capacity_and_first_excess_reservation_are_deterministic(self) -> None:
        def source_with_created(count: int) -> str:
            creates = "\n".join("    Item := nes.sprite_create();" for _ in range(count))
            return program(
                creates + "\n    Player := nes.metasprite_create(player.idle_0);",
                "    Item: sprite;\n    Player: metasprite;\n",
            )

        exact = resolve(source_with_created(57), (self.asset,))
        self.assertEqual(len(exact.oam_reservations), 64)
        with self.assertRaises(CompilerError) as raised:
            resolve(source_with_created(58), (self.asset,))
        self.assertEqual(
            raised.exception.code, DiagnosticCode.OAM_SPRITE_CAPACITY_EXHAUSTED
        )
        self.assertIn("player", str(raised.exception))
        self.assertIn("7", str(raised.exception))

    def test_import_create_operation_and_type_errors_are_stable(self) -> None:
        cases = (
            (
                """program MissingImport;
var Player: metasprite;
begin
    Player := nes.metasprite_create(player.idle_0);
    nes.set_background_color($0F);
    nes.run;
end.
""",
                "E3051",
            ),
            (program("Player := nes.metasprite_create();"), "E3053"),
            (
                program(
                    "Player := nes.metasprite_create(player.idle_0);\n"
                    "    nes.metasprite_set_position(Player, $10);"
                ),
                "E3054",
            ),
            (program("Player := $00;"), "E4009"),
        )
        for source, code in cases:
            with self.subTest(code=code):
                with self.assertRaises(CompilerError) as raised:
                    resolve(source, (self.asset,))
                self.assertEqual(raised.exception.code, code)

    def test_every_language_diagnostic_fixture_emits_only_its_expected_code(self) -> None:
        enemy_frames = tuple(
            replace(
                frame,
                id=frame.id + len(self.asset.frames),
                symbol=frame.symbol.replace("player.", "enemy."),
                asset_name="enemy",
            )
            for frame in self.asset.frames
        )
        enemy = MetaspriteAsset("enemy", "enemy.json", enemy_frames)
        fixtures = {
            "invalid_metasprite_import.nsp": ("E3051", (self.asset,)),
            "duplicate_metasprite_import.nsp": ("E3052", (self.asset,)),
            "invalid_metasprite_create.nsp": ("E3053", (self.asset,)),
            "metasprite_argument_count.nsp": ("E3054", (self.asset,)),
            "incompatible_metasprite_frame.nsp": (
                "E3055",
                (self.asset, enemy),
            ),
            "invalid_metasprite_value.nsp": ("E4009", (self.asset,)),
        }
        directory = ROOT / "tests" / "fixtures" / "diagnostics"
        for filename, (expected, assets) in fixtures.items():
            with self.subTest(filename=filename):
                path = directory / filename
                source = path.read_text(encoding="utf-8")
                with self.assertRaises(CompilerError) as raised:
                    resolve(source, assets)
                self.assertEqual(raised.exception.code, expected)

    def test_frames_with_fewer_components_keep_the_creation_maximum(self) -> None:
        document = synthetic_document()
        shorter = copy.deepcopy(document["animations"][0]["frames"][0])
        shorter["sprites"] = shorter["sprites"][:1]
        document["animations"][0]["frames"].append(shorter)
        asset = load_temporary_document(document)[0]
        source = """program VariableFrameSizes;
var
    Shape: metasprite;
begin
    nes.import_metasprite(shape);
    Shape := nes.metasprite_create(shape.pose_0);
    nes.metasprite_set_frame(Shape, shape.pose_1);
    nes.metasprite_set_position(Shape, $40, $50);
    nes.metasprite_show(Shape);
    nes.set_background_color($0F);
    nes.run;
end.
"""
        resolved = resolve(source, (asset,))
        self.assertEqual(resolved.metasprite_instances[0].oam_indexes, (0, 1, 2))
        assembly = generate(resolved)
        self.assertIn("metasprite_frame_0:\n    .byte $03", assembly)
        self.assertIn("metasprite_frame_1:\n    .byte $01", assembly)
        self.assertIn("@metasprite_hide_one", assembly)


class MetaspriteBackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.asset = load_reference_asset()
        cls.source = EXAMPLE.read_text(encoding="utf-8")
        cls.resolved = resolve(cls.source, (cls.asset,))
        cls.layout = build_memory_layout(cls.resolved)
        cls.assembly = generate(cls.resolved, cls.layout, chr_rom=CHR.read_bytes())

    def test_geometry_is_compact_immutable_prg_data(self) -> None:
        self.assertIn("; Asset: immutable metasprite tables in PRG-ROM", self.assembly)
        self.assertIn("metasprite_frame_0:\n    .byte $07 ; player.idle_0", self.assembly)
        self.assertIn("    .byte $FC, $F4, $00, $00", self.assembly)
        self.assertIn("    .byte $04, $F4, $00, $40", self.assembly)
        self.assertNotIn("source_tile_column", self.assembly)
        self.assertNotIn("source_x", self.assembly)
        chr_section = self.assembly.split('.segment "CHR"', 1)[1]
        self.assertEqual(chr_section.count("; Asset: configured CHR-ROM bytes"), 1)
        self.assertEqual(chr_section.count("    .byte "), 512)

    def test_mutable_ram_is_four_bytes_per_instance_plus_shared_scratch(self) -> None:
        meta_symbols = [
            symbol
            for symbol in self.layout.runtime_symbols
            if symbol.assembly_symbol.startswith("runtime_metasprite_")
            and symbol.region_name == self.layout.runtime_data.name
        ]
        self.assertEqual(sum(symbol.size for symbol in meta_symbols), 12)
        self.assertEqual(
            {
                symbol.assembly_symbol: symbol.size
                for symbol in meta_symbols[:4]
            },
            {
                "runtime_metasprite_x": 1,
                "runtime_metasprite_y": 1,
                "runtime_metasprite_frame": 1,
                "runtime_metasprite_flags": 1,
            },
        )

    def test_runtime_updates_all_slots_and_preserves_state_across_operations(self) -> None:
        routine = self.assembly.split("runtime_metasprite_render:", 1)[1].split(
            "runtime_metasprite_advance_frame_pointer:", 1
        )[0]
        self.assertIn("runtime_metasprite_slots_remaining", routine)
        self.assertIn("runtime_metasprite_frame_remaining", routine)
        self.assertIn("sta runtime_oam_shadow + 3, y", routine)
        self.assertIn("sta runtime_oam_shadow, y ; publish Y last", routine)
        self.assertIn("@metasprite_hide_slots", routine)
        self.assertIn("eor #$40", routine)
        self.assertIn("eor #$80", routine)
        self.assertIn("sbc #$07", routine)

    def test_component_clipping_has_no_unsigned_wrap_path(self) -> None:
        routine = self.assembly.split("runtime_metasprite_render:", 1)[1].split(
            "runtime_metasprite_advance_frame_pointer:", 1
        )[0]
        self.assertIn("bcs @metasprite_hide_one", routine)
        self.assertIn("bcc @metasprite_hide_one", routine)
        self.assertIn("cmp #$F9", routine)
        self.assertIn(
            "cmp #$F9                ; negative offsets still obey the right edge",
            routine,
        )
        self.assertIn("cmp #$E9", routine)
        self.assertIn("beq @metasprite_hide_one ; $FF is reserved", routine)
        self.assertIn("sbc #$01                ; logical top -> NES OAM Y", routine)

    def test_oam_dma_remains_in_nmi_but_layout_work_does_not(self) -> None:
        nmi = self.assembly.split("NMI:", 1)[1].split("IRQ:", 1)[0]
        self.assertIn("sta $4014", nmi)
        self.assertNotIn("runtime_metasprite_render", nmi)
        self.assertNotIn("metasprite_frame_pointer_low", nmi)

    def test_unrelated_program_has_no_metasprite_dependency(self) -> None:
        resolved = resolve(SOURCE, ())
        assembly = generate(resolved)
        symbols = {
            symbol.assembly_symbol
            for symbol in build_memory_layout(resolved).runtime_symbols
        }
        self.assertNotIn("metasprite", assembly)
        self.assertFalse(any(name.startswith("runtime_metasprite_") for name in symbols))

    @unittest.skipUnless(
        shutil.which("ca65") and shutil.which("ld65"),
        "metasprite ROM integration requires ca65 and ld65",
    )
    def test_reference_example_builds_valid_nrom_without_duplicating_chr(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "metasprite_player.nes"
            compile_source(
                EXAMPLE,
                output,
                chr_path="assets/game.chr",
                metasprite_paths=("assets/player_idle.json",),
            )
            rom = output.read_bytes()
        self.assertEqual(rom[:4], b"NES\x1A")
        self.assertEqual(rom[4:6], bytes((2, 1)))
        self.assertEqual(len(rom), 16 + 32 * 1024 + 8 * 1024)
        self.assertEqual(rom[-8192:], CHR.read_bytes())


if __name__ == "__main__":
    unittest.main()
