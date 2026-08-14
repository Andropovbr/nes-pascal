"""Semantic validation, name resolution, and strict type checking."""

from dataclasses import dataclass, fields, is_dataclass
from typing import Iterator

from .ast import (
    ArrayElementAssignment,
    ArrayIndexExpression,
    ArrayType,
    Assignment,
    BinaryExpression,
    BooleanBinaryExpression,
    BooleanLiteral,
    BooleanNotExpression,
    BreakStatement,
    BuiltinCall,
    BuiltInType,
    CallbackKind,
    CallbackRegistration,
    ComparisonExpression,
    ComparisonOperator,
    ConstantDeclaration,
    ConstantReference,
    ContinueStatement,
    DecrementStatement,
    EnumType,
    EnumTypeDeclaration,
    ForStatement,
    HexLiteral,
    IfStatement,
    ImmediateValue,
    IncrementStatement,
    ImportMetasprite,
    LoadBackground,
    MetaspriteAsset,
    MetaspriteAnimation,
    MetaspriteFrame,
    MetaspriteInstance,
    NamedTypeReference,
    OamOwnerKind,
    OamReservation,
    Program,
    ProcedureCall,
    ProcedureDeclaration,
    RepeatStatement,
    RecordField,
    RecordFieldAssignment,
    RecordFieldExpression,
    RecordType,
    RecordTypeDeclaration,
    ResolvedArgument,
    ResolvedArrayElement,
    ResolvedArrayElementAssignment,
    ResolvedAssignment,
    ResolvedBinaryExpression,
    ResolvedBooleanBinaryExpression,
    ResolvedBooleanNotExpression,
    ResolvedBreakStatement,
    ResolvedCallbackRegistration,
    ResolvedComparisonExpression,
    ResolvedBuiltinCall,
    ResolvedContinueStatement,
    ResolvedDecrementStatement,
    ResolvedForStatement,
    ResolvedIfStatement,
    ResolvedIncrementStatement,
    ResolvedImportMetasprite,
    ResolvedLoadBackground,
    ResolvedRepeatStatement,
    ResolvedRecordField,
    ResolvedRecordFieldAssignment,
    ResolvedProgram,
    ResolvedProcedure,
    ResolvedProcedureCall,
    ResolvedStatement,
    ResolvedValue,
    ResolvedVariable,
    ResolvedWhileStatement,
    ResolvedUnaryExpression,
    Run,
    ScalarType,
    SourcePosition,
    Statement,
    UnaryExpression,
    ValueExpression,
    VariableValue,
    VariableReference,
    VariableType,
    WhileStatement,
)
from .builtins import (
    BuiltinDescriptor,
    BuiltinId,
    BuiltinKind,
    SemanticHook,
    builtin_by_name,
)
from .diagnostics import CompilerError, DiagnosticCode, SourceLocation


CONTROLLER_BUTTONS: dict[str, int] = {
    "nes.button_a": 0x01,
    "nes.button_b": 0x02,
    "nes.button_select": 0x04,
    "nes.button_start": 0x08,
    "nes.button_up": 0x10,
    "nes.button_down": 0x20,
    "nes.button_left": 0x40,
    "nes.button_right": 0x80,
}

SPRITE_OPERATION_IDS = frozenset(
    {
        BuiltinId.SPRITE_SET_POSITION,
        BuiltinId.SPRITE_SET_X,
        BuiltinId.SPRITE_SET_Y,
        BuiltinId.SPRITE_SET_TILE,
        BuiltinId.SPRITE_SET_PALETTE,
        BuiltinId.SPRITE_SET_ATTRIBUTES,
        BuiltinId.SPRITE_HIDE,
        BuiltinId.SPRITE_SHOW,
        BuiltinId.SPRITE_SET_FLIP_HORIZONTAL,
        BuiltinId.SPRITE_SET_FLIP_VERTICAL,
        BuiltinId.SPRITE_SET_BEHIND_BACKGROUND,
    }
)
METASPRITE_OPERATION_IDS = frozenset(
    {
        BuiltinId.METASPRITE_SET_POSITION,
        BuiltinId.METASPRITE_SET_FRAME,
        BuiltinId.METASPRITE_SET_ANIMATION,
        BuiltinId.METASPRITE_RESTART_ANIMATION,
        BuiltinId.METASPRITE_HIDE,
        BuiltinId.METASPRITE_SHOW,
        BuiltinId.METASPRITE_SET_FLIP_HORIZONTAL,
        BuiltinId.METASPRITE_SET_FLIP_VERTICAL,
    }
)
CONTROLLER_QUERY_IDS = frozenset(
    {
        BuiltinId.CONTROLLER_DOWN,
        BuiltinId.CONTROLLER_PRESSED,
        BuiltinId.CONTROLLER_RELEASED,
    }
)


def _parsed_builtin_id(call: BuiltinCall) -> BuiltinId:
    descriptor = builtin_by_name(call.name)
    assert descriptor is not None
    return descriptor.id


@dataclass(frozen=True, slots=True)
class TypedConstant:
    type: ScalarType
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


@dataclass(frozen=True, slots=True)
class SpriteAllocationPlan:
    """Static OAM ownership shared by individual hardware-sprite features."""

    create_indexes: dict[SourcePosition, int]
    reservations: tuple[OamReservation, ...]
    metasprite_create_indexes: dict[SourcePosition, int]
    metasprite_instances: tuple[MetaspriteInstance, ...]


class SemanticAnalyzer:
    def __init__(
        self,
        source: str,
        filename: str = "<input>",
        metasprite_assets: tuple[MetaspriteAsset, ...] = (),
    ) -> None:
        self.source_lines = source.splitlines()
        self.filename = filename
        self.required_variables: set[str] | None = None
        self.procedure_summaries: dict[str, ProcedureSummary] = {}
        self.callback_registrations: dict[
            CallbackKind, CallbackRegistration
        ] = {}
        self.callback_symbols: dict[CallbackKind, ProcedureSymbol] = {}
        self.configured_metasprite_assets = {
            asset.name.lower(): asset for asset in metasprite_assets
        }
        self.imported_metasprite_assets: tuple[MetaspriteAsset, ...] = ()
        self.metasprite_frames_by_id: dict[int, MetaspriteFrame] = {}
        self.metasprite_animations_by_id: dict[int, MetaspriteAnimation] = {}
        self.sprite_allocation_plan = SpriteAllocationPlan({}, (), {}, ())

    def analyze(self, program: Program) -> ResolvedProgram:
        self.imported_metasprite_assets = self._resolve_metasprite_imports(program)
        self.metasprite_frames_by_id = {
            frame.id: frame
            for asset in self.imported_metasprite_assets
            for frame in asset.frames
        }
        self.metasprite_animations_by_id = {
            animation.id: animation
            for asset in self.imported_metasprite_assets
            for animation in asset.animations
        }
        constants: dict[str, TypedConstant] = {
            name: TypedConstant(BuiltInType.BYTE, value)
            for name, value in CONTROLLER_BUTTONS.items()
        }
        for asset in self.imported_metasprite_assets:
            for animation in asset.animations:
                constants[animation.symbol.lower()] = TypedConstant(
                    BuiltInType.METASPRITE_ANIMATION,
                    animation.id,
                )
            for frame in asset.frames:
                constants[frame.symbol.lower()] = TypedConstant(
                    BuiltInType.METASPRITE_FRAME,
                    frame.id,
                )
        declared_names: set[str] = set()
        for declaration in program.enum_types:
            enum_type = declaration.type
            self._ensure_unique_name(
                enum_type.name,
                declaration.position,
                declared_names,
            )
            if len(declaration.members) > 256:
                self._error(
                    declaration.position,
                    DiagnosticCode.ENUM_TOO_MANY_MEMBERS,
                    f"Enumeration {enum_type.name} declares {len(declaration.members)} "
                    "members, but a byte-sized enumeration supports at most 256.",
                    "Remove members so the enumeration contains at most 256 values.",
                    len(enum_type.name),
                )
            declared_names.add(enum_type.name.lower())

            member_names: set[str] = set()
            for value, member in enumerate(declaration.members):
                normalized_name = member.name.lower()
                if normalized_name in member_names:
                    self._error(
                        member.position,
                        DiagnosticCode.DUPLICATE_ENUM_MEMBER,
                        f"Enumeration {enum_type.name} already declares member "
                        f"{member.name}.",
                        "Use a unique member name within the enumeration.",
                        len(member.name),
                    )
                self._ensure_unique_name(
                    member.name,
                    member.position,
                    declared_names,
                )
                member_names.add(normalized_name)
                declared_names.add(normalized_name)
                constants[normalized_name] = TypedConstant(enum_type, value)

        record_types = self._resolve_record_types(
            program.record_types,
            program.enum_types,
            declared_names,
        )

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
            resolved_type = self._resolve_variable_type(
                declaration.type,
                record_types,
            )
            if isinstance(resolved_type, ArrayType):
                array_type = resolved_type
                if array_type.element_type not in (
                    BuiltInType.BYTE,
                    BuiltInType.BOOLEAN,
                ) and not isinstance(array_type.element_type, RecordType):
                    self._error(
                        array_type.element_type_position or declaration.position,
                        DiagnosticCode.INVALID_ARRAY_ELEMENT_TYPE,
                        f"Arrays of {array_type.element_type.value} are not supported.",
                        "Use byte, boolean, or a declared record as the array element type.",
                        len(array_type.element_type.value),
                    )
                if array_type.lower_bound != 0:
                    self._error(
                        array_type.lower_bound_position or declaration.position,
                        DiagnosticCode.INVALID_ARRAY_BOUNDS,
                        "Array lower bounds must be $00.",
                        "Declare a zero-based range such as array[$00..$07].",
                        3,
                    )
                if (
                    array_type.upper_bound < array_type.lower_bound
                    or array_type.upper_bound > 0xFF
                ):
                    self._error(
                        array_type.upper_bound_position or declaration.position,
                        DiagnosticCode.INVALID_ARRAY_BOUNDS,
                        f"Array upper bound ${array_type.upper_bound:X} is invalid.",
                        "Use an upper bound from $00 through $FF.",
                        max(3, len(f"${array_type.upper_bound:X}")),
                    )
            variable = ResolvedVariable(
                declaration.name,
                resolved_type,
                f"variable_{declaration.name}",
                declaration.position,
            )
            variables[normalized_name] = variable
            resolved_variables.append(variable)
            declared_names.add(normalized_name)

        self.sprite_allocation_plan = self._plan_sprite_ownership(
            program,
            constants,
            variables,
        )

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

        self._validate_callback_registrations(program, procedures)

        procedure_order = self._procedure_resolution_order(
            program.procedures,
            procedures,
        )
        self._validate_known_procedure_calls(
            program.statements,
            procedures,
        )
        self._validate_vblank_callback(procedures)
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
                runtime_started=True,
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
        resolved_statements, final_assignments = self._resolve_statements(
            program.statements,
            constants,
            variables,
            set(),
            inside_conditional=False,
            loop_depth=0,
            protected_control_variables=frozenset(),
            inside_procedure=False,
            runtime_started=False,
        )

        update_symbol = self.callback_symbols.get(CallbackKind.UPDATE)
        if update_symbol is not None:
            summary = self.procedure_summaries[update_symbol.declaration.name.lower()]
            missing_variables = summary.required_variables - final_assignments
            if missing_variables:
                normalized_variable = sorted(missing_variables)[0]
                variable = variables[normalized_variable]
                registration = self.callback_registrations[CallbackKind.UPDATE]
                self._error(
                    registration.procedure_position,
                    DiagnosticCode.VARIABLE_READ_BEFORE_ASSIGNMENT,
                    f"Update callback {registration.procedure_name} requires "
                    f"variable {variable.name} to be assigned before the "
                    "runtime callback loop starts.",
                    f"Assign {variable.name} in the main block before it ends.",
                    len(registration.procedure_name),
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
            self.sprite_allocation_plan.reservations,
            self.imported_metasprite_assets,
            self.sprite_allocation_plan.metasprite_instances,
            tuple(record_types.values()),
        )

    def _resolve_record_types(
        self,
        declarations: tuple[RecordTypeDeclaration, ...],
        enum_declarations: tuple[EnumTypeDeclaration, ...],
        declared_names: set[str],
    ) -> dict[str, RecordType]:
        record_names: set[str] = set()
        for declaration in declarations:
            self._ensure_unique_name(
                declaration.name,
                declaration.position,
                declared_names | record_names,
            )
            record_names.add(declaration.name.lower())
        declared_names.update(record_names)

        enum_types = {
            declaration.type.name.lower(): declaration.type
            for declaration in enum_declarations
        }
        resolved: dict[str, RecordType] = {}
        for declaration in declarations:
            if not declaration.fields:
                self._error(
                    declaration.position,
                    DiagnosticCode.RECORD_LAYOUT_OVERFLOW,
                    f"Record {declaration.name} must declare at least one field.",
                    "Add a byte, boolean, or enumeration field.",
                    len(declaration.name),
                )
            fields_: list[RecordField] = []
            field_names: set[str] = set()
            for field_declaration in declaration.fields:
                normalized_field = field_declaration.name.lower()
                if normalized_field in field_names:
                    self._error(
                        field_declaration.position,
                        DiagnosticCode.DUPLICATE_RECORD_FIELD,
                        f"Record {declaration.name} already declares field "
                        f"{field_declaration.name}.",
                        "Use a unique field name within the record.",
                        len(field_declaration.name),
                    )
                field_names.add(normalized_field)
                field_type = field_declaration.type
                if isinstance(field_type, NamedTypeReference):
                    normalized_type = field_type.name.lower()
                    if normalized_type == declaration.name.lower():
                        self._error(
                            field_type.position,
                            DiagnosticCode.RECURSIVE_RECORD_DEFINITION,
                            f"Record {declaration.name} cannot contain itself through "
                            f"field {field_declaration.name}.",
                            "Use a byte, boolean, or enumeration field; record fields "
                            "inside records are not supported.",
                            len(field_type.name),
                        )
                    enum_type = enum_types.get(normalized_type)
                    if enum_type is not None:
                        field_type = enum_type
                    else:
                        self._error(
                            field_type.position,
                            DiagnosticCode.UNSUPPORTED_RECORD_FIELD_TYPE,
                            f"Field {declaration.name}.{field_declaration.name} has "
                            f"unsupported type {field_type.name}.",
                            "Record fields may have type byte, boolean, or a declared enumeration.",
                            len(field_type.name),
                        )
                if isinstance(field_type, (ArrayType, RecordType)) or (
                    field_type not in (BuiltInType.BYTE, BuiltInType.BOOLEAN)
                    and not isinstance(field_type, EnumType)
                ):
                    self._error(
                        field_declaration.type_position,
                        DiagnosticCode.UNSUPPORTED_RECORD_FIELD_TYPE,
                        f"Field {declaration.name}.{field_declaration.name} has "
                        f"unsupported type {field_type.value}.",
                        "Record fields may have type byte, boolean, or a declared enumeration.",
                        len(field_type.value),
                    )
                offset = len(fields_)
                if offset >= 0x100:
                    self._error(
                        field_declaration.position,
                        DiagnosticCode.RECORD_LAYOUT_OVERFLOW,
                        f"Record {declaration.name} exceeds the supported 256-byte layout.",
                        "Reduce the record to at most 256 byte-sized fields.",
                        len(field_declaration.name),
                    )
                assert isinstance(field_type, (BuiltInType, EnumType))
                fields_.append(
                    RecordField(
                        field_declaration.name,
                        field_type,
                        offset,
                        field_declaration.position,
                    )
                )
            resolved[declaration.name.lower()] = RecordType(
                declaration.name,
                tuple(fields_),
                len(fields_),
            )
        return resolved

    def _resolve_variable_type(
        self,
        declared_type: VariableType,
        record_types: dict[str, RecordType],
    ) -> VariableType:
        if isinstance(declared_type, NamedTypeReference):
            record_type = record_types.get(declared_type.name.lower())
            if record_type is None:
                self._error(
                    declared_type.position,
                    DiagnosticCode.UNKNOWN_TYPE,
                    f"Unknown type: {declared_type.name}.",
                    "Use a declared enumeration or record type.",
                    len(declared_type.name),
                )
            return record_type
        if isinstance(declared_type, ArrayType) and isinstance(
            declared_type.element_type,
            NamedTypeReference,
        ):
            element = record_types.get(declared_type.element_type.name.lower())
            if element is None:
                self._error(
                    declared_type.element_type.position,
                    DiagnosticCode.UNKNOWN_TYPE,
                    f"Unknown type: {declared_type.element_type.name}.",
                    "Use byte, boolean, or a declared record type as the array element type.",
                    len(declared_type.element_type.name),
                )
            return ArrayType(
                element,
                declared_type.lower_bound,
                declared_type.upper_bound,
                declared_type.position,
                declared_type.lower_bound_position,
                declared_type.upper_bound_position,
                declared_type.element_type_position,
            )
        return declared_type

    def _resolve_metasprite_imports(
        self,
        program: Program,
    ) -> tuple[MetaspriteAsset, ...]:
        top_level_imports = [
            statement
            for statement in program.statements
            if isinstance(statement, ImportMetasprite)
        ]
        top_level_positions = {statement.position for statement in top_level_imports}
        for node in self._walk_ast_nodes(program):
            if (
                isinstance(node, ImportMetasprite)
                and node.position not in top_level_positions
            ):
                self._error(
                    node.position,
                    DiagnosticCode.INVALID_METASPRITE_IMPORT,
                    "nes.import_metasprite is a compile-time top-level import.",
                    "Move the import directly into the main program block.",
                    len("nes.import_metasprite"),
                )

        run_index = next(
            (
                index
                for index, statement in enumerate(program.statements)
                if isinstance(statement, Run)
            ),
            len(program.statements),
        )
        imported: list[MetaspriteAsset] = []
        imported_names: set[str] = set()
        for import_statement in top_level_imports:
            statement_index = program.statements.index(import_statement)
            if statement_index > run_index:
                self._error(
                    import_statement.position,
                    DiagnosticCode.INVALID_METASPRITE_IMPORT,
                    "nes.import_metasprite must appear before nes.run.",
                    "Move the compile-time import before runtime startup.",
                    len("nes.import_metasprite"),
                )
            if len(import_statement.arguments) != 1 or not isinstance(
                import_statement.arguments[0],
                (ConstantReference, VariableReference),
            ):
                self._error(
                    import_statement.position,
                    DiagnosticCode.INVALID_METASPRITE_IMPORT,
                    "nes.import_metasprite expects exactly one configured asset name.",
                    "Use nes.import_metasprite(player) after configuring "
                    "player metadata with --metasprite.",
                    len("nes.import_metasprite"),
                )
            reference = import_statement.arguments[0]
            if "." in reference.name:
                self._error(
                    reference.position,
                    DiagnosticCode.INVALID_METASPRITE_IMPORT,
                    "A metasprite import names the asset root, not a frame.",
                    "Import player, then reference a frame such as player.idle_0.",
                    len(reference.name),
                )
            normalized = reference.name.lower()
            asset = self.configured_metasprite_assets.get(normalized)
            if asset is None:
                self._error(
                    reference.position,
                    DiagnosticCode.INVALID_METASPRITE_IMPORT,
                    f"Metasprite asset {reference.name} was not configured.",
                    "Pass its JSON path with --metasprite and ensure the JSON "
                    "root name matches the import.",
                    len(reference.name),
                )
            if normalized in imported_names:
                self._error(
                    reference.position,
                    DiagnosticCode.DUPLICATE_METASPRITE_IMPORT,
                    f"Metasprite asset {reference.name} is imported more than once.",
                    "Keep one compile-time import for each configured asset.",
                    len(reference.name),
                )
            imported_names.add(normalized)
            imported.append(asset)

        unimported = set(self.configured_metasprite_assets) - imported_names
        if unimported:
            name = sorted(unimported)[0]
            position = program.end_position or SourcePosition(1, 1)
            self._error(
                position,
                DiagnosticCode.INVALID_METASPRITE_IMPORT,
                f"Configured metasprite asset {name} is not imported by the program.",
                f"Add nes.import_metasprite({name}); before nes.run, or remove "
                "its --metasprite option.",
                len(name),
            )
        return tuple(imported)

    def _plan_sprite_ownership(
        self,
        program: Program,
        constants: dict[str, TypedConstant],
        variables: dict[str, ResolvedVariable],
    ) -> SpriteAllocationPlan:
        """Reserve physical OAM slots before control-flow resolution.

        Explicit individual-sprite indexes have priority. Each syntactic
        ``nes.sprite_create()`` site then receives the lowest remaining slot.
        This makes allocation independent of runtime branches, loops, and call
        counts while leaving an explicit reservation table for metasprites.
        """

        explicit_positions: dict[int, SourcePosition] = {}
        for declaration in program.constants:
            if declaration.type is BuiltInType.SPRITE:
                explicit_positions.setdefault(
                    declaration.value.value,
                    declaration.value.position,
                )

        for node in self._walk_ast_nodes(program):
            if (
                isinstance(node, BuiltinCall)
                and _parsed_builtin_id(node) is BuiltinId.SET_SPRITE_ZERO
            ):
                explicit_positions.setdefault(0, node.position)
            elif (
                isinstance(node, BuiltinCall)
                and _parsed_builtin_id(node) in SPRITE_OPERATION_IDS
                and node.arguments
            ):
                explicit = self._explicit_sprite_index(
                    node.arguments[0],
                    constants,
                )
                if explicit is not None:
                    explicit_positions.setdefault(
                        explicit,
                        node.arguments[0].position,
                    )
            elif isinstance(node, Assignment):
                target = variables.get(node.target.lower())
                if target is not None and target.type is BuiltInType.SPRITE:
                    explicit = self._explicit_sprite_index(node.value, constants)
                    if explicit is not None:
                        explicit_positions.setdefault(explicit, node.value.position)

        create_sites = sorted(
            (
                node
                for node in self._walk_ast_nodes(program)
                if isinstance(node, BuiltinCall)
                and _parsed_builtin_id(node) is BuiltinId.SPRITE_CREATE
            ),
            key=lambda create: (create.position.line, create.position.column),
        )
        for create in create_sites:
            if create.arguments:
                self._error(
                    create.position,
                    DiagnosticCode.INVALID_SPRITE_CREATE_ARGUMENT_COUNT,
                    "nes.sprite_create expects exactly 0 arguments, but "
                    f"{len(create.arguments)} were provided.",
                    "Call nes.sprite_create() without arguments.",
                    len("nes.sprite_create"),
                )

        available = [
            index for index in range(64) if index not in explicit_positions
        ]
        create_indexes: dict[SourcePosition, int] = {}
        created_reservations: list[OamReservation] = []
        for allocation_number, create in enumerate(create_sites):
            if allocation_number >= len(available):
                self._error(
                    create.position,
                    DiagnosticCode.OAM_SPRITE_CAPACITY_EXHAUSTED,
                    "nes.sprite_create cannot reserve another hardware sprite: "
                    "all 64 OAM entries are already owned.",
                    "Remove an individual sprite reservation or creation site. "
                    "The NES has exactly 64 hardware sprites.",
                    len("nes.sprite_create"),
                )
            index = available[allocation_number]
            create_indexes[create.position] = index
            created_reservations.append(
                OamReservation(
                    index,
                    OamOwnerKind.INDIVIDUAL_CREATED,
                    create.position,
                )
                )

        remaining = available[len(create_sites) :]
        metasprite_create_sites = sorted(
            (
                node
                for node in self._walk_ast_nodes(program)
                if isinstance(node, BuiltinCall)
                and _parsed_builtin_id(node) is BuiltinId.METASPRITE_CREATE
            ),
            key=lambda create: (create.position.line, create.position.column),
        )
        if len(metasprite_create_sites) > 256:
            overflow = metasprite_create_sites[256]
            self._error(
                overflow.position,
                DiagnosticCode.INVALID_METASPRITE_CREATE,
                "A program can contain at most 256 static metasprite creation sites.",
                "Reduce the number of metasprite instances in this NROM program.",
                len("nes.metasprite_create"),
            )
        metasprite_create_indexes: dict[SourcePosition, int] = {}
        metasprite_instances: list[MetaspriteInstance] = []
        metasprite_reservations: list[OamReservation] = []
        for instance_index, create in enumerate(metasprite_create_sites):
            if len(create.arguments) != 1:
                self._error(
                    create.position,
                    DiagnosticCode.INVALID_METASPRITE_CREATE,
                    "nes.metasprite_create expects exactly one symbolic frame, "
                    f"but {len(create.arguments)} arguments were provided.",
                    "Pass an imported frame such as player.idle_0.",
                    len("nes.metasprite_create"),
                )
            frame = self._static_metasprite_frame(
                create.arguments[0],
                constants,
                "nes.metasprite_create",
            )
            asset = next(
                asset
                for asset in self.imported_metasprite_assets
                if asset.name == frame.asset_name
            )
            required = asset.maximum_component_count
            if len(remaining) < required:
                self._error(
                    create.position,
                    DiagnosticCode.OAM_SPRITE_CAPACITY_EXHAUSTED,
                    f"Metasprite asset {asset.name} needs {required} hardware "
                    f"sprite slots, but only {len(remaining)} remain after "
                    "individual and earlier metasprite reservations.",
                    "Reduce individual sprites or metasprite instances. The NES "
                    "has exactly 64 shared OAM entries.",
                    len("nes.metasprite_create"),
                )
            indexes = tuple(remaining[:required])
            remaining = remaining[required:]
            metasprite_create_indexes[create.position] = instance_index
            metasprite_instances.append(
                MetaspriteInstance(
                    instance_index,
                    asset.name,
                    frame.id,
                    indexes,
                    create.position,
                )
            )
            metasprite_reservations.extend(
                OamReservation(
                    oam_index,
                    OamOwnerKind.METASPRITE_COMPONENT,
                    create.position,
                    instance_index,
                    component_index,
                )
                for component_index, oam_index in enumerate(indexes)
            )

        reservations = [
            OamReservation(
                index,
                OamOwnerKind.INDIVIDUAL_EXPLICIT,
                position,
            )
            for index, position in explicit_positions.items()
        ]
        reservations.extend(created_reservations)
        reservations.extend(metasprite_reservations)
        reservations.sort(key=lambda reservation: reservation.index)
        return SpriteAllocationPlan(
            create_indexes,
            tuple(reservations),
            metasprite_create_indexes,
            tuple(metasprite_instances),
        )

    def _static_metasprite_frame(
        self,
        expression: ValueExpression,
        constants: dict[str, TypedConstant],
        command: str,
    ) -> MetaspriteFrame:
        if isinstance(expression, ConstantReference):
            constant = constants.get(expression.name.lower())
            if (
                constant is not None
                and constant.type is BuiltInType.METASPRITE_FRAME
            ):
                return self.metasprite_frames_by_id[constant.value]
        self._error(
            expression.position,
            DiagnosticCode.INVALID_METASPRITE_CREATE,
            f"{command} requires an imported symbolic metasprite frame.",
            "Use a frame such as player.idle_0 from an imported asset.",
            len(getattr(expression, "name", command)),
        )
        raise AssertionError("unreachable")

    def _static_metasprite_animation(
        self,
        expression: ValueExpression,
        constants: dict[str, TypedConstant],
        command: str,
    ) -> MetaspriteAnimation:
        if isinstance(expression, ConstantReference):
            constant = constants.get(expression.name.lower())
            if (
                constant is not None
                and constant.type is BuiltInType.METASPRITE_ANIMATION
            ):
                return self.metasprite_animations_by_id[constant.value]
        self._error(
            expression.position,
            DiagnosticCode.INVALID_METASPRITE_ANIMATION,
            f"{command} requires an imported symbolic metasprite animation.",
            "Use an animation such as player.idle from an imported asset.",
            len(getattr(expression, "name", command)),
        )
        raise AssertionError("unreachable")

    @staticmethod
    def _explicit_sprite_index(
        expression: ValueExpression,
        constants: dict[str, TypedConstant],
    ) -> int | None:
        if isinstance(expression, HexLiteral):
            return expression.value if expression.value <= 0x3F else None
        if isinstance(expression, ConstantReference):
            constant = constants.get(expression.name.lower())
            if constant is not None and constant.type is BuiltInType.SPRITE:
                return constant.value
        return None

    def _walk_ast_nodes(self, value: object) -> Iterator[object]:
        if isinstance(value, tuple):
            for item in value:
                yield from self._walk_ast_nodes(item)
            return
        if not is_dataclass(value):
            return
        yield value
        for field in fields(value):
            yield from self._walk_ast_nodes(getattr(value, field.name))

    def _resolve_statements(
        self,
        statements: tuple[Statement, ...],
        constants: dict[str, TypedConstant],
        variables: dict[str, ResolvedVariable],
        assigned_variables: set[str],
        inside_conditional: bool,
        loop_depth: int,
        protected_control_variables: frozenset[str],
        inside_procedure: bool,
        runtime_started: bool,
    ) -> tuple[tuple[ResolvedStatement, ...], set[str]]:
        current_assignments = set(assigned_variables)
        resolved_statements: list[ResolvedStatement] = []
        for statement in statements:
            if isinstance(statement, RecordFieldAssignment):
                self._reject_control_variable_modification(
                    statement.target,
                    statement.target_position,
                    protected_control_variables,
                )
                resolved = self._resolve_record_field_assignment(
                    statement,
                    constants,
                    variables,
                    current_assignments,
                )
                resolved_statements.append(resolved)
                current_assignments.add(statement.target.lower())
            elif isinstance(statement, ArrayElementAssignment):
                self._reject_control_variable_modification(
                    statement.target,
                    statement.target_position,
                    protected_control_variables,
                )
                resolved = self._resolve_array_assignment(
                    statement,
                    constants,
                    variables,
                    current_assignments,
                )
                resolved_statements.append(resolved)
                current_assignments.add(statement.target.lower())
            elif isinstance(statement, Assignment):
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
                    runtime_started=runtime_started,
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
                        runtime_started=runtime_started,
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
                    runtime_started=runtime_started,
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
                    runtime_started=runtime_started,
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
                    runtime_started=runtime_started,
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
            elif isinstance(statement, CallbackRegistration):
                symbol = self.callback_symbols[statement.kind]
                resolved_statements.append(
                    ResolvedCallbackRegistration(
                        statement.kind,
                        symbol.declaration.name,
                        symbol.label,
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
            elif isinstance(statement, BuiltinCall):
                descriptor = builtin_by_name(statement.name)
                assert descriptor is not None
                if descriptor.kind is not BuiltinKind.STATEMENT:
                    self._invalid_builtin_context(statement, descriptor)
                if (
                    descriptor.id is BuiltinId.WAIT_FRAME
                    and inside_procedure
                ):
                    self._procedure_runtime_command_error(
                        statement.position,
                        descriptor.public_name,
                    )
                resolved_statements.append(
                    self._resolve_builtin_call(
                        statement,
                        descriptor,
                        constants,
                        variables,
                        current_assignments,
                        queued=runtime_started or inside_procedure,
                    )
                )
            elif isinstance(statement, ImportMetasprite):
                reference = statement.arguments[0]
                assert isinstance(reference, (ConstantReference, VariableReference))
                resolved_statements.append(
                    ResolvedImportMetasprite(reference.name.lower())
                )
            elif isinstance(statement, LoadBackground):
                if statement.arguments:
                    self._error(
                        statement.position,
                        DiagnosticCode.INVALID_BACKGROUND_LOAD_ARGUMENT_COUNT,
                        "nes.load_background expects no arguments, but "
                        f"{len(statement.arguments)} were provided.",
                        "Call nes.load_background(); without arguments.",
                        len("nes.load_background"),
                    )
                if inside_procedure:
                    self._procedure_runtime_command_error(
                        statement.position,
                        "nes.load_background",
                    )
                if loop_depth > 0:
                    self._loop_runtime_command_error(
                        statement.position,
                        "nes.load_background",
                    )
                if inside_conditional:
                    self._conditional_runtime_command_error(
                        statement.position,
                        "nes.load_background",
                    )
                if runtime_started:
                    self._error(
                        statement.position,
                        DiagnosticCode.BACKGROUND_LOAD_AFTER_RUN,
                        "nes.load_background cannot execute after nes.run "
                        "enables rendering.",
                        "Move nes.load_background(); before nes.run;.",
                        len("nes.load_background"),
                    )
                resolved_statements.append(ResolvedLoadBackground())
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
                vblank_symbol = self.callback_symbols.get(CallbackKind.VBLANK)
                if vblank_symbol is not None:
                    summary = self.procedure_summaries[
                        vblank_symbol.declaration.name.lower()
                    ]
                    missing_variables = (
                        summary.required_variables - current_assignments
                    )
                    if missing_variables:
                        normalized_variable = sorted(missing_variables)[0]
                        variable = variables[normalized_variable]
                        registration = self.callback_registrations[
                            CallbackKind.VBLANK
                        ]
                        self._error(
                            registration.procedure_position,
                            DiagnosticCode.VARIABLE_READ_BEFORE_ASSIGNMENT,
                            f"VBlank callback {registration.procedure_name} "
                            f"requires variable {variable.name} to be assigned "
                            "before nes.run enables NMI.",
                            f"Assign {variable.name} before nes.run;.",
                            len(registration.procedure_name),
                        )
                resolved_statements.append(Run())
                runtime_started = True

        return (
            tuple(resolved_statements),
            current_assignments,
        )

    def _validate_callback_registrations(
        self,
        program: Program,
        procedures: dict[str, ProcedureSymbol],
    ) -> None:
        for declaration in program.procedures:
            nested = self._first_callback_registration(declaration.body)
            if nested is not None:
                self._invalid_callback_context(
                    nested,
                    "Callback registration cannot appear inside a procedure.",
                )

        for statement in program.statements:
            if isinstance(statement, CallbackRegistration):
                continue
            nested = self._first_callback_registration((statement,))
            if nested is not None:
                self._invalid_callback_context(
                    nested,
                    "Callback registration must be unconditional top-level "
                    "initialization.",
                )

        run_index = next(
            (
                index
                for index, statement in enumerate(program.statements)
                if isinstance(statement, Run)
            ),
            None,
        )
        registrations: dict[CallbackKind, CallbackRegistration] = {}
        symbols: dict[CallbackKind, ProcedureSymbol] = {}
        for index, statement in enumerate(program.statements):
            if not isinstance(statement, CallbackRegistration):
                continue
            if run_index is not None and index > run_index:
                self._invalid_callback_context(
                    statement,
                    "Callback registration must execute before nes.run.",
                )
            previous = registrations.get(statement.kind)
            if previous is not None:
                code = (
                    DiagnosticCode.DUPLICATE_UPDATE_CALLBACK
                    if statement.kind is CallbackKind.UPDATE
                    else DiagnosticCode.DUPLICATE_VBLANK_CALLBACK
                )
                command = f"nes.on_{statement.kind.value}"
                callback_name = (
                    "update"
                    if statement.kind is CallbackKind.UPDATE
                    else "VBlank"
                )
                self._error(
                    statement.position,
                    code,
                    f"Only one {callback_name} callback may be registered.",
                    f"Remove the additional {command}(...) registration.",
                    len(command),
                )
            symbol = procedures.get(statement.procedure_name.lower())
            if symbol is None:
                self._error(
                    statement.procedure_position,
                    DiagnosticCode.UNKNOWN_CALLBACK_PROCEDURE,
                    f"Unknown callback procedure: {statement.procedure_name}.",
                    "Declare a parameterless procedure before the main block.",
                    len(statement.procedure_name),
                )
            if symbol.parameters:
                self._error(
                    statement.procedure_position,
                    DiagnosticCode.INVALID_CALLBACK_SIGNATURE,
                    f"Callback procedure {statement.procedure_name} must not "
                    "have parameters.",
                    "Use a procedure declared without a parameter list.",
                    len(statement.procedure_name),
                )
            registrations[statement.kind] = statement
            symbols[statement.kind] = symbol

        update = registrations.get(CallbackKind.UPDATE)
        vblank = registrations.get(CallbackKind.VBLANK)
        if (
            update is not None
            and vblank is not None
            and update.procedure_name.lower() == vblank.procedure_name.lower()
        ):
            self._error(
                vblank.procedure_position,
                DiagnosticCode.CONFLICTING_CALLBACK_REGISTRATION,
                f"Procedure {vblank.procedure_name} cannot be registered as "
                "both update and VBlank callbacks.",
                "Declare separate parameterless procedures for the two contexts.",
                len(vblank.procedure_name),
            )

        self.callback_registrations = registrations
        self.callback_symbols = symbols

    def _first_callback_registration(
        self,
        statements: tuple[Statement, ...],
    ) -> CallbackRegistration | None:
        for statement in statements:
            if isinstance(statement, CallbackRegistration):
                return statement
            branches: tuple[tuple[Statement, ...], ...] = ()
            if isinstance(statement, IfStatement):
                branches = (statement.then_branch,)
                if statement.else_branch is not None:
                    branches += (statement.else_branch,)
            elif isinstance(
                statement,
                (WhileStatement, RepeatStatement, ForStatement),
            ):
                branches = (statement.body,)
            for branch in branches:
                found = self._first_callback_registration(branch)
                if found is not None:
                    return found
        return None

    def _invalid_callback_context(
        self,
        registration: CallbackRegistration,
        message: str,
    ) -> None:
        command = f"nes.on_{registration.kind.value}"
        self._error(
            registration.position,
            DiagnosticCode.INVALID_CALLBACK_REGISTRATION_CONTEXT,
            message,
            f"Move {command}(...) to unconditional initialization before nes.run;.",
            len(command),
        )

    def _validate_vblank_callback(
        self,
        procedures: dict[str, ProcedureSymbol],
    ) -> None:
        root = self.callback_symbols.get(CallbackKind.VBLANK)
        if root is None:
            return
        update = self.callback_symbols.get(CallbackKind.UPDATE)
        update_name = (
            update.declaration.name.lower() if update is not None else None
        )
        validated: set[str] = set()

        def validate(symbol: ProcedureSymbol) -> None:
            normalized_name = symbol.declaration.name.lower()
            if normalized_name in validated:
                return
            validated.add(normalized_name)
            for statement in symbol.declaration.body:
                validate_statement(statement, symbol.declaration.name)

        def validate_statement(statement: Statement, owner: str) -> None:
            if isinstance(statement, RecordFieldAssignment):
                if statement.index is not None and not self._vblank_expression_is_safe(
                    statement.index
                ):
                    self._vblank_unsafe_expression(statement.index, owner)
                if not self._vblank_expression_is_safe(statement.value):
                    self._vblank_unsafe_expression(statement.value, owner)
                return
            if isinstance(statement, ArrayElementAssignment):
                if not self._vblank_expression_is_safe(statement.index):
                    self._vblank_unsafe_expression(statement.index, owner)
                if not self._vblank_expression_is_safe(statement.value):
                    self._vblank_unsafe_expression(statement.value, owner)
                return
            if isinstance(statement, Assignment):
                if not self._vblank_expression_is_safe(statement.value):
                    self._vblank_unsafe_expression(statement.value, owner)
                return
            if (
                isinstance(statement, BuiltinCall)
                and _parsed_builtin_id(statement) is BuiltinId.SET_SPRITE_ZERO
            ):
                self._error(
                    statement.position,
                    DiagnosticCode.VBLANK_UNSAFE_OPERATION,
                    f"VBlank callback path through {owner} reaches unsupported "
                    "operation nes.set_sprite_zero.",
                    "Stage sprite 0 from the update callback; the runtime "
                    "commits it safely during NMI.",
                    len("nes.set_sprite_zero"),
                )
            if (
                isinstance(statement, BuiltinCall)
                and _parsed_builtin_id(statement) in SPRITE_OPERATION_IDS
            ):
                command = statement.name
                self._error(
                    statement.position,
                    DiagnosticCode.VBLANK_UNSAFE_OPERATION,
                    f"VBlank callback path through {owner} reaches unsupported "
                    f"operation {command}.",
                    "Update the OAM shadow from main code or the update callback; "
                    "NMI owns OAM DMA.",
                    len(command),
                )
            if (
                isinstance(statement, BuiltinCall)
                and _parsed_builtin_id(statement) in METASPRITE_OPERATION_IDS
            ):
                command = statement.name
                self._error(
                    statement.position,
                    DiagnosticCode.VBLANK_UNSAFE_OPERATION,
                    f"VBlank callback path through {owner} reaches unsupported "
                    f"operation {command}.",
                    "Update metasprites from main code or the update callback; "
                    "NMI owns OAM DMA.",
                    len(command),
                )
            if (
                isinstance(statement, BuiltinCall)
                and _parsed_builtin_id(statement)
                in {
                    BuiltinId.SET_BACKGROUND_COLOR,
                    BuiltinId.SET_BACKGROUND_PALETTE,
                    BuiltinId.SET_SPRITE_PALETTE,
                    BuiltinId.SET_BACKGROUND_PALETTE_COLOR,
                    BuiltinId.SET_SPRITE_PALETTE_COLOR,
                    BuiltinId.SET_SCROLL,
                }
            ):
                values = statement.arguments
                for value in values:
                    if not self._vblank_expression_is_safe(value):
                        self._vblank_unsafe_expression(value, owner)
                return
            if isinstance(statement, (IncrementStatement, DecrementStatement)):
                if statement.amount is not None:
                    self._error(
                        statement.position,
                        DiagnosticCode.VBLANK_UNSAFE_OPERATION,
                        f"VBlank callback path through {owner} uses an update "
                        "amount that requires shared expression storage.",
                        "Use inc(Target) or dec(Target) without an amount.",
                        len("inc"),
                    )
                return
            if isinstance(statement, IfStatement):
                if not self._vblank_expression_is_safe(statement.condition):
                    self._vblank_unsafe_expression(statement.condition, owner)
                for item in statement.then_branch:
                    validate_statement(item, owner)
                if statement.else_branch is not None:
                    for item in statement.else_branch:
                        validate_statement(item, owner)
                return
            if isinstance(statement, ProcedureCall):
                callee_name = statement.name.lower()
                if callee_name == update_name:
                    self._error(
                        statement.position,
                        DiagnosticCode.INVALID_CALLBACK_CALL_GRAPH,
                        f"VBlank callback path through {owner} calls update "
                        f"callback {statement.name}.",
                        "Keep update logic outside the NMI call graph.",
                        len(statement.name),
                    )
                callee = procedures[callee_name]
                if statement.arguments or callee.parameters:
                    self._error(
                        statement.position,
                        DiagnosticCode.INVALID_CALLBACK_CALL_GRAPH,
                        f"VBlank callback path through {owner} calls "
                        f"parameterized procedure {statement.name}.",
                        "Call only parameterless procedures from VBlank callbacks.",
                        len(statement.name),
                    )
                validate(callee)
                return

            position = self._statement_position_for_callback(statement)
            operation = self._callback_operation_name(statement)
            self._error(
                position,
                DiagnosticCode.VBLANK_UNSAFE_OPERATION,
                f"VBlank callback path through {owner} reaches unsupported "
                f"operation {operation}.",
                "Use only scalar assignments, simple inc/dec, bounded simple "
                "conditionals, and calls to transitively VBlank-safe procedures.",
                len(operation),
            )

        validate(root)

    def _vblank_expression_is_safe(self, value: ValueExpression) -> bool:
        if (
            isinstance(value, BuiltinCall)
            and _parsed_builtin_id(value)
            in (*CONTROLLER_QUERY_IDS, BuiltinId.GET_TILE)
        ):
            return False
        if isinstance(value, (BinaryExpression, ComparisonExpression)):
            return False
        if isinstance(value, (UnaryExpression, BooleanNotExpression)):
            return self._vblank_expression_is_safe(value.operand)
        if isinstance(value, ArrayIndexExpression):
            return self._vblank_expression_is_safe(value.index)
        if isinstance(value, RecordFieldExpression):
            return value.index is None or self._vblank_expression_is_safe(value.index)
        if isinstance(value, BooleanBinaryExpression):
            return self._vblank_expression_is_safe(
                value.left
            ) and self._vblank_expression_is_safe(value.right)
        return True

    def _vblank_unsafe_expression(
        self,
        value: ValueExpression,
        owner: str,
    ) -> None:
        tile_query = self._first_get_tile(value)
        if tile_query is not None:
            self._error(
                tile_query.position,
                DiagnosticCode.VBLANK_UNSAFE_OPERATION,
                f"VBlank callback path through {owner} queries nes.get_tile.",
                "Read the background shadow from main code or the update "
                "callback; NMI owns background queue consumption.",
                len("nes.get_tile"),
            )
        controller_query = self._first_controller_query(value)
        if controller_query is not None:
            command = controller_query.name
            self._error(
                controller_query.position,
                DiagnosticCode.VBLANK_UNSAFE_OPERATION,
                f"VBlank callback path through {owner} queries {command}.",
                "Query controller state from main code or the update callback; "
                "controller polling runs outside NMI.",
                len(command),
            )
        self._error(
            value.position,
            DiagnosticCode.VBLANK_UNSAFE_OPERATION,
            f"VBlank callback path through {owner} uses an expression that "
            "requires shared compiler temporary storage.",
            "Use literals, constants, variables, unary operations, or "
            "short-circuit boolean operations without arithmetic or comparisons.",
        )

    def _first_controller_query(
        self,
        value: ValueExpression,
    ) -> BuiltinCall | None:
        if (
            isinstance(value, BuiltinCall)
            and _parsed_builtin_id(value) in CONTROLLER_QUERY_IDS
        ):
            return value
        if isinstance(value, (UnaryExpression, BooleanNotExpression)):
            return self._first_controller_query(value.operand)
        if isinstance(value, ArrayIndexExpression):
            return self._first_controller_query(value.index)
        if isinstance(value, RecordFieldExpression) and value.index is not None:
            return self._first_controller_query(value.index)
        if isinstance(
            value,
            (BinaryExpression, BooleanBinaryExpression, ComparisonExpression),
        ):
            return self._first_controller_query(
                value.left
            ) or self._first_controller_query(value.right)
        if isinstance(value, BuiltinCall):
            for argument in value.arguments:
                found = self._first_controller_query(argument)
                if found is not None:
                    return found
        return None

    def _first_get_tile(self, value: ValueExpression) -> BuiltinCall | None:
        if (
            isinstance(value, BuiltinCall)
            and _parsed_builtin_id(value) is BuiltinId.GET_TILE
        ):
            return value
        if isinstance(value, (UnaryExpression, BooleanNotExpression)):
            return self._first_get_tile(value.operand)
        if isinstance(value, ArrayIndexExpression):
            return self._first_get_tile(value.index)
        if isinstance(value, RecordFieldExpression) and value.index is not None:
            return self._first_get_tile(value.index)
        if isinstance(
            value,
            (BinaryExpression, BooleanBinaryExpression, ComparisonExpression),
        ):
            return self._first_get_tile(value.left) or self._first_get_tile(value.right)
        if isinstance(value, BuiltinCall):
            for argument in value.arguments:
                found = self._first_get_tile(argument)
                if found is not None:
                    return found
        return None

    def _statement_position_for_callback(self, statement: Statement) -> SourcePosition:
        if isinstance(
            statement,
            (Assignment, ArrayElementAssignment, RecordFieldAssignment),
        ):
            return statement.target_position
        position = getattr(statement, "position", None)
        assert position is not None
        return position

    def _callback_operation_name(self, statement: Statement) -> str:
        if isinstance(statement, WhileStatement):
            return "while"
        if isinstance(statement, RepeatStatement):
            return "repeat"
        if isinstance(statement, ForStatement):
            return "for"
        if isinstance(statement, Run):
            return "nes.run"
        if isinstance(statement, BuiltinCall):
            return statement.name
        if isinstance(statement, ImportMetasprite):
            return "nes.import_metasprite"
        if isinstance(statement, LoadBackground):
            return "nes.load_background"
        if isinstance(statement, CallbackRegistration):
            return f"nes.on_{statement.kind.value}"
        if isinstance(statement, BreakStatement):
            return "break"
        assert isinstance(statement, ContinueStatement)
        return "continue"

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

    def _invalid_builtin_context(
        self,
        call: BuiltinCall,
        descriptor: BuiltinDescriptor,
    ) -> None:
        expected = (
            "a statement"
            if descriptor.kind is BuiltinKind.STATEMENT
            else "a value expression"
        )
        self._error(
            call.position,
            DiagnosticCode.INVALID_BUILTIN_CONTEXT,
            f"{descriptor.public_name} is {expected} and cannot be used here.",
            (
                f"Use {descriptor.public_name} as a standalone statement."
                if descriptor.kind is BuiltinKind.STATEMENT
                else f"Use the result of {descriptor.public_name} in an expression."
            ),
            len(descriptor.public_name),
        )

    def _require_builtin_argument_count(
        self,
        call: BuiltinCall,
        descriptor: BuiltinDescriptor,
    ) -> None:
        expected = len(descriptor.parameter_types)
        actual = len(call.arguments)
        if actual == expected:
            return
        self._error(
            call.position,
            descriptor.argument_count_diagnostic,
            f"{descriptor.public_name} expects exactly {expected} arguments, "
            f"but {actual} were provided.",
            descriptor.argument_count_suggestion,
            len(descriptor.public_name),
        )

    def _resolve_builtin_call(
        self,
        call: BuiltinCall,
        descriptor: BuiltinDescriptor,
        constants: dict[str, TypedConstant],
        variables: dict[str, ResolvedVariable],
        assigned_variables: set[str],
        *,
        queued: bool = False,
    ) -> ResolvedBuiltinCall:
        self._require_builtin_argument_count(call, descriptor)
        hook = descriptor.semantic_hook

        if hook is SemanticHook.CONTROLLER_QUERY:
            controller = self._resolve_controller_index(
                call.arguments[0], constants, variables, descriptor.public_name
            )
            _, button = self._resolve_controller_button(
                call.arguments[1], constants, variables, descriptor.public_name
            )
            arguments = (
                ImmediateValue(controller, BuiltInType.BYTE),
                ImmediateValue(button, BuiltInType.BYTE),
            )
        elif hook is SemanticHook.SPRITE_CREATE:
            arguments = (
                ImmediateValue(
                    self.sprite_allocation_plan.create_indexes[call.position],
                    BuiltInType.BYTE,
                ),
            )
        elif hook is SemanticHook.METASPRITE_CREATE:
            frame = self._static_metasprite_frame(
                call.arguments[0], constants, descriptor.public_name
            )
            arguments = (
                ImmediateValue(
                    self.sprite_allocation_plan.metasprite_create_indexes[
                        call.position
                    ],
                    BuiltInType.BYTE,
                ),
                ImmediateValue(frame.id, BuiltInType.METASPRITE_FRAME),
            )
        elif hook is SemanticHook.PALETTE:
            palette_index = self._resolve_palette_index(
                call.arguments[0],
                descriptor.id,
                constants,
                variables,
                descriptor.public_name,
            )
            arguments = (
                ImmediateValue(palette_index, BuiltInType.BYTE),
                *(
                    self._resolve_palette_color(
                        argument,
                        constants,
                        variables,
                        assigned_variables,
                        descriptor.public_name,
                    )
                    for argument in call.arguments[1:]
                ),
            )
        elif hook is SemanticHook.PALETTE_COLOR:
            palette_index = self._resolve_palette_index(
                call.arguments[0],
                descriptor.id,
                constants,
                variables,
                descriptor.public_name,
            )
            color_index = self._resolve_palette_color_index(
                call.arguments[1],
                constants,
                variables,
                descriptor.public_name,
            )
            arguments = (
                ImmediateValue(palette_index, BuiltInType.BYTE),
                ImmediateValue(color_index, BuiltInType.BYTE),
                self._resolve_palette_color(
                    call.arguments[2],
                    constants,
                    variables,
                    assigned_variables,
                    descriptor.public_name,
                ),
            )
        elif hook is SemanticHook.METASPRITE_OPERATION:
            arguments = self._resolve_metasprite_builtin_arguments(
                call,
                descriptor,
                constants,
                variables,
                assigned_variables,
            )
        else:
            arguments = tuple(
                self._resolve_value(
                    argument,
                    expected_type,
                    constants,
                    variables,
                    assigned_variables,
                )
                for argument, expected_type in zip(
                    call.arguments, descriptor.parameter_types, strict=True
                )
            )
            if hook is SemanticHook.TILE_COORDINATES:
                self._validate_immediate_coordinate(
                    arguments[0],
                    31,
                    "tile X",
                    call.position,
                    DiagnosticCode.INVALID_TILE_COORDINATE,
                )
                self._validate_immediate_coordinate(
                    arguments[1],
                    29,
                    "tile Y",
                    call.position,
                    DiagnosticCode.INVALID_TILE_COORDINATE,
                )
            elif hook is SemanticHook.ATTRIBUTE_COORDINATES:
                self._validate_immediate_coordinate(
                    arguments[0],
                    7,
                    "attribute X",
                    call.position,
                    DiagnosticCode.INVALID_ATTRIBUTE_COORDINATE,
                )
                self._validate_immediate_coordinate(
                    arguments[1],
                    7,
                    "attribute Y",
                    call.position,
                    DiagnosticCode.INVALID_ATTRIBUTE_COORDINATE,
                )
            elif (
                hook is SemanticHook.SPRITE_OPERATION
                and descriptor.id is BuiltinId.SPRITE_SET_PALETTE
                and isinstance(arguments[1], ImmediateValue)
                and arguments[1].value > 3
            ):
                argument = call.arguments[1]
                text = getattr(
                    argument,
                    "text",
                    getattr(argument, "name", str(arguments[1].value)),
                )
                self._error(
                    argument.position,
                    DiagnosticCode.INVALID_SPRITE_PALETTE,
                    f"Sprite palette {text} is outside the valid range $00..$03.",
                    "Use sprite palette $00, $01, $02, or $03.",
                    len(text),
                )

        return ResolvedBuiltinCall(
            descriptor.id,
            tuple(arguments),
            queued and bool(descriptor.queued_runtime_features),
        )

    def _resolve_metasprite_builtin_arguments(
        self,
        call: BuiltinCall,
        descriptor: BuiltinDescriptor,
        constants: dict[str, TypedConstant],
        variables: dict[str, ResolvedVariable],
        assigned_variables: set[str],
    ) -> tuple[ResolvedValue, ...]:
        instance = self._resolve_value(
            call.arguments[0],
            BuiltInType.METASPRITE,
            constants,
            variables,
            assigned_variables,
        )
        if descriptor.id is BuiltinId.METASPRITE_SET_FRAME:
            frame = self._static_metasprite_frame(
                call.arguments[1], constants, descriptor.public_name
            )
            self._validate_metasprite_asset(instance, frame.asset_name, frame.symbol, call)
            return (instance, ImmediateValue(frame.id, BuiltInType.METASPRITE_FRAME))
        if descriptor.id is BuiltinId.METASPRITE_SET_ANIMATION:
            animation = self._static_metasprite_animation(
                call.arguments[1], constants, descriptor.public_name
            )
            self._validate_metasprite_asset(
                instance, animation.asset_name, animation.symbol, call, animation=True
            )
            return (
                instance,
                ImmediateValue(animation.id, BuiltInType.METASPRITE_ANIMATION),
            )
        return (
            instance,
            *(
                self._resolve_value(
                    argument,
                    expected_type,
                    constants,
                    variables,
                    assigned_variables,
                )
                for argument, expected_type in zip(
                    call.arguments[1:],
                    descriptor.parameter_types[1:],
                    strict=True,
                )
            ),
        )

    def _validate_metasprite_asset(
        self,
        instance: ResolvedValue,
        asset_name: str,
        symbol: str,
        call: BuiltinCall,
        *,
        animation: bool = False,
    ) -> None:
        if not (
            isinstance(instance, ResolvedBuiltinCall)
            and instance.builtin is BuiltinId.METASPRITE_CREATE
        ):
            return
        instance_index = instance.arguments[0]
        assert isinstance(instance_index, ImmediateValue)
        created = self.sprite_allocation_plan.metasprite_instances[
            instance_index.value
        ]
        if created.asset_name == asset_name:
            return
        code = (
            DiagnosticCode.INVALID_METASPRITE_ANIMATION
            if animation
            else DiagnosticCode.INCOMPATIBLE_METASPRITE_FRAME
        )
        noun = "Animation" if animation else "Frame"
        self._error(
            call.arguments[1].position,
            code,
            f"{noun} {symbol} belongs to asset {asset_name}, but this "
            f"instance owns asset {created.asset_name}.",
            f"Select {'an animation' if animation else 'a frame'} from the "
            "same imported asset.",
            len(symbol),
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
        if isinstance(target.type, ArrayType):
            self._error(
                assignment.target_position,
                DiagnosticCode.INVALID_ARRAY_USAGE,
                f"Array {target.name} cannot be assigned as a whole value.",
                f"Assign one element, for example {target.name}[$00] := value.",
                len(target.name),
            )
        if isinstance(target.type, RecordType):
            self._error(
                assignment.target_position,
                DiagnosticCode.INVALID_RECORD_USAGE,
                f"Record {target.name} cannot be assigned as a whole value.",
                f"Assign one field, for example {target.name}.Field := value.",
                len(target.name),
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

    def _resolve_array_assignment(
        self,
        assignment: ArrayElementAssignment,
        constants: dict[str, TypedConstant],
        variables: dict[str, ResolvedVariable],
        assigned_variables: set[str],
    ) -> ResolvedArrayElementAssignment:
        normalized_target = assignment.target.lower()
        target = variables.get(normalized_target)
        if target is None:
            if normalized_target in constants:
                self._error(
                    assignment.target_position,
                    DiagnosticCode.ASSIGNMENT_TO_CONSTANT,
                    f"Cannot index and assign to constant {assignment.target}.",
                    "Use a declared array variable as the assignment target.",
                    len(assignment.target),
                )
            self._error(
                assignment.target_position,
                DiagnosticCode.UNKNOWN_ASSIGNMENT_TARGET,
                f"Unknown array variable: {assignment.target}.",
                "Declare the array in the var section before assigning it.",
                len(assignment.target),
            )
        if not isinstance(target.type, ArrayType):
            self._error(
                assignment.target_position,
                DiagnosticCode.INVALID_ARRAY_USAGE,
                f"Variable {target.name} has type {target.type.value} and cannot be indexed.",
                "Index only a variable declared with an array type.",
                len(target.name),
            )
        if isinstance(target.type.element_type, RecordType):
            self._error(
                assignment.target_position,
                DiagnosticCode.INVALID_RECORD_USAGE,
                f"Record array element {target.name}[...] cannot be assigned as a whole value.",
                f"Assign one field, for example {target.name}[$00].Field := value.",
                len(target.name),
            )

        # Index first, then value. The backend preserves this order for variable
        # indexes without reserving permanent Zero Page state.
        index = self._resolve_array_index(
            assignment.index,
            target,
            constants,
            variables,
            assigned_variables,
        )
        value = self._resolve_value(
            assignment.value,
            target.type.element_type,
            constants,
            variables,
            assigned_variables,
        )
        return ResolvedArrayElementAssignment(target, index, value)

    def _resolve_record_field_assignment(
        self,
        assignment: RecordFieldAssignment,
        constants: dict[str, TypedConstant],
        variables: dict[str, ResolvedVariable],
        assigned_variables: set[str],
    ) -> ResolvedRecordFieldAssignment:
        target = variables.get(assignment.target.lower())
        if target is None:
            self._error(
                assignment.target_position,
                DiagnosticCode.UNKNOWN_ASSIGNMENT_TARGET,
                f"Unknown record variable: {assignment.target}.",
                "Declare the record variable in the var section before assigning a field.",
                len(assignment.target),
            )
        record_type, index = self._resolve_record_container(
            target,
            assignment.index,
            assignment.target_position,
            constants,
            variables,
            assigned_variables,
        )
        field = record_type.field_named(assignment.field_name)
        if field is None:
            self._error(
                assignment.field_position,
                DiagnosticCode.UNKNOWN_RECORD_FIELD,
                f"Record {record_type.name} has no field named {assignment.field_name}.",
                "Use a field declared by the record type.",
                len(assignment.field_name),
            )
        self._validate_record_index_range(
            target,
            record_type,
            field,
            index,
            assignment.target_position,
        )
        field_target = ResolvedVariable(
            f"{target.name}.{field.name}",
            field.type,
            target.label,
            assignment.field_position,
        )
        value = self._resolve_value(
            assignment.value,
            field.type,
            constants,
            variables,
            assigned_variables,
            assignment_target=field_target,
        )
        return ResolvedRecordFieldAssignment(target, field, value, index)

    def _resolve_record_field_value(
        self,
        expression: RecordFieldExpression,
        expected_type: ScalarType,
        constants: dict[str, TypedConstant],
        variables: dict[str, ResolvedVariable],
        assigned_variables: set[str],
        assignment_target: ResolvedVariable | None,
    ) -> ResolvedRecordField:
        variable = variables.get(expression.record_name.lower())
        if variable is None:
            self._error(
                expression.position,
                DiagnosticCode.UNKNOWN_IDENTIFIER,
                f"Unknown record identifier: {expression.record_name}.",
                "Declare the record variable in the var section before reading a field.",
                len(expression.record_name),
            )
        record_type, index = self._resolve_record_container(
            variable,
            expression.index,
            expression.position,
            constants,
            variables,
            assigned_variables,
        )
        field = record_type.field_named(expression.field_name)
        if field is None:
            self._error(
                expression.field_position,
                DiagnosticCode.UNKNOWN_RECORD_FIELD,
                f"Record {record_type.name} has no field named {expression.field_name}.",
                "Use a field declared by the record type.",
                len(expression.field_name),
            )
        self._validate_record_index_range(
            variable,
            record_type,
            field,
            index,
            expression.position,
        )
        self._require_expression_result_type(
            expression.position,
            field.type,
            expected_type,
            f"Record field {variable.name}.{field.name}",
            assignment_target,
        )
        normalized_name = variable.name.lower()
        if normalized_name not in assigned_variables:
            if self.required_variables is not None:
                self.required_variables.add(normalized_name)
                assigned_variables.add(normalized_name)
            else:
                self._error(
                    expression.position,
                    DiagnosticCode.VARIABLE_READ_BEFORE_ASSIGNMENT,
                    f"Record variable {variable.name} is read before a field is assigned.",
                    f"Assign {variable.name}.{field.name} before reading the record.",
                    len(variable.name),
                )
        return ResolvedRecordField(variable, field, index)

    def _resolve_record_container(
        self,
        variable: ResolvedVariable,
        index_expression: ValueExpression | None,
        position: SourcePosition,
        constants: dict[str, TypedConstant],
        variables: dict[str, ResolvedVariable],
        assigned_variables: set[str],
    ) -> tuple[RecordType, ResolvedValue | None]:
        if index_expression is None:
            if not isinstance(variable.type, RecordType):
                self._error(
                    position,
                    DiagnosticCode.FIELD_ACCESS_ON_NON_RECORD,
                    f"Variable {variable.name} has type {variable.type.value} and has no record fields.",
                    "Access fields only on a record variable or an array of records.",
                    len(variable.name),
                )
            return variable.type, None
        if not (
            isinstance(variable.type, ArrayType)
            and isinstance(variable.type.element_type, RecordType)
        ):
            self._error(
                position,
                DiagnosticCode.FIELD_ACCESS_ON_NON_RECORD,
                f"Variable {variable.name} is not an array of records.",
                "Use indexed field access only with an array whose element type is a record.",
                len(variable.name),
            )
        index = self._resolve_array_index(
            index_expression,
            variable,
            constants,
            variables,
            assigned_variables,
        )
        return variable.type.element_type, index

    def _validate_record_index_range(
        self,
        variable: ResolvedVariable,
        record_type: RecordType,
        field: RecordField,
        index: ResolvedValue | None,
        position: SourcePosition,
    ) -> None:
        if index is None or isinstance(index, ImmediateValue):
            return
        assert isinstance(variable.type, ArrayType)
        maximum_offset = (
            (variable.type.element_count - 1) * record_type.size + field.offset
        )
        if record_type.size <= 0xFF and maximum_offset <= 0xFF:
            return
        self._error(
            position,
            DiagnosticCode.RECORD_LAYOUT_OVERFLOW,
            f"Variable indexing of {variable.name}.{field.name} can require byte "
            f"offset {maximum_offset}, beyond the 8-bit indexed range.",
            "Use constant indexes or reduce the record array so every scaled field offset is at most 255.",
            len(variable.name),
        )

    def _resolve_value(
        self,
        expression: ValueExpression,
        expected_type: ScalarType,
        constants: dict[str, TypedConstant],
        variables: dict[str, ResolvedVariable],
        assigned_variables: set[str],
        assignment_target: ResolvedVariable | None = None,
    ) -> ResolvedValue:
        if isinstance(expression, RecordFieldExpression):
            return self._resolve_record_field_value(
                expression,
                expected_type,
                constants,
                variables,
                assigned_variables,
                assignment_target,
            )
        if isinstance(expression, ArrayIndexExpression):
            return self._resolve_array_element(
                expression,
                expected_type,
                constants,
                variables,
                assigned_variables,
                assignment_target,
            )
        if isinstance(expression, BuiltinCall):
            descriptor = builtin_by_name(expression.name)
            assert descriptor is not None
            if descriptor.kind is not BuiltinKind.VALUE:
                self._invalid_builtin_context(expression, descriptor)
            assert descriptor.return_type is not None
            self._require_expression_result_type(
                expression.position,
                descriptor.return_type,
                expected_type,
                f"{descriptor.public_name} result",
                assignment_target,
            )
            return self._resolve_builtin_call(
                expression,
                descriptor,
                constants,
                variables,
                assigned_variables,
            )
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
            if isinstance(expected_type, EnumType):
                self._error(
                    expression.position,
                    DiagnosticCode.UNKNOWN_ENUM_MEMBER,
                    f"{expression.name} is not a member of enumeration "
                    f"{expected_type.value}.",
                    f"Use a member declared by {expected_type.value}.",
                    len(expression.name),
                )
            self._error(
                expression.position,
                DiagnosticCode.UNKNOWN_IDENTIFIER,
                f"Unknown identifier: {expression.name}.",
                "Declare the constant or variable before using it.",
            )
        if isinstance(variable.type, ArrayType):
            self._error(
                expression.position,
                DiagnosticCode.INVALID_ARRAY_USAGE,
                f"Array {variable.name} cannot be used as a scalar value.",
                f"Read one element, for example {variable.name}[$00].",
                len(expression.name),
            )
        if isinstance(variable.type, RecordType):
            self._error(
                expression.position,
                DiagnosticCode.INVALID_RECORD_USAGE,
                f"Record {variable.name} cannot be used as a scalar value.",
                f"Read one field, for example {variable.name}.Field.",
                len(expression.name),
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

    def _resolve_array_element(
        self,
        expression: ArrayIndexExpression,
        expected_type: ScalarType,
        constants: dict[str, TypedConstant],
        variables: dict[str, ResolvedVariable],
        assigned_variables: set[str],
        assignment_target: ResolvedVariable | None,
    ) -> ResolvedArrayElement:
        normalized_name = expression.array_name.lower()
        array = variables.get(normalized_name)
        if array is None:
            self._error(
                expression.position,
                DiagnosticCode.UNKNOWN_IDENTIFIER,
                f"Unknown array identifier: {expression.array_name}.",
                "Declare the array in the var section before using it.",
                len(expression.array_name),
            )
        if not isinstance(array.type, ArrayType):
            self._error(
                expression.position,
                DiagnosticCode.INVALID_ARRAY_USAGE,
                f"Variable {array.name} has type {array.type.value} and cannot be indexed.",
                "Index only a variable declared with an array type.",
                len(array.name),
            )
        if isinstance(array.type.element_type, RecordType):
            self._error(
                expression.position,
                DiagnosticCode.INVALID_RECORD_USAGE,
                f"Record array element {array.name}[...] cannot be used as a scalar value.",
                f"Read one field, for example {array.name}[$00].Field.",
                len(array.name),
            )
        self._require_expression_result_type(
            expression.position,
            array.type.element_type,
            expected_type,
            f"Array element {array.name}[...]",
            assignment_target,
        )
        index = self._resolve_array_index(
            expression.index,
            array,
            constants,
            variables,
            assigned_variables,
        )
        if normalized_name not in assigned_variables:
            if self.required_variables is not None:
                self.required_variables.add(normalized_name)
                assigned_variables.add(normalized_name)
            else:
                self._error(
                    expression.position,
                    DiagnosticCode.VARIABLE_READ_BEFORE_ASSIGNMENT,
                    f"Array {array.name} is read before an element is assigned.",
                    f"Assign {array.name}[index] before reading the array.",
                    len(array.name),
                )
        return ResolvedArrayElement(array, index)

    def _resolve_array_index(
        self,
        expression: ValueExpression,
        array: ResolvedVariable,
        constants: dict[str, TypedConstant],
        variables: dict[str, ResolvedVariable],
        assigned_variables: set[str],
    ) -> ResolvedValue:
        assert isinstance(array.type, ArrayType)
        type_hint = self._expression_type_hint(expression, constants, variables)
        if type_hint is not None and type_hint is not BuiltInType.BYTE:
            self._error(
                expression.position,
                DiagnosticCode.INVALID_ARRAY_INDEX_TYPE,
                f"Array index for {array.name} must have type byte, but "
                f"the expression has type {type_hint.value}.",
                "Use a byte expression as the array index.",
            )
        resolved = self._resolve_value(
            expression,
            BuiltInType.BYTE,
            constants,
            variables,
            assigned_variables,
        )
        constant_index = self._constant_byte_value(expression, constants)
        if constant_index is None:
            return resolved
        if not array.type.lower_bound <= constant_index <= array.type.upper_bound:
            self._error(
                expression.position,
                DiagnosticCode.ARRAY_INDEX_OUT_OF_BOUNDS,
                f"Index ${constant_index:02X} is outside {array.name}'s range "
                f"${array.type.lower_bound:02X}..${array.type.upper_bound:02X}.",
                "Use an index within the declared array bounds.",
            )
        return ImmediateValue(
            constant_index - array.type.lower_bound,
            BuiltInType.BYTE,
        )

    def _constant_byte_value(
        self,
        expression: ValueExpression,
        constants: dict[str, TypedConstant],
    ) -> int | None:
        if isinstance(expression, HexLiteral):
            return expression.value if expression.value <= 0xFF else None
        if isinstance(expression, ConstantReference):
            constant = constants.get(expression.name.lower())
            if constant is not None and constant.type is BuiltInType.BYTE:
                return constant.value
            return None
        if isinstance(expression, UnaryExpression):
            operand = self._constant_byte_value(expression.operand, constants)
            if operand is None:
                return None
            return operand if expression.operator.value == "+" else (-operand) & 0xFF
        if isinstance(expression, BinaryExpression):
            left = self._constant_byte_value(expression.left, constants)
            right = self._constant_byte_value(expression.right, constants)
            if left is None or right is None:
                return None
            if expression.operator.value == "+":
                return (left + right) & 0xFF
            return (left - right) & 0xFF
        return None

    def _resolve_controller_index(
        self,
        argument: ValueExpression,
        constants: dict[str, TypedConstant],
        variables: dict[str, ResolvedVariable],
        command: str,
    ) -> int:
        if isinstance(argument, BooleanLiteral):
            self._controller_argument_type_error(
                argument.position,
                command,
                "controller index",
                "boolean",
            )
        if isinstance(argument, HexLiteral):
            value = argument.value
            position = argument.position
            text = argument.text
        elif isinstance(argument, ConstantReference):
            normalized = argument.name.lower()
            constant = constants.get(normalized)
            if constant is None:
                self._error(
                    argument.position,
                    DiagnosticCode.UNKNOWN_IDENTIFIER,
                    f"Unknown identifier: {argument.name}.",
                    "Declare a byte constant with value $01 or $02.",
                    len(argument.name),
                )
            if constant.type is not BuiltInType.BYTE:
                self._controller_argument_type_error(
                    argument.position,
                    command,
                    "controller index",
                    constant.type.value,
                )
            value = constant.value
            position = argument.position
            text = argument.name
        elif isinstance(argument, VariableReference):
            variable = variables.get(argument.name.lower())
            if variable is not None and variable.type is not BuiltInType.BYTE:
                self._controller_argument_type_error(
                    argument.position,
                    command,
                    "controller index",
                    variable.type.value,
                )
            self._error(
                argument.position,
                DiagnosticCode.DYNAMIC_CONTROLLER_INDEX,
                f"{command} requires a compile-time controller index; "
                f"{argument.name} is dynamic.",
                "Pass $01, $02, or a byte constant with one of those values.",
                len(argument.name),
            )
        else:
            actual_type = self._expression_type_hint(
                argument,
                constants,
                variables,
            )
            if actual_type is BuiltInType.BOOLEAN:
                self._controller_argument_type_error(
                    argument.position,
                    command,
                    "controller index",
                    "boolean",
                )
            self._error(
                argument.position,
                DiagnosticCode.DYNAMIC_CONTROLLER_INDEX,
                f"{command} requires a direct compile-time controller index.",
                "Pass $01, $02, or a byte constant with one of those values.",
            )

        if value not in (1, 2):
            self._error(
                position,
                DiagnosticCode.INVALID_CONTROLLER_INDEX,
                f"Controller index {text} is invalid for {command}.",
                "Use controller $01 or $02.",
                len(text),
            )
        return value

    def _validate_immediate_coordinate(
        self,
        value: ResolvedValue,
        maximum: int,
        description: str,
        position: SourcePosition,
        code: DiagnosticCode,
    ) -> None:
        if not isinstance(value, ImmediateValue) or value.value <= maximum:
            return
        self._error(
            position,
            code,
            f"The {description} coordinate must be between 0 and {maximum}, "
            f"but {value.value} was provided.",
            f"Use a {description} coordinate from 0 through {maximum}.",
        )

    def _resolve_palette_index(
        self,
        argument: ValueExpression,
        builtin_id: BuiltinId,
        constants: dict[str, TypedConstant],
        variables: dict[str, ResolvedVariable],
        command: str,
    ) -> int:
        code = (
            DiagnosticCode.INVALID_BACKGROUND_PALETTE_INDEX
            if builtin_id
            in (
                BuiltinId.SET_BACKGROUND_PALETTE,
                BuiltinId.SET_BACKGROUND_PALETTE_COLOR,
            )
            else DiagnosticCode.INVALID_SPRITE_PALETTE_INDEX
        )
        return self._resolve_fixed_palette_index(
            argument,
            constants,
            variables,
            command,
            "palette",
            code,
        )

    def _resolve_palette_color_index(
        self,
        argument: ValueExpression,
        constants: dict[str, TypedConstant],
        variables: dict[str, ResolvedVariable],
        command: str,
    ) -> int:
        return self._resolve_fixed_palette_index(
            argument,
            constants,
            variables,
            command,
            "color",
            DiagnosticCode.INVALID_PALETTE_COLOR_INDEX,
        )

    def _resolve_fixed_palette_index(
        self,
        argument: ValueExpression,
        constants: dict[str, TypedConstant],
        variables: dict[str, ResolvedVariable],
        command: str,
        description: str,
        code: DiagnosticCode,
    ) -> int:
        value: int | None = None
        text = getattr(argument, "text", getattr(argument, "name", "expression"))
        if isinstance(argument, HexLiteral):
            value = argument.value
        elif isinstance(argument, ConstantReference):
            constant = constants.get(argument.name.lower())
            if constant is None:
                self._resolve_value(
                    argument,
                    BuiltInType.BYTE,
                    constants,
                    variables,
                    set(),
                )
                raise AssertionError("unreachable")
            if constant.type is not BuiltInType.BYTE:
                self._palette_argument_type_error(
                    argument.position,
                    command,
                    f"{description} index",
                    constant.type,
                )
            value = constant.value
        else:
            actual_type = self._expression_type_hint(argument, constants, variables)
            if actual_type is not None and actual_type is not BuiltInType.BYTE:
                self._palette_argument_type_error(
                    argument.position,
                    command,
                    f"{description} index",
                    actual_type,
                )
            self._error(
                argument.position,
                code,
                f"The {description} index for {command} must be a compile-time "
                "byte value in $00..$03.",
                "Use $00, $01, $02, $03, or a byte constant with one of those values.",
                len(str(text)),
            )
        assert value is not None
        if value > 3:
            self._error(
                argument.position,
                code,
                f"{description.capitalize()} index {text} is invalid for {command}.",
                "Use an index in the range $00..$03.",
                len(str(text)),
            )
        return value

    def _resolve_palette_color(
        self,
        argument: ValueExpression,
        constants: dict[str, TypedConstant],
        variables: dict[str, ResolvedVariable],
        assigned_variables: set[str],
        command: str,
    ) -> ResolvedValue:
        actual_type = self._expression_type_hint(argument, constants, variables)
        if actual_type is not None and actual_type is not BuiltInType.NES_COLOR:
            self._palette_argument_type_error(
                argument.position,
                command,
                "color",
                actual_type,
            )
        return self._resolve_value(
            argument,
            BuiltInType.NES_COLOR,
            constants,
            variables,
            assigned_variables,
        )

    def _palette_argument_type_error(
        self,
        position: SourcePosition,
        command: str,
        argument_name: str,
        actual_type: BuiltInType,
    ) -> None:
        expected = "byte" if "index" in argument_name else "nes_color"
        self._error(
            position,
            DiagnosticCode.INVALID_PALETTE_ARGUMENT_TYPE,
            f"The {argument_name} argument to {command} has type "
            f"{actual_type.value}, but {expected} is required.",
            f"Use a {expected} value for the {argument_name} argument.",
        )

    def _resolve_controller_button(
        self,
        argument: ValueExpression,
        constants: dict[str, TypedConstant],
        variables: dict[str, ResolvedVariable],
        command: str,
    ) -> tuple[str, int]:
        if isinstance(argument, ConstantReference):
            normalized = argument.name.lower()
            mask = CONTROLLER_BUTTONS.get(normalized)
            if mask is not None:
                return normalized, mask
            constant = constants.get(normalized)
            if constant is not None and constant.type is not BuiltInType.BYTE:
                self._controller_argument_type_error(
                    argument.position,
                    command,
                    "button",
                    constant.type.value,
                )
        elif isinstance(argument, BooleanLiteral):
            self._controller_argument_type_error(
                argument.position,
                command,
                "button",
                "boolean",
            )
        elif isinstance(argument, VariableReference):
            variable = variables.get(argument.name.lower())
            if variable is not None and variable.type is not BuiltInType.BYTE:
                self._controller_argument_type_error(
                    argument.position,
                    command,
                    "button",
                    variable.type.value,
                )

        position = argument.position
        text = getattr(argument, "name", getattr(argument, "text", "expression"))
        self._error(
            position,
            DiagnosticCode.INVALID_CONTROLLER_BUTTON,
            f"{text} is not a valid controller button for {command}.",
            "Use exactly one of nes.button_a, nes.button_b, "
            "nes.button_select, nes.button_start, nes.button_up, "
            "nes.button_down, nes.button_left, or nes.button_right.",
            len(text),
        )

    def _controller_argument_type_error(
        self,
        position: SourcePosition,
        command: str,
        argument_name: str,
        actual_type: str,
    ) -> None:
        self._error(
            position,
            DiagnosticCode.INVALID_CONTROLLER_ARGUMENT_TYPE,
            f"The {argument_name} argument to {command} has type "
            f"{actual_type}, but a byte constant is required.",
            "Use $01 or $02 for the controller and a nes.button_* constant "
            "for the button.",
        )

    def _resolve_arithmetic_expression(
        self,
        expression: UnaryExpression | BinaryExpression,
        expected_type: ScalarType,
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
        expected_type: ScalarType,
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
        expected_type: ScalarType,
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
        comparison_types = (
            self._expression_type_hint(expression.left, constants, variables),
            self._expression_type_hint(expression.right, constants, variables),
        )
        record_type = next(
            (type_ for type_ in comparison_types if isinstance(type_, RecordType)),
            None,
        )
        if record_type is not None:
            self._error(
                expression.position,
                DiagnosticCode.INVALID_RECORD_USAGE,
                f"Whole-record comparison is not supported for type {record_type.name}.",
                "Compare individual record fields instead.",
                len(expression.operator.value),
            )
        ordered_operators = {
            ComparisonOperator.LESS,
            ComparisonOperator.GREATER,
            ComparisonOperator.LESS_EQUAL,
            ComparisonOperator.GREATER_EQUAL,
        }
        if expression.operator in ordered_operators:
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
            enum_type = next(
                (
                    type_
                    for type_ in (left_type, right_type)
                    if isinstance(type_, EnumType)
                ),
                None,
            )
            if enum_type is not None:
                self._error(
                    expression.position,
                    DiagnosticCode.INVALID_ENUM_COMPARISON,
                    f"Enumeration {enum_type.value} supports only '=' and '<>' "
                    "comparisons.",
                    "Compare enum values for equality or inequality.",
                    len(expression.operator.value),
                )
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
    ) -> ScalarType | RecordType | None:
        if isinstance(expression, RecordFieldExpression):
            variable = variables.get(expression.record_name.lower())
            if variable is None:
                return None
            record_type = (
                variable.type
                if expression.index is None and isinstance(variable.type, RecordType)
                else variable.type.element_type
                if expression.index is not None
                and isinstance(variable.type, ArrayType)
                and isinstance(variable.type.element_type, RecordType)
                else None
            )
            if record_type is None:
                return None
            field = record_type.field_named(expression.field_name)
            return field.type if field is not None else None
        if isinstance(expression, ArrayIndexExpression):
            variable = variables.get(expression.array_name.lower())
            if variable is not None and isinstance(variable.type, ArrayType):
                return variable.type.element_type
            return None
        if isinstance(expression, BuiltinCall):
            descriptor = builtin_by_name(expression.name)
            assert descriptor is not None
            return descriptor.return_type
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
        return (
            variable.type
            if variable is not None and not isinstance(variable.type, ArrayType)
            else None
        )

    def _require_expression_result_type(
        self,
        position: SourcePosition,
        actual_type: ScalarType,
        expected_type: ScalarType,
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
            f"Use the expression only where a {expected_type.value} value is expected.",
        )

    def _require_matching_type(
        self,
        name: str,
        position: SourcePosition,
        actual_type: ScalarType,
        expected_type: ScalarType,
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
        expected_type: ScalarType,
        assignment_target: ResolvedVariable | None = None,
    ) -> int:
        if isinstance(expected_type, EnumType):
            self._literal_type_error(
                literal,
                "boolean" if isinstance(literal, BooleanLiteral) else "hexadecimal",
                expected_type,
                assignment_target,
            )
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
        if expected_type in (
            BuiltInType.METASPRITE,
            BuiltInType.METASPRITE_FRAME,
        ):
            self._error(
                literal.position,
                DiagnosticCode.INVALID_METASPRITE_VALUE,
                f"A hexadecimal literal cannot identify a {expected_type.value}.",
                "Create a metasprite with nes.metasprite_create(frame) or use "
                "an imported symbolic frame.",
                len(literal.text),
            )
        if expected_type is BuiltInType.NES_COLOR and literal.value > 0x3F:
            self._error(
                literal.position,
                DiagnosticCode.INVALID_NES_COLOR_VALUE,
                f"Value {literal.text} is not valid for type nes_color.",
                "Allowed range: $00..$3F.",
                len(literal.text),
            )
        if expected_type is BuiltInType.SPRITE and literal.value > 0x3F:
            self._error(
                literal.position,
                DiagnosticCode.INVALID_SPRITE_VALUE,
                f"Value {literal.text} is not valid for type sprite.",
                "Allowed range: $00..$3F (hardware sprites 0..63).",
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
        expected_type: ScalarType,
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
        run_commands = [
            (index, statement)
            for index, statement in enumerate(program.statements)
            if isinstance(statement, Run)
        ]
        if not run_commands:
            assert program.end_position is not None
            self._error(
                program.end_position,
                DiagnosticCode.MISSING_RUN,
                "The program must start the runtime with nes.run.",
                "Add one unconditional nes.run; call to the main program block.",
            )
        run_index, _ = run_commands[0]
        if len(run_commands) > 1:
            duplicate = run_commands[1][1]
            assert duplicate.position is not None
            self._error(
                duplicate.position,
                DiagnosticCode.STATEMENT_AFTER_RUN,
                "nes.run may appear only once.",
                "Remove the later nes.run; call.",
                len("nes.run"),
            )

        color_commands = [
            (index, statement)
            for index, statement in enumerate(program.statements)
            if isinstance(statement, BuiltinCall)
            and _parsed_builtin_id(statement) is BuiltinId.SET_BACKGROUND_COLOR
            and index < run_index
        ]
        if len(color_commands) != 1:
            position = (
                color_commands[1][1].position
                if len(color_commands) > 1
                else program.end_position
            )
            assert position is not None
            self._error(
                position,
                DiagnosticCode.INVALID_BACKGROUND_COLOR_CALL_COUNT,
                "The program must set its initial background color exactly once.",
                "Add one nes.set_background_color(value); call before nes.run;.",
            )
        background_loads = [
            statement
            for statement in program.statements
            if isinstance(statement, LoadBackground)
        ]
        if len(background_loads) > 1:
            self._error(
                background_loads[1].position,
                DiagnosticCode.DUPLICATE_BACKGROUND_LOAD,
                "nes.load_background may appear at most once.",
                "Remove the later nes.load_background(); call.",
                len("nes.load_background"),
            )
        early_wait = self._first_wait_frame(program.statements[:run_index])
        if early_wait is not None:
            assert early_wait.position is not None
            self._error(
                early_wait.position,
                DiagnosticCode.FRAME_WAIT_BEFORE_RUNTIME,
                "nes.wait_frame cannot execute before nes.run starts NMI.",
                "Move nes.wait_frame; and its containing frame loop after nes.run;.",
                len("nes.wait_frame"),
            )

    def _first_wait_frame(
        self,
        statements: tuple[Statement, ...],
    ) -> BuiltinCall | None:
        for statement in statements:
            if (
                isinstance(statement, BuiltinCall)
                and _parsed_builtin_id(statement) is BuiltinId.WAIT_FRAME
            ):
                return statement
            if isinstance(statement, IfStatement):
                found = self._first_wait_frame(statement.then_branch)
                if found is not None:
                    return found
                if statement.else_branch is not None:
                    found = self._first_wait_frame(statement.else_branch)
                    if found is not None:
                        return found
            elif isinstance(
                statement,
                (WhileStatement, RepeatStatement, ForStatement),
            ):
                found = self._first_wait_frame(statement.body)
                if found is not None:
                    return found
        return None

    def _statement_position(
        self,
        statement: Statement,
        program: Program,
    ) -> SourcePosition:
        if isinstance(
            statement,
            (Assignment, ArrayElementAssignment, RecordFieldAssignment),
        ):
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
                BuiltinCall,
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
    program: Program,
    source: str,
    filename: str = "<input>",
    *,
    metasprite_assets: tuple[MetaspriteAsset, ...] = (),
) -> ResolvedProgram:
    return SemanticAnalyzer(source, filename, metasprite_assets).analyze(program)
