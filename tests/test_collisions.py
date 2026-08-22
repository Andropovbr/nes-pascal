import json
from pathlib import Path
import shutil
import tempfile
import unittest

from nes_pascal.assets import (
    COLLISION_MAP_PACKED_SIZE,
    load_collision_map,
)
from nes_pascal.ast import BuiltInType, NES_RECT_TYPE, ResolvedRecordReference
from nes_pascal.backend_ca65 import generate
from nes_pascal.builtins import (
    BackendEmitter,
    BuiltinId,
    RuntimeFeature,
    SemanticHook,
    builtin_by_id,
)
from nes_pascal.cli import compile_source
from nes_pascal.diagnostics import CompilerError, DiagnosticCode
from nes_pascal.memory_layout import (
    build_memory_layout,
    collect_runtime_features,
    detect_collision_runtime_features,
)
from nes_pascal.metasprite_assets import load_metasprite_assets
from nes_pascal.parser import parse
from nes_pascal.semantic import analyze
from tools.measure_benchmarks import BENCHMARKS, measure_benchmark


ROOT = Path(__file__).resolve().parents[1]


def resolve(source: str, *, assets=()):
    return analyze(
        parse(source, "collision_test.nsp"),
        source,
        "collision_test.nsp",
        metasprite_assets=assets,
    )


def geometry_source(body: str) -> str:
    return f"""program CollisionTest;
var
    A: nes_rect;
    B: nes_rect;
    Result: boolean;
begin
    A.X := $10;
    A.Y := $20;
    A.Width := $08;
    A.Height := $08;
    B.X := $17;
    B.Y := $27;
    B.Width := $08;
    B.Height := $08;
    {body}
    nes.set_background_color($0F);
    nes.run;
end.
"""


class CollisionTypeAndRegistryTests(unittest.TestCase):
    def test_nes_rect_is_the_ordinary_four_byte_record_representation(self) -> None:
        source = geometry_source("Result := nes.collides(A, B);")
        program = resolve(source)
        self.assertIs(program.variables[0].type, NES_RECT_TYPE)
        self.assertEqual(NES_RECT_TYPE.size, 4)
        self.assertEqual(
            [(field.name, field.type, field.offset) for field in NES_RECT_TYPE.fields],
            [
                ("X", BuiltInType.BYTE, 0),
                ("Y", BuiltInType.BYTE, 1),
                ("Width", BuiltInType.BYTE, 2),
                ("Height", BuiltInType.BYTE, 3),
            ],
        )
        call = program.statements[8].value
        self.assertIs(call.builtin, BuiltinId.COLLIDES)
        self.assertTrue(all(isinstance(arg, ResolvedRecordReference) for arg in call.arguments))

    def test_collision_builtins_are_declarative_and_feature_gated(self) -> None:
        expected = {
            BuiltinId.POINT_IN_RECT: (
                BackendEmitter.POINT_IN_RECT,
                (RuntimeFeature.COLLISION_POINT,),
            ),
            BuiltinId.COLLIDES: (
                BackendEmitter.COLLIDES,
                (RuntimeFeature.COLLISION_RECTS,),
            ),
            BuiltinId.SPRITE_BOUNDS: (
                BackendEmitter.SPRITE_BOUNDS,
                (RuntimeFeature.SPRITE_API, RuntimeFeature.COLLISION_SPRITE_BOUNDS),
            ),
            BuiltinId.METASPRITE_BOUNDS: (
                BackendEmitter.METASPRITE_BOUNDS,
                (RuntimeFeature.METASPRITE_API, RuntimeFeature.COLLISION_METASPRITE_BOUNDS),
            ),
            BuiltinId.BACKGROUND_COLLISION: (
                BackendEmitter.BACKGROUND_COLLISION,
                (RuntimeFeature.COLLISION_BACKGROUND,),
            ),
        }
        for builtin_id, (emitter, features) in expected.items():
            with self.subTest(builtin=builtin_id.name):
                descriptor = builtin_by_id(builtin_id)
                self.assertIs(descriptor.emitter, emitter)
                self.assertEqual(descriptor.runtime_features, features)
                if builtin_id is not BuiltinId.BACKGROUND_COLLISION:
                    self.assertIs(descriptor.semantic_hook, SemanticHook.COLLISION)

    def test_non_collision_program_has_zero_collision_code_ram_and_zp(self) -> None:
        source = """program MinimalCollisionCost;
begin
    nes.set_background_color($0F);
    nes.run;
end.
"""
        program = resolve(source)
        layout = build_memory_layout(program)
        assembly = generate(program, layout)
        self.assertFalse(detect_collision_runtime_features(program).enabled)
        self.assertFalse(
            any("collision" in symbol.assembly_symbol for symbol in layout.runtime_symbols)
        )
        self.assertNotIn("runtime_collision_", assembly)
        self.assertNotIn("collision_map_data", assembly)

    def test_rect_queries_use_ten_regular_bytes_and_two_zp_pointer_bytes(self) -> None:
        source = geometry_source(
            "Result := nes.point_in_rect($10, $20, A) and nes.collides(A, B);"
        )
        program = resolve(source)
        layout = build_memory_layout(program)
        collision_symbols = [
            symbol
            for symbol in layout.runtime_symbols
            if symbol.assembly_symbol.startswith("runtime_collision_")
        ]
        self.assertEqual(
            sum(symbol.size for symbol in collision_symbols if symbol.address >= 0x0100),
            10,
        )
        pointer = next(
            symbol
            for symbol in collision_symbols
            if symbol.assembly_symbol == "runtime_collision_pointer"
        )
        self.assertEqual((pointer.address, pointer.size), (0x000D, 2))

    def test_collision_rect_arguments_are_strongly_typed_and_direct(self) -> None:
        source = """program WrongRect;
type
    Other = record X: byte; Y: byte; Width: byte; Height: byte; end;
var
    A: Other;
    B: nes_rect;
    Result: boolean;
begin
    A.X := $00;
    B.X := $00;
    Result := nes.collides(A, B);
    nes.set_background_color($0F);
    nes.run;
end.
"""
        with self.assertRaises(CompilerError) as raised:
            resolve(source)
        self.assertEqual(raised.exception.code, "E4004")
        self.assertIn("requires nes_rect", raised.exception.message)

    def test_collision_queries_are_rejected_on_vblank_callback_paths(self) -> None:
        source = """program VBlankCollision;
var
    A: nes_rect;
    B: nes_rect;
    Hit: boolean;

procedure DuringVBlank;
begin
    Hit := nes.collides(A, B);
end;

begin
    A.X := $00;
    B.X := $00;
    nes.on_vblank(DuringVBlank);
    nes.set_background_color($0F);
    nes.run;
end.
"""
        with self.assertRaises(CompilerError) as raised:
            resolve(source)
        self.assertEqual(
            raised.exception.code,
            DiagnosticCode.VBLANK_UNSAFE_OPERATION.value,
        )
        self.assertIn("nes.collides", raised.exception.message)
        self.assertIn("shared runtime scratch", raised.exception.suggestion or "")


class CollisionAssetTests(unittest.TestCase):
    def test_text_map_packs_960_logical_tiles_into_120_rom_bytes(self) -> None:
        source_path = ROOT / "examples" / "collision_helpers.nsp"
        packed = load_collision_map(
            ROOT / "examples" / "assets" / "collision_map.cmap",
            source_path,
            source_path.read_text(encoding="utf-8"),
        )
        assert packed is not None
        self.assertEqual(len(packed), COLLISION_MAP_PACKED_SIZE)
        self.assertEqual(packed[:4], bytes((0xFF, 0xFF, 0xFF, 0xFF)))
        self.assertEqual(packed[4], 0x01)
        self.assertEqual(packed[80:84], bytes((0xFF, 0xFF, 0xFF, 0xFF)))
        self.assertEqual(packed[-4:], bytes((0xFF, 0xFF, 0xFF, 0xFF)))

    def test_malformed_dimensions_and_values_have_stable_diagnostics(self) -> None:
        cases = (
            ("0\n" * 29, "height"),
            (("0" * 31 + "\n") * 30, "width"),
            (("0" * 32 + "\n") * 29 + "0" * 31 + "x\n", "value"),
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "main.nsp"
            source_path.write_text("program Test;", encoding="utf-8")
            for index, (contents, expected) in enumerate(cases):
                path = root / f"invalid_{index}.cmap"
                path.write_text(contents, encoding="utf-8")
                with self.subTest(expected=expected):
                    with self.assertRaises(CompilerError) as raised:
                        load_collision_map(path, source_path, "program Test;")
                    self.assertEqual(raised.exception.code, "E6021")
                    self.assertIn(expected, raised.exception.message.lower())

    def test_missing_and_unreadable_maps_have_distinct_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "main.nsp"
            source_path.write_text("program Test;", encoding="utf-8")

            with self.assertRaises(CompilerError) as missing:
                load_collision_map(
                    root / "missing.cmap",
                    source_path,
                    "program Test;",
                )
            self.assertEqual(missing.exception.code, "E6019")

            with self.assertRaises(CompilerError) as unreadable:
                load_collision_map(root, source_path, "program Test;")
            self.assertEqual(unreadable.exception.code, "E6020")

    def test_background_query_requires_an_asset_and_does_not_force_tile_shadow(self) -> None:
        source = geometry_source("Result := nes.background_collision($00, $00);")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "main.nsp"
            source_path.write_text(source, encoding="utf-8")
            with self.assertRaises(CompilerError) as raised:
                compile_source(source_path, root / "main.nes")
        self.assertEqual(raised.exception.code, "E6022")

        program = resolve(source)
        layout = build_memory_layout(program)
        self.assertIn(RuntimeFeature.COLLISION_BACKGROUND, collect_runtime_features(program))
        self.assertNotIn(
            "runtime_background_shadow",
            {symbol.assembly_symbol for symbol in layout.runtime_symbols},
        )

    def test_unused_collision_map_is_rejected_as_configuration_error(self) -> None:
        source = geometry_source("Result := nes.collides(A, B);")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "main.nsp"
            source_path.write_text(source, encoding="utf-8")
            with self.assertRaises(CompilerError) as raised:
                compile_source(
                    source_path,
                    root / "main.nes",
                    collision_map_path=(
                        ROOT / "examples" / "assets" / "collision_map.cmap"
                    ),
                )
        self.assertEqual(raised.exception.code, "E6022")

    def test_metasprite_collision_metadata_is_optional_and_flip_safe(self) -> None:
        metadata = ROOT / "tests" / "fixtures" / "runtime" / "collision_metasprite.json"
        assets = load_metasprite_assets(
            (metadata,),
            ROOT / "tests" / "fixtures" / "runtime" / "collisions.nsp",
            "program CollisionRuntime;",
            (ROOT / "examples" / "assets" / "game.chr").read_bytes(),
        )
        frame = assets[0].frames[0]
        self.assertTrue(frame.collision_box_custom)
        self.assertEqual(
            (
                frame.collision_x_offset,
                frame.collision_y_offset,
                frame.collision_width,
                frame.collision_height,
            ),
            (1, 2, 6, 5),
        )
        self.assertEqual(-frame.collision_x_offset - frame.collision_width, -7)
        self.assertEqual(-frame.collision_y_offset - frame.collision_height, -7)

        player = load_metasprite_assets(
            (ROOT / "examples" / "assets" / "player_idle.json",),
            ROOT / "examples" / "metasprite_player.nsp",
            (ROOT / "examples" / "metasprite_player.nsp").read_text(encoding="utf-8"),
            (ROOT / "examples" / "assets" / "game.chr").read_bytes(),
        )[0]
        fallback = player.frames[0]
        self.assertFalse(fallback.collision_box_custom)
        self.assertEqual(
            (
                fallback.collision_x_offset,
                fallback.collision_y_offset,
                fallback.collision_width,
                fallback.collision_height,
            ),
            (-12, -12, 24, 24),
        )

    def test_invalid_metasprite_collision_boxes_use_metadata_diagnostic(self) -> None:
        fixture = (
            ROOT / "tests" / "fixtures" / "runtime" / "collision_metasprite.json"
        )
        base = json.loads(fixture.read_text(encoding="utf-8"))
        cases = (
            ({"x": 1, "y": 2, "width": 0, "height": 5}, "width"),
            ({"x": 127, "y": 2, "width": 2, "height": 5}, "flipped"),
            (
                {"x": 1, "y": 2, "width": 6, "height": 5, "extra": 0},
                "unsupported",
            ),
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index, (box, expected) in enumerate(cases):
                metadata = json.loads(json.dumps(base))
                metadata["animations"][0]["frames"][0]["collision_box"] = box
                path = root / f"invalid_{index}.json"
                path.write_text(json.dumps(metadata), encoding="utf-8")
                with self.subTest(expected=expected):
                    with self.assertRaises(CompilerError) as raised:
                        load_metasprite_assets(
                            (path,),
                            ROOT / "tests" / "fixtures" / "runtime" / "collisions.nsp",
                            "program CollisionRuntime;",
                            (
                                ROOT / "examples" / "assets" / "game.chr"
                            ).read_bytes(),
                        )
                    self.assertEqual(raised.exception.code, "E6016")
                    self.assertIn(expected, raised.exception.message.lower())


class CollisionBackendTests(unittest.TestCase):
    def test_geometry_and_background_paths_match_focused_golden_fragments(self) -> None:
        source_path = ROOT / "examples" / "collision_helpers.nsp"
        source = source_path.read_text(encoding="utf-8")
        chr_rom = (ROOT / "examples" / "assets" / "game.chr").read_bytes()
        assets = load_metasprite_assets(
            (ROOT / "examples" / "assets" / "player_idle.json",),
            source_path,
            source,
            chr_rom,
        )
        program = resolve(source, assets=assets)
        packed = load_collision_map(
            ROOT / "examples" / "assets" / "collision_map.cmap",
            source_path,
            source,
        )
        assert packed is not None
        assembly = generate(program, build_memory_layout(program), chr_rom, None, packed)
        fragments = (
            ROOT / "tests" / "golden" / "collisions.asm"
        ).read_text(encoding="utf-8").split("\n---\n")
        for fragment in fragments:
            with self.subTest(fragment=fragment.splitlines()[0]):
                self.assertIn(fragment.strip(), assembly)

    def test_widened_bounds_and_high_map_rows_are_visible_in_assembly(self) -> None:
        source = geometry_source("Result := nes.collides(A, B);")
        program = resolve(source)
        assembly = generate(program, build_memory_layout(program))
        self.assertIn("carry plus nonzero low byte means > 256", assembly)
        self.assertIn("cmp runtime_collision_right_width", assembly)

    def test_earlier_arguments_survive_later_functions_using_collision_scratch(self) -> None:
        source = """program NestedCollisionArguments;
var
    A: nes_rect;
    Result: boolean;

function LaterY: byte;
begin
    Result := nes.point_in_rect($10, $20, A);
    LaterY := $20;
end;

begin
    A.X := $10;
    A.Y := $20;
    A.Width := $08;
    A.Height := $08;
    Result := nes.point_in_rect($18, LaterY(), A);
    nes.set_background_color($0F);
    nes.run;
end.
"""
        program = resolve(source)
        layout = build_memory_layout(program)
        assembly = generate(program, layout)

        self.assertEqual(layout.expression_temporary_bytes, 1)
        preserve = "sta expression_temporary_0 ; preserve across later call"
        restore = "lda expression_temporary_0\n    sta runtime_collision_point_x"
        self.assertIn(preserve, assembly)
        self.assertIn(restore, assembly)
        self.assertLess(assembly.index(preserve), assembly.index("jsr function_LaterY"))
        self.assertLess(assembly.index("jsr function_LaterY"), assembly.index(restore))


class CollisionBenchmarkTests(unittest.TestCase):
    @unittest.skipUnless(
        shutil.which("ca65") is not None and shutil.which("ld65") is not None,
        "collision benchmark measurement requires ca65 and ld65",
    )
    def test_focused_collision_benchmark_metrics_are_stable(self) -> None:
        expected = {
            "collision_rectangles": {
                "prg_code": 1907,
                "prg_occupied": 1913,
                "instructions": 760,
                "cycles": 2510,
                "zp": 17,
                "regular": 110,
                "oam": 256,
                "collision_data": 0,
            },
            "collision_background": {
                "prg_code": 476,
                "prg_occupied": 482,
                "instructions": 161,
                "cycles": 530,
                "zp": 11,
                "regular": 10,
                "oam": 0,
                "collision_data": 120,
            },
        }
        specifications = {
            item.name: item for item in BENCHMARKS if item.name in expected
        }

        for name, values in expected.items():
            with self.subTest(benchmark=name):
                metrics = measure_benchmark(specifications[name])
                self.assertEqual(metrics.prg_code_bytes, values["prg_code"])
                self.assertEqual(metrics.prg_total_used_bytes, values["prg_occupied"])
                self.assertEqual(
                    metrics.pattern_stats.total_instructions,
                    values["instructions"],
                )
                self.assertEqual(metrics.estimated_static_base_cycles, values["cycles"])
                self.assertEqual(
                    metrics.memory.zp_benchmark_allocated_or_reserved_bytes,
                    values["zp"],
                )
                self.assertEqual(
                    metrics.memory.regular_runtime_user_allocated_bytes,
                    values["regular"],
                )
                self.assertEqual(
                    metrics.memory.oam_shadow_allocated_bytes,
                    values["oam"],
                )
                self.assertEqual(metrics.max_live_temporaries, 0)
                self.assertEqual(metrics.collision_data_bytes, values["collision_data"])


if __name__ == "__main__":
    unittest.main()
