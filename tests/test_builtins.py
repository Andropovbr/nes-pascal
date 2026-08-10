from dataclasses import fields
import unittest

from nes_pascal.ast import (
    BuiltinCall,
    CallbackRegistration,
    ImportMetasprite,
    LoadBackground,
    ResolvedBuiltinCall,
    Run,
)
from nes_pascal.builtins import (
    BUILTINS_BY_ID,
    BUILTINS_BY_NAME,
    BackendEmitter,
    BuiltinId,
    BuiltinKind,
    RuntimeFeature,
)
from nes_pascal.diagnostics import CompilerError
from nes_pascal.memory_layout import (
    build_memory_layout,
    collect_runtime_features,
)
from nes_pascal.parser import parse
from nes_pascal.semantic import analyze


def program_with(body: str, variables: str = "") -> str:
    variable_section = f"var\n{variables}\n" if variables else ""
    return f"""program BuiltinTest;
{variable_section}begin
{body}
end.
"""


def analyze_source(source: str):
    return analyze(parse(source, "builtins.nsp"), source, "builtins.nsp")


class BuiltinRegistryTests(unittest.TestCase):
    def test_registry_has_one_immutable_descriptor_per_stable_identity(self) -> None:
        self.assertEqual(len(BUILTINS_BY_NAME), len(BUILTINS_BY_ID))
        self.assertEqual(set(BUILTINS_BY_ID), set(BuiltinId))
        for public_name, descriptor in BUILTINS_BY_NAME.items():
            with self.subTest(public_name=public_name):
                self.assertEqual(public_name, public_name.lower())
                self.assertIs(BUILTINS_BY_ID[descriptor.id], descriptor)
                self.assertIsInstance(descriptor.emitter, BackendEmitter)
                self.assertEqual(
                    descriptor.return_type is None,
                    descriptor.kind is BuiltinKind.STATEMENT,
                )

    def test_ast_shape_does_not_grow_per_ordinary_builtin(self) -> None:
        self.assertEqual(
            [field.name for field in fields(BuiltinCall)],
            ["name", "arguments", "position"],
        )
        self.assertEqual(
            [field.name for field in fields(ResolvedBuiltinCall)],
            ["builtin", "arguments", "queued"],
        )


class BuiltinPipelineTests(unittest.TestCase):
    def test_statement_families_share_the_builtin_call_parser_path(self) -> None:
        source = program_with(
            """nes.set_background_palette($00, $0F, $01, $11, $21);
nes.set_scroll($00, $00);
nes.sprite_show($00);
nes.metasprite_hide(Player);
nes.metasprite_restart_animation(Player);
nes.set_background_color($0F);
nes.run;""",
            "Player: metasprite;",
        )
        parsed = parse(source)
        calls = [item for item in parsed.statements if isinstance(item, BuiltinCall)]
        self.assertEqual(
            [call.name for call in calls],
            [
                "nes.set_background_palette",
                "nes.set_scroll",
                "nes.sprite_show",
                "nes.metasprite_hide",
                "nes.metasprite_restart_animation",
                "nes.set_background_color",
            ],
        )

    def test_value_families_resolve_to_stable_builtin_identities(self) -> None:
        source = program_with(
            """Sprite := nes.sprite_create();
Pressed := nes.controller_pressed($01, nes.button_a);
Overflowed := nes.background_updates_overflowed();
nes.set_background_color($0F);
nes.run;""",
            "Sprite: sprite;\nPressed: boolean;\nOverflowed: boolean;",
        )
        resolved = analyze_source(source)
        values = [resolved.statements[index].value for index in range(3)]
        self.assertEqual(
            [value.builtin for value in values],
            [
                BuiltinId.SPRITE_CREATE,
                BuiltinId.CONTROLLER_PRESSED,
                BuiltinId.BACKGROUND_UPDATES_OVERFLOWED,
            ],
        )

    def test_generic_argument_count_and_context_diagnostics_are_stable(self) -> None:
        cases = (
            (
                program_with("nes.set_background_color($0F, $01);\nnes.run;"),
                "E3058",
            ),
            (
                program_with(
                    "Value := nes.set_scroll($00, $00);\n"
                    "nes.set_background_color($0F);\nnes.run;",
                    "Value: byte;",
                ),
                "E3057",
            ),
            (
                program_with(
                    "nes.sprite_create();\nnes.set_background_color($0F);\nnes.run;"
                ),
                "E3057",
            ),
        )
        for source, code in cases:
            with self.subTest(code=code):
                with self.assertRaises(CompilerError) as raised:
                    analyze_source(source)
                self.assertEqual(raised.exception.code, code)

    def test_custom_validation_stays_behind_explicit_hooks(self) -> None:
        source = program_with(
            "Pressed := nes.controller_down($03, nes.button_a);\n"
            "nes.set_background_color($0F);\nnes.run;",
            "Pressed: boolean;",
        )
        with self.assertRaises(CompilerError) as raised:
            analyze_source(source)
        self.assertEqual(raised.exception.code, "E3026")

    def test_runtime_dependencies_come_from_resolved_descriptors(self) -> None:
        source = program_with(
            "nes.set_background_color($0F);\n"
            "nes.run;\n"
            "nes.set_tile($01, $02, $03);"
        )
        resolved = analyze_source(source)
        features = collect_runtime_features(resolved)
        self.assertIn(RuntimeFeature.BACKGROUND_SET_TILE, features)
        self.assertNotIn(RuntimeFeature.BACKGROUND_GET_TILE, features)
        layout = build_memory_layout(resolved)
        self.assertNotIn(
            "runtime_background_shadow",
            {symbol.assembly_symbol for symbol in layout.runtime_symbols},
        )

    def test_special_constructs_remain_intentionally_specialized(self) -> None:
        source = program_with(
            """nes.import_metasprite(player);
nes.load_background();
nes.on_update(Update);
nes.on_vblank(VBlank);
nes.set_background_color($0F);
nes.run;"""
        )
        parsed = parse(source)
        self.assertIsInstance(parsed.statements[0], ImportMetasprite)
        self.assertIsInstance(parsed.statements[1], LoadBackground)
        self.assertIsInstance(parsed.statements[2], CallbackRegistration)
        self.assertIsInstance(parsed.statements[3], CallbackRegistration)
        self.assertIsInstance(parsed.statements[-1], Run)


if __name__ == "__main__":
    unittest.main()
