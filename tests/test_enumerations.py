from pathlib import Path
import shutil
import unittest

from nes_pascal.ast import (
    ComparisonExpression,
    EnumType,
    ImmediateValue,
    ResolvedAssignment,
    ResolvedComparisonExpression,
    ResolvedIfStatement,
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
    return f"""program Enumerations;
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


def resolve(source: str, filename: str = "enumerations.nsp"):
    return analyze(parse(source, filename), source, filename)


class EnumerationParserTests(unittest.TestCase):
    def test_lexer_recognizes_type_keyword(self) -> None:
        tokens = tokenize("type GameState = (Title, Playing);")
        self.assertEqual(tokens[0].kind, TokenKind.TYPE)

    def test_parses_multiple_enum_types_variables_assignments_and_comparisons(self) -> None:
        source = program_with(
            "    State := Title;\n    if State = Playing then\n        State := Paused;",
            "    GameState = (Title, Playing, Paused);\n    Direction = (Left, Right);",
            "    State: GameState;\n    Facing: Direction;",
        )
        program = parse(source, "enum-parser.nsp")

        self.assertEqual(len(program.enum_types), 2)
        self.assertEqual(program.enum_types[0].type.name, "GameState")
        self.assertEqual(program.enum_types[0].type.members, ("Title", "Playing", "Paused"))
        self.assertIs(program.variables[0].type, program.enum_types[0].type)
        self.assertIsInstance(program.statements[1].condition, ComparisonExpression)

    def test_rejects_empty_and_malformed_member_lists(self) -> None:
        declarations = (
            "    GameState = ();",
            "    GameState = (Title,);",
            "    GameState = Title, Playing);",
        )
        for declaration in declarations:
            with self.subTest(declaration=declaration):
                with self.assertRaises(CompilerError) as context:
                    parse(
                        program_with(
                            "    State := Title;",
                            declaration,
                            "    State: GameState;",
                        ),
                        "malformed-enum.nsp",
                    )
                self.assertEqual(context.exception.code, "E2102")


class EnumerationSemanticTests(unittest.TestCase):
    def test_members_are_nominal_typed_constants_with_deterministic_values(self) -> None:
        source = program_with(
            """    State := Title;
    Previous := State;
    if State = Previous then
        State := GameOver;
    Different := State <> Paused;""",
            "    GameState = (Title, Playing, Paused, GameOver);",
            "    State: GameState;\n    Previous: GameState;\n    Different: boolean;",
        )
        resolved = resolve(source)
        game_state = resolved.variables[0].type
        self.assertIsInstance(game_state, EnumType)
        assert isinstance(game_state, EnumType)
        self.assertEqual(game_state.members, ("Title", "Playing", "Paused", "GameOver"))

        assignment = resolved.statements[0]
        self.assertIsInstance(assignment, ResolvedAssignment)
        assert isinstance(assignment, ResolvedAssignment)
        self.assertEqual(assignment.value, ImmediateValue(0, game_state))
        condition = resolved.statements[2]
        self.assertIsInstance(condition, ResolvedIfStatement)
        assert isinstance(condition, ResolvedIfStatement)
        self.assertIsInstance(condition.condition, ResolvedComparisonExpression)
        comparison = resolved.statements[3]
        self.assertIsInstance(comparison, ResolvedAssignment)
        assert isinstance(comparison, ResolvedAssignment)
        self.assertIsInstance(comparison.value, ResolvedComparisonExpression)

    def test_strict_nominal_assignment_and_comparison_rules(self) -> None:
        cases = (
            ("State := $01;", "E4004"),
            ("State := true;", "E4004"),
            ("State := Left;", "E4004"),
            ("Enabled := State = Left;", "E4004"),
            ("Enabled := State < Playing;", "E4017"),
        )
        for body, code in cases:
            with self.subTest(body=body):
                source = program_with(
                    f"    State := Title;\n    {body}",
                    "    GameState = (Title, Playing);\n    Direction = (Left, Right);",
                    "    State: GameState;\n    Enabled: boolean;",
                )
                with self.assertRaises(CompilerError) as context:
                    resolve(source)
                self.assertEqual(context.exception.code, code)

    def test_rejects_unknown_enum_type_and_type_name_used_as_value(self) -> None:
        unknown_type = """program UnknownEnumType;
var
    State: GameState;
begin
    nes.set_background_color($0F);
    nes.run;
end.
"""
        with self.assertRaises(CompilerError) as context:
            parse(unknown_type, "unknown-enum-type.nsp")
        self.assertEqual(context.exception.code, "E4001")

        source = program_with(
            "    State := GameState;",
            "    GameState = (Title, Playing);",
            "    State: GameState;",
        )
        with self.assertRaises(CompilerError) as context:
            resolve(source)
        self.assertEqual(context.exception.code, "E4018")

    def test_enum_diagnostic_fixtures_are_focused_and_stable(self) -> None:
        expected = {
            "duplicate_enum_member.nsp": "E4015",
            "invalid_enum_ordering.nsp": "E4017",
            "unknown_enum_member.nsp": "E4018",
        }
        for name, code in expected.items():
            with self.subTest(name=name):
                path = DIAGNOSTICS / name
                source = path.read_text(encoding="utf-8")
                with self.assertRaises(CompilerError) as context:
                    resolve(source, str(path))
                self.assertEqual(context.exception.code, code)
                self.assertEqual(str(context.exception).count(code), 1)

    def test_rejects_more_than_256_members_without_value_wraparound(self) -> None:
        members = ", ".join(f"Value{index}" for index in range(257))
        source = program_with(
            "    State := Value0;",
            f"    GameState = ({members});",
            "    State: GameState;",
        )
        with self.assertRaises(CompilerError) as context:
            resolve(source)
        self.assertEqual(context.exception.code, "E4016")


class EnumerationMemoryAndBackendTests(unittest.TestCase):
    def test_enum_variables_are_one_byte_scalar_symbols_without_member_storage(self) -> None:
        source = program_with(
            "    State := Title;\n    Previous := State;",
            "    GameState = (Title, Playing, Paused);",
            "    State: GameState;\n    Previous: GameState;",
        )
        resolved = resolve(source)
        layout = build_memory_layout(resolved, source=source, filename="enums.nsp")
        self.assertEqual([symbol.size for symbol in layout.user_symbols], [1, 1])
        self.assertEqual(len(layout.user_symbols), 2)
        memory_map = generate_memory_map(layout)
        self.assertIn("GameState", memory_map)
        self.assertNotIn("enum_member_", memory_map)

    def test_enum_codegen_core_matches_focused_golden(self) -> None:
        path = ROOT / "tests" / "fixtures" / "codegen" / "enumerations.nsp"
        source = path.read_text(encoding="utf-8")
        assembly = generate(resolve(source, str(path)))
        core = assembly.split("; Source: State := value", 1)[1].split(
            "; Source: nes.set_background_color(value)", 1
        )[0]
        actual = ("; Source: State := value" + core).rstrip() + "\n"
        expected = (ROOT / "tests" / "golden" / "enumerations.asm").read_text(
            encoding="utf-8"
        )
        self.assertEqual(actual, expected)
        self.assertIn("variable_State: .res 1", assembly)
        self.assertNotIn("enum_", assembly)

    @unittest.skipUnless(
        shutil.which("ca65") is not None and shutil.which("ld65") is not None,
        "enumeration benchmark measurement requires ca65 and ld65",
    )
    def test_enumeration_benchmark_reports_focused_resource_accounting(self) -> None:
        from tools.measure_benchmarks import BENCHMARKS, measure_benchmark

        spec = next(item for item in BENCHMARKS if item.name == "enumerations")
        metrics = measure_benchmark(spec)
        self.assertEqual(metrics.prg_code_bytes, 275)
        self.assertEqual(metrics.prg_total_used_bytes, 281)
        self.assertEqual(metrics.pattern_stats.total_instructions, 125)
        self.assertEqual(metrics.estimated_static_base_cycles, 408)
        self.assertEqual(metrics.max_expression_tree_depth, 1)
        self.assertEqual(metrics.max_live_temporaries, 0)
        self.assertEqual(metrics.memory.zp_temporary_required_bytes, 0)
        self.assertEqual(metrics.memory.regular_user_bytes, 2)
        self.assertEqual(metrics.memory.zp_promoted_user_bytes, 1)
        self.assertEqual(metrics.runtime_features, ())


if __name__ == "__main__":
    unittest.main()
