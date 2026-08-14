from pathlib import Path
import unittest

from nes_pascal.ast import (
    BuiltInType,
    FunctionCall,
    ResolvedFunctionCall,
    ResolvedFunctionResultAssignment,
)
from nes_pascal.backend_ca65 import generate
from nes_pascal.diagnostics import CompilerError, DiagnosticCode
from nes_pascal.memory_layout import build_memory_layout, generate_linker_config
from nes_pascal.parser import parse
from nes_pascal.semantic import analyze


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "codegen" / "functions.nsp"
GOLDEN = ROOT / "tests" / "golden" / "functions_abi.asm"
PRESSURE_FIXTURE = (
    ROOT / "tests" / "fixtures" / "codegen" / "functions_temporary_pressure.nsp"
)
PRESSURE_GOLDEN = ROOT / "tests" / "golden" / "functions_temporary_pressure.asm"
DIAGNOSTICS = ROOT / "tests" / "fixtures" / "diagnostics"


def resolve(source: str):
    return analyze(parse(source, "functions_test.nsp"), source, "functions_test.nsp")


def program_with(declarations: str, statements: str) -> str:
    return f"""program FunctionTest;
var
    Value: byte;
    Flag: boolean;
{declarations}
begin
    Value := $00;
    Flag := false;
    nes.set_background_color($0F);
{statements}
    nes.run;
end.
"""


class FunctionTests(unittest.TestCase):
    def test_parser_represents_typed_function_and_explicit_call(self) -> None:
        source = program_with(
            """function One: byte;
begin
    One := $01;
end;
""",
            "    Value := One();",
        )
        parsed = parse(source)
        self.assertEqual(len(parsed.functions), 1)
        self.assertEqual(parsed.functions[0].return_type, BuiltInType.BYTE)
        call = parsed.statements[3].value
        self.assertIsInstance(call, FunctionCall)
        assert isinstance(call, FunctionCall)
        self.assertEqual(call.arguments, ())

    def test_semantic_analysis_resolves_result_and_nested_calls(self) -> None:
        source = program_with(
            """function Add(Left: byte; Right: byte): byte;
begin
    Add := Left + Right;
end;
""",
            "    Value := Add($01, Add($02, $03));",
        )
        resolved = resolve(source)
        function = resolved.functions[0]
        self.assertIsInstance(function.body[0], ResolvedFunctionResultAssignment)
        call = resolved.statements[3].value
        self.assertIsInstance(call, ResolvedFunctionCall)
        assert isinstance(call, ResolvedFunctionCall)
        self.assertEqual(call.return_type, BuiltInType.BYTE)
        self.assertIsInstance(call.arguments[1].value, ResolvedFunctionCall)

    def test_boolean_function_is_valid_in_short_circuit_expression(self) -> None:
        source = program_with(
            """function Enabled(Input: boolean): boolean;
begin
    Enabled := Input;
end;
""",
            "    Flag := false and Enabled(true);",
        )
        assembly = generate(resolve(source))
        self.assertIn("; boolean and: evaluate left operand", assembly)
        self.assertIn("jsr function_Enabled", assembly)

    def test_function_and_builtin_calls_share_expression_lowering(self) -> None:
        source = program_with(
            """function Echo(Input: boolean): boolean;
begin
    Echo := Input;
end;
""",
            "    Flag := Echo(nes.controller_down($01, nes.button_a));",
        )
        assembly = generate(resolve(source))
        self.assertIn("; nes.controller_down($01, nes.button_a)", assembly)
        self.assertIn("jsr function_Echo", assembly)

        statement_source = program_with(
            """function Coordinate(Input: byte): byte;
begin
    Coordinate := Input;
end;
""",
            (
                "    nes.set_scroll(Coordinate($11), "
                "Coordinate($22));"
            ),
        )
        statement_assembly = generate(resolve(statement_source))
        self.assertEqual(
            statement_assembly.count("jsr function_Coordinate"), 2
        )
        self.assertIn("sta runtime_scroll_pending_x", statement_assembly)
        self.assertIn("sta runtime_scroll_pending_y", statement_assembly)

    def test_forward_calls_resolve_in_callee_first_order(self) -> None:
        source = program_with(
            """function Outer(Input: byte): byte;
begin
    Outer := Inner(Input);
end;

function Inner(Input: byte): byte;
begin
    Inner := Input;
end;
""",
            "    Value := Outer($2A);",
        )
        resolved = resolve(source)
        self.assertEqual([item.name for item in resolved.functions], ["Outer", "Inner"])

    def test_result_must_be_assigned_on_every_path(self) -> None:
        source = program_with(
            """function Maybe(Input: boolean): byte;
begin
    if Input then
        Maybe := $01;
end;
""",
            "",
        )
        self.assert_diagnostic(source, DiagnosticCode.UNDEFINED_FUNCTION_RESULT)

    def test_both_conditional_branches_define_the_result(self) -> None:
        source = program_with(
            """function Choose(Input: boolean): byte;
begin
    if Input then
        Choose := $01
    else
        Choose := $02;
end;
""",
            "    Value := Choose(true);",
        )
        self.assertEqual(resolve(source).functions[0].return_type, BuiltInType.BYTE)

    def test_short_circuit_rhs_assignments_are_not_definite(self) -> None:
        source = """program ShortCircuitAssignment;
var
    Value: byte;
    Flag: boolean;

function Initialize: boolean;
begin
    Value := $2A;
    Initialize := true;
end;

begin
    Flag := false and Initialize();
    Value := Value + $01;
    nes.set_background_color($0F);
    nes.run;
end.
"""
        self.assert_diagnostic(
            source, DiagnosticCode.VARIABLE_READ_BEFORE_ASSIGNMENT
        )

    def test_short_circuit_left_assignments_remain_definite(self) -> None:
        source = """program ShortCircuitAssignment;
var
    Value: byte;
    Flag: boolean;

function Initialize: boolean;
begin
    Value := $2A;
    Initialize := true;
end;

begin
    Flag := Initialize() and true;
    Value := Value + $01;
    nes.set_background_color($0F);
    nes.run;
end.
"""
        resolve(source)

    def test_parser_rejects_malformed_function_declarations(self) -> None:
        malformed = (
            "program Bad; function Value; begin end; begin nes.run; end.",
            "program Bad; function Value: ; begin end; begin nes.run; end.",
            (
                "program Bad; function Value(): byte; begin Value := $00; "
                "end; begin nes.run; end."
            ),
        )
        for source in malformed:
            with self.subTest(source=source):
                with self.assertRaises(CompilerError) as raised:
                    parse(source, "malformed_function.nsp")
                self.assertEqual(
                    raised.exception.code, DiagnosticCode.INVALID_SYNTAX
                )

    def test_function_diagnostics_cover_call_and_type_errors(self) -> None:
        cases = (
            (
                program_with("", "    Value := Missing();"),
                DiagnosticCode.UNKNOWN_FUNCTION,
            ),
            (
                program_with(
                    """function One(Input: byte): byte;
begin
    One := Input;
end;
""",
                    "    Value := One();",
                ),
                DiagnosticCode.FUNCTION_ARGUMENT_COUNT,
            ),
            (
                program_with(
                    """function One(Input: byte): byte;
begin
    One := Input;
end;
""",
                    "    One($01);",
                ),
                DiagnosticCode.FUNCTION_USED_AS_STATEMENT,
            ),
            (
                program_with(
                    """procedure Work;
begin
    Value := $01;
end;
""",
                    "    Value := Work();",
                ),
                DiagnosticCode.PROCEDURE_USED_AS_EXPRESSION,
            ),
            (
                program_with(
                    """function Wrong: boolean;
begin
    Wrong := $01;
end;
""",
                    "",
                ),
                DiagnosticCode.INCOMPATIBLE_TYPES,
            ),
            (
                program_with(
                    """function SpriteResult: sprite;
begin
    SpriteResult := $00;
end;
""",
                    "",
                ),
                DiagnosticCode.UNSUPPORTED_FUNCTION_RETURN_TYPE,
            ),
            (
                program_with(
                    """function Enabled(Input: boolean): boolean;
begin
    Enabled := Input;
end;
""",
                    "    Flag := Enabled($01);",
                ),
                DiagnosticCode.INCOMPATIBLE_TYPES,
            ),
        )
        for source, code in cases:
            with self.subTest(code=code):
                self.assert_diagnostic(source, code)

    def test_direct_indirect_and_mixed_recursion_are_rejected(self) -> None:
        direct = program_with(
            """function Loop: byte;
begin
    Loop := Loop();
end;
""",
            "",
        )
        indirect = program_with(
            """function First: byte;
begin
    First := Second();
end;

function Second: byte;
begin
    Second := First();
end;
""",
            "",
        )
        mixed = program_with(
            """procedure Step;
begin
    Value := Compute();
end;

function Compute: byte;
begin
    Step;
    Compute := $01;
end;
""",
            "",
        )
        for source in (direct, indirect, mixed):
            with self.subTest(source=source):
                self.assert_diagnostic(
                    source, DiagnosticCode.RECURSIVE_PROCEDURE_CALL
                )

    def test_function_diagnostic_fixtures_emit_their_canonical_codes(self) -> None:
        cases = {
            "unknown_function.nsp": DiagnosticCode.UNKNOWN_FUNCTION,
            "function_argument_count.nsp": DiagnosticCode.FUNCTION_ARGUMENT_COUNT,
            "function_used_as_statement.nsp": DiagnosticCode.FUNCTION_USED_AS_STATEMENT,
            "procedure_used_as_expression.nsp": DiagnosticCode.PROCEDURE_USED_AS_EXPRESSION,
            "undefined_function_result.nsp": DiagnosticCode.UNDEFINED_FUNCTION_RESULT,
            "unsupported_function_return_type.nsp": (
                DiagnosticCode.UNSUPPORTED_FUNCTION_RETURN_TYPE
            ),
            "wrong_byte_function_result.nsp": DiagnosticCode.INCOMPATIBLE_TYPES,
            "wrong_boolean_function_result.nsp": DiagnosticCode.INCOMPATIBLE_TYPES,
            "recursive_function_call.nsp": DiagnosticCode.RECURSIVE_PROCEDURE_CALL,
            "recursive_function_call_indirect.nsp": (
                DiagnosticCode.RECURSIVE_PROCEDURE_CALL
            ),
            "recursive_callable_mixed.nsp": DiagnosticCode.RECURSIVE_PROCEDURE_CALL,
        }
        for filename, code in cases.items():
            path = DIAGNOSTICS / filename
            source = path.read_text(encoding="utf-8")
            with self.subTest(filename=filename):
                with self.assertRaises(CompilerError) as raised:
                    analyze(parse(source, str(path)), source, str(path))
                self.assertEqual(raised.exception.code, code)

    def test_return_storage_is_regular_ram_and_absent_without_functions(self) -> None:
        with_functions = resolve(FIXTURE.read_text(encoding="utf-8"))
        layout = build_memory_layout(with_functions)
        self.assertEqual(layout.function_result_storage.size, 3)
        self.assertEqual(
            [symbol.address for symbol in layout.function_result_symbols],
            [0x0204, 0x0205, 0x0206],
        )
        self.assertIn("FUNCTION_RESULTS", generate_linker_config(layout))

        without_functions = resolve(program_with("", ""))
        no_function_layout = build_memory_layout(without_functions)
        self.assertEqual(no_function_layout.function_result_storage.size, 0)
        self.assertEqual(no_function_layout.function_result_symbols, ())
        self.assertNotIn("FUNCTION_RESULTS", generate_linker_config(no_function_layout))

    def test_nested_calls_preserve_caller_temporaries_and_match_golden_abi(self) -> None:
        source = FIXTURE.read_text(encoding="utf-8")
        resolved = resolve(source)
        layout = build_memory_layout(resolved)
        assembly = generate(resolved, layout)
        selected = [
            line
            for line in assembly.splitlines()
            if (
                "FUNCTION_RESULTS" in line
                or "function_result_" in line
                or line.startswith("; Function:")
                or (
                    line.startswith("function_")
                    and not line.startswith("function_result_")
                )
                or "jsr function_" in line
                or "preserve across later call" in line
                or (
                    line.startswith("    ")
                    and "expression_temporary_" in line
                )
                or "comparison =:" in line
                or "boolean and:" in line
                or "short-circuit" in line
            )
        ]
        self.assertEqual("\n".join(selected) + "\n", GOLDEN.read_text(encoding="utf-8"))
        self.assertEqual(layout.expression_temporary_bytes, 2)
        bases = dict(layout.temporary_requirements.callable_bases)
        self.assertEqual(bases["function_Identity"], 2)

    def test_three_level_call_chain_uses_distinct_temporary_prefixes(self) -> None:
        source = PRESSURE_FIXTURE.read_text(encoding="utf-8")
        resolved = resolve(source)
        layout = build_memory_layout(resolved)
        assembly = generate(resolved, layout)
        selected = [
            line
            for line in assembly.splitlines()
            if (
                (
                    line.startswith("    ")
                    and "expression_temporary_" in line
                )
                or line.startswith("; Function:")
                or (
                    line.startswith("function_")
                    and not line.startswith("function_result_")
                )
                or "jsr function_" in line
            )
        ]
        self.assertEqual(
            "\n".join(selected) + "\n",
            PRESSURE_GOLDEN.read_text(encoding="utf-8"),
        )
        self.assertEqual(layout.expression_temporary_bytes, 3)
        bases = dict(layout.temporary_requirements.callable_bases)
        self.assertEqual(bases["function_Middle"], 1)
        self.assertEqual(bases["function_Leaf"], 2)
        self.assertEqual(layout.temporary_requirements.max_call_depth, 2)

    def test_callable_names_share_the_existing_global_namespace(self) -> None:
        procedure_function_collision = program_with(
            """procedure Shared;
begin
end;

function Shared: byte;
begin
    Shared := $00;
end;
""",
            "",
        )
        variable_function_collision = program_with(
            """function Value: byte;
begin
    Value := $00;
end;
""",
            "",
        )
        for source in (procedure_function_collision, variable_function_collision):
            with self.subTest(source=source):
                self.assert_diagnostic(
                    source, DiagnosticCode.DUPLICATE_SYMBOL
                )

    def assert_diagnostic(self, source: str, code: DiagnosticCode) -> None:
        with self.assertRaises(CompilerError) as raised:
            resolve(source)
        self.assertEqual(raised.exception.code, code)


if __name__ == "__main__":
    unittest.main()
