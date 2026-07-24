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


ValueExpression = (
    HexLiteral
    | BooleanLiteral
    | ConstantReference
    | VariableReference
    | UnaryExpression
    | BinaryExpression
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


Statement = Assignment | SetBackgroundColor | Run


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


ResolvedValue = (
    ImmediateValue
    | VariableValue
    | ResolvedUnaryExpression
    | ResolvedBinaryExpression
)


@dataclass(frozen=True, slots=True)
class ResolvedAssignment:
    target: ResolvedVariable
    value: ResolvedValue


@dataclass(frozen=True, slots=True)
class ResolvedSetBackgroundColor:
    argument: ResolvedValue


ResolvedStatement = ResolvedAssignment | ResolvedSetBackgroundColor | Run


@dataclass(frozen=True, slots=True)
class ResolvedProgram:
    name: str
    variables: tuple[ResolvedVariable, ...]
    statements: tuple[ResolvedStatement, ...]
