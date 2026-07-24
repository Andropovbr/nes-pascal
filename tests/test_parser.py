import unittest

from nes_pascal.ast import (
    Assignment,
    BinaryExpression,
    BinaryOperator,
    BooleanBinaryExpression,
    BooleanNotExpression,
    BooleanOperator,
    BooleanLiteral,
    BuiltInType,
    ConstantDeclaration,
    ConstantReference,
    ComparisonExpression,
    ComparisonOperator,
    HexLiteral,
    IfStatement,
    Run,
    SetBackgroundColor,
    SourcePosition,
    UnaryExpression,
    UnaryOperator,
    VariableDeclaration,
    VariableReference,
)
from nes_pascal.diagnostics import CompilerError
from nes_pascal.parser import parse
from nes_pascal.semantic import analyze


def program_with(body: str, constants: str = "", variables: str = "") -> str:
    const_section = f"const\n{constants}\n" if constants else ""
    var_section = f"var\n{variables}\n" if variables else ""
    return f"program Minimal;\n{const_section}{var_section}begin\n{body}\nend.\n"


class ParserTests(unittest.TestCase):
    def test_builds_minimal_ast(self) -> None:
        program = parse(
            program_with("nes.set_background_color($21);\nnes.run;"),
            "minimal.nsp",
        )
        self.assertEqual(program.name, "Minimal")
        self.assertEqual(program.constants, ())
        self.assertEqual(program.variables, ())
        self.assertEqual(
            program.statements,
            (
                SetBackgroundColor(HexLiteral(0x21, "$21", SourcePosition(3, 26))),
                Run(),
            ),
        )

    def test_parses_typed_constant_and_reference_nodes(self) -> None:
        program = parse(
            program_with(
                "nes.set_background_color(BackgroundColor);\nnes.run;",
                "    BackgroundColor: nes_color = $21;",
            ),
            "constant.nsp",
        )
        self.assertEqual(
            program.constants,
            (
                ConstantDeclaration(
                    "BackgroundColor",
                    BuiltInType.NES_COLOR,
                    HexLiteral(0x21, "$21", SourcePosition(3, 34)),
                    SourcePosition(3, 5),
                ),
            ),
        )
        self.assertEqual(
            program.statements[0],
            SetBackgroundColor(
                ConstantReference("BackgroundColor", SourcePosition(5, 26))
            ),
        )

    def test_accepts_case_insensitive_commands(self) -> None:
        program = parse(program_with("NES.SET_BACKGROUND_COLOR($0F);\nNES.RUN;"))
        statement = program.statements[0]
        self.assertIsInstance(statement, SetBackgroundColor)
        assert isinstance(statement, SetBackgroundColor)
        self.assertEqual(statement.argument.value, 0x0F)

    def test_rejects_color_outside_palette_range(self) -> None:
        source = program_with("nes.set_background_color($40);\nnes.run;")
        with self.assertRaises(CompilerError) as context:
            analyze(parse(source, "invalid-color.nsp"), source, "invalid-color.nsp")
        error = context.exception
        self.assertEqual(error.code, "E4002")
        self.assertIn("$00..$3F", str(error))
        self.assertEqual(error.location.filename, "invalid-color.nsp")

    def test_rejects_statement_after_run(self) -> None:
        source = program_with(
            "nes.set_background_color($21);\n"
            "nes.run;\n"
            "nes.set_background_color($10);"
        )
        with self.assertRaises(CompilerError) as context:
            analyze(parse(source), source)
        self.assertEqual(context.exception.code, "E3002")

    def test_rejects_unknown_command_without_traceback(self) -> None:
        with self.assertRaises(CompilerError) as context:
            parse(program_with("nes.background($21);\nnes.run;"))
        self.assertEqual(context.exception.code, "E2101")
        self.assertIn("nes.background", str(context.exception))

    def test_rejects_unknown_type(self) -> None:
        with self.assertRaises(CompilerError) as context:
            parse(
                program_with(
                    "nes.set_background_color(BackgroundColor);\nnes.run;",
                    "    BackgroundColor: word = $21;",
                )
            )
        self.assertEqual(context.exception.code, "E4001")
        self.assertIn(
            "Supported types: nes_color, byte, boolean.",
            str(context.exception),
        )

    def test_parses_variable_declarations_and_assignments(self) -> None:
        program = parse(
            program_with(
                "BackgroundColor := $21;\n"
                "Enabled := true;\n"
                "nes.set_background_color(BackgroundColor);\n"
                "nes.run;",
                variables=(
                    "    BackgroundColor: nes_color;\n"
                    "    Enabled: boolean;"
                ),
            )
        )
        self.assertEqual(
            [(variable.name, variable.type) for variable in program.variables],
            [
                ("BackgroundColor", BuiltInType.NES_COLOR),
                ("Enabled", BuiltInType.BOOLEAN),
            ],
        )
        self.assertIsInstance(program.statements[0], Assignment)
        assignment = program.statements[1]
        self.assertIsInstance(assignment, Assignment)
        assert isinstance(assignment, Assignment)
        self.assertEqual(
            assignment.value,
            BooleanLiteral(True, "true", assignment.value.position),
        )
        color_command = program.statements[2]
        self.assertIsInstance(color_command, SetBackgroundColor)
        assert isinstance(color_command, SetBackgroundColor)
        self.assertIsInstance(color_command.argument, VariableReference)

    def test_parses_all_milestone_three_variable_types(self) -> None:
        program = parse(
            program_with(
                "Color := $21;\n"
                "Counter := $FF;\n"
                "Enabled := false;\n"
                "nes.set_background_color(Color);\n"
                "nes.run;",
                variables=(
                    "    Color: nes_color;\n"
                    "    Counter: byte;\n"
                    "    Enabled: boolean;"
                ),
            )
        )
        self.assertEqual(
            [variable.type for variable in program.variables],
            [
                BuiltInType.NES_COLOR,
                BuiltInType.BYTE,
                BuiltInType.BOOLEAN,
            ],
        )

    def test_parses_left_associative_arithmetic_expression(self) -> None:
        program = parse(
            program_with(
                "Counter := $08 - $03 + $01;\n"
                "nes.set_background_color($21);\n"
                "nes.run;",
                variables="    Counter: byte;",
            )
        )
        assignment = program.statements[0]
        self.assertIsInstance(assignment, Assignment)
        assert isinstance(assignment, Assignment)
        expression = assignment.value
        self.assertIsInstance(expression, BinaryExpression)
        assert isinstance(expression, BinaryExpression)
        self.assertEqual(expression.operator, BinaryOperator.ADD)
        self.assertIsInstance(expression.left, BinaryExpression)
        assert isinstance(expression.left, BinaryExpression)
        self.assertEqual(expression.left.operator, BinaryOperator.SUBTRACT)

    def test_parentheses_and_unary_operators_override_grouping(self) -> None:
        program = parse(
            program_with(
                "Counter := -($01 + +$02);\n"
                "nes.set_background_color($21);\n"
                "nes.run;",
                variables="    Counter: byte;",
            )
        )
        assignment = program.statements[0]
        assert isinstance(assignment, Assignment)
        expression = assignment.value
        self.assertIsInstance(expression, UnaryExpression)
        assert isinstance(expression, UnaryExpression)
        self.assertEqual(expression.operator, UnaryOperator.NEGATE)
        self.assertIsInstance(expression.operand, BinaryExpression)
        assert isinstance(expression.operand, BinaryExpression)
        self.assertIsInstance(expression.operand.right, UnaryExpression)
        assert isinstance(expression.operand.right, UnaryExpression)
        self.assertEqual(expression.operand.right.operator, UnaryOperator.PLUS)

    def test_parses_comparison_and_boolean_precedence(self) -> None:
        program = parse(
            program_with(
                "Result := not Left = Right and Left < Right or false;\n"
                "nes.set_background_color($21);\n"
                "nes.run;",
                variables=(
                    "    Left: byte;\n"
                    "    Right: byte;\n"
                    "    Result: boolean;"
                ),
            )
        )
        assignment = program.statements[0]
        assert isinstance(assignment, Assignment)
        expression = assignment.value
        self.assertIsInstance(expression, BooleanBinaryExpression)
        assert isinstance(expression, BooleanBinaryExpression)
        self.assertEqual(expression.operator, BooleanOperator.OR)
        self.assertIsInstance(expression.left, BooleanBinaryExpression)
        assert isinstance(expression.left, BooleanBinaryExpression)
        self.assertEqual(expression.left.operator, BooleanOperator.AND)
        self.assertIsInstance(expression.left.left, ComparisonExpression)
        assert isinstance(expression.left.left, ComparisonExpression)
        self.assertEqual(
            expression.left.left.operator,
            ComparisonOperator.EQUAL,
        )
        self.assertIsInstance(expression.left.left.left, BooleanNotExpression)

    def test_parses_every_comparison_operator(self) -> None:
        operators = {
            "=": ComparisonOperator.EQUAL,
            "<>": ComparisonOperator.NOT_EQUAL,
            "<": ComparisonOperator.LESS,
            ">": ComparisonOperator.GREATER,
            "<=": ComparisonOperator.LESS_EQUAL,
            ">=": ComparisonOperator.GREATER_EQUAL,
        }
        for spelling, expected_operator in operators.items():
            with self.subTest(operator=spelling):
                program = parse(
                    program_with(
                        f"Result := Left {spelling} Right;\n"
                        "nes.set_background_color($21);\n"
                        "nes.run;",
                        variables=(
                            "    Left: byte;\n"
                            "    Right: byte;\n"
                            "    Result: boolean;"
                        ),
                    )
                )
                assignment = program.statements[0]
                assert isinstance(assignment, Assignment)
                expression = assignment.value
                self.assertIsInstance(expression, ComparisonExpression)
                assert isinstance(expression, ComparisonExpression)
                self.assertEqual(expression.operator, expected_operator)

    def test_parses_if_else_with_compound_branches(self) -> None:
        program = parse(
            program_with(
                "if Enabled then\n"
                "begin\n"
                "    Counter := $01;\n"
                "end\n"
                "else\n"
                "begin\n"
                "    Counter := $02;\n"
                "end;\n"
                "nes.set_background_color($21);\n"
                "nes.run;",
                variables=(
                    "    Counter: byte;\n"
                    "    Enabled: boolean;"
                ),
            )
        )
        statement = program.statements[0]
        self.assertIsInstance(statement, IfStatement)
        assert isinstance(statement, IfStatement)
        self.assertEqual(len(statement.then_branch), 1)
        self.assertEqual(len(statement.else_branch or ()), 1)
        self.assertIsInstance(statement.then_branch[0], Assignment)

    def test_parses_nested_if_and_attaches_else_to_nearest_if(self) -> None:
        program = parse(
            program_with(
                "if First then\n"
                "    if Second then\n"
                "        Counter := $01\n"
                "    else\n"
                "        Counter := $02;\n"
                "nes.set_background_color($21);\n"
                "nes.run;",
                variables=(
                    "    Counter: byte;\n"
                    "    First: boolean;\n"
                    "    Second: boolean;"
                ),
            )
        )
        outer = program.statements[0]
        assert isinstance(outer, IfStatement)
        self.assertIsNone(outer.else_branch)
        inner = outer.then_branch[0]
        self.assertIsInstance(inner, IfStatement)
        assert isinstance(inner, IfStatement)
        self.assertIsNotNone(inner.else_branch)

    def test_rejects_if_without_then(self) -> None:
        with self.assertRaises(CompilerError) as context:
            parse(
                program_with(
                    "if Enabled Counter := $01;\n"
                    "nes.set_background_color($21);\n"
                    "nes.run;",
                    variables=(
                        "    Counter: byte;\n"
                        "    Enabled: boolean;"
                    ),
                ),
                "missing-then.nsp",
            )
        self.assertEqual(context.exception.code, "E2102")
        self.assertIn(
            "Expected 'then' after the if condition.",
            str(context.exception),
        )


if __name__ == "__main__":
    unittest.main()
