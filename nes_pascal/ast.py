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
    SPRITE = "sprite"
    METASPRITE = "metasprite"
    METASPRITE_FRAME = "metasprite_frame"


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


class ControllerQueryKind(Enum):
    DOWN = "down"
    PRESSED = "pressed"
    RELEASED = "released"


class PaletteKind(Enum):
    BACKGROUND = "background"
    SPRITE = "sprite"


class SpriteOperationKind(Enum):
    SET_POSITION = "set_position"
    SET_X = "set_x"
    SET_Y = "set_y"
    SET_TILE = "set_tile"
    SET_PALETTE = "set_palette"
    SET_ATTRIBUTES = "set_attributes"
    HIDE = "hide"
    SHOW = "show"
    SET_FLIP_HORIZONTAL = "set_flip_horizontal"
    SET_FLIP_VERTICAL = "set_flip_vertical"
    SET_BEHIND_BACKGROUND = "set_behind_background"


class MetaspriteOperationKind(Enum):
    SET_POSITION = "set_position"
    SET_FRAME = "set_frame"
    HIDE = "hide"
    SHOW = "show"
    SET_FLIP_HORIZONTAL = "set_flip_horizontal"
    SET_FLIP_VERTICAL = "set_flip_vertical"


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
class ControllerQuery:
    kind: ControllerQueryKind
    arguments: tuple[ValueExpression, ...]
    position: SourcePosition


@dataclass(frozen=True, slots=True)
class SpriteCreate:
    arguments: tuple[ValueExpression, ...]
    position: SourcePosition


@dataclass(frozen=True, slots=True)
class MetaspriteCreate:
    arguments: tuple[ValueExpression, ...]
    position: SourcePosition


@dataclass(frozen=True, slots=True)
class GetTile:
    arguments: tuple[ValueExpression, ...]
    position: SourcePosition


@dataclass(frozen=True, slots=True)
class BackgroundUpdatesOverflowed:
    arguments: tuple[ValueExpression, ...]
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
    | ControllerQuery
    | SpriteCreate
    | MetaspriteCreate
    | GetTile
    | BackgroundUpdatesOverflowed
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
class SetPalette:
    kind: PaletteKind
    arguments: tuple[ValueExpression, ...]
    position: SourcePosition


@dataclass(frozen=True, slots=True)
class SetPaletteColor:
    kind: PaletteKind
    arguments: tuple[ValueExpression, ...]
    position: SourcePosition


@dataclass(frozen=True, slots=True)
class LoadBackground:
    arguments: tuple[ValueExpression, ...]
    position: SourcePosition


@dataclass(frozen=True, slots=True)
class SetTile:
    arguments: tuple[ValueExpression, ...]
    position: SourcePosition


@dataclass(frozen=True, slots=True)
class SetAttribute:
    arguments: tuple[ValueExpression, ...]
    position: SourcePosition


@dataclass(frozen=True, slots=True)
class SetScroll:
    arguments: tuple[ValueExpression, ...]
    position: SourcePosition


@dataclass(frozen=True, slots=True)
class ClearBackgroundUpdates:
    arguments: tuple[ValueExpression, ...]
    position: SourcePosition


@dataclass(frozen=True, slots=True)
class ClearBackgroundUpdateOverflow:
    arguments: tuple[ValueExpression, ...]
    position: SourcePosition


@dataclass(frozen=True, slots=True)
class Run:
    position: SourcePosition | None = field(default=None, compare=False)


@dataclass(frozen=True, slots=True)
class WaitFrame:
    position: SourcePosition | None = field(default=None, compare=False)


@dataclass(frozen=True, slots=True)
class CallbackRegistration:
    kind: CallbackKind
    procedure_name: str
    position: SourcePosition
    procedure_position: SourcePosition


@dataclass(frozen=True, slots=True)
class SetSpriteZero:
    arguments: tuple[ValueExpression, ...]
    position: SourcePosition


@dataclass(frozen=True, slots=True)
class SpriteOperation:
    kind: SpriteOperationKind
    arguments: tuple[ValueExpression, ...]
    position: SourcePosition


@dataclass(frozen=True, slots=True)
class ImportMetasprite:
    arguments: tuple[ValueExpression, ...]
    position: SourcePosition


@dataclass(frozen=True, slots=True)
class MetaspriteOperation:
    kind: MetaspriteOperationKind
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
    | SetBackgroundColor
    | SetPalette
    | SetPaletteColor
    | LoadBackground
    | SetTile
    | SetAttribute
    | SetScroll
    | ClearBackgroundUpdates
    | ClearBackgroundUpdateOverflow
    | Run
    | WaitFrame
    | CallbackRegistration
    | SetSpriteZero
    | SpriteOperation
    | ImportMetasprite
    | MetaspriteOperation
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
class Program:
    name: str
    constants: tuple[ConstantDeclaration, ...]
    variables: tuple[VariableDeclaration, ...]
    procedures: tuple[ProcedureDeclaration, ...]
    statements: tuple[Statement, ...]
    end_position: SourcePosition | None = field(default=None, compare=False)


@dataclass(frozen=True, slots=True)
class ResolvedVariable:
    name: str
    type: BuiltInType
    label: str
    position: SourcePosition | None = field(default=None, compare=False)


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


@dataclass(frozen=True, slots=True)
class ResolvedControllerQuery:
    kind: ControllerQueryKind
    controller_index: int
    button_mask: int
    button_name: str


@dataclass(frozen=True, slots=True)
class ResolvedSpriteCreate:
    index: int


@dataclass(frozen=True, slots=True)
class ResolvedMetaspriteCreate:
    instance_index: int
    initial_frame_id: int


@dataclass(frozen=True, slots=True)
class ResolvedGetTile:
    x: ResolvedValue
    y: ResolvedValue


@dataclass(frozen=True, slots=True)
class ResolvedBackgroundUpdatesOverflowed:
    pass


ResolvedValue = (
    ImmediateValue
    | VariableValue
    | ResolvedUnaryExpression
    | ResolvedBinaryExpression
    | ResolvedComparisonExpression
    | ResolvedBooleanNotExpression
    | ResolvedBooleanBinaryExpression
    | ResolvedControllerQuery
    | ResolvedSpriteCreate
    | ResolvedMetaspriteCreate
    | ResolvedGetTile
    | ResolvedBackgroundUpdatesOverflowed
)


@dataclass(frozen=True, slots=True)
class ResolvedAssignment:
    target: ResolvedVariable
    value: ResolvedValue


@dataclass(frozen=True, slots=True)
class ResolvedSetBackgroundColor:
    argument: ResolvedValue
    queued: bool = False


@dataclass(frozen=True, slots=True)
class ResolvedSetPalette:
    kind: PaletteKind
    palette_index: int
    colors: tuple[ResolvedValue, ResolvedValue, ResolvedValue, ResolvedValue]
    queued: bool


@dataclass(frozen=True, slots=True)
class ResolvedSetPaletteColor:
    kind: PaletteKind
    palette_index: int
    color_index: int
    color: ResolvedValue
    queued: bool


@dataclass(frozen=True, slots=True)
class ResolvedLoadBackground:
    pass


@dataclass(frozen=True, slots=True)
class ResolvedSetTile:
    x: ResolvedValue
    y: ResolvedValue
    tile: ResolvedValue


@dataclass(frozen=True, slots=True)
class ResolvedSetAttribute:
    x: ResolvedValue
    y: ResolvedValue
    value: ResolvedValue


@dataclass(frozen=True, slots=True)
class ResolvedSetScroll:
    x: ResolvedValue
    y: ResolvedValue


@dataclass(frozen=True, slots=True)
class ResolvedClearBackgroundUpdates:
    pass


@dataclass(frozen=True, slots=True)
class ResolvedClearBackgroundUpdateOverflow:
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
class ResolvedSetSpriteZero:
    x: ResolvedValue
    y: ResolvedValue
    tile: ResolvedValue
    attributes: ResolvedValue


@dataclass(frozen=True, slots=True)
class ResolvedSpriteOperation:
    kind: SpriteOperationKind
    sprite: ResolvedValue
    value: ResolvedValue | None = None
    secondary_value: ResolvedValue | None = None


@dataclass(frozen=True, slots=True)
class ResolvedImportMetasprite:
    asset_name: str


@dataclass(frozen=True, slots=True)
class ResolvedMetaspriteOperation:
    kind: MetaspriteOperationKind
    instance: ResolvedValue
    value: ResolvedValue | None = None
    secondary_value: ResolvedValue | None = None


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


@dataclass(frozen=True, slots=True)
class MetaspriteAsset:
    name: str
    configured_path: str
    frames: tuple[MetaspriteFrame, ...]

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
    | ResolvedSetBackgroundColor
    | ResolvedSetPalette
    | ResolvedSetPaletteColor
    | ResolvedLoadBackground
    | ResolvedSetTile
    | ResolvedSetAttribute
    | ResolvedSetScroll
    | ResolvedClearBackgroundUpdates
    | ResolvedClearBackgroundUpdateOverflow
    | Run
    | WaitFrame
    | ResolvedCallbackRegistration
    | ResolvedSetSpriteZero
    | ResolvedSpriteOperation
    | ResolvedImportMetasprite
    | ResolvedMetaspriteOperation
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
class ResolvedProgram:
    name: str
    variables: tuple[ResolvedVariable, ...]
    procedures: tuple[ResolvedProcedure, ...]
    statements: tuple[ResolvedStatement, ...]
    oam_reservations: tuple[OamReservation, ...] = ()
    metasprite_assets: tuple[MetaspriteAsset, ...] = ()
    metasprite_instances: tuple[MetaspriteInstance, ...] = ()
