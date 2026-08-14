from pathlib import Path
import unittest

from nes_pascal.diagnostics import CompilerError
from nes_pascal.parser import parse
from nes_pascal.semantic import analyze


FIXTURES = Path(__file__).parent / "fixtures" / "diagnostics"


def diagnostic_for(name: str) -> CompilerError:
    path = FIXTURES / name
    source = path.read_text(encoding="utf-8")
    with unittest.TestCase().assertRaises(CompilerError) as context:
        analyze(parse(source, str(path)), source, str(path))
    return context.exception


class DiagnosticPrecedenceTests(unittest.TestCase):
    def assert_primary_diagnostic(
        self,
        fixture: str,
        code: str,
        line: int,
        column: int,
        message: str,
        caret: str,
    ) -> CompilerError:
        error = diagnostic_for(fixture)
        rendered = str(error)
        self.assertEqual(error.code, code)
        self.assertEqual((error.location.line, error.location.column), (line, column))
        self.assertIn(message, rendered)
        self.assertIn(caret, rendered)
        self.assertNotIn("E3003", rendered)
        self.assertNotIn(
            "The program must set the background color exactly once.",
            rendered,
        )
        return error

    def test_boolean_assigned_to_byte_reports_source_type(self) -> None:
        self.assert_primary_diagnostic(
            "boolean_to_byte.nsp",
            "E4004",
            9,
            16,
            "Cannot assign a value of type boolean to variable Counter of type byte.",
            "               ^^^^^^",
        )

    def test_byte_assigned_to_boolean_reports_source_type(self) -> None:
        self.assert_primary_diagnostic(
            "byte_to_boolean.nsp",
            "E4004",
            9,
            15,
            "Cannot assign a value of type byte to variable Active of type boolean.",
            "              ^^^^^^^",
        )

    def test_invalid_nes_color_assignment_reports_literal_range(self) -> None:
        error = self.assert_primary_diagnostic(
            "invalid_nes_color_assignment.nsp",
            "E4002",
            7,
            24,
            "Value $80 is not valid for type nes_color.",
            "                       ^^^",
        )
        self.assertIn("Allowed range: $00..$3F.", str(error))

    def test_hexadecimal_assigned_to_boolean_reports_literal_kind(self) -> None:
        error = self.assert_primary_diagnostic(
            "hexadecimal_to_boolean.nsp",
            "E4004",
            7,
            15,
            "Cannot assign a hexadecimal literal to boolean variable Active.",
            "              ^^^",
        )
        self.assertIn("Use true or false.", str(error))

    def test_uninitialized_variable_diagnostic_is_preserved(self) -> None:
        error = self.assert_primary_diagnostic(
            "uninitialized_variable.nsp",
            "E3008",
            7,
            30,
            "Variable BackgroundColor is read before it is assigned.",
            "                             ^^^^^^^^^^^^^^^",
        )
        self.assertIn(
            "Assign a value to the variable before reading it.",
            str(error),
        )

    def test_runtime_command_inside_conditional_is_preserved(self) -> None:
        self.assert_primary_diagnostic(
            "conditional_runtime_command.nsp",
            "E3009",
            9,
            9,
            "nes.run cannot appear inside a conditional branch.",
            "        ^^^^^^^",
        )

    def test_loop_control_outside_loop_is_preserved(self) -> None:
        self.assert_primary_diagnostic(
            "loop_control_outside_loop.nsp",
            "E3010",
            4,
            5,
            "break can appear only inside a loop.",
            "    ^",
        )

    def test_runtime_command_inside_loop_is_preserved(self) -> None:
        self.assert_primary_diagnostic(
            "loop_runtime_command.nsp",
            "E3011",
            9,
            9,
            "nes.run cannot appear inside a loop body.",
            "        ^^^^^^^",
        )

    def test_for_control_variable_modification_is_preserved(self) -> None:
        self.assert_primary_diagnostic(
            "for_control_variable_modification.nsp",
            "E3012",
            8,
            9,
            "For control variable Index cannot be modified inside its loop body.",
            "        ^^^^^",
        )

    def test_unknown_procedure_is_preserved(self) -> None:
        self.assert_primary_diagnostic(
            "unknown_procedure.nsp",
            "E3013",
            4,
            5,
            "Unknown procedure: Missing.",
            "    ^^^^^^^",
        )

    def test_recursive_procedure_call_is_preserved(self) -> None:
        self.assert_primary_diagnostic(
            "recursive_procedure_call.nsp",
            "E3014",
            10,
            5,
            "Recursive procedure call involving First is not supported.",
            "    ^^^^^",
        )

    def test_runtime_command_inside_procedure_is_preserved(self) -> None:
        self.assert_primary_diagnostic(
            "procedure_runtime_command.nsp",
            "E3015",
            5,
            5,
            "nes.run cannot appear inside a procedure.",
            "    ^^^^^^^",
        )

    def test_procedure_argument_count_is_preserved(self) -> None:
        self.assert_primary_diagnostic(
            "procedure_argument_count.nsp",
            "E3016",
            6,
            5,
            "Procedure Initialize expects 1 argument(s), but 0 were provided.",
            "    ^^^^^^^^^^",
        )

    def test_unsupported_parameter_type_is_preserved(self) -> None:
        self.assert_primary_diagnostic(
            "unsupported_parameter_type.nsp",
            "E4005",
            2,
            27,
            "Type nes_color is not supported for procedure parameters.",
            "                          ^^^^^^^^^",
        )

    def test_procedure_argument_type_is_preserved(self) -> None:
        self.assert_primary_diagnostic(
            "procedure_argument_type.nsp",
            "E4004",
            6,
            16,
            "A hexadecimal literal is not valid for type boolean.",
            "               ^^^",
        )

    def test_assignment_error_precedes_missing_background_color(self) -> None:
        source = """program InvalidPrecedence;
var
    Counter: byte;
    Active: boolean;
begin
    Active := true;
    Counter := Active;
    nes.run;
end.
"""
        with self.assertRaises(CompilerError) as context:
            analyze(parse(source, "precedence.nsp"), source, "precedence.nsp")
        rendered = str(context.exception)
        self.assertEqual(context.exception.code, "E4004")
        self.assertIn("Cannot assign a value of type boolean", rendered)
        self.assertNotIn("E3003", rendered)

    def test_background_color_requirement_remains_after_valid_semantics(self) -> None:
        source = """program MissingColor;
var
    Counter: byte;
begin
    Counter := $01;
    nes.run;
end.
"""
        with self.assertRaises(CompilerError) as context:
            analyze(parse(source, "missing-color.nsp"), source, "missing-color.nsp")
        self.assertEqual(context.exception.code, "E3003")

    def test_run_requirement_remains_after_valid_semantics(self) -> None:
        source = """program MissingRun;
begin
    nes.set_background_color($21);
end.
"""
        with self.assertRaises(CompilerError) as context:
            analyze(parse(source, "missing-run.nsp"), source, "missing-run.nsp")
        self.assertEqual(context.exception.code, "E3001")

    def test_duplicate_run_reports_the_later_statement(self) -> None:
        source = """program DuplicateRun;
begin
    nes.set_background_color($21);
    nes.run;
    nes.run;
end.
"""
        with self.assertRaises(CompilerError) as context:
            analyze(parse(source, "duplicate-run.nsp"), source, "duplicate-run.nsp")
        rendered = str(context.exception)
        self.assertEqual(context.exception.code, "E3002")
        self.assertEqual(
            (context.exception.location.line, context.exception.location.column),
            (5, 5),
        )
        self.assertIn("nes.run may appear only once.", rendered)
        self.assertIn("Remove the later nes.run; call.", rendered)
        self.assertNotIn("E3001", rendered)
        self.assertNotIn("E3003", rendered)
        self.assertNotIn(
            "The program must set the background color exactly once.",
            rendered,
        )


if __name__ == "__main__":
    unittest.main()
