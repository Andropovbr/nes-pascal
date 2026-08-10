from pathlib import Path
import unittest

from nes_pascal.ast import (
    Assignment,
    BuiltinCall,
    BuiltInType,
    ImmediateValue,
    OamOwnerKind,
    ResolvedAssignment,
    ResolvedBuiltinCall,
)
from nes_pascal.builtins import BuiltinId
from nes_pascal.backend_ca65 import generate
from nes_pascal.diagnostics import CompilerError
from nes_pascal.memory_layout import build_memory_layout
from nes_pascal.parser import parse
from nes_pascal.semantic import analyze


ROOT = Path(__file__).resolve().parents[1]


def program(body: str, declarations: str = "    Current: sprite;\n") -> str:
    variable_section = f"var\n{declarations}" if declarations else ""
    return f"""program SpriteManagement;
{variable_section}
begin
    {body}
    nes.set_background_color($0F);
    nes.run;
end.
"""


def resolve(source: str, filename: str = "sprite_management_test.nsp"):
    return analyze(parse(source, filename), source, filename)


class SpriteAllocationTests(unittest.TestCase):
    def test_parser_and_semantics_model_static_sprite_creation(self) -> None:
        source = program("Current := nes.sprite_create();")
        parsed = parse(source)
        assignment = parsed.statements[0]
        self.assertIsInstance(assignment, Assignment)
        assert isinstance(assignment, Assignment)
        self.assertIsInstance(assignment.value, BuiltinCall)
        self.assertEqual(assignment.value.name, "nes.sprite_create")

        resolved = resolve(source)
        resolved_assignment = resolved.statements[0]
        self.assertIsInstance(resolved_assignment, ResolvedAssignment)
        assert isinstance(resolved_assignment, ResolvedAssignment)
        self.assertEqual(
            resolved_assignment.value,
            ResolvedBuiltinCall(
                BuiltinId.SPRITE_CREATE,
                (ImmediateValue(0, BuiltInType.BYTE),),
            ),
        )
        self.assertEqual(
            [(item.index, item.owner) for item in resolved.oam_reservations],
            [(0, OamOwnerKind.INDIVIDUAL_CREATED)],
        )

    def test_multiple_creation_sites_are_distinct_and_deterministic(self) -> None:
        source = program(
            "First := nes.sprite_create();\n"
            "    Second := nes.sprite_create();\n"
            "    Third := nes.sprite_create();",
            "    First: sprite;\n    Second: sprite;\n    Third: sprite;\n",
        )
        resolved = resolve(source)
        values = [
            statement.value.arguments[0].value
            for statement in resolved.statements[:3]
            if isinstance(statement, ResolvedAssignment)
            and isinstance(statement.value, ResolvedBuiltinCall)
            and statement.value.builtin is BuiltinId.SPRITE_CREATE
        ]
        self.assertEqual(values, [0, 1, 2])
        self.assertEqual(len(values), len(set(values)))

    def test_explicit_indexes_are_reserved_before_automatic_allocation(self) -> None:
        source = """program MixedSpriteOwnership;
const
    ReservedZero: sprite = $00;
    ReservedTwo: sprite = $02;
var
    First: sprite;
    Second: sprite;
begin
    First := nes.sprite_create();
    Second := nes.sprite_create();
    nes.sprite_show($04);
    nes.set_background_color($0F);
    nes.run;
end.
"""
        resolved = resolve(source)
        reservations = {
            item.index: item.owner for item in resolved.oam_reservations
        }
        self.assertEqual(
            reservations,
            {
                0: OamOwnerKind.INDIVIDUAL_EXPLICIT,
                1: OamOwnerKind.INDIVIDUAL_CREATED,
                2: OamOwnerKind.INDIVIDUAL_EXPLICIT,
                3: OamOwnerKind.INDIVIDUAL_CREATED,
                4: OamOwnerKind.INDIVIDUAL_EXPLICIT,
            },
        )

    def test_one_creation_site_inside_a_procedure_keeps_one_identity(self) -> None:
        source = """program ProcedureSpriteCreation;
var
    Current: sprite;
procedure Acquire;
begin
    Current := nes.sprite_create();
end;
begin
    Acquire;
    Acquire;
    nes.sprite_show(Current);
    nes.set_background_color($0F);
    nes.run;
end.
"""
        resolved = resolve(source)
        created = [
            item
            for item in resolved.oam_reservations
            if item.owner is OamOwnerKind.INDIVIDUAL_CREATED
        ]
        self.assertEqual([item.index for item in created], [0])

    def test_conditional_creation_sites_reserve_distinct_static_slots(self) -> None:
        source = """program ConditionalSpriteCreation;
var
    Enabled: boolean;
    First: sprite;
    Second: sprite;
begin
    Enabled := true;
    if Enabled then
        First := nes.sprite_create()
    else
        Second := nes.sprite_create();
    nes.set_background_color($0F);
    nes.run;
end.
"""
        resolved = resolve(source)
        created = [
            item.index
            for item in resolved.oam_reservations
            if item.owner is OamOwnerKind.INDIVIDUAL_CREATED
        ]
        self.assertEqual(created, [0, 1])

    def test_exactly_64_creation_sites_use_every_hardware_slot_once(self) -> None:
        assignments = "\n".join(
            "    Current := nes.sprite_create();" for _ in range(64)
        )
        resolved = resolve(program(assignments))
        created = [
            item.index
            for item in resolved.oam_reservations
            if item.owner is OamOwnerKind.INDIVIDUAL_CREATED
        ]
        self.assertEqual(created, list(range(64)))

    def test_creation_diagnostics_are_focused_and_stable(self) -> None:
        fixtures = {
            "sprite_create_argument_count.nsp": "E3049",
            "sprite_capacity_exhausted.nsp": "E3050",
        }
        directory = ROOT / "tests" / "fixtures" / "diagnostics"
        for filename, expected in fixtures.items():
            with self.subTest(filename=filename):
                path = directory / filename
                source = path.read_text(encoding="utf-8")
                with self.assertRaises(CompilerError) as context:
                    resolve(source, str(path))
                self.assertEqual(context.exception.code, expected)

    def test_sprite_create_result_requires_a_sprite_context(self) -> None:
        source = program(
            "Counter := nes.sprite_create();",
            "    Counter: byte;\n",
        )
        with self.assertRaises(CompilerError) as context:
            resolve(source)
        self.assertEqual(context.exception.code, "E4004")


class SpritePositionTests(unittest.TestCase):
    def test_second_staging_byte_is_linked_only_for_set_position(self) -> None:
        resolved = resolve(
            program("nes.sprite_set_x($00, $40);", "")
        )
        symbols = {
            symbol.assembly_symbol
            for symbol in build_memory_layout(resolved).runtime_symbols
        }
        self.assertNotIn("runtime_sprite_secondary_value", symbols)

    def test_parser_models_set_position_and_boundaries_are_valid(self) -> None:
        source = program(
            "nes.sprite_set_position($00, $00, $00);\n"
            "    nes.sprite_set_position($3F, $FF, $FF);",
            "",
        )
        parsed = parse(source)
        operations = [
            statement
            for statement in parsed.statements
            if isinstance(statement, BuiltinCall)
            and statement.name == "nes.sprite_set_position"
        ]
        self.assertEqual(
            [operation.name for operation in operations],
            ["nes.sprite_set_position", "nes.sprite_set_position"],
        )
        resolve(source)

    def test_set_position_requires_sprite_byte_byte(self) -> None:
        invalid_sources = (
            (program("nes.sprite_set_position($00, $10);", ""), "E3047"),
            (
                program("nes.sprite_set_position($00, true, $10);", ""),
                "E4004",
            ),
        )
        for source, expected in invalid_sources:
            with self.subTest(expected=expected):
                with self.assertRaises(CompilerError) as context:
                    resolve(source)
                self.assertEqual(context.exception.code, expected)

    def test_dynamic_set_position_computes_the_oam_address_once(self) -> None:
        source = program(
            "Current := nes.sprite_create();\n"
            "    nes.sprite_set_position(Current, $40, $80);\n"
            "    nes.sprite_hide(Current);\n"
            "    nes.sprite_show(Current);"
        )
        resolved = resolve(source)
        layout = build_memory_layout(resolved)
        symbols = {
            symbol.assembly_symbol: (symbol.address, symbol.size)
            for symbol in layout.runtime_symbols
        }
        self.assertEqual(symbols["runtime_sprite_secondary_value"], (0x0341, 1))

        assembly = generate(resolved, layout)
        routine = assembly.split("runtime_sprite_set_position:", 1)[1].split(
            "rts", 1
        )[0]
        self.assertEqual(routine.count("asl a"), 2)
        self.assertEqual(routine.count("tax"), 1)
        self.assertIn("sta runtime_oam_shadow + 3, x", routine)
        self.assertIn("sta runtime_sprite_logical_y, y", routine)
        self.assertIn("cmp #$FF", routine)
        self.assertIn("sta runtime_oam_shadow, x", routine)

    def test_constant_set_position_updates_x_and_logical_y_directly(self) -> None:
        source = program(
            "nes.sprite_set_position($3F, $40, $80);\n"
            "    nes.sprite_hide($3F);\n"
            "    nes.sprite_show($3F);",
            "",
        )
        assembly = generate(resolve(source))
        block = assembly.split("; Source: nes.sprite_set_position", 1)[1].split(
            "; Source: nes.sprite_hide", 1
        )[0]
        self.assertIn("sta runtime_oam_shadow + 252 + 3", block)
        self.assertIn("sta runtime_sprite_logical_y + 63", block)
        self.assertIn("sta runtime_oam_shadow + 252", block)


if __name__ == "__main__":
    unittest.main()
