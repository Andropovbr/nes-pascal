import unittest

from nes_pascal.ast import (
    BuiltInType,
    ImmediateValue,
    ResolvedAssignment,
    ResolvedSetBackgroundColor,
    Run,
    VariableValue,
)
from nes_pascal.diagnostics import CompilerError
from nes_pascal.parser import parse
from nes_pascal.semantic import analyze


def analyze_source(source: str, filename: str = "semantic.nsp"):
    return analyze(parse(source, filename), source, filename)


class SemanticTests(unittest.TestCase):
    def test_resolves_valid_nes_color_constant(self) -> None:
        source = """program Minimal;
const
    BackgroundColor: nes_color = $21;
begin
    nes.set_background_color(BackgroundColor);
    nes.run;
end.
"""
        resolved = analyze_source(source)
        self.assertEqual(
            resolved.statements,
            (
                ResolvedSetBackgroundColor(
                    ImmediateValue(0x21, BuiltInType.NES_COLOR)
                ),
                Run(),
            ),
        )

    def test_literal_and_constant_resolve_to_the_same_program(self) -> None:
        literal_source = """program Minimal;
begin
    nes.set_background_color($21);
    nes.run;
end.
"""
        constant_source = """program Minimal;
const
    BackgroundColor: nes_color = $21;
begin
    nes.set_background_color(BackgroundColor);
    nes.run;
end.
"""
        self.assertEqual(
            analyze_source(literal_source),
            analyze_source(constant_source),
        )

    def test_rejects_invalid_nes_color_constant_with_precise_diagnostic(self) -> None:
        source = """program Minimal;
const
    BackgroundColor: nes_color = $80;
begin
    nes.set_background_color(BackgroundColor);
    nes.run;
end.
"""
        with self.assertRaises(CompilerError) as context:
            analyze_source(source, "invalid-constant.nsp")
        error = context.exception
        self.assertEqual(error.code, "E4002")
        self.assertEqual(error.location.filename, "invalid-constant.nsp")
        self.assertEqual((error.location.line, error.location.column), (3, 34))
        self.assertIn(
            "Value $80 is not valid for type nes_color.",
            str(error),
        )
        self.assertIn("Allowed range: $00..$3F.", str(error))

    def test_rejects_unknown_constant(self) -> None:
        source = """program Minimal;
begin
    nes.set_background_color(MissingColor);
    nes.run;
end.
"""
        with self.assertRaises(CompilerError) as context:
            analyze_source(source)
        self.assertEqual(context.exception.code, "E3005")
        self.assertIn("Unknown identifier: MissingColor.", str(context.exception))

    def test_rejects_duplicate_constant_names_case_insensitively(self) -> None:
        source = """program Minimal;
const
    BackgroundColor: nes_color = $21;
    BACKGROUNDCOLOR: nes_color = $0F;
begin
    nes.set_background_color(BackgroundColor);
    nes.run;
end.
"""
        with self.assertRaises(CompilerError) as context:
            analyze_source(source)
        self.assertEqual(context.exception.code, "E3004")

    def test_resolves_typed_assignments_and_variable_read(self) -> None:
        source = """program Variables;
var
    Color: nes_color;
    Counter: byte;
    Enabled: boolean;
begin
    Color := $21;
    Counter := $FF;
    Enabled := true;
    nes.set_background_color(Color);
    nes.run;
end.
"""
        resolved = analyze_source(source)
        self.assertEqual(
            [variable.type for variable in resolved.variables],
            [
                BuiltInType.NES_COLOR,
                BuiltInType.BYTE,
                BuiltInType.BOOLEAN,
            ],
        )
        self.assertIsInstance(resolved.statements[0], ResolvedAssignment)
        color_command = resolved.statements[3]
        self.assertIsInstance(color_command, ResolvedSetBackgroundColor)
        assert isinstance(color_command, ResolvedSetBackgroundColor)
        self.assertIsInstance(color_command.argument, VariableValue)

    def test_resolves_byte_and_boolean_constants_in_assignments(self) -> None:
        source = """program Variables;
const
    Maximum: byte = $FF;
    InitiallyEnabled: boolean = true;
var
    Counter: byte;
    Enabled: boolean;
begin
    Counter := Maximum;
    Enabled := InitiallyEnabled;
    nes.set_background_color($21);
    nes.run;
end.
"""
        resolved = analyze_source(source)
        counter_assignment = resolved.statements[0]
        enabled_assignment = resolved.statements[1]
        self.assertIsInstance(counter_assignment, ResolvedAssignment)
        self.assertIsInstance(enabled_assignment, ResolvedAssignment)
        assert isinstance(counter_assignment, ResolvedAssignment)
        assert isinstance(enabled_assignment, ResolvedAssignment)
        self.assertEqual(
            counter_assignment.value,
            ImmediateValue(0xFF, BuiltInType.BYTE),
        )
        self.assertEqual(
            enabled_assignment.value,
            ImmediateValue(1, BuiltInType.BOOLEAN),
        )

    def test_resolves_variable_to_variable_assignment(self) -> None:
        source = """program Variables;
var
    First: byte;
    Second: byte;
begin
    First := $2A;
    Second := First;
    nes.set_background_color($21);
    nes.run;
end.
"""
        resolved = analyze_source(source)
        second_assignment = resolved.statements[1]
        self.assertIsInstance(second_assignment, ResolvedAssignment)
        assert isinstance(second_assignment, ResolvedAssignment)
        self.assertIsInstance(second_assignment.value, VariableValue)

    def test_rejects_byte_outside_range(self) -> None:
        source = """program Variables;
var
    Counter: byte;
begin
    Counter := $100;
    nes.set_background_color($21);
    nes.run;
end.
"""
        with self.assertRaises(CompilerError) as context:
            analyze_source(source)
        self.assertEqual(context.exception.code, "E4003")
        self.assertIn("Allowed range: $00..$FF.", str(context.exception))

    def test_rejects_boolean_assignment_from_hexadecimal_literal(self) -> None:
        source = """program Variables;
var
    Enabled: boolean;
begin
    Enabled := $01;
    nes.set_background_color($21);
    nes.run;
end.
"""
        with self.assertRaises(CompilerError) as context:
            analyze_source(source)
        self.assertEqual(context.exception.code, "E4004")
        self.assertIn(
            "Cannot assign a hexadecimal literal to boolean variable Enabled.",
            str(context.exception),
        )
        self.assertIn("Use true or false.", str(context.exception))

    def test_rejects_mismatched_variable_type(self) -> None:
        source = """program Variables;
var
    Counter: byte;
begin
    Counter := $21;
    nes.set_background_color(Counter);
    nes.run;
end.
"""
        with self.assertRaises(CompilerError) as context:
            analyze_source(source)
        self.assertEqual(context.exception.code, "E4004")
        self.assertIn(
            "Counter has type byte, but nes_color is required.",
            str(context.exception),
        )

    def test_rejects_variable_read_before_assignment(self) -> None:
        source = """program Variables;
var
    Color: nes_color;
begin
    nes.set_background_color(Color);
    nes.run;
end.
"""
        with self.assertRaises(CompilerError) as context:
            analyze_source(source)
        self.assertEqual(context.exception.code, "E3008")
        self.assertIn("read before it is assigned", str(context.exception))

    def test_rejects_assignment_to_constant(self) -> None:
        source = """program Variables;
const
    Color: nes_color = $21;
begin
    Color := $0F;
    nes.set_background_color(Color);
    nes.run;
end.
"""
        with self.assertRaises(CompilerError) as context:
            analyze_source(source)
        self.assertEqual(context.exception.code, "E3006")
        self.assertIn("Cannot assign to constant Color.", str(context.exception))

    def test_rejects_name_collision_between_constant_and_variable(self) -> None:
        source = """program Variables;
const
    Color: nes_color = $21;
var
    COLOR: nes_color;
begin
    nes.set_background_color(Color);
    nes.run;
end.
"""
        with self.assertRaises(CompilerError) as context:
            analyze_source(source)
        self.assertEqual(context.exception.code, "E3004")


if __name__ == "__main__":
    unittest.main()
