from dataclasses import asdict
from pathlib import Path
import shutil
import unittest

from nes_pascal.ast import (
    ArrayType,
    BuiltInType,
    EnumType,
    ImmediateValue,
    RecordFieldAssignment,
    RecordFieldExpression,
    RecordType,
    ResolvedAssignment,
    ResolvedRecordField,
    ResolvedRecordFieldAssignment,
)
from nes_pascal.backend_ca65 import generate
from nes_pascal.diagnostics import CompilerError
from nes_pascal.lexer import TokenKind, tokenize
from nes_pascal.memory_layout import build_memory_layout, generate_memory_map
from nes_pascal.parser import parse
from nes_pascal.semantic import analyze


ROOT = Path(__file__).resolve().parents[1]
DIAGNOSTICS = ROOT / "tests" / "fixtures" / "diagnostics"


def program_with(body: str, types: str, variables: str) -> str:
    return f"""program Records;
type
{types}
var
{variables}
begin
{body}
    nes.set_background_color($0F);
    nes.run;
end.
"""


def resolve(source: str, filename: str = "records.nsp"):
    return analyze(parse(source, filename), source, filename)


RECORD_TYPES = """    EntityState = (Idle, Moving, Dead);
    Entity = record
        X: byte;
        Y: byte;
        Active: boolean;
        State: EntityState;
    end;"""


class RecordParserTests(unittest.TestCase):
    def test_lexer_and_parser_preserve_named_record_structure(self) -> None:
        tokens = tokenize("Entity = record X: byte; end;")
        self.assertIn(TokenKind.RECORD, [token.kind for token in tokens])
        source = program_with(
            "    Player.X := $10;\n    Result := Enemies[Index].Y;",
            RECORD_TYPES,
            "    Player: Entity;\n    Enemies: array[$00..$03] of Entity;\n    Index: byte;\n    Result: byte;",
        )
        program = parse(source)
        declaration = program.record_types[0]
        self.assertEqual(declaration.name, "Entity")
        self.assertEqual([field.name for field in declaration.fields], ["X", "Y", "Active", "State"])
        self.assertIsInstance(program.statements[0], RecordFieldAssignment)
        read = program.statements[1]
        assert isinstance(read, object)
        self.assertIsInstance(read.value, RecordFieldExpression)
        self.assertIsNotNone(read.value.index)

    def test_rejects_malformed_record_declarations(self) -> None:
        malformed = (
            "    Entity = record X byte; end;",
            "    Entity = record X: byte end;",
            "    Entity = record X: byte;",
        )
        for declaration in malformed:
            with self.subTest(declaration=declaration):
                source = program_with("", declaration, "    Counter: byte;")
                with self.assertRaises(CompilerError) as context:
                    parse(source, "malformed-record.nsp")
                self.assertEqual(context.exception.code, "E2102")


class RecordSemanticTests(unittest.TestCase):
    def test_resolves_nominal_layout_and_typed_fields(self) -> None:
        source = program_with(
            """    Index := $01;
    Player.X := $10;
    Player.Active := true;
    Player.State := Moving;
    Enemies[Index].Y := Player.X;
    Result := Enemies[Index].Y;""",
            RECORD_TYPES,
            "    Player: Entity;\n    Enemies: array[$00..$03] of Entity;\n    Index: byte;\n    Result: byte;",
        )
        resolved = resolve(source)
        record_type = resolved.record_types[0]
        self.assertIsInstance(record_type, RecordType)
        self.assertEqual(record_type.size, 4)
        self.assertEqual([field.offset for field in record_type.fields], [0, 1, 2, 3])
        self.assertIs(record_type.fields[0].type, BuiltInType.BYTE)
        self.assertIs(record_type.fields[2].type, BuiltInType.BOOLEAN)
        self.assertIsInstance(record_type.fields[3].type, EnumType)
        self.assertIs(resolved.variables[0].type, record_type)
        array_type = resolved.variables[1].type
        self.assertIsInstance(array_type, ArrayType)
        assert isinstance(array_type, ArrayType)
        self.assertIs(array_type.element_type, record_type)
        write = resolved.statements[4]
        self.assertIsInstance(write, ResolvedRecordFieldAssignment)
        assert isinstance(write, ResolvedRecordFieldAssignment)
        self.assertEqual(write.field.offset, 1)
        read = resolved.statements[5]
        self.assertIsInstance(read, ResolvedAssignment)
        assert isinstance(read, ResolvedAssignment)
        self.assertIsInstance(read.value, ResolvedRecordField)

    def test_record_types_are_nominal_and_whole_values_are_rejected(self) -> None:
        types = """    Position = record X: byte; Y: byte; end;
    Velocity = record X: byte; Y: byte; end;"""
        source = program_with(
            "    PositionValue.X := $01;\n    VelocityValue.X := $02;\n    PositionValue := VelocityValue;",
            types,
            "    PositionValue: Position;\n    VelocityValue: Velocity;",
        )
        with self.assertRaises(CompilerError) as context:
            resolve(source)
        self.assertEqual(context.exception.code, "E4025")

    def test_field_types_use_existing_strict_assignment_rules(self) -> None:
        cases = (
            ("Player.X := true;", "E4004"),
            ("Player.Active := $01;", "E4004"),
            ("Player.State := $01;", "E4004"),
        )
        for body, code in cases:
            with self.subTest(body=body):
                source = program_with(body, RECORD_TYPES, "    Player: Entity;")
                with self.assertRaises(CompilerError) as context:
                    resolve(source)
                self.assertEqual(context.exception.code, code)

    def test_enum_fields_reject_members_from_a_different_enum(self) -> None:
        types = RECORD_TYPES + "\n    OtherState = (Stopped, Running);"
        source = program_with(
            "    Player.State := Running;",
            types,
            "    Player: Entity;",
        )
        with self.assertRaises(CompilerError) as context:
            resolve(source)
        self.assertEqual(context.exception.code, "E4004")

    def test_unknown_record_type_uses_the_existing_unknown_type_diagnostic(self) -> None:
        source = program_with(
            "",
            RECORD_TYPES,
            "    Missing: UnknownRecord;",
        )
        with self.assertRaises(CompilerError) as context:
            resolve(source)
        self.assertEqual(context.exception.code, "E4001")

    def test_record_diagnostic_fixtures_are_focused_and_stable(self) -> None:
        expected = {
            "duplicate_record_field.nsp": "E4019",
            "unknown_record_field.nsp": "E4020",
            "field_access_on_non_record.nsp": "E4021",
            "unsupported_record_field_type.nsp": "E4022",
            "recursive_record_definition.nsp": "E4023",
            "empty_record_definition.nsp": "E4024",
            "oversized_record_definition.nsp": "E4024",
            "invalid_record_usage.nsp": "E4025",
            "whole_record_comparison.nsp": "E4025",
        }
        for name, code in expected.items():
            with self.subTest(name=name):
                path = DIAGNOSTICS / name
                source = path.read_text(encoding="utf-8")
                with self.assertRaises(CompilerError) as context:
                    resolve(source, str(path))
                self.assertEqual(context.exception.code, code)
                self.assertEqual(str(context.exception).count(code), 1)

    def test_rejects_variable_scaled_offsets_beyond_one_byte(self) -> None:
        source = program_with(
            "    Index := $40;\n    Enemies[Index].X := $10;",
            RECORD_TYPES,
            "    Enemies: array[$00..$40] of Entity;\n    Index: byte;",
        )
        with self.assertRaises(CompilerError) as context:
            resolve(source)
        self.assertEqual(context.exception.code, "E4024")

    def test_record_layout_and_usage_fixtures_target_the_intended_rule(self) -> None:
        expected = {
            "empty_record_definition.nsp": (
                "E4024",
                "Record Empty must declare at least one field.",
            ),
            "oversized_record_definition.nsp": (
                "E4024",
                "Record Large exceeds the supported 256-byte layout.",
            ),
            "whole_record_comparison.nsp": (
                "E4025",
                "Whole-record comparison is not supported for type Position.",
            ),
        }
        for name, (code, message) in expected.items():
            with self.subTest(name=name):
                path = DIAGNOSTICS / name
                source = path.read_text(encoding="utf-8")
                with self.assertRaises(CompilerError) as context:
                    resolve(source, str(path))
                self.assertEqual(context.exception.code, code)
                self.assertIn(message, str(context.exception))


class RecordMemoryAndBackendTests(unittest.TestCase):
    def test_records_and_record_arrays_are_contiguous_regular_ram(self) -> None:
        source = program_with(
            "    Player.X := $10;\n    Enemies[$00].X := $20;",
            RECORD_TYPES,
            "    Player: Entity;\n    Enemies: array[$00..$07] of Entity;",
        )
        resolved = resolve(source)
        layout = build_memory_layout(resolved, source=source, filename="records.nsp")
        player, enemies = layout.user_symbols
        self.assertEqual((player.size, enemies.size), (4, 32))
        self.assertEqual(enemies.address, player.address + player.size)
        self.assertEqual(player.region_name, layout.user_capacity.name)
        self.assertEqual(enemies.region_name, layout.user_capacity.name)
        self.assertEqual(layout.promoted_bytes_used, 0)
        memory_map = generate_memory_map(layout)
        self.assertIn("Entity", memory_map)
        self.assertIn("array[$00..$07] of Entity", memory_map)

    def test_one_byte_record_is_never_automatically_promoted(self) -> None:
        source = program_with(
            """    Value.Only := $01;
    Result := Value.Only;
    Result := Value.Only + Result;
    Result := Value.Only + Result;""",
            "    Wrapper = record Only: byte; end;",
            "    Value: Wrapper;\n    Result: byte;",
        )
        resolved = resolve(source)
        layout = build_memory_layout(resolved, source=source, filename="records.nsp")
        value = next(symbol for symbol in layout.user_symbols if symbol.source_name == "Value")
        self.assertEqual(value.size, 1)
        self.assertEqual(value.region_name, layout.user_capacity.name)
        self.assertNotIn(value, layout.promoted_user_symbols)

    def test_constant_and_variable_field_addressing_are_size_aware(self) -> None:
        path = ROOT / "tests" / "fixtures" / "codegen" / "records.nsp"
        source = path.read_text(encoding="utf-8")
        resolved = resolve(source, str(path))
        assembly = generate(resolved)
        core = assembly.split("; Source: Index := value", 1)[1].split(
            "; Source: nes.set_background_color(value)", 1
        )[0]
        actual = ("; Source: Index := value" + core).rstrip() + "\n"
        expected = (ROOT / "tests" / "golden" / "records.asm").read_text(
            encoding="utf-8"
        )
        self.assertEqual(actual, expected)
        self.assertIn("variable_Player + 1", assembly)
        self.assertIn("variable_Player + 2", assembly)
        self.assertIn("variable_Player + 3", assembly)
        self.assertIn("variable_Entities + 8", assembly)
        self.assertIn("asl a                   ; scale record index", assembly)
        self.assertGreaterEqual(assembly.count("asl a                   ; scale record index"), 4)
        self.assertNotIn("record_runtime", assembly)
        self.assertNotIn("record_descriptor", assembly)

    def test_non_power_of_two_record_size_uses_local_repeated_addition(self) -> None:
        types = """    Triple = record
        A: byte;
        B: byte;
        C: byte;
    end;"""
        source = program_with(
            "    Index := $01;\n    Values[Index].C := $10;",
            types,
            "    Values: array[$00..$03] of Triple;\n    Index: byte;",
        )
        assembly = generate(resolve(source))
        self.assertIn("adc #$03", assembly)
        self.assertIn("@record_index_scale_", assembly)

    def test_indexed_write_preserves_index_before_evaluating_rhs(self) -> None:
        source = program_with(
            """    Index := $01;
    Player.X := $03;
    Enemies[Index].Y := Player.X + $02;""",
            RECORD_TYPES,
            "    Player: Entity;\n    Enemies: array[$00..$03] of Entity;\n    Index: byte;",
        )
        assembly = generate(resolve(source))
        section = assembly.split("; Source: Enemies[index].Y := value", 1)[1].split(
            "; Source: nes.set_background_color(value)", 1
        )[0]
        self.assertLess(section.index("lda variable_Index"), section.index("pha"))
        self.assertLess(section.index("pha"), section.index("lda variable_Player"))
        self.assertLess(section.index("lda variable_Player"), section.index("pla"))
        self.assertLess(section.index("pla"), section.index("sta variable_Enemies,x"))

    def test_record_array_ram_exhaustion_uses_existing_layout_diagnostic(self) -> None:
        record_fields = "\n".join(f"        F{index}: byte;" for index in range(16))
        source = program_with(
            "    First[$00].F0 := $01;",
            f"    Large = record\n{record_fields}\n    end;",
            "    First: array[$00..$7F] of Large;",
        )
        resolved = resolve(source)
        with self.assertRaises(CompilerError) as context:
            build_memory_layout(resolved, source=source, filename="records.nsp")
        self.assertEqual(context.exception.code, "E5003")

    @unittest.skipUnless(
        shutil.which("ca65") is not None and shutil.which("ld65") is not None,
        "records benchmark measurement requires ca65 and ld65",
    )
    def test_records_benchmark_reports_focused_resource_accounting(self) -> None:
        from tools.measure_benchmarks import BENCHMARKS, measure_benchmark

        spec = next(item for item in BENCHMARKS if item.name == "records")
        metrics = measure_benchmark(spec)
        self.assertEqual(metrics.prg_code_bytes, 389)
        self.assertEqual(metrics.prg_total_used_bytes, 395)
        self.assertEqual(metrics.pattern_stats.total_instructions, 196)
        self.assertEqual(metrics.estimated_static_base_cycles, 605)
        self.assertEqual(metrics.max_expression_tree_depth, 2)
        self.assertEqual(metrics.max_live_temporaries, 0)
        self.assertEqual(
            asdict(metrics.memory),
            {
                "zp_runtime_symbol_bytes": 9,
                "zp_expression_temporary_reserved_bytes": 0,
                "zp_compiler_cache_bytes": 0,
                "zp_promoted_user_bytes": 2,
                "zp_benchmark_allocated_or_reserved_bytes": 11,
                "zp_policy_reserved_unavailable_bytes": 103,
                "zp_allocator_visible_free_bytes": 142,
                "regular_runtime_bytes": 4,
                "regular_compiler_bytes": 0,
                "regular_user_bytes": 21,
                "regular_runtime_user_allocated_bytes": 25,
                "oam_shadow_allocated_bytes": 0,
                "non_zp_allocated_bytes": 25,
                "hardware_stack_reserved_bytes": 256,
                "regular_allocator_visible_free_bytes": 1511,
                "total_allocator_visible_free_bytes": 1653,
                "compiler_runtime_user_allocated_or_reserved_bytes": 36,
                "total_committed_or_reserved_address_space_bytes": 395,
            },
        )
        self.assertEqual(metrics.runtime_features, ())


if __name__ == "__main__":
    unittest.main()
