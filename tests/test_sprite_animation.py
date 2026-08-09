import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from nes_pascal.ast import (
    ImmediateValue,
    MetaspriteOperationKind,
    ResolvedAssignment,
    ResolvedMetaspriteAnimationFinished,
    ResolvedMetaspriteOperation,
)
from nes_pascal.backend_ca65 import generate
from nes_pascal.cli import compile_source
from nes_pascal.diagnostics import CompilerError, DiagnosticCode
from nes_pascal.memory_layout import build_memory_layout
from nes_pascal.metasprite_assets import load_metasprite_assets
from nes_pascal.parser import parse
from nes_pascal.semantic import analyze


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "sprite_animation.nsp"
METADATA = ROOT / "examples" / "assets" / "player_consolidated.json"
CHR = ROOT / "examples" / "assets" / "game.chr"
RUNTIME_SOURCE = ROOT / "tests" / "fixtures" / "runtime" / "sprite_animation.nsp"
RUNTIME_METADATA = ROOT / "tests" / "fixtures" / "runtime" / "sprite_animation.json"
MINIMAL_SOURCE = "program AssetTest;\nbegin\n    nes.run;\nend.\n"


def load_assets(paths: tuple[Path, ...]):
    return load_metasprite_assets(
        paths,
        EXAMPLE,
        EXAMPLE.read_text(encoding="utf-8"),
        CHR.read_bytes(),
    )


def load_document(document: object):
    with tempfile.TemporaryDirectory() as temporary_directory:
        path = Path(temporary_directory) / "asset.json"
        path.write_text(json.dumps(document), encoding="utf-8")
        return load_metasprite_assets(
            (path,),
            Path(temporary_directory) / "main.nsp",
            MINIMAL_SOURCE,
            CHR.read_bytes(),
        )[0]


def resolve(source: str, assets):
    return analyze(
        parse(source, "sprite_animation_test.nsp"),
        source,
        "sprite_animation_test.nsp",
        metasprite_assets=assets,
    )


def animation_program(body: str, *, declarations: str = "") -> str:
    extra = f"    {declarations}\n" if declarations else ""
    return f"""program SpriteAnimationTest;
var
    Player: metasprite;
{extra}begin
    nes.import_metasprite(shape);
    Player := nes.metasprite_create(shape.cycle_0);
    {body}
    nes.set_background_color($0F);
    nes.run;
end.
"""


class SpriteAnimationAssetTests(unittest.TestCase):
    def test_attached_player_animation_is_imported_as_symbolic_sequences(self) -> None:
        self.assertFalse(METADATA.with_name("player_consolidated.png").exists())
        asset = load_assets((METADATA,))[0]
        self.assertEqual(asset.name, "player")
        self.assertEqual(len(asset.frames), 14)
        self.assertEqual(
            [animation.symbol for animation in asset.animations],
            ["player.idle", "player.movement_right"],
        )
        self.assertEqual([animation.id for animation in asset.animations], [0, 1])
        self.assertEqual(asset.animations[0].frame_ids, tuple(range(6)))
        self.assertEqual(asset.animations[1].frame_ids, tuple(range(6, 14)))
        self.assertEqual(asset.animations[0].durations, (6,) * 6)
        self.assertEqual(asset.animations[1].durations, (6,) * 8)
        self.assertTrue(all(animation.loop for animation in asset.animations))

    def test_manual_and_animated_consumers_share_normalized_frame_geometry(self) -> None:
        asset = load_assets((METADATA,))[0]
        idle = asset.animations[0]
        direct_frame = next(frame for frame in asset.frames if frame.symbol == "player.idle_0")
        animated_frame = asset.frames[idle.frame_ids[0]]
        self.assertIs(direct_frame, animated_frame)
        self.assertEqual((direct_frame.origin_x, direct_frame.origin_y), (12, 12))
        self.assertEqual(
            [(component.x_offset, component.y_offset) for component in direct_frame.components],
            [(-4, -12), (4, -12), (-4, -4), (4, -4), (-12, 4), (-4, 4), (4, 4)],
        )

        direct_source = """program DirectFrameGeometry;
var Player: metasprite;
begin
    nes.import_metasprite(player);
    Player := nes.metasprite_create(player.idle_0);
    nes.metasprite_set_frame(Player, player.idle_0);
    nes.set_background_color($0F);
    nes.run;
end.
"""
        animated_source = direct_source.replace(
            "nes.metasprite_set_frame(Player, player.idle_0);",
            "nes.metasprite_set_animation(Player, player.idle);",
        )
        direct_assembly = generate(resolve(direct_source, (asset,)))
        animated_assembly = generate(resolve(animated_source, (asset,)))

        def emitted_frame(assembly: str) -> str:
            return assembly.split("metasprite_frame_0:", 1)[1].split(
                "metasprite_frame_1:", 1
            )[0]

        self.assertEqual(emitted_frame(direct_assembly), emitted_frame(animated_assembly))

    def test_centered_player_bounds_and_component_flip_xor_are_stable(self) -> None:
        asset = load_assets((METADATA,))[0]
        for frame in asset.frames:
            normal = [
                (component.x_offset, component.y_offset, component.attributes)
                for component in frame.components
            ]
            horizontal = [
                (-component.x_offset - 8, component.y_offset, component.attributes ^ 0x40)
                for component in frame.components
            ]
            vertical = [
                (component.x_offset, -component.y_offset - 8, component.attributes ^ 0x80)
                for component in frame.components
            ]

            def bounds(geometry):
                return (
                    min(x for x, _, _ in geometry),
                    max(x + 8 for x, _, _ in geometry),
                    min(y for _, y, _ in geometry),
                    max(y + 8 for _, y, _ in geometry),
                )

            self.assertEqual(bounds(normal), (-12, 12, -12, 12))
            self.assertEqual(bounds(horizontal), bounds(normal))
            self.assertEqual(bounds(vertical), bounds(normal))

        first = asset.frames[0]
        self.assertEqual(first.components[0].attributes & 0x40, 0)
        self.assertEqual(first.components[1].attributes & 0x40, 0x40)
        self.assertEqual(first.components[0].attributes ^ 0x40, 0x40)
        self.assertEqual(first.components[1].attributes ^ 0x40, 0)

    def test_player_example_switches_state_without_directional_animation_names(self) -> None:
        source = EXAMPLE.read_text(encoding="utf-8")
        self.assertIn("Moving := false;", source)
        self.assertIn(
            "if Moving then\n"
            "        nes.metasprite_set_animation(Player, player.movement_right)\n"
            "    else\n"
            "        nes.metasprite_set_animation(Player, player.idle);",
            source,
        )
        self.assertIn("Player := nes.metasprite_create(player.idle_0);", source)
        self.assertNotIn("movement_left", source)
        parse(source, str(EXAMPLE))

    def test_animated_frames_clip_at_every_edge_without_coordinate_wrap(self) -> None:
        asset = load_assets((METADATA,))[0]
        edge_positions = (
            (8, 104),
            (248, 104),
            (112, 8),
            (112, 236),
        )
        for frame in asset.frames:
            for horizontal_flip in (False, True):
                for vertical_flip in (False, True):
                    offsets = [
                        (
                            -component.x_offset - 8
                            if horizontal_flip
                            else component.x_offset,
                            -component.y_offset - 8
                            if vertical_flip
                            else component.y_offset,
                        )
                        for component in frame.components
                    ]
                    for logical_x, logical_y in edge_positions:
                        geometry = [
                            (logical_x + x_offset, logical_y + y_offset)
                            for x_offset, y_offset in offsets
                        ]
                        visible = [
                            (x, y)
                            for x, y in geometry
                            if 0 <= x <= 248 and 1 <= y <= 232
                        ]
                        with self.subTest(
                            frame=frame.symbol,
                            horizontal_flip=horizontal_flip,
                            vertical_flip=vertical_flip,
                            position=(logical_x, logical_y),
                        ):
                            self.assertTrue(visible)
                            self.assertLess(len(visible), len(geometry))
                            self.assertTrue(
                                all(0 <= x <= 248 and 1 <= y <= 232 for x, y in visible)
                            )

    def test_human_clipping_demo_is_partial_and_does_not_link_animation(self) -> None:
        path = ROOT / "examples" / "metasprite_clipping.nsp"
        source = path.read_text(encoding="utf-8")
        parsed = parse(source, str(path))
        constants = {
            declaration.name: declaration.value.value
            for declaration in parsed.constants
        }
        self.assertEqual(
            {
                name: constants[name]
                for name in (
                    "PartlyBeyondLeftX",
                    "PartlyBeyondRightX",
                    "PartlyBeyondTopY",
                    "PartlyBeyondBottomY",
                )
            },
            {
                "PartlyBeyondLeftX": 0x08,
                "PartlyBeyondRightX": 0xF8,
                "PartlyBeyondTopY": 0x08,
                "PartlyBeyondBottomY": 0xEC,
            },
        )
        static_asset = load_assets(
            (ROOT / "examples" / "assets" / "player_idle.json",)
        )[0]
        resolved = resolve(source, (static_asset,))
        assembly = generate(resolved)
        symbols = {
            symbol.assembly_symbol
            for symbol in build_memory_layout(resolved).runtime_symbols
        }
        self.assertNotIn("runtime_metasprite_animation", symbols)
        self.assertNotIn("runtime_metasprite_update_animations", assembly)

    def test_default_per_frame_duration_and_loop_policy_are_preserved(self) -> None:
        asset = load_assets((RUNTIME_METADATA,))[0]
        cycle, burst = asset.animations
        self.assertEqual(cycle.durations, (2, 3, 1))
        self.assertEqual(cycle.frame_ids, (0, 1, 2))
        self.assertTrue(cycle.loop)
        self.assertEqual(burst.durations, (1, 2))
        self.assertEqual(burst.frame_ids, (3, 4))
        self.assertFalse(burst.loop)

    def test_legacy_static_metadata_without_durations_defaults_to_one(self) -> None:
        document = json.loads(RUNTIME_METADATA.read_text(encoding="utf-8"))
        animation = document["animations"][0]
        animation.pop("default_frame_duration")
        for frame in animation["frames"]:
            frame.pop("duration", None)
        asset = load_document(document)
        self.assertEqual(asset.animations[0].durations, (1, 1, 1))

    def test_invalid_animation_metadata_is_rejected_deterministically(self) -> None:
        base = json.loads(RUNTIME_METADATA.read_text(encoding="utf-8"))
        cases = []

        zero_default = copy.deepcopy(base)
        zero_default["animations"][0]["default_frame_duration"] = 0
        cases.append(zero_default)

        zero_frame = copy.deepcopy(base)
        zero_frame["animations"][0]["frames"][0]["duration"] = 0
        cases.append(zero_frame)

        invalid_loop = copy.deepcopy(base)
        invalid_loop["animations"][0]["loop"] = 1
        cases.append(invalid_loop)

        duplicate = copy.deepcopy(base)
        duplicate["animations"][1]["name"] = "cycle"
        cases.append(duplicate)

        empty = copy.deepcopy(base)
        empty["animations"][0]["frames"] = []
        cases.append(empty)

        unsupported = copy.deepcopy(base)
        unsupported["animations"][0]["playback_speed"] = 2
        cases.append(unsupported)

        for document in cases:
            with self.subTest(document=document):
                with self.assertRaises(CompilerError) as raised:
                    load_document(document)
                self.assertEqual(
                    raised.exception.code,
                    DiagnosticCode.INVALID_METASPRITE_METADATA,
                )


class SpriteAnimationSemanticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.asset = load_assets((RUNTIME_METADATA,))[0]

    def test_public_operations_and_completion_expression_resolve(self) -> None:
        source = animation_program(
            "nes.metasprite_set_animation(Player, shape.cycle);\n"
            "    nes.metasprite_restart_animation(Player);\n"
            "    Finished := nes.metasprite_animation_finished(Player);",
            declarations="Finished: boolean;",
        )
        resolved = resolve(source, (self.asset,))
        operations = [
            statement
            for statement in resolved.statements
            if isinstance(statement, ResolvedMetaspriteOperation)
        ]
        self.assertEqual(
            [operation.kind for operation in operations],
            [
                MetaspriteOperationKind.SET_ANIMATION,
                MetaspriteOperationKind.RESTART_ANIMATION,
            ],
        )
        self.assertEqual(operations[0].value, ImmediateValue(0, operations[0].value.type))
        assignment = next(
            statement
            for statement in resolved.statements
            if isinstance(statement, ResolvedAssignment)
            and statement.target.name == "Finished"
        )
        self.assertIsInstance(assignment.value, ResolvedMetaspriteAnimationFinished)

    def test_numeric_animation_is_rejected_by_the_public_diagnostic(self) -> None:
        source = animation_program("nes.metasprite_set_animation(Player, $00);")
        with self.assertRaises(CompilerError) as raised:
            resolve(source, (self.asset,))
        self.assertEqual(
            raised.exception.code,
            DiagnosticCode.INVALID_METASPRITE_ANIMATION,
        )

    def test_cross_asset_animation_is_rejected_when_the_instance_is_static(self) -> None:
        shape_document = json.loads(RUNTIME_METADATA.read_text(encoding="utf-8"))
        enemy_document = copy.deepcopy(shape_document)
        enemy_document["name"] = "enemy"
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            shape_path = root / "shape.json"
            enemy_path = root / "enemy.json"
            shape_path.write_text(json.dumps(shape_document), encoding="utf-8")
            enemy_path.write_text(json.dumps(enemy_document), encoding="utf-8")
            assets = load_metasprite_assets(
                (shape_path, enemy_path),
                root / "main.nsp",
                MINIMAL_SOURCE,
                CHR.read_bytes(),
            )
        source = """program CrossAssetAnimation;
begin
    nes.import_metasprite(shape);
    nes.import_metasprite(enemy);
    nes.metasprite_set_animation(
        nes.metasprite_create(shape.cycle_0),
        enemy.cycle
    );
    nes.set_background_color($0F);
    nes.run;
end.
"""
        with self.assertRaises(CompilerError) as raised:
            resolve(source, assets)
        self.assertEqual(
            raised.exception.code,
            DiagnosticCode.INVALID_METASPRITE_ANIMATION,
        )

    def test_diagnostic_fixture_emits_only_e3056(self) -> None:
        player = load_assets((ROOT / "examples" / "assets" / "player_idle.json",))[0]
        path = ROOT / "tests" / "fixtures" / "diagnostics" / "invalid_metasprite_animation.nsp"
        source = path.read_text(encoding="utf-8")
        with self.assertRaises(CompilerError) as raised:
            resolve(source, (player,))
        self.assertEqual(raised.exception.code, "E3056")


class SpriteAnimationBackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.asset = load_assets((RUNTIME_METADATA,))[0]
        cls.source = RUNTIME_SOURCE.read_text(encoding="utf-8")
        cls.resolved = resolve(cls.source, (cls.asset,))
        cls.layout = build_memory_layout(cls.resolved)
        cls.assembly = generate(cls.resolved, cls.layout, chr_rom=CHR.read_bytes())

    def test_animation_state_cost_is_four_extra_bytes_per_instance(self) -> None:
        symbols = {
            symbol.assembly_symbol: symbol.size
            for symbol in self.layout.runtime_symbols
            if symbol.assembly_symbol.startswith("runtime_metasprite_")
            and symbol.region_name == self.layout.runtime_data.name
        }
        self.assertEqual(
            {name: symbols[name] for name in (
                "runtime_metasprite_animation",
                "runtime_metasprite_animation_frame",
                "runtime_metasprite_animation_timer",
                "runtime_metasprite_animation_flags",
            )},
            {
                "runtime_metasprite_animation": 2,
                "runtime_metasprite_animation_frame": 2,
                "runtime_metasprite_animation_timer": 2,
                "runtime_metasprite_animation_flags": 2,
            },
        )
        self.assertEqual(sum(symbols.values()), 24)

    def test_animation_sequences_are_compact_prg_rom_tables(self) -> None:
        self.assertIn("metasprite_animation_frame_count:\n    .byte $03, $02", self.assembly)
        self.assertIn("metasprite_animation_flags:\n    .byte $01, $00", self.assembly)
        self.assertIn(
            "; shape.cycle: frame id, duration pairs\n"
            "    .byte $00, $02, $01, $03, $02, $01",
            self.assembly,
        )
        self.assertIn(
            "; shape.burst: frame id, duration pairs\n"
            "    .byte $03, $01, $04, $02",
            self.assembly,
        )
        self.assertEqual(self.assembly.count("metasprite_animation_0:"), 1)

    def test_update_is_main_thread_frame_synchronized_and_outside_nmi(self) -> None:
        main_loop = self.assembly.split("@runtime_update_loop:", 1)[1].split(
            "; Runtime: idempotent controller update", 1
        )[0]
        self.assertLess(
            main_loop.index("jsr runtime_metasprite_update_animations"),
            main_loop.index("jsr procedure_Update"),
        )
        nmi = self.assembly.split("NMI:", 1)[1].split("IRQ:", 1)[0]
        self.assertNotIn("runtime_metasprite_update_animations", nmi)
        self.assertNotIn("runtime_metasprite_render", nmi)

    def test_animation_without_user_callback_still_gets_a_frame_loop(self) -> None:
        source = animation_program(
            "nes.metasprite_set_animation(Player, shape.cycle);"
        )
        assembly = generate(resolve(source, (self.asset,)))
        self.assertIn("@runtime_animation_loop:", assembly)
        self.assertIn("jsr runtime_metasprite_update_animations", assembly)
        self.assertNotIn("jsr procedure_", assembly)

    def test_same_assignment_restart_and_manual_frame_rules_are_explicit(self) -> None:
        set_animation = self.assembly.split(
            "runtime_metasprite_set_animation:", 1
        )[1].split("runtime_metasprite_restart_animation:", 1)[0]
        self.assertIn("same active animation keeps timing", set_animation)
        self.assertIn("jsr runtime_metasprite_begin_animation", set_animation)
        self.assertIn("runtime_metasprite_restart_animation:", self.assembly)
        self.assertIn("manual frame disables playback", self.assembly)

    def test_one_shot_completion_and_hidden_playback_have_distinct_state(self) -> None:
        update = self.assembly.split(
            "runtime_metasprite_update_animations:", 1
        )[1].split("runtime_metasprite_begin_animation:", 1)[0]
        self.assertNotIn("runtime_metasprite_flags", update)
        advance = self.assembly.split(
            "runtime_metasprite_advance_animation:", 1
        )[1].split("runtime_metasprite_render:", 1)[0]
        self.assertIn("@metasprite_animation_complete:", advance)
        self.assertIn("ora #$01", advance)
        self.assertIn("keep final frame and mark completed", advance)

    def test_static_metasprites_do_not_link_animation_state_or_code(self) -> None:
        source = animation_program("nes.metasprite_set_frame(Player, shape.cycle_1);")
        resolved = resolve(source, (self.asset,))
        assembly = generate(resolved)
        symbols = {
            symbol.assembly_symbol
            for symbol in build_memory_layout(resolved).runtime_symbols
        }
        self.assertNotIn("runtime_metasprite_animation", symbols)
        self.assertNotIn("runtime_metasprite_update_animations", assembly)
        self.assertNotIn("metasprite_animation_pointer_low", assembly)

    @unittest.skipUnless(
        shutil.which("ca65") and shutil.which("ld65"),
        "sprite animation ROM integration requires ca65 and ld65",
    )
    def test_public_example_builds_a_valid_nrom_image(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "sprite_animation.nes"
            compile_source(
                EXAMPLE,
                output,
                chr_path="assets/game.chr",
                metasprite_paths=("assets/player_consolidated.json",),
            )
            rom = output.read_bytes()
        self.assertEqual(rom[:6], b"NES\x1A\x02\x01")
        self.assertEqual(len(rom), 16 + 32 * 1024 + 8 * 1024)
        self.assertEqual(rom[-8192:], CHR.read_bytes())


if __name__ == "__main__":
    unittest.main()
