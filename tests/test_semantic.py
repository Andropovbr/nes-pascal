import unittest

from nes_pascal.ast import (
    BinaryOperator,
    BooleanOperator,
    BuiltInType,
    ImmediateValue,
    ResolvedAssignment,
    ResolvedBinaryExpression,
    ResolvedBooleanBinaryExpression,
    ResolvedBooleanNotExpression,
    ResolvedComparisonExpression,
    ResolvedIfStatement,
    ResolvedSetBackgroundColor,
    ResolvedUnaryExpression,
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

    def test_resolves_byte_arithmetic_with_constants_and_variables(self) -> None:
        source = """program Arithmetic;
const
    Step: byte = $02;
var
    Counter: byte;
    Result: byte;
begin
    Counter := $05;
    Result := -(Counter + Step) - $01;
    nes.set_background_color($21);
    nes.run;
end.
"""
        resolved = analyze_source(source)
        assignment = resolved.statements[1]
        assert isinstance(assignment, ResolvedAssignment)
        expression = assignment.value
        self.assertIsInstance(expression, ResolvedBinaryExpression)
        assert isinstance(expression, ResolvedBinaryExpression)
        self.assertEqual(expression.operator, BinaryOperator.SUBTRACT)
        self.assertIsInstance(expression.left, ResolvedUnaryExpression)

    def test_rejects_arithmetic_for_nes_color(self) -> None:
        source = """program Arithmetic;
var
    Color: nes_color;
begin
    Color := $20 + $01;
    nes.set_background_color(Color);
    nes.run;
end.
"""
        with self.assertRaises(CompilerError) as context:
            analyze_source(source)
        self.assertEqual(context.exception.code, "E4004")
        self.assertIn(
            "arithmetic expression of type byte",
            str(context.exception),
        )

    def test_rejects_boolean_operand_in_byte_arithmetic(self) -> None:
        source = """program Arithmetic;
var
    Counter: byte;
    Enabled: boolean;
begin
    Enabled := true;
    Counter := $01 + Enabled;
    nes.set_background_color($21);
    nes.run;
end.
"""
        with self.assertRaises(CompilerError) as context:
            analyze_source(source)
        self.assertEqual(context.exception.code, "E4004")
        self.assertIn(
            "Enabled has type boolean, but byte is required.",
            str(context.exception),
        )

    def test_detects_uninitialized_variable_inside_arithmetic(self) -> None:
        source = """program Arithmetic;
var
    Counter: byte;
    Result: byte;
begin
    Result := Counter + $01;
    nes.set_background_color($21);
    nes.run;
end.
"""
        with self.assertRaises(CompilerError) as context:
            analyze_source(source)
        self.assertEqual(context.exception.code, "E3008")
        self.assertIn("Counter is read before it is assigned.", str(context.exception))

    def test_resolves_comparisons_and_boolean_operators(self) -> None:
        source = """program BooleanExpressions;
var
    Left: byte;
    Right: byte;
    Equal: boolean;
    Result: boolean;
begin
    Left := $0F;
    Right := $10;
    Equal := Left = Right;
    Result := not Equal and (Left < Right or Left >= $20);
    nes.set_background_color($21);
    nes.run;
end.
"""
        resolved = analyze_source(source)
        equality = resolved.statements[2]
        result = resolved.statements[3]
        assert isinstance(equality, ResolvedAssignment)
        assert isinstance(result, ResolvedAssignment)
        self.assertIsInstance(equality.value, ResolvedComparisonExpression)
        self.assertIsInstance(result.value, ResolvedBooleanBinaryExpression)
        assert isinstance(result.value, ResolvedBooleanBinaryExpression)
        self.assertEqual(result.value.operator, BooleanOperator.AND)
        self.assertIsInstance(result.value.left, ResolvedBooleanNotExpression)

    def test_allows_equality_for_matching_boolean_and_nes_color_types(self) -> None:
        source = """program Equality;
var
    FirstColor: nes_color;
    SameColor: boolean;
    Enabled: boolean;
    SameState: boolean;
begin
    FirstColor := $21;
    Enabled := true;
    SameColor := FirstColor = $21;
    SameState := Enabled <> false;
    nes.set_background_color(FirstColor);
    nes.run;
end.
"""
        resolved = analyze_source(source)
        self.assertIsInstance(
            resolved.statements[2].value,
            ResolvedComparisonExpression,
        )
        self.assertIsInstance(
            resolved.statements[3].value,
            ResolvedComparisonExpression,
        )

    def test_rejects_equality_between_different_types(self) -> None:
        source = """program InvalidComparison;
var
    Counter: byte;
    Enabled: boolean;
    Result: boolean;
begin
    Counter := $01;
    Enabled := true;
    Result := Counter = Enabled;
    nes.set_background_color($21);
    nes.run;
end.
"""
        with self.assertRaises(CompilerError) as context:
            analyze_source(source)
        self.assertEqual(context.exception.code, "E4004")
        self.assertIn(
            "Comparison operands must have exactly the same type",
            str(context.exception),
        )

    def test_rejects_ordered_comparison_for_nes_color(self) -> None:
        source = """program InvalidComparison;
var
    Color: nes_color;
    Result: boolean;
begin
    Color := $21;
    Result := Color < $30;
    nes.set_background_color(Color);
    nes.run;
end.
"""
        with self.assertRaises(CompilerError) as context:
            analyze_source(source)
        self.assertEqual(context.exception.code, "E4004")
        self.assertIn(
            "Color has type nes_color, but byte is required.",
            str(context.exception),
        )

    def test_rejects_non_boolean_operand_for_boolean_operator(self) -> None:
        source = """program InvalidBoolean;
var
    Counter: byte;
    Result: boolean;
begin
    Counter := $01;
    Result := true and Counter;
    nes.set_background_color($21);
    nes.run;
end.
"""
        with self.assertRaises(CompilerError) as context:
            analyze_source(source)
        self.assertEqual(context.exception.code, "E4004")
        self.assertIn(
            "Counter has type byte, but boolean is required.",
            str(context.exception),
        )

    def test_rejects_boolean_expression_assigned_to_byte(self) -> None:
        source = """program InvalidBoolean;
var
    Counter: byte;
begin
    Counter := true or false;
    nes.set_background_color($21);
    nes.run;
end.
"""
        with self.assertRaises(CompilerError) as context:
            analyze_source(source)
        self.assertEqual(context.exception.code, "E4004")
        self.assertIn(
            "Cannot assign a boolean expression of type boolean",
            str(context.exception),
        )

    def test_resolves_if_else_and_definite_assignment(self) -> None:
        source = """program Conditionals;
var
    Enabled: boolean;
    Counter: byte;
    Result: byte;
begin
    Enabled := true;
    if Enabled then
        Counter := $01
    else
        Counter := $02;
    Result := Counter;
    nes.set_background_color($21);
    nes.run;
end.
"""
        resolved = analyze_source(source)
        conditional = resolved.statements[1]
        self.assertIsInstance(conditional, ResolvedIfStatement)
        assert isinstance(conditional, ResolvedIfStatement)
        self.assertEqual(len(conditional.then_branch), 1)
        self.assertEqual(len(conditional.else_branch or ()), 1)
        self.assertIsInstance(resolved.statements[2], ResolvedAssignment)

    def test_if_without_else_does_not_definitely_assign(self) -> None:
        source = """program Conditionals;
var
    Enabled: boolean;
    Counter: byte;
    Result: byte;
begin
    Enabled := true;
    if Enabled then
        Counter := $01;
    Result := Counter;
    nes.set_background_color($21);
    nes.run;
end.
"""
        with self.assertRaises(CompilerError) as context:
            analyze_source(source)
        self.assertEqual(context.exception.code, "E3008")
        self.assertIn("Counter is read before it is assigned.", str(context.exception))

    def test_rejects_non_boolean_if_condition(self) -> None:
        source = """program Conditionals;
var
    Counter: byte;
begin
    Counter := $01;
    if Counter then
        Counter := $02;
    nes.set_background_color($21);
    nes.run;
end.
"""
        with self.assertRaises(CompilerError) as context:
            analyze_source(source)
        self.assertEqual(context.exception.code, "E4004")
        self.assertIn(
            "Counter has type byte, but boolean is required.",
            str(context.exception),
        )

    def test_rejects_runtime_command_inside_conditional(self) -> None:
        source = """program Conditionals;
var
    Enabled: boolean;
begin
    Enabled := true;
    if Enabled then
        nes.run;
    nes.set_background_color($21);
    nes.run;
end.
"""
        with self.assertRaises(CompilerError) as context:
            analyze_source(source, "conditional-runtime.nsp")
        self.assertEqual(context.exception.code, "E3009")
        self.assertIn(
            "nes.run cannot appear inside a conditional branch.",
            str(context.exception),
        )


if __name__ == "__main__":
    unittest.main()
