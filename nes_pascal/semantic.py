"""Semantic validation, name resolution, and strict type checking."""

from dataclasses import dataclass

from .ast import (
    Assignment,
    BinaryExpression,
    BooleanBinaryExpression,
    BooleanLiteral,
    BooleanNotExpression,
    BreakStatement,
    BuiltInType,
    ComparisonExpression,
    ComparisonOperator,
    ConstantDeclaration,
    ConstantReference,
    ContinueStatement,
    DecrementStatement,
    ForStatement,
    HexLiteral,
    IfStatement,
    ImmediateValue,
    IncrementStatement,
    Program,
    ProcedureCall,
    ProcedureDeclaration,
    RepeatStatement,
    ResolvedArgument,
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
    ResolvedRepeatStatement,
    ResolvedProgram,
    ResolvedProcedure,
    ResolvedProcedureCall,
    ResolvedSetBackgroundColor,
    ResolvedStatement,
    ResolvedValue,
    ResolvedVariable,
    ResolvedWhileStatement,
    ResolvedUnaryExpression,
    Run,
    SetBackgroundColor,
    SourcePosition,
    Statement,
    UnaryExpression,
    ValueExpression,
    VariableValue,
    VariableReference,
    WhileStatement,
)
from .diagnostics import CompilerError, DiagnosticCode, SourceLocation


@dataclass(frozen=True, slots=True)
class TypedConstant:
    type: BuiltInType
    value: int


@dataclass(frozen=True, slots=True)
class ProcedureSymbol:
    declaration: ProcedureDeclaration
    label: str
    parameters: tuple[ResolvedVariable, ...]


@dataclass(frozen=True, slots=True)
class ProcedureSummary:
    required_variables: frozenset[str]
    assigned_variables: frozenset[str]
    procedure: ResolvedProcedure


class SemanticAnalyzer:
    def __init__(self, source: str, filename: str = "<input>") -> None:
        self.source_lines = source.splitlines()
        self.filename = filename
        self.required_variables: set[str] | None = None
        self.procedure_summaries: dict[str, ProcedureSummary] = {}

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
                declaration.position,
            )
            variables[normalized_name] = variable
            resolved_variables.append(variable)
            declared_names.add(normalized_name)

        procedures: dict[str, ProcedureSymbol] = {}
        for declaration in program.procedures:
            normalized_name = declaration.name.lower()
            self._ensure_unique_name(
                declaration.name,
                declaration.position,
                declared_names,
            )
            procedures[normalized_name] = ProcedureSymbol(
                declaration,
                f"procedure_{declaration.name}",
                (),
            )
            declared_names.add(normalized_name)

        for declaration in program.procedures:
            normalized_name = declaration.name.lower()
            parameter_names: set[str] = set()
            resolved_parameters: list[ResolvedVariable] = []
            for parameter in declaration.parameters:
                if parameter.type not in (
                    BuiltInType.BYTE,
                    BuiltInType.BOOLEAN,
                ):
                    self._error(
                        parameter.type_position or parameter.position,
                        DiagnosticCode.UNSUPPORTED_PARAMETER_TYPE,
                        f"Type {parameter.type.value} is not supported for "
                        "procedure parameters.",
                        "Use byte or boolean for a value parameter.",
                        len(parameter.type.value),
                    )
                self._ensure_unique_name(
                    parameter.name,
                    parameter.position,
                    declared_names | parameter_names,
                )
                parameter_names.add(parameter.name.lower())
                resolved_parameters.append(
                    ResolvedVariable(
                        parameter.name,
                        parameter.type,
                        f"parameter_{declaration.name}_{parameter.name}",
                        parameter.position,
                    )
                )
            symbol = procedures[normalized_name]
            procedures[normalized_name] = ProcedureSymbol(
                symbol.declaration,
                symbol.label,
                tuple(resolved_parameters),
            )

        procedure_order = self._procedure_resolution_order(
            program.procedures,
            procedures,
        )
        self._validate_known_procedure_calls(
            program.statements,
            procedures,
        )
        resolved_procedures: dict[str, ResolvedProcedure] = {}
        for normalized_name in procedure_order:
            symbol = procedures[normalized_name]
            self.required_variables = set()
            procedure_variables = dict(variables)
            procedure_variables.update(
                (parameter.name.lower(), parameter)
                for parameter in symbol.parameters
            )
            body, assigned_variables = self._resolve_statements(
                symbol.declaration.body,
                constants,
                procedure_variables,
                {parameter.name.lower() for parameter in symbol.parameters},
                inside_conditional=False,
                loop_depth=0,
                protected_control_variables=frozenset(),
                inside_procedure=True,
            )
            required_variables = frozenset(self.required_variables)
            resolved_procedure = ResolvedProcedure(
                symbol.declaration.name,
                symbol.label,
                body,
                symbol.parameters,
            )
            self.procedure_summaries[normalized_name] = ProcedureSummary(
                required_variables,
                frozenset(
                    (assigned_variables | required_variables)
                    & variables.keys()
                ),
                resolved_procedure,
            )
            resolved_procedures[normalized_name] = resolved_procedure

        self.required_variables = None
        resolved_statements, _ = self._resolve_statements(
            program.statements,
            constants,
            variables,
            set(),
            inside_conditional=False,
            loop_depth=0,
            protected_control_variables=frozenset(),
            inside_procedure=False,
        )

        self._validate_program_structure(program)
        return ResolvedProgram(
            program.name,
            tuple(resolved_variables),
            tuple(
                resolved_procedures[declaration.name.lower()]
                for declaration in program.procedures
            ),
            resolved_statements,
        )

    def _resolve_statements(
        self,
        statements: tuple[
            Assignment
            | SetBackgroundColor
            | Run
            | IfStatement
            | WhileStatement
            | RepeatStatement
            | BreakStatement
            | ContinueStatement
            | IncrementStatement
            | DecrementStatement
            | ForStatement
            | ProcedureCall,
            ...,
        ],
        constants: dict[str, TypedConstant],
        variables: dict[str, ResolvedVariable],
        assigned_variables: set[str],
        inside_conditional: bool,
        loop_depth: int,
        protected_control_variables: frozenset[str],
        inside_procedure: bool,
    ) -> tuple[tuple[ResolvedStatement, ...], set[str]]:
        current_assignments = set(assigned_variables)
        resolved_statements: list[ResolvedStatement] = []
        for statement in statements:
            if isinstance(statement, Assignment):
                self._reject_control_variable_modification(
                    statement.target,
                    statement.target_position,
                    protected_control_variables,
                )
                resolved = self._resolve_assignment(
                    statement,
                    constants,
                    variables,
                    current_assignments,
                )
                resolved_statements.append(resolved)
                current_assignments.add(statement.target.lower())
            elif isinstance(statement, IfStatement):
                condition = self._resolve_value(
                    statement.condition,
                    BuiltInType.BOOLEAN,
                    constants,
                    variables,
                    current_assignments,
                )
                then_branch, then_assignments = self._resolve_statements(
                    statement.then_branch,
                    constants,
                    variables,
                    current_assignments,
                    inside_conditional=True,
                    loop_depth=loop_depth,
                    protected_control_variables=protected_control_variables,
                    inside_procedure=inside_procedure,
                )
                resolved_else = None
                if statement.else_branch is not None:
                    resolved_else, else_assignments = self._resolve_statements(
                        statement.else_branch,
                        constants,
                        variables,
                        current_assignments,
                        inside_conditional=True,
                        loop_depth=loop_depth,
                        protected_control_variables=protected_control_variables,
                        inside_procedure=inside_procedure,
                    )
                    current_assignments = (
                        then_assignments & else_assignments
                    )
                resolved_statements.append(
                    ResolvedIfStatement(
                        condition,
                        then_branch,
                        resolved_else,
                    )
                )
            elif isinstance(statement, WhileStatement):
                condition = self._resolve_value(
                    statement.condition,
                    BuiltInType.BOOLEAN,
                    constants,
                    variables,
                    current_assignments,
                )
                body, _ = self._resolve_statements(
                    statement.body,
                    constants,
                    variables,
                    current_assignments,
                    inside_conditional=inside_conditional,
                    loop_depth=loop_depth + 1,
                    protected_control_variables=protected_control_variables,
                    inside_procedure=inside_procedure,
                )
                resolved_statements.append(
                    ResolvedWhileStatement(condition, body)
                )
            elif isinstance(statement, RepeatStatement):
                body, _ = self._resolve_statements(
                    statement.body,
                    constants,
                    variables,
                    current_assignments,
                    inside_conditional=inside_conditional,
                    loop_depth=loop_depth + 1,
                    protected_control_variables=protected_control_variables,
                    inside_procedure=inside_procedure,
                )
                condition = self._resolve_value(
                    statement.condition,
                    BuiltInType.BOOLEAN,
                    constants,
                    variables,
                    current_assignments,
                )
                resolved_statements.append(
                    ResolvedRepeatStatement(body, condition)
                )
            elif isinstance(
                statement,
                (IncrementStatement, DecrementStatement),
            ):
                self._reject_control_variable_modification(
                    statement.target,
                    statement.target_position,
                    protected_control_variables,
                )
                target = self._resolve_update_target(
                    statement.target,
                    statement.target_position,
                    constants,
                    variables,
                    current_assignments,
                )
                amount = (
                    self._resolve_value(
                        statement.amount,
                        BuiltInType.BYTE,
                        constants,
                        variables,
                        current_assignments,
                    )
                    if statement.amount is not None
                    else None
                )
                if isinstance(statement, IncrementStatement):
                    resolved_statements.append(
                        ResolvedIncrementStatement(target, amount)
                    )
                else:
                    resolved_statements.append(
                        ResolvedDecrementStatement(target, amount)
                    )
            elif isinstance(statement, ForStatement):
                normalized_target = statement.target.lower()
                self._reject_control_variable_modification(
                    statement.target,
                    statement.target_position,
                    protected_control_variables,
                )
                target = self._resolve_for_target(
                    statement.target,
                    statement.target_position,
                    constants,
                    variables,
                )
                initial = self._resolve_value(
                    statement.initial,
                    BuiltInType.BYTE,
                    constants,
                    variables,
                    current_assignments,
                )
                assignments_with_control = {
                    *current_assignments,
                    normalized_target,
                }
                final = self._resolve_value(
                    statement.final,
                    BuiltInType.BYTE,
                    constants,
                    variables,
                    assignments_with_control,
                )
                body, _ = self._resolve_statements(
                    statement.body,
                    constants,
                    variables,
                    assignments_with_control,
                    inside_conditional=inside_conditional,
                    loop_depth=loop_depth + 1,
                    protected_control_variables=(
                        protected_control_variables | {normalized_target}
                    ),
                    inside_procedure=inside_procedure,
                )
                resolved_statements.append(
                    ResolvedForStatement(
                        target,
                        initial,
                        final,
                        statement.direction,
                        body,
                    )
                )
                current_assignments.add(normalized_target)
            elif isinstance(statement, ProcedureCall):
                summary = self.procedure_summaries[statement.name.lower()]
                parameters = summary.procedure.parameters
                if len(statement.arguments) != len(parameters):
                    expected_count = len(parameters)
                    actual_count = len(statement.arguments)
                    self._error(
                        statement.position,
                        DiagnosticCode.PROCEDURE_ARGUMENT_COUNT,
                        f"Procedure {statement.name} expects "
                        f"{expected_count} argument(s), but {actual_count} "
                        "were provided.",
                        f"Pass exactly {expected_count} argument(s) to "
                        f"{statement.name}.",
                        len(statement.name),
                    )
                resolved_arguments = tuple(
                    ResolvedArgument(
                        parameter,
                        self._resolve_value(
                            argument,
                            parameter.type,
                            constants,
                            variables,
                            current_assignments,
                        ),
                    )
                    for argument, parameter in zip(
                        statement.arguments,
                        parameters,
                    )
                )
                missing_variables = (
                    summary.required_variables - current_assignments
                )
                if missing_variables and self.required_variables is None:
                    normalized_variable = sorted(missing_variables)[0]
                    variable = variables[normalized_variable]
                    self._error(
                        statement.position,
                        DiagnosticCode.VARIABLE_READ_BEFORE_ASSIGNMENT,
                        f"Procedure {statement.name} requires variable "
                        f"{variable.name} to be assigned before the call.",
                        f"Assign {variable.name} before calling "
                        f"{statement.name}.",
                        len(statement.name),
                    )
                if self.required_variables is not None:
                    self.required_variables.update(missing_variables)
                current_assignments.update(missing_variables)
                current_assignments.update(summary.assigned_variables)
                resolved_statements.append(
                    ResolvedProcedureCall(
                        summary.procedure.name,
                        summary.procedure.label,
                        resolved_arguments,
                    )
                )
            elif isinstance(statement, (BreakStatement, ContinueStatement)):
                if loop_depth == 0:
                    self._error(
                        statement.position,
                        DiagnosticCode.LOOP_CONTROL_OUTSIDE_LOOP,
                        f"{type(statement).__name__.removesuffix('Statement').lower()} "
                        "can appear only inside a loop.",
                        "Move the statement inside a while, repeat, or for loop.",
                    )
                if isinstance(statement, BreakStatement):
                    resolved_statements.append(ResolvedBreakStatement())
                else:
                    resolved_statements.append(ResolvedContinueStatement())
            elif isinstance(statement, SetBackgroundColor):
                if inside_procedure:
                    self._procedure_runtime_command_error(
                        statement.position,
                        "nes.set_background_color",
                    )
                if loop_depth > 0:
                    self._loop_runtime_command_error(
                        statement.position,
                        "nes.set_background_color",
                    )
                if inside_conditional:
                    self._conditional_runtime_command_error(
                        statement.position,
                        "nes.set_background_color",
                    )
                resolved_statements.append(
                    ResolvedSetBackgroundColor(
                        self._resolve_value(
                            statement.argument,
                            BuiltInType.NES_COLOR,
                            constants,
                            variables,
                            current_assignments,
                        )
                    )
                )
            else:
                assert isinstance(statement, Run)
                if inside_procedure:
                    self._procedure_runtime_command_error(
                        statement.position,
                        "nes.run",
                    )
                if loop_depth > 0:
                    self._loop_runtime_command_error(
                        statement.position,
                        "nes.run",
                    )
                if inside_conditional:
                    self._conditional_runtime_command_error(
                        statement.position,
                        "nes.run",
                    )
                resolved_statements.append(Run())

        return (
            tuple(resolved_statements),
            current_assignments,
        )

    def _procedure_resolution_order(
        self,
        declarations: tuple[ProcedureDeclaration, ...],
        procedures: dict[str, ProcedureSymbol],
    ) -> list[str]:
        calls_by_procedure: dict[str, tuple[ProcedureCall, ...]] = {}
        for declaration in declarations:
            normalized_name = declaration.name.lower()
            calls = tuple(self._procedure_calls(declaration.body))
            self._validate_known_procedure_calls(
                declaration.body,
                procedures,
            )
            calls_by_procedure[normalized_name] = calls

        states: dict[str, int] = {}
        order: list[str] = []

        def visit(normalized_name: str) -> None:
            states[normalized_name] = 1
            for call in calls_by_procedure[normalized_name]:
                callee_name = call.name.lower()
                callee_state = states.get(callee_name, 0)
                if callee_state == 1:
                    self._error(
                        call.position,
                        DiagnosticCode.RECURSIVE_PROCEDURE_CALL,
                        f"Recursive procedure call involving "
                        f"{call.name} is not supported.",
                        "Remove the direct or indirect recursive call.",
                        len(call.name),
                    )
                if callee_state == 0:
                    visit(callee_name)
            states[normalized_name] = 2
            order.append(normalized_name)

        for declaration in declarations:
            normalized_name = declaration.name.lower()
            if states.get(normalized_name, 0) == 0:
                visit(normalized_name)
        return order

    def _validate_known_procedure_calls(
        self,
        statements: tuple[Statement, ...],
        procedures: dict[str, ProcedureSymbol],
    ) -> None:
        for call in self._procedure_calls(statements):
            if call.name.lower() in procedures:
                continue
            self._error(
                call.position,
                DiagnosticCode.UNKNOWN_PROCEDURE,
                f"Unknown procedure: {call.name}.",
                "Declare the procedure before the main program block.",
                len(call.name),
            )

    def _procedure_calls(
        self,
        statements: tuple[Statement, ...],
    ) -> list[ProcedureCall]:
        calls: list[ProcedureCall] = []
        for statement in statements:
            if isinstance(statement, ProcedureCall):
                calls.append(statement)
            elif isinstance(statement, IfStatement):
                calls.extend(self._procedure_calls(statement.then_branch))
                if statement.else_branch is not None:
                    calls.extend(
                        self._procedure_calls(statement.else_branch)
                    )
            elif isinstance(
                statement,
                (WhileStatement, RepeatStatement, ForStatement),
            ):
                calls.extend(self._procedure_calls(statement.body))
        return calls

    def _procedure_runtime_command_error(
        self,
        position: SourcePosition | None,
        command: str,
    ) -> None:
        assert position is not None
        self._error(
            position,
            DiagnosticCode.PROCEDURE_RUNTIME_COMMAND,
            f"{command} cannot appear inside a procedure.",
            "Move the NES runtime command to the main program block.",
            len(command),
        )

    def _loop_runtime_command_error(
        self,
        position: SourcePosition | None,
        command: str,
    ) -> None:
        assert position is not None
        self._error(
            position,
            DiagnosticCode.LOOP_RUNTIME_COMMAND,
            f"{command} cannot appear inside a loop body.",
            "Move the NES runtime command to the top-level program block.",
            len(command),
        )

    def _conditional_runtime_command_error(
        self,
        position: SourcePosition | None,
        command: str,
    ) -> None:
        assert position is not None
        self._error(
            position,
            DiagnosticCode.CONDITIONAL_RUNTIME_COMMAND,
            f"{command} cannot appear inside a conditional branch.",
            "Move the NES runtime command to the top-level program block.",
            len(command),
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
            "Use a unique name in the current scope.",
        )

    def _reject_control_variable_modification(
        self,
        name: str,
        position: SourcePosition,
        protected_control_variables: frozenset[str],
    ) -> None:
        if name.lower() not in protected_control_variables:
            return
        self._error(
            position,
            DiagnosticCode.FOR_CONTROL_VARIABLE_MODIFICATION,
            f"For control variable {name} cannot be modified inside its loop body.",
            "Remove the assignment or update the value after the for loop.",
            len(name),
        )

    def _resolve_update_target(
        self,
        name: str,
        position: SourcePosition,
        constants: dict[str, TypedConstant],
        variables: dict[str, ResolvedVariable],
        assigned_variables: set[str],
    ) -> ResolvedVariable:
        target = self._resolve_mutable_target(
            name,
            position,
            constants,
            variables,
        )
        self._require_byte_target(target, position, "Increment and decrement")
        if name.lower() not in assigned_variables:
            if self.required_variables is not None:
                self.required_variables.add(name.lower())
                assigned_variables.add(name.lower())
            else:
                self._error(
                    position,
                    DiagnosticCode.VARIABLE_READ_BEFORE_ASSIGNMENT,
                    f"Variable {name} is read before it is assigned.",
                    "Assign a value to the variable before updating it.",
                    len(name),
                )
        return target

    def _resolve_for_target(
        self,
        name: str,
        position: SourcePosition,
        constants: dict[str, TypedConstant],
        variables: dict[str, ResolvedVariable],
    ) -> ResolvedVariable:
        target = self._resolve_mutable_target(
            name,
            position,
            constants,
            variables,
        )
        self._require_byte_target(target, position, "A for control variable")
        return target

    def _resolve_mutable_target(
        self,
        name: str,
        position: SourcePosition,
        constants: dict[str, TypedConstant],
        variables: dict[str, ResolvedVariable],
    ) -> ResolvedVariable:
        normalized_name = name.lower()
        target = variables.get(normalized_name)
        if target is not None:
            return target
        if normalized_name in constants:
            self._error(
                position,
                DiagnosticCode.ASSIGNMENT_TO_CONSTANT,
                f"Cannot assign to constant {name}.",
                "Use a variable as the target.",
                len(name),
            )
        self._error(
            position,
            DiagnosticCode.UNKNOWN_ASSIGNMENT_TARGET,
            f"Unknown variable: {name}.",
            "Declare the variable in the var section before using it.",
            len(name),
        )
        raise AssertionError("unreachable")

    def _require_byte_target(
        self,
        target: ResolvedVariable,
        position: SourcePosition,
        description: str,
    ) -> None:
        if target.type is BuiltInType.BYTE:
            return
        self._error(
            position,
            DiagnosticCode.INCOMPATIBLE_TYPES,
            f"{description} must have type byte, but {target.name} has type "
            f"{target.type.value}.",
            "Use a variable declared as byte.",
            len(target.name),
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
        if isinstance(
            expression,
            (BooleanNotExpression, BooleanBinaryExpression),
        ):
            return self._resolve_boolean_expression(
                expression,
                expected_type,
                constants,
                variables,
                assigned_variables,
                assignment_target,
            )
        if isinstance(expression, ComparisonExpression):
            return self._resolve_comparison_expression(
                expression,
                expected_type,
                constants,
                variables,
                assigned_variables,
                assignment_target,
            )
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
            if self.required_variables is not None:
                self.required_variables.add(normalized_name)
                assigned_variables.add(normalized_name)
            else:
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

    def _resolve_boolean_expression(
        self,
        expression: BooleanNotExpression | BooleanBinaryExpression,
        expected_type: BuiltInType,
        constants: dict[str, TypedConstant],
        variables: dict[str, ResolvedVariable],
        assigned_variables: set[str],
        assignment_target: ResolvedVariable | None,
    ) -> ResolvedValue:
        self._require_expression_result_type(
            expression.position,
            BuiltInType.BOOLEAN,
            expected_type,
            "Boolean expression",
            assignment_target,
        )
        if isinstance(expression, BooleanNotExpression):
            operand = self._resolve_value(
                expression.operand,
                BuiltInType.BOOLEAN,
                constants,
                variables,
                assigned_variables,
            )
            return ResolvedBooleanNotExpression(operand)

        left = self._resolve_value(
            expression.left,
            BuiltInType.BOOLEAN,
            constants,
            variables,
            assigned_variables,
        )
        right = self._resolve_value(
            expression.right,
            BuiltInType.BOOLEAN,
            constants,
            variables,
            assigned_variables,
        )
        return ResolvedBooleanBinaryExpression(left, expression.operator, right)

    def _resolve_comparison_expression(
        self,
        expression: ComparisonExpression,
        expected_type: BuiltInType,
        constants: dict[str, TypedConstant],
        variables: dict[str, ResolvedVariable],
        assigned_variables: set[str],
        assignment_target: ResolvedVariable | None,
    ) -> ResolvedValue:
        self._require_expression_result_type(
            expression.position,
            BuiltInType.BOOLEAN,
            expected_type,
            "Comparison expression",
            assignment_target,
        )
        ordered_operators = {
            ComparisonOperator.LESS,
            ComparisonOperator.GREATER,
            ComparisonOperator.LESS_EQUAL,
            ComparisonOperator.GREATER_EQUAL,
        }
        if expression.operator in ordered_operators:
            operand_type = BuiltInType.BYTE
        else:
            left_type = self._expression_type_hint(
                expression.left,
                constants,
                variables,
            )
            right_type = self._expression_type_hint(
                expression.right,
                constants,
                variables,
            )
            if (
                left_type is not None
                and right_type is not None
                and left_type is not right_type
            ):
                self._error(
                    expression.position,
                    DiagnosticCode.INCOMPATIBLE_TYPES,
                    "Comparison operands must have exactly the same type, but "
                    f"the left operand has type {left_type.value} and the right "
                    f"operand has type {right_type.value}.",
                    "Compare values with exactly matching types.",
                    len(expression.operator.value),
                )
            operand_type = left_type or right_type or BuiltInType.BYTE

        left = self._resolve_value(
            expression.left,
            operand_type,
            constants,
            variables,
            assigned_variables,
        )
        right = self._resolve_value(
            expression.right,
            operand_type,
            constants,
            variables,
            assigned_variables,
        )
        return ResolvedComparisonExpression(left, expression.operator, right)

    def _expression_type_hint(
        self,
        expression: ValueExpression,
        constants: dict[str, TypedConstant],
        variables: dict[str, ResolvedVariable],
    ) -> BuiltInType | None:
        if isinstance(
            expression,
            (
                BooleanLiteral,
                BooleanNotExpression,
                BooleanBinaryExpression,
                ComparisonExpression,
            ),
        ):
            return BuiltInType.BOOLEAN
        if isinstance(expression, (UnaryExpression, BinaryExpression)):
            return BuiltInType.BYTE
        if isinstance(expression, HexLiteral):
            return None
        assert isinstance(expression, (ConstantReference, VariableReference))
        constant = constants.get(expression.name.lower())
        if constant is not None:
            return constant.type
        variable = variables.get(expression.name.lower())
        return variable.type if variable is not None else None

    def _require_expression_result_type(
        self,
        position: SourcePosition,
        actual_type: BuiltInType,
        expected_type: BuiltInType,
        description: str,
        assignment_target: ResolvedVariable | None,
    ) -> None:
        if actual_type is expected_type:
            return
        if assignment_target is not None:
            self._error(
                position,
                DiagnosticCode.INCOMPATIBLE_TYPES,
                f"Cannot assign a {description.lower()} of type "
                f"{actual_type.value} to variable {assignment_target.name} "
                f"of type {assignment_target.type.value}.",
                "The expression and target types must match.",
            )
        self._error(
            position,
            DiagnosticCode.INCOMPATIBLE_TYPES,
            f"{description} has type {actual_type.value}, but "
            f"{expected_type.value} is required.",
            "Use the expression only where a boolean value is expected.",
        )

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
        statement: (
            Assignment
            | SetBackgroundColor
            | Run
            | IfStatement
            | WhileStatement
            | RepeatStatement
            | BreakStatement
            | ContinueStatement
            | IncrementStatement
            | DecrementStatement
            | ForStatement
        ),
        program: Program,
    ) -> SourcePosition:
        if isinstance(statement, Assignment):
            return statement.target_position
        if isinstance(statement, IfStatement):
            return statement.position
        if isinstance(
            statement,
            (
                WhileStatement,
                RepeatStatement,
                BreakStatement,
                ContinueStatement,
                IncrementStatement,
                DecrementStatement,
                ForStatement,
                ProcedureCall,
            ),
        ):
            return statement.position
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
