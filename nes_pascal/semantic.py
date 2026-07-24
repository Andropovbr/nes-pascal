"""Semantic validation, name resolution, and strict type checking."""

from dataclasses import dataclass

from .ast import (
    Assignment,
    BinaryExpression,
    BooleanLiteral,
    BuiltInType,
    ConstantDeclaration,
    ConstantReference,
    HexLiteral,
    ImmediateValue,
    Program,
    ResolvedAssignment,
    ResolvedBinaryExpression,
    ResolvedProgram,
    ResolvedSetBackgroundColor,
    ResolvedStatement,
    ResolvedValue,
    ResolvedVariable,
    ResolvedUnaryExpression,
    Run,
    SetBackgroundColor,
    SourcePosition,
    UnaryExpression,
    ValueExpression,
    VariableValue,
    VariableReference,
)
from .diagnostics import CompilerError, DiagnosticCode, SourceLocation


@dataclass(frozen=True, slots=True)
class TypedConstant:
    type: BuiltInType
    value: int


class SemanticAnalyzer:
    def __init__(self, source: str, filename: str = "<input>") -> None:
        self.source_lines = source.splitlines()
        self.filename = filename

    def analyze(self, program: Program) -> ResolvedProgram:
        constants: dict[str, TypedConstant] = {}
        declared_names: set[str] = set()
        for declaration in program.constants:
            normalized_name = declaration.name.lower()
            self._ensure_unique_name(
                declaration.name,
                declaration.position,
                declared_names,
            )
            constants[normalized_name] = TypedConstant(
                declaration.type,
                self._evaluate_literal(declaration.value, declaration.type),
            )
            declared_names.add(normalized_name)

        variables: dict[str, ResolvedVariable] = {}
        resolved_variables: list[ResolvedVariable] = []
        for declaration in program.variables:
            normalized_name = declaration.name.lower()
            self._ensure_unique_name(
                declaration.name,
                declaration.position,
                declared_names,
            )
            variable = ResolvedVariable(
                declaration.name,
                declaration.type,
                f"variable_{declaration.name}",
            )
            variables[normalized_name] = variable
            resolved_variables.append(variable)
            declared_names.add(normalized_name)

        assigned_variables: set[str] = set()
        resolved_statements: list[ResolvedStatement] = []
        for statement in program.statements:
            if isinstance(statement, Assignment):
                resolved = self._resolve_assignment(
                    statement,
                    constants,
                    variables,
                    assigned_variables,
                )
                resolved_statements.append(resolved)
                assigned_variables.add(statement.target.lower())
            elif isinstance(statement, SetBackgroundColor):
                resolved_statements.append(
                    ResolvedSetBackgroundColor(
                        self._resolve_value(
                            statement.argument,
                            BuiltInType.NES_COLOR,
                            constants,
                            variables,
                            assigned_variables,
                        )
                    )
                )
            else:
                assert isinstance(statement, Run)
                resolved_statements.append(Run())

        self._validate_program_structure(program)
        return ResolvedProgram(
            program.name,
            tuple(resolved_variables),
            tuple(resolved_statements),
        )

    def _ensure_unique_name(
        self,
        name: str,
        position: SourcePosition,
        declared_names: set[str],
    ) -> None:
        if name.lower() not in declared_names:
            return
        self._error(
            position,
            DiagnosticCode.DUPLICATE_SYMBOL,
            f"Symbol {name} is already declared.",
            "Use a unique name for every constant and variable.",
        )

    def _resolve_assignment(
        self,
        assignment: Assignment,
        constants: dict[str, TypedConstant],
        variables: dict[str, ResolvedVariable],
        assigned_variables: set[str],
    ) -> ResolvedAssignment:
        normalized_target = assignment.target.lower()
        target = variables.get(normalized_target)
        if target is None:
            if normalized_target in constants:
                self._error(
                    assignment.target_position,
                    DiagnosticCode.ASSIGNMENT_TO_CONSTANT,
                    f"Cannot assign to constant {assignment.target}.",
                    "Use a variable as the assignment target.",
                )
            self._error(
                assignment.target_position,
                DiagnosticCode.UNKNOWN_ASSIGNMENT_TARGET,
                f"Unknown variable: {assignment.target}.",
                "Declare the variable in the var section before assigning it.",
            )
        value = self._resolve_value(
            assignment.value,
            target.type,
            constants,
            variables,
            assigned_variables,
            assignment_target=target,
        )
        return ResolvedAssignment(target, value)

    def _resolve_value(
        self,
        expression: ValueExpression,
        expected_type: BuiltInType,
        constants: dict[str, TypedConstant],
        variables: dict[str, ResolvedVariable],
        assigned_variables: set[str],
        assignment_target: ResolvedVariable | None = None,
    ) -> ResolvedValue:
        if isinstance(expression, (UnaryExpression, BinaryExpression)):
            return self._resolve_arithmetic_expression(
                expression,
                expected_type,
                constants,
                variables,
                assigned_variables,
                assignment_target,
            )
        if isinstance(expression, (HexLiteral, BooleanLiteral)):
            return ImmediateValue(
                self._evaluate_literal(
                    expression,
                    expected_type,
                    assignment_target=assignment_target,
                ),
                expected_type,
            )

        assert isinstance(expression, (ConstantReference, VariableReference))
        normalized_name = expression.name.lower()
        constant = constants.get(normalized_name)
        if constant is not None:
            self._require_matching_type(
                expression.name,
                expression.position,
                constant.type,
                expected_type,
                assignment_target,
            )
            return ImmediateValue(constant.value, constant.type)

        variable = variables.get(normalized_name)
        if variable is None:
            self._error(
                expression.position,
                DiagnosticCode.UNKNOWN_IDENTIFIER,
                f"Unknown identifier: {expression.name}.",
                "Declare the constant or variable before using it.",
            )
        self._require_matching_type(
            expression.name,
            expression.position,
            variable.type,
            expected_type,
            assignment_target,
        )
        if normalized_name not in assigned_variables:
            self._error(
                expression.position,
                DiagnosticCode.VARIABLE_READ_BEFORE_ASSIGNMENT,
                f"Variable {expression.name} is read before it is assigned.",
                "Assign a value to the variable before reading it.",
                len(expression.name),
            )
        return VariableValue(variable)

    def _resolve_arithmetic_expression(
        self,
        expression: UnaryExpression | BinaryExpression,
        expected_type: BuiltInType,
        constants: dict[str, TypedConstant],
        variables: dict[str, ResolvedVariable],
        assigned_variables: set[str],
        assignment_target: ResolvedVariable | None,
    ) -> ResolvedValue:
        if expected_type is not BuiltInType.BYTE:
            if assignment_target is not None:
                self._error(
                    expression.position,
                    DiagnosticCode.INCOMPATIBLE_TYPES,
                    "Cannot assign an arithmetic expression of type byte to "
                    f"variable {assignment_target.name} of type "
                    f"{assignment_target.type.value}.",
                    "Arithmetic expressions require a byte target.",
                )
            self._error(
                expression.position,
                DiagnosticCode.INCOMPATIBLE_TYPES,
                f"Arithmetic expressions have type byte, but "
                f"{expected_type.value} is required.",
                "Use arithmetic only where a byte value is expected.",
            )

        if isinstance(expression, UnaryExpression):
            operand = self._resolve_value(
                expression.operand,
                BuiltInType.BYTE,
                constants,
                variables,
                assigned_variables,
            )
            return ResolvedUnaryExpression(expression.operator, operand)

        left = self._resolve_value(
            expression.left,
            BuiltInType.BYTE,
            constants,
            variables,
            assigned_variables,
        )
        right = self._resolve_value(
            expression.right,
            BuiltInType.BYTE,
            constants,
            variables,
            assigned_variables,
        )
        return ResolvedBinaryExpression(left, expression.operator, right)

    def _require_matching_type(
        self,
        name: str,
        position: SourcePosition,
        actual_type: BuiltInType,
        expected_type: BuiltInType,
        assignment_target: ResolvedVariable | None = None,
    ) -> None:
        if actual_type is expected_type:
            return
        if assignment_target is not None:
            self._error(
                position,
                DiagnosticCode.INCOMPATIBLE_TYPES,
                f"Cannot assign a value of type {actual_type.value} to variable "
                f"{assignment_target.name} of type {assignment_target.type.value}.",
                "The source and target types must match.",
                len(name),
            )
        self._error(
            position,
            DiagnosticCode.INCOMPATIBLE_TYPES,
            f"Type mismatch: {name} has type {actual_type.value}, "
            f"but {expected_type.value} is required.",
            "Use a value with exactly the required type.",
            len(name),
        )

    def _evaluate_literal(
        self,
        literal: HexLiteral | BooleanLiteral,
        expected_type: BuiltInType,
        assignment_target: ResolvedVariable | None = None,
    ) -> int:
        if isinstance(literal, BooleanLiteral):
            if expected_type is not BuiltInType.BOOLEAN:
                self._literal_type_error(
                    literal,
                    "boolean",
                    expected_type,
                    assignment_target,
                )
            return int(literal.value)

        if expected_type is BuiltInType.BOOLEAN:
            self._literal_type_error(
                literal,
                "hexadecimal",
                expected_type,
                assignment_target,
            )
        if expected_type is BuiltInType.NES_COLOR and literal.value > 0x3F:
            self._error(
                literal.position,
                DiagnosticCode.INVALID_NES_COLOR_VALUE,
                f"Value {literal.text} is not valid for type nes_color.",
                "Allowed range: $00..$3F.",
                len(literal.text),
            )
        if expected_type is BuiltInType.BYTE and literal.value > 0xFF:
            self._error(
                literal.position,
                DiagnosticCode.INVALID_BYTE_VALUE,
                f"Value {literal.text} is not valid for type byte.",
                "Allowed range: $00..$FF.",
                len(literal.text),
            )
        return literal.value

    def _literal_type_error(
        self,
        literal: HexLiteral | BooleanLiteral,
        literal_type: str,
        expected_type: BuiltInType,
        assignment_target: ResolvedVariable | None,
    ) -> None:
        if assignment_target is not None:
            article = "an" if literal_type[0].lower() in "aeiou" else "a"
            self._error(
                literal.position,
                DiagnosticCode.INCOMPATIBLE_TYPES,
                f"Cannot assign {article} {literal_type} literal to "
                f"{expected_type.value} variable {assignment_target.name}.",
                "Use true or false."
                if expected_type is BuiltInType.BOOLEAN
                else "Use a literal that exactly matches the target type.",
                len(literal.text),
            )
        self._error(
            literal.position,
            DiagnosticCode.INCOMPATIBLE_TYPES,
            f"A {literal_type} literal is not valid for type {expected_type.value}.",
            "Use a literal that exactly matches the declared type.",
            len(literal.text),
        )

    def _validate_program_structure(self, program: Program) -> None:
        run_indices = [
            index
            for index, statement in enumerate(program.statements)
            if isinstance(statement, Run)
        ]
        if run_indices and run_indices[0] != len(program.statements) - 1:
            offending_statement = program.statements[run_indices[0] + 1]
            self._error(
                self._statement_position(offending_statement, program),
                DiagnosticCode.STATEMENT_AFTER_RUN,
                "No statement may appear after nes.run.",
                "Move 'nes.run;' to the end of the program block.",
            )

        color_commands = [
            statement
            for statement in program.statements
            if isinstance(statement, SetBackgroundColor)
        ]
        if len(color_commands) != 1:
            position = (
                color_commands[1].position
                if len(color_commands) > 1
                else program.end_position
            )
            assert position is not None
            self._error(
                position,
                DiagnosticCode.INVALID_BACKGROUND_COLOR_CALL_COUNT,
                "The program must set the background color exactly once.",
                "Add one nes.set_background_color(value); call before nes.run.",
            )

        if not run_indices:
            assert program.end_position is not None
            self._error(
                program.end_position,
                DiagnosticCode.MISSING_RUN,
                "The program must end with nes.run.",
                "Add 'nes.run;' as the last statement in the block.",
            )

    def _statement_position(
        self,
        statement: Assignment | SetBackgroundColor | Run,
        program: Program,
    ) -> SourcePosition:
        if isinstance(statement, Assignment):
            return statement.target_position
        if statement.position is not None:
            return statement.position
        assert program.end_position is not None
        return program.end_position

    def _error(
        self,
        position: SourcePosition,
        code: DiagnosticCode,
        message: str,
        suggestion: str,
        highlight_length: int = 1,
    ) -> None:
        source_line = (
            self.source_lines[position.line - 1]
            if 0 < position.line <= len(self.source_lines)
            else ""
        )
        raise CompilerError(
            code,
            message,
            SourceLocation(self.filename, position.line, position.column),
            source_line,
            suggestion,
            highlight_length,
        )


def analyze(
    program: Program, source: str, filename: str = "<input>"
) -> ResolvedProgram:
    return SemanticAnalyzer(source, filename).analyze(program)
