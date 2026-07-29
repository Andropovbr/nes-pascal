from pathlib import Path
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
    ResolvedBreakStatement,
    ResolvedComparisonExpression,
    ResolvedContinueStatement,
    ResolvedDecrementStatement,
    ResolvedForStatement,
    ResolvedIfStatement,
    ResolvedIncrementStatement,
    ResolvedProcedureCall,
    ResolvedRepeatStatement,
    ResolvedSetBackgroundColor,
    ResolvedUnaryExpression,
    ResolvedWhileStatement,
    Run,
    VariableValue,
    WaitFrame,
)
from nes_pascal.diagnostics import CompilerError
from nes_pascal.parser import parse
from nes_pascal.semantic import analyze


ROOT = Path(__file__).resolve().parents[1]


def analyze_source(source: str, filename: str = "semantic.nsp"):
    return analyze(parse(source, filename), source, filename)


class SemanticTests(unittest.TestCase):
    def test_resolves_frame_wait_after_runtime_start(self) -> None:
        source = """program FrameLoop;
begin
    nes.set_background_color($21);
    nes.run;
    while true do
        nes.wait_frame;
end.
"""
        resolved = analyze_source(source)

        loop = resolved.statements[2]
        self.assertIsInstance(loop, ResolvedWhileStatement)
        assert isinstance(loop, ResolvedWhileStatement)
        self.assertEqual(loop.body, (WaitFrame(),))

    def test_rejects_frame_wait_before_runtime_start(self) -> None:
        path = (
            ROOT
            / "tests"
            / "fixtures"
            / "diagnostics"
            / "frame_wait_before_run.nsp"
        )
        source = path.read_text(encoding="utf-8")

        with self.assertRaises(CompilerError) as context:
            analyze_source(source, str(path))

        self.assertEqual(context.exception.code, "E3017")
        self.assertIn(
            "cannot execute before nes.run starts NMI",
            str(context.exception),
        )
        self.assertNotIn("E3001", str(context.exception))

    def test_rejects_frame_wait_inside_procedure(self) -> None:
        source = """program ProcedureWait;
procedure WaitInsideProcedure;
begin
    nes.wait_frame;
end;
begin
    nes.set_background_color($21);
    nes.run;
end.
"""
        with self.assertRaises(CompilerError) as context:
            analyze_source(source)

        self.assertEqual(context.exception.code, "E3015")
        self.assertIn(
            "nes.wait_frame cannot appear inside a procedure",
            str(context.exception),
        )

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

    def test_resolves_nested_loops_break_and_continue(self) -> None:
        source = """program Loops;
var
    Counter: byte;
    Running: boolean;
begin
    Counter := $00;
    Running := true;
    while Running do
    begin
        repeat
            Counter := Counter + $01;
            if Counter = $02 then
                continue;
        until Counter >= $03;
        break;
    end;
    nes.set_background_color($21);
    nes.run;
end.
"""
        resolved = analyze_source(source)
        while_loop = resolved.statements[2]
        self.assertIsInstance(while_loop, ResolvedWhileStatement)
        assert isinstance(while_loop, ResolvedWhileStatement)
        repeat_loop = while_loop.body[0]
        self.assertIsInstance(repeat_loop, ResolvedRepeatStatement)
        assert isinstance(repeat_loop, ResolvedRepeatStatement)
        nested_if = repeat_loop.body[1]
        assert isinstance(nested_if, ResolvedIfStatement)
        self.assertIsInstance(
            nested_if.then_branch[0],
            ResolvedContinueStatement,
        )
        self.assertIsInstance(while_loop.body[1], ResolvedBreakStatement)

    def test_loop_assignment_does_not_propagate_after_loop(self) -> None:
        source = """program Loops;
var
    Running: boolean;
    Counter: byte;
    Result: byte;
begin
    Running := false;
    while Running do
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

    def test_rejects_non_boolean_loop_conditions(self) -> None:
        sources = (
            """program InvalidWhile;
var
    Counter: byte;
begin
    Counter := $01;
    while Counter do
        Counter := $02;
    nes.set_background_color($21);
    nes.run;
end.
""",
            """program InvalidRepeat;
var
    Counter: byte;
begin
    Counter := $01;
    repeat
        Counter := Counter + $01;
    until Counter;
    nes.set_background_color($21);
    nes.run;
end.
""",
        )
        for source in sources:
            with self.subTest(program=source.splitlines()[0]):
                with self.assertRaises(CompilerError) as context:
                    analyze_source(source)
                self.assertEqual(context.exception.code, "E4004")
                self.assertIn(
                    "Counter has type byte, but boolean is required.",
                    str(context.exception),
                )

    def test_rejects_break_and_continue_outside_loop(self) -> None:
        for statement in ("break", "continue"):
            with self.subTest(statement=statement):
                source = f"""program InvalidLoopControl;
begin
    {statement};
    nes.set_background_color($21);
    nes.run;
end.
"""
                with self.assertRaises(CompilerError) as context:
                    analyze_source(source)
                self.assertEqual(context.exception.code, "E3010")
                self.assertIn(
                    f"{statement} can appear only inside a loop.",
                    str(context.exception),
                )

    def test_rejects_runtime_command_inside_loop(self) -> None:
        source = """program InvalidLoopRuntime;
var
    Running: boolean;
begin
    Running := true;
    while Running do
        nes.run;
    nes.set_background_color($21);
    nes.run;
end.
"""
        with self.assertRaises(CompilerError) as context:
            analyze_source(source)
        self.assertEqual(context.exception.code, "E3011")
        self.assertIn(
            "nes.run cannot appear inside a loop body.",
            str(context.exception),
        )

    def test_resolves_updates_and_nested_for_loops(self) -> None:
        source = """program Counting;
var
    Counter: byte;
    Outer: byte;
    Inner: byte;
begin
    Counter := $00;
    inc(Counter);
    dec(Counter, $02);
    for Outer := $00 to $01 do
    begin
        for Inner := $01 downto $00 do
            inc(Counter, Inner);
    end;
    nes.set_background_color($21);
    nes.run;
end.
"""
        resolved = analyze_source(source)
        self.assertIsInstance(
            resolved.statements[1],
            ResolvedIncrementStatement,
        )
        self.assertIsInstance(
            resolved.statements[2],
            ResolvedDecrementStatement,
        )
        outer = resolved.statements[3]
        self.assertIsInstance(outer, ResolvedForStatement)
        assert isinstance(outer, ResolvedForStatement)
        inner = outer.body[0]
        self.assertIsInstance(inner, ResolvedForStatement)

    def test_for_control_variable_is_definitely_assigned_after_loop(self) -> None:
        source = """program Counting;
var
    Index: byte;
    Result: byte;
begin
    for Index := $03 to $01 do
        break;
    Result := Index;
    nes.set_background_color($21);
    nes.run;
end.
"""
        resolved = analyze_source(source)
        assignment = resolved.statements[1]
        self.assertIsInstance(assignment, ResolvedAssignment)

    def test_for_final_expression_can_read_initialized_control(self) -> None:
        source = """program Counting;
var
    Index: byte;
begin
    for Index := $01 to Index + $02 do
        continue;
    nes.set_background_color($21);
    nes.run;
end.
"""
        resolved = analyze_source(source)
        self.assertIsInstance(resolved.statements[0], ResolvedForStatement)

    def test_rejects_update_before_assignment(self) -> None:
        source = """program InvalidUpdate;
var
    Counter: byte;
begin
    inc(Counter);
    nes.set_background_color($21);
    nes.run;
end.
"""
        with self.assertRaises(CompilerError) as context:
            analyze_source(source)
        self.assertEqual(context.exception.code, "E3008")
        self.assertIn(
            "Variable Counter is read before it is assigned.",
            str(context.exception),
        )

    def test_rejects_non_byte_update_target_and_amount(self) -> None:
        sources = (
            """program InvalidTarget;
var
    Enabled: boolean;
begin
    Enabled := true;
    inc(Enabled);
    nes.set_background_color($21);
    nes.run;
end.
""",
            """program InvalidAmount;
var
    Counter: byte;
    Enabled: boolean;
begin
    Counter := $00;
    Enabled := true;
    inc(Counter, Enabled);
    nes.set_background_color($21);
    nes.run;
end.
""",
        )
        for source in sources:
            with self.subTest(program=source.splitlines()[0]):
                with self.assertRaises(CompilerError) as context:
                    analyze_source(source)
                self.assertEqual(context.exception.code, "E4004")

    def test_rejects_non_byte_for_components(self) -> None:
        sources = (
            """program InvalidControl;
var
    Enabled: boolean;
begin
    for Enabled := $00 to $01 do
        break;
    nes.set_background_color($21);
    nes.run;
end.
""",
            """program InvalidFinal;
var
    Index: byte;
    Enabled: boolean;
begin
    Enabled := true;
    for Index := $00 to Enabled do
        break;
    nes.set_background_color($21);
    nes.run;
end.
""",
            """program InvalidInitial;
var
    Index: byte;
begin
    for Index := true to $01 do
        break;
    nes.set_background_color($21);
    nes.run;
end.
""",
        )
        for source in sources:
            with self.subTest(program=source.splitlines()[0]):
                with self.assertRaises(CompilerError) as context:
                    analyze_source(source)
                self.assertEqual(context.exception.code, "E4004")

    def test_rejects_for_control_variable_modification(self) -> None:
        statements = (
            "Index := $02;",
            "inc(Index);",
            "dec(Index, $01);",
            "for Index := $00 to $01 do break;",
        )
        for statement in statements:
            with self.subTest(statement=statement):
                source = f"""program InvalidControl;
var
    Index: byte;
begin
    for Index := $00 to $03 do
    begin
        {statement}
    end;
    nes.set_background_color($21);
    nes.run;
end.
"""
                with self.assertRaises(CompilerError) as context:
                    analyze_source(source)
                self.assertEqual(context.exception.code, "E3012")
                self.assertIn(
                    "For control variable Index cannot be modified",
                    str(context.exception),
                )

    def test_resolves_forward_and_nested_procedure_calls(self) -> None:
        source = """program Procedures;
var
    Counter: byte;
procedure Start;
begin
    Initialize;
    Advance;
end;
procedure Advance;
begin
    inc(Counter);
end;
procedure Initialize;
begin
    Counter := $00;
end;
begin
    Start;
    nes.set_background_color($21);
    nes.run;
end.
"""
        resolved = analyze_source(source)
        self.assertEqual(
            [procedure.name for procedure in resolved.procedures],
            ["Start", "Advance", "Initialize"],
        )
        start = resolved.procedures[0]
        self.assertIsInstance(start.body[0], ResolvedProcedureCall)
        self.assertIsInstance(start.body[1], ResolvedProcedureCall)
        self.assertIsInstance(
            resolved.statements[0],
            ResolvedProcedureCall,
        )

    def test_procedure_assignments_propagate_to_the_caller(self) -> None:
        source = """program ProcedureAssignment;
var
    Counter: byte;
    Result: byte;
procedure Initialize;
begin
    Counter := $01;
end;
begin
    Initialize;
    Result := Counter;
    nes.set_background_color($21);
    nes.run;
end.
"""
        resolved = analyze_source(source)
        self.assertIsInstance(resolved.statements[1], ResolvedAssignment)

    def test_procedure_read_precondition_accepts_assigned_variable(self) -> None:
        source = """program ProcedureRequirement;
var
    Counter: byte;
procedure Advance;
begin
    inc(Counter);
end;
begin
    Counter := $00;
    Advance;
    nes.set_background_color($21);
    nes.run;
end.
"""
        resolved = analyze_source(source)
        self.assertIsInstance(
            resolved.statements[1],
            ResolvedProcedureCall,
        )

    def test_rejects_call_with_unassigned_required_variable(self) -> None:
        source = """program ProcedureRequirement;
var
    Counter: byte;
procedure Advance;
begin
    inc(Counter);
end;
begin
    Advance;
    nes.set_background_color($21);
    nes.run;
end.
"""
        with self.assertRaises(CompilerError) as context:
            analyze_source(source)
        self.assertEqual(context.exception.code, "E3008")
        self.assertIn(
            "Procedure Advance requires variable Counter",
            str(context.exception),
        )

    def test_procedure_conditional_assignment_is_not_definite(self) -> None:
        source = """program ConditionalProcedure;
var
    Enabled: boolean;
    Counter: byte;
    Result: byte;
procedure MaybeAssign;
begin
    if Enabled then
        Counter := $01;
end;
begin
    Enabled := true;
    MaybeAssign;
    Result := Counter;
    nes.set_background_color($21);
    nes.run;
end.
"""
        with self.assertRaises(CompilerError) as context:
            analyze_source(source)
        self.assertEqual(context.exception.code, "E3008")
        self.assertIn(
            "Variable Counter is read before it is assigned.",
            str(context.exception),
        )

    def test_rejects_duplicate_procedure_name(self) -> None:
        source = """program DuplicateProcedure;
procedure Initialize;
begin
end;
procedure INITIALIZE;
begin
end;
begin
    nes.set_background_color($21);
    nes.run;
end.
"""
        with self.assertRaises(CompilerError) as context:
            analyze_source(source)
        self.assertEqual(context.exception.code, "E3004")

    def test_rejects_name_collision_between_variable_and_procedure(self) -> None:
        source = """program ProcedureCollision;
var
    Initialize: byte;
procedure INITIALIZE;
begin
end;
begin
    nes.set_background_color($21);
    nes.run;
end.
"""
        with self.assertRaises(CompilerError) as context:
            analyze_source(source)
        self.assertEqual(context.exception.code, "E3004")

    def test_rejects_unknown_procedure(self) -> None:
        source = """program UnknownProcedure;
begin
    Missing;
    nes.set_background_color($21);
    nes.run;
end.
"""
        with self.assertRaises(CompilerError) as context:
            analyze_source(source)
        self.assertEqual(context.exception.code, "E3013")

    def test_rejects_direct_and_indirect_recursion(self) -> None:
        sources = (
            """program DirectRecursion;
procedure Again;
begin
    Again;
end;
begin
    nes.set_background_color($21);
    nes.run;
end.
""",
            """program IndirectRecursion;
procedure First;
begin
    Second;
end;
procedure Second;
begin
    First;
end;
begin
    nes.set_background_color($21);
    nes.run;
end.
""",
        )
        for source in sources:
            with self.subTest(program=source.splitlines()[0]):
                with self.assertRaises(CompilerError) as context:
                    analyze_source(source)
                self.assertEqual(context.exception.code, "E3014")

    def test_rejects_runtime_command_inside_procedure(self) -> None:
        source = """program ProcedureRuntime;
procedure StartRuntime;
begin
    nes.run;
end;
begin
    nes.set_background_color($21);
    nes.run;
end.
"""
        with self.assertRaises(CompilerError) as context:
            analyze_source(source)
        self.assertEqual(context.exception.code, "E3015")
        self.assertIn(
            "nes.run cannot appear inside a procedure.",
            str(context.exception),
        )

    def test_resolves_byte_and_boolean_value_parameters(self) -> None:
        source = """program Parameters;
var
    Counter: byte;
    Active: boolean;
procedure Initialize(Value: byte; Enabled: boolean);
begin
    Counter := Value;
    Active := Enabled;
end;
begin
    Initialize($01 + $02, true);
    nes.set_background_color($21);
    nes.run;
end.
"""
        resolved = analyze_source(source)
        procedure = resolved.procedures[0]
        self.assertEqual(
            [(parameter.name, parameter.type) for parameter in procedure.parameters],
            [
                ("Value", BuiltInType.BYTE),
                ("Enabled", BuiltInType.BOOLEAN),
            ],
        )
        self.assertEqual(
            [parameter.label for parameter in procedure.parameters],
            [
                "parameter_Initialize_Value",
                "parameter_Initialize_Enabled",
            ],
        )
        call = resolved.statements[0]
        self.assertIsInstance(call, ResolvedProcedureCall)
        assert isinstance(call, ResolvedProcedureCall)
        self.assertEqual(len(call.arguments), 2)
        self.assertIsInstance(call.arguments[0].value, ResolvedBinaryExpression)
        self.assertEqual(
            call.arguments[1].value,
            ImmediateValue(1, BuiltInType.BOOLEAN),
        )

    def test_value_parameters_are_initialized_mutable_local_copies(self) -> None:
        source = """program MutableParameter;
var
    Result: byte;
procedure StoreIncremented(Value: byte);
begin
    inc(Value);
    Result := Value;
end;
begin
    StoreIncremented($02);
    nes.set_background_color($21);
    nes.run;
end.
"""
        resolved = analyze_source(source)
        procedure = resolved.procedures[0]
        increment = procedure.body[0]
        assignment = procedure.body[1]
        self.assertIsInstance(increment, ResolvedIncrementStatement)
        self.assertIsInstance(assignment, ResolvedAssignment)
        assert isinstance(increment, ResolvedIncrementStatement)
        assert isinstance(assignment, ResolvedAssignment)
        self.assertEqual(
            increment.target.label,
            "parameter_StoreIncremented_Value",
        )
        self.assertIsInstance(assignment.value, VariableValue)

    def test_resolves_parameterized_forward_and_nested_calls(self) -> None:
        source = """program NestedParameters;
var
    Result: byte;
procedure Start(Value: byte);
begin
    Finish(Value + $01, true);
end;
procedure Finish(Value: byte; Store: boolean);
begin
    if Store then
        Result := Value;
end;
begin
    Start($02);
    nes.set_background_color($21);
    nes.run;
end.
"""
        resolved = analyze_source(source)
        nested_call = resolved.procedures[0].body[0]
        self.assertIsInstance(nested_call, ResolvedProcedureCall)
        assert isinstance(nested_call, ResolvedProcedureCall)
        self.assertEqual(len(nested_call.arguments), 2)
        self.assertEqual(
            nested_call.arguments[0].parameter.label,
            "parameter_Finish_Value",
        )

    def test_rejects_incorrect_procedure_argument_count(self) -> None:
        calls = ("Initialize;", "Initialize($01, true);")
        for call in calls:
            with self.subTest(call=call):
                source = f"""program ArgumentCount;
procedure Initialize(Value: byte);
begin
end;
begin
    {call}
    nes.set_background_color($21);
    nes.run;
end.
"""
                with self.assertRaises(CompilerError) as context:
                    analyze_source(source)
                self.assertEqual(context.exception.code, "E3016")
                self.assertIn(
                    "Procedure Initialize expects 1 argument(s)",
                    str(context.exception),
                )

    def test_rejects_incompatible_procedure_argument_type(self) -> None:
        source = """program ArgumentType;
procedure SetEnabled(Enabled: boolean);
begin
end;
begin
    SetEnabled($01);
    nes.set_background_color($21);
    nes.run;
end.
"""
        with self.assertRaises(CompilerError) as context:
            analyze_source(source)
        self.assertEqual(context.exception.code, "E4004")
        self.assertIn(
            "A hexadecimal literal is not valid for type boolean.",
            str(context.exception),
        )

    def test_rejects_unsupported_nes_color_parameter(self) -> None:
        source = """program UnsupportedParameter;
procedure SetColor(Color: nes_color);
begin
end;
begin
    nes.set_background_color($21);
    nes.run;
end.
"""
        with self.assertRaises(CompilerError) as context:
            analyze_source(source)
        self.assertEqual(context.exception.code, "E4005")
        self.assertIn(
            "Type nes_color is not supported for procedure parameters.",
            str(context.exception),
        )

    def test_rejects_duplicate_parameter_names(self) -> None:
        source = """program DuplicateParameter;
procedure Initialize(Value: byte; VALUE: boolean);
begin
end;
begin
    nes.set_background_color($21);
    nes.run;
end.
"""
        with self.assertRaises(CompilerError) as context:
            analyze_source(source)
        self.assertEqual(context.exception.code, "E3004")

    def test_rejects_parameter_name_collision_with_global_symbol(self) -> None:
        source = """program ParameterCollision;
var
    Value: byte;
procedure Initialize(VALUE: byte);
begin
end;
begin
    nes.set_background_color($21);
    nes.run;
end.
"""
        with self.assertRaises(CompilerError) as context:
            analyze_source(source)
        self.assertEqual(context.exception.code, "E3004")

    def test_rejects_uninitialized_variable_used_as_argument(self) -> None:
        source = """program UninitializedArgument;
var
    Value: byte;
procedure Consume(Input: byte);
begin
end;
begin
    Consume(Value);
    nes.set_background_color($21);
    nes.run;
end.
"""
        with self.assertRaises(CompilerError) as context:
            analyze_source(source)
        self.assertEqual(context.exception.code, "E3008")

    def test_parameterized_recursion_remains_rejected(self) -> None:
        sources = (
            """program ParameterRecursion;
procedure Again(Value: byte);
begin
    Again(Value);
end;
begin
    nes.set_background_color($21);
    nes.run;
end.
""",
            """program IndirectParameterRecursion;
procedure First(Value: byte);
begin
    Second(Value);
end;
procedure Second(Value: byte);
begin
    First(Value);
end;
begin
    nes.set_background_color($21);
    nes.run;
end.
""",
        )
        for source in sources:
            with self.subTest(program=source.splitlines()[0]):
                with self.assertRaises(CompilerError) as context:
                    analyze_source(source)
                self.assertEqual(context.exception.code, "E3014")


if __name__ == "__main__":
    unittest.main()
