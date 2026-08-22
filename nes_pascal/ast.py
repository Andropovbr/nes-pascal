"""AST nodes supported by the current language milestone."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .builtins import BuiltinId


@dataclass(frozen=True, slots=True)
class SourcePosition:
    line: int
    column: int


class BuiltInType(Enum):
    NES_COLOR = "nes_color"
    BYTE = "byte"
    BOOLEAN = "boolean"
    SPRITE = "sprite"
    METASPRITE = "metasprite"
    METASPRITE_FRAME = "metasprite_frame"
    METASPRITE_ANIMATION = "metasprite_animation"


@dataclass(frozen=True, slots=True, eq=False)
class EnumType:
    """A nominal, byte-sized user-defined enumeration type."""

    name: str
    members: tuple[str, ...]

    @property
    def value(self) -> str:
        return self.name


ScalarType = BuiltInType | EnumType


@dataclass(frozen=True, slots=True)
class NamedTypeReference:
    """A parsed user type name awaiting semantic resolution."""

    name: str
    position: SourcePosition

    @property
    def value(self) -> str:
        return self.name


@dataclass(frozen=True, slots=True)
class RecordField:
    """One resolved byte-sized field in a fixed-layout record."""

    name: str
    type: ScalarType
    offset: int
    position: SourcePosition | None = field(default=None, compare=False)


@dataclass(frozen=True, slots=True, eq=False)
class RecordType:
    """A nominal, compile-time-laid-out user-defined record type."""

    name: str
    fields: tuple[RecordField, ...]
    size: int

    @property
    def value(self) -> str:
        return self.name

    def field_named(self, name: str) -> RecordField | None:
        normalized = name.lower()
        return next(
            (field for field in self.fields if field.name.lower() == normalized),
            None,
        )


# Public collision rectangles use the ordinary record implementation.  Keeping
# one canonical nominal instance lets builtin signatures remain strongly typed
# without adding a collision-specific scalar or runtime object representation.
NES_RECT_TYPE = RecordType(
    "nes_rect",
    (
        RecordField("X", BuiltInType.BYTE, 0),
        RecordField("Y", BuiltInType.BYTE, 1),
        RecordField("Width", BuiltInType.BYTE, 2),
        RecordField("Height", BuiltInType.BYTE, 3),
    ),
    4,
)


@dataclass(frozen=True, slots=True)
class ArrayType:
    """A fixed-size, zero-based global array type."""

    element_type: ScalarType | RecordType | NamedTypeReference
    lower_bound: int
    upper_bound: int
    position: SourcePosition | None = field(default=None, compare=False)
    lower_bound_position: SourcePosition | None = field(default=None, compare=False)
    upper_bound_position: SourcePosition | None = field(default=None, compare=False)
    element_type_position: SourcePosition | None = field(default=None, compare=False)

    @property
    def element_count(self) -> int:
        return self.upper_bound - self.lower_bound + 1

    @property
    def value(self) -> str:
        return (
            f"array[${self.lower_bound:02X}..${self.upper_bound:02X}] "
            f"of {self.element_type.value}"
        )


VariableType = ScalarType | RecordType | NamedTypeReference | ArrayType


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


class CallbackKind(Enum):
    UPDATE = "update"
    VBLANK = "vblank"


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
class EnumMember:
    name: str
    position: SourcePosition


@dataclass(frozen=True, slots=True)
class EnumTypeDeclaration:
    type: EnumType
    members: tuple[EnumMember, ...]
    position: SourcePosition


@dataclass(frozen=True, slots=True)
class RecordFieldDeclaration:
    name: str
    type: VariableType
    position: SourcePosition
    type_position: SourcePosition


@dataclass(frozen=True, slots=True)
class RecordTypeDeclaration:
    name: str
    fields: tuple[RecordFieldDeclaration, ...]
    position: SourcePosition


@dataclass(frozen=True, slots=True)
class VariableDeclaration:
    name: str
    type: VariableType
    position: SourcePosition


@dataclass(frozen=True, slots=True)
class ProcedureParameter:
    name: str
    type: BuiltInType
    position: SourcePosition
    type_position: SourcePosition | None = field(default=None, compare=False)


@dataclass(frozen=True, slots=True)
class ConstantReference:
    name: str
    position: SourcePosition


@dataclass(frozen=True, slots=True)
class VariableReference:
    name: str
    position: SourcePosition


@dataclass(frozen=True, slots=True)
class ArrayIndexExpression:
    array_name: str
    index: ValueExpression
    position: SourcePosition


@dataclass(frozen=True, slots=True)
class RecordFieldExpression:
    record_name: str
    field_name: str
    position: SourcePosition
    field_position: SourcePosition
    index: ValueExpression | None = None


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


@dataclass(frozen=True, slots=True)
class BuiltinCall:
    name: str
    arguments: tuple[ValueExpression, ...]
    position: SourcePosition


@dataclass(frozen=True, slots=True)
class FunctionCall:
    name: str
    arguments: tuple[ValueExpression, ...]
    position: SourcePosition


ValueExpression = (
    HexLiteral
    | BooleanLiteral
    | ConstantReference
    | VariableReference
    | ArrayIndexExpression
    | RecordFieldExpression
    | UnaryExpression
    | BinaryExpression
    | ComparisonExpression
    | BooleanNotExpression
    | BooleanBinaryExpression
    | BuiltinCall
    | FunctionCall
)


@dataclass(frozen=True, slots=True)
class Assignment:
    target: str
    target_position: SourcePosition
    value: ValueExpression


@dataclass(frozen=True, slots=True)
class ArrayElementAssignment:
    target: str
    target_position: SourcePosition
    index: ValueExpression
    value: ValueExpression


@dataclass(frozen=True, slots=True)
class RecordFieldAssignment:
    target: str
    field_name: str
    target_position: SourcePosition
    field_position: SourcePosition
    value: ValueExpression
    index: ValueExpression | None = None


@dataclass(frozen=True, slots=True)
class LoadBackground:
    arguments: tuple[ValueExpression, ...]
    position: SourcePosition


@dataclass(frozen=True, slots=True)
class Run:
    position: SourcePosition | None = field(default=None, compare=False)


@dataclass(frozen=True, slots=True)
class CallbackRegistration:
    kind: CallbackKind
    procedure_name: str
    position: SourcePosition
    procedure_position: SourcePosition


@dataclass(frozen=True, slots=True)
class ImportMetasprite:
    arguments: tuple[ValueExpression, ...]
    position: SourcePosition


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


@dataclass(frozen=True, slots=True)
class IncrementStatement:
    target: str
    target_position: SourcePosition
    amount: ValueExpression | None
    position: SourcePosition


@dataclass(frozen=True, slots=True)
class DecrementStatement:
    target: str
    target_position: SourcePosition
    amount: ValueExpression | None
    position: SourcePosition


class ForDirection(Enum):
    TO = "to"
    DOWNTO = "downto"


@dataclass(frozen=True, slots=True)
class ForStatement:
    target: str
    target_position: SourcePosition
    initial: ValueExpression
    final: ValueExpression
    direction: ForDirection
    body: tuple[Statement, ...]
    position: SourcePosition


@dataclass(frozen=True, slots=True)
class ProcedureCall:
    name: str
    position: SourcePosition
    arguments: tuple[ValueExpression, ...] = ()


Statement = (
    Assignment
    | ArrayElementAssignment
    | RecordFieldAssignment
    | BuiltinCall
    | LoadBackground
    | Run
    | CallbackRegistration
    | ImportMetasprite
    | IfStatement
    | WhileStatement
    | RepeatStatement
    | BreakStatement
    | ContinueStatement
    | IncrementStatement
    | DecrementStatement
    | ForStatement
    | ProcedureCall
)


@dataclass(frozen=True, slots=True)
class ProcedureDeclaration:
    name: str
    body: tuple[Statement, ...]
    position: SourcePosition
    parameters: tuple[ProcedureParameter, ...] = ()


@dataclass(frozen=True, slots=True)
class FunctionDeclaration:
    name: str
    body: tuple[Statement, ...]
    position: SourcePosition
    return_type: VariableType
    return_type_position: SourcePosition
    parameters: tuple[ProcedureParameter, ...] = ()


@dataclass(frozen=True, slots=True)
class Program:
    name: str
    enum_types: tuple[EnumTypeDeclaration, ...]
    record_types: tuple[RecordTypeDeclaration, ...]
    constants: tuple[ConstantDeclaration, ...]
    variables: tuple[VariableDeclaration, ...]
    procedures: tuple[ProcedureDeclaration, ...]
    functions: tuple[FunctionDeclaration, ...]
    statements: tuple[Statement, ...]
    end_position: SourcePosition | None = field(default=None, compare=False)


@dataclass(frozen=True, slots=True)
class ResolvedVariable:
    name: str
    type: VariableType
    label: str
    position: SourcePosition | None = field(default=None, compare=False)


@dataclass(frozen=True, slots=True)
class ImmediateValue:
    value: int
    type: ScalarType


@dataclass(frozen=True, slots=True)
class VariableValue:
    variable: ResolvedVariable


@dataclass(frozen=True, slots=True)
class ResolvedArrayElement:
    array: ResolvedVariable
    index: ResolvedValue


@dataclass(frozen=True, slots=True)
class ResolvedRecordField:
    variable: ResolvedVariable
    field: RecordField
    index: ResolvedValue | None = None


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


@dataclass(frozen=True, slots=True)
class ResolvedRecordReference:
    """One standalone record passed by address to a specialized builtin."""

    variable: ResolvedVariable
    output: bool = False


@dataclass(frozen=True, slots=True)
class ResolvedBuiltinCall:
    builtin: BuiltinId
    arguments: tuple[ResolvedValue | ResolvedRecordReference, ...]
    queued: bool = False


@dataclass(frozen=True, slots=True)
class ResolvedFunctionCall:
    name: str
    label: str
    arguments: tuple[ResolvedArgument, ...]
    return_type: BuiltInType


ResolvedValue = (
    ImmediateValue
    | VariableValue
    | ResolvedArrayElement
    | ResolvedRecordField
    | ResolvedUnaryExpression
    | ResolvedBinaryExpression
    | ResolvedComparisonExpression
    | ResolvedBooleanNotExpression
    | ResolvedBooleanBinaryExpression
    | ResolvedBuiltinCall
    | ResolvedFunctionCall
)


@dataclass(frozen=True, slots=True)
class ResolvedAssignment:
    target: ResolvedVariable
    value: ResolvedValue


@dataclass(frozen=True, slots=True)
class ResolvedFunctionResultAssignment:
    result: ResolvedVariable
    value: ResolvedValue


@dataclass(frozen=True, slots=True)
class ResolvedArrayElementAssignment:
    target: ResolvedVariable
    index: ResolvedValue
    value: ResolvedValue


@dataclass(frozen=True, slots=True)
class ResolvedRecordFieldAssignment:
    target: ResolvedVariable
    field: RecordField
    value: ResolvedValue
    index: ResolvedValue | None = None


@dataclass(frozen=True, slots=True)
class ResolvedLoadBackground:
    pass


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


@dataclass(frozen=True, slots=True)
class ResolvedIncrementStatement:
    target: ResolvedVariable
    amount: ResolvedValue | None


@dataclass(frozen=True, slots=True)
class ResolvedDecrementStatement:
    target: ResolvedVariable
    amount: ResolvedValue | None


@dataclass(frozen=True, slots=True)
class ResolvedForStatement:
    target: ResolvedVariable
    initial: ResolvedValue
    final: ResolvedValue
    direction: ForDirection
    body: tuple[ResolvedStatement, ...]


@dataclass(frozen=True, slots=True)
class ResolvedArgument:
    parameter: ResolvedVariable
    value: ResolvedValue


@dataclass(frozen=True, slots=True)
class ResolvedProcedureCall:
    name: str
    label: str
    arguments: tuple[ResolvedArgument, ...] = ()


@dataclass(frozen=True, slots=True)
class ResolvedCallbackRegistration:
    kind: CallbackKind
    procedure_name: str
    procedure_label: str


@dataclass(frozen=True, slots=True)
class ResolvedImportMetasprite:
    asset_name: str


@dataclass(frozen=True, slots=True)
class MetaspriteComponent:
    x_offset: int
    y_offset: int
    tile: int
    attributes: int


@dataclass(frozen=True, slots=True)
class MetaspriteFrame:
    id: int
    symbol: str
    asset_name: str
    animation_name: str
    animation_frame_index: int
    width: int
    height: int
    origin_x: int
    origin_y: int
    components: tuple[MetaspriteComponent, ...]
    collision_x_offset: int = 0
    collision_y_offset: int = 0
    collision_width: int = 0
    collision_height: int = 0
    collision_box_custom: bool = False


@dataclass(frozen=True, slots=True)
class MetaspriteAnimation:
    """Playback metadata referencing canonical MetaspriteFrame IDs only."""

    id: int
    symbol: str
    asset_name: str
    name: str
    frame_ids: tuple[int, ...]
    durations: tuple[int, ...]
    loop: bool


@dataclass(frozen=True, slots=True)
class MetaspriteAsset:
    name: str
    configured_path: str
    frames: tuple[MetaspriteFrame, ...]
    animations: tuple[MetaspriteAnimation, ...] = ()

    @property
    def maximum_component_count(self) -> int:
        return max((len(frame.components) for frame in self.frames), default=0)


@dataclass(frozen=True, slots=True)
class MetaspriteInstance:
    index: int
    asset_name: str
    initial_frame_id: int
    oam_indexes: tuple[int, ...]
    position: SourcePosition | None = field(default=None, compare=False)


class OamOwnerKind(Enum):
    """Compile-time ownership classes for physical hardware-sprite slots."""

    INDIVIDUAL_EXPLICIT = "individual_explicit"
    INDIVIDUAL_CREATED = "individual_created"
    METASPRITE_COMPONENT = "metasprite_component"


@dataclass(frozen=True, slots=True)
class OamReservation:
    index: int
    owner: OamOwnerKind
    position: SourcePosition | None = field(default=None, compare=False)
    owner_index: int | None = None
    component_index: int | None = None


ResolvedStatement = (
    ResolvedAssignment
    | ResolvedFunctionResultAssignment
    | ResolvedArrayElementAssignment
    | ResolvedRecordFieldAssignment
    | ResolvedBuiltinCall
    | ResolvedLoadBackground
    | Run
    | ResolvedCallbackRegistration
    | ResolvedImportMetasprite
    | ResolvedIfStatement
    | ResolvedWhileStatement
    | ResolvedRepeatStatement
    | ResolvedBreakStatement
    | ResolvedContinueStatement
    | ResolvedIncrementStatement
    | ResolvedDecrementStatement
    | ResolvedForStatement
    | ResolvedProcedureCall
)


@dataclass(frozen=True, slots=True)
class ResolvedProcedure:
    name: str
    label: str
    body: tuple[ResolvedStatement, ...]
    parameters: tuple[ResolvedVariable, ...] = ()


@dataclass(frozen=True, slots=True)
class ResolvedFunction:
    name: str
    label: str
    body: tuple[ResolvedStatement, ...]
    return_type: BuiltInType
    result: ResolvedVariable
    parameters: tuple[ResolvedVariable, ...] = ()


@dataclass(frozen=True, slots=True)
class ResolvedProgram:
    name: str
    variables: tuple[ResolvedVariable, ...]
    procedures: tuple[ResolvedProcedure, ...]
    functions: tuple[ResolvedFunction, ...]
    statements: tuple[ResolvedStatement, ...]
    oam_reservations: tuple[OamReservation, ...] = ()
    metasprite_assets: tuple[MetaspriteAsset, ...] = ()
    metasprite_instances: tuple[MetaspriteInstance, ...] = ()
    record_types: tuple[RecordType, ...] = ()
