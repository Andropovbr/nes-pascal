"""AST nodes supported by the current language milestone."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


@dataclass(frozen=True, slots=True)
class SourcePosition:
    line: int
    column: int


class BuiltInType(Enum):
    NES_COLOR = "nes_color"
    BYTE = "byte"
    BOOLEAN = "boolean"


class UnaryOperator(Enum):
    PLUS = "+"
    NEGATE = "-"


class BinaryOperator(Enum):
    ADD = "+"
    SUBTRACT = "-"


class ComparisonOperator(Enum):
    EQUAL = "="
    NOT_EQUAL = "<>"
    LESS = "<"
    GREATER = ">"
    LESS_EQUAL = "<="
    GREATER_EQUAL = ">="


class BooleanOperator(Enum):
    AND = "and"
    OR = "or"


@dataclass(frozen=True, slots=True)
class HexLiteral:
    value: int
    text: str
    position: SourcePosition


@dataclass(frozen=True, slots=True)
class BooleanLiteral:
    value: bool
    text: str
    position: SourcePosition


Literal = HexLiteral | BooleanLiteral


@dataclass(frozen=True, slots=True)
class ConstantDeclaration:
    name: str
    type: BuiltInType
    value: Literal
    position: SourcePosition


@dataclass(frozen=True, slots=True)
class VariableDeclaration:
    name: str
    type: BuiltInType
    position: SourcePosition


@dataclass(frozen=True, slots=True)
class ConstantReference:
    name: str
    position: SourcePosition


@dataclass(frozen=True, slots=True)
class VariableReference:
    name: str
    position: SourcePosition


@dataclass(frozen=True, slots=True)
class UnaryExpression:
    operator: UnaryOperator
    operand: ValueExpression
    position: SourcePosition


@dataclass(frozen=True, slots=True)
class BinaryExpression:
    left: ValueExpression
    operator: BinaryOperator
    right: ValueExpression
    position: SourcePosition


@dataclass(frozen=True, slots=True)
class ComparisonExpression:
    left: ValueExpression
    operator: ComparisonOperator
    right: ValueExpression
    position: SourcePosition


@dataclass(frozen=True, slots=True)
class BooleanNotExpression:
    operand: ValueExpression
    position: SourcePosition


@dataclass(frozen=True, slots=True)
class BooleanBinaryExpression:
    left: ValueExpression
    operator: BooleanOperator
    right: ValueExpression
    position: SourcePosition


ValueExpression = (
    HexLiteral
    | BooleanLiteral
    | ConstantReference
    | VariableReference
    | UnaryExpression
    | BinaryExpression
    | ComparisonExpression
    | BooleanNotExpression
    | BooleanBinaryExpression
)


@dataclass(frozen=True, slots=True)
class Assignment:
    target: str
    target_position: SourcePosition
    value: ValueExpression


@dataclass(frozen=True, slots=True)
class SetBackgroundColor:
    argument: ValueExpression
    position: SourcePosition | None = field(default=None, compare=False)


@dataclass(frozen=True, slots=True)
class Run:
    position: SourcePosition | None = field(default=None, compare=False)


@dataclass(frozen=True, slots=True)
class IfStatement:
    condition: ValueExpression
    then_branch: tuple[Statement, ...]
    else_branch: tuple[Statement, ...] | None
    position: SourcePosition


@dataclass(frozen=True, slots=True)
class WhileStatement:
    condition: ValueExpression
    body: tuple[Statement, ...]
    position: SourcePosition


@dataclass(frozen=True, slots=True)
class RepeatStatement:
    body: tuple[Statement, ...]
    condition: ValueExpression
    position: SourcePosition


@dataclass(frozen=True, slots=True)
class BreakStatement:
    position: SourcePosition


@dataclass(frozen=True, slots=True)
class ContinueStatement:
    position: SourcePosition


Statement = (
    Assignment
    | SetBackgroundColor
    | Run
    | IfStatement
    | WhileStatement
    | RepeatStatement
    | BreakStatement
    | ContinueStatement
)


@dataclass(frozen=True, slots=True)
class Program:
    name: str
    constants: tuple[ConstantDeclaration, ...]
    variables: tuple[VariableDeclaration, ...]
    statements: tuple[Statement, ...]
    end_position: SourcePosition | None = field(default=None, compare=False)


@dataclass(frozen=True, slots=True)
class ResolvedVariable:
    name: str
    type: BuiltInType
    label: str


@dataclass(frozen=True, slots=True)
class ImmediateValue:
    value: int
    type: BuiltInType


@dataclass(frozen=True, slots=True)
class VariableValue:
    variable: ResolvedVariable


@dataclass(frozen=True, slots=True)
class ResolvedUnaryExpression:
    operator: UnaryOperator
    operand: ResolvedValue


@dataclass(frozen=True, slots=True)
class ResolvedBinaryExpression:
    left: ResolvedValue
    operator: BinaryOperator
    right: ResolvedValue


@dataclass(frozen=True, slots=True)
class ResolvedComparisonExpression:
    left: ResolvedValue
    operator: ComparisonOperator
    right: ResolvedValue


@dataclass(frozen=True, slots=True)
class ResolvedBooleanNotExpression:
    operand: ResolvedValue


@dataclass(frozen=True, slots=True)
class ResolvedBooleanBinaryExpression:
    left: ResolvedValue
    operator: BooleanOperator
    right: ResolvedValue


ResolvedValue = (
    ImmediateValue
    | VariableValue
    | ResolvedUnaryExpression
    | ResolvedBinaryExpression
    | ResolvedComparisonExpression
    | ResolvedBooleanNotExpression
    | ResolvedBooleanBinaryExpression
)


@dataclass(frozen=True, slots=True)
class ResolvedAssignment:
    target: ResolvedVariable
    value: ResolvedValue


@dataclass(frozen=True, slots=True)
class ResolvedSetBackgroundColor:
    argument: ResolvedValue


@dataclass(frozen=True, slots=True)
class ResolvedIfStatement:
    condition: ResolvedValue
    then_branch: tuple[ResolvedStatement, ...]
    else_branch: tuple[ResolvedStatement, ...] | None


@dataclass(frozen=True, slots=True)
class ResolvedWhileStatement:
    condition: ResolvedValue
    body: tuple[ResolvedStatement, ...]


@dataclass(frozen=True, slots=True)
class ResolvedRepeatStatement:
    body: tuple[ResolvedStatement, ...]
    condition: ResolvedValue


@dataclass(frozen=True, slots=True)
class ResolvedBreakStatement:
    pass


@dataclass(frozen=True, slots=True)
class ResolvedContinueStatement:
    pass


ResolvedStatement = (
    ResolvedAssignment
    | ResolvedSetBackgroundColor
    | Run
    | ResolvedIfStatement
    | ResolvedWhileStatement
    | ResolvedRepeatStatement
    | ResolvedBreakStatement
    | ResolvedContinueStatement
)


@dataclass(frozen=True, slots=True)
class ResolvedProgram:
    name: str
    variables: tuple[ResolvedVariable, ...]
    statements: tuple[ResolvedStatement, ...]
