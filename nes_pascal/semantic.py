"""Semantic validation, name resolution, and strict type checking."""

from dataclasses import dataclass, fields, is_dataclass
from typing import Iterator

from .ast import (
    Assignment,
    BackgroundUpdatesOverflowed,
    BinaryExpression,
    BooleanBinaryExpression,
    BooleanLiteral,
    BooleanNotExpression,
    BreakStatement,
    BuiltInType,
    CallbackKind,
    CallbackRegistration,
    ClearBackgroundUpdates,
    ClearBackgroundUpdateOverflow,
    ControllerQuery,
    ComparisonExpression,
    ComparisonOperator,
    ConstantDeclaration,
    ConstantReference,
    ContinueStatement,
    DecrementStatement,
    ForStatement,
    GetTile,
    HexLiteral,
    IfStatement,
    ImmediateValue,
    IncrementStatement,
    ImportMetasprite,
    LoadBackground,
    MetaspriteAsset,
    MetaspriteAnimation,
    MetaspriteAnimationFinished,
    MetaspriteCreate,
    MetaspriteFrame,
    MetaspriteInstance,
    MetaspriteOperation,
    MetaspriteOperationKind,
    OamOwnerKind,
    OamReservation,
    PaletteKind,
    Program,
    ProcedureCall,
    ProcedureDeclaration,
    RepeatStatement,
    ResolvedArgument,
    ResolvedAssignment,
    ResolvedBackgroundUpdatesOverflowed,
    ResolvedBinaryExpression,
    ResolvedBooleanBinaryExpression,
    ResolvedBooleanNotExpression,
    ResolvedBreakStatement,
    ResolvedCallbackRegistration,
    ResolvedClearBackgroundUpdates,
    ResolvedClearBackgroundUpdateOverflow,
    ResolvedComparisonExpression,
    ResolvedControllerQuery,
    ResolvedContinueStatement,
    ResolvedDecrementStatement,
    ResolvedForStatement,
    ResolvedGetTile,
    ResolvedIfStatement,
    ResolvedIncrementStatement,
    ResolvedImportMetasprite,
    ResolvedLoadBackground,
    ResolvedMetaspriteCreate,
    ResolvedMetaspriteAnimationFinished,
    ResolvedMetaspriteOperation,
    ResolvedRepeatStatement,
    ResolvedProgram,
    ResolvedProcedure,
    ResolvedProcedureCall,
    ResolvedSetBackgroundColor,
    ResolvedSetAttribute,
    ResolvedSetPalette,
    ResolvedSetPaletteColor,
    ResolvedSetSpriteZero,
    ResolvedSpriteCreate,
    ResolvedSpriteOperation,
    ResolvedSetScroll,
    ResolvedSetTile,
    ResolvedStatement,
    ResolvedValue,
    ResolvedVariable,
    ResolvedWhileStatement,
    ResolvedUnaryExpression,
    Run,
    SetBackgroundColor,
    SetAttribute,
    SetPalette,
    SetPaletteColor,
    SetSpriteZero,
    SetScroll,
    SetTile,
    SourcePosition,
    SpriteCreate,
    SpriteOperation,
    SpriteOperationKind,
    Statement,
    UnaryExpression,
    ValueExpression,
    VariableValue,
    VariableReference,
    WaitFrame,
    WhileStatement,
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
        )

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
            if isinstance(node, SetSpriteZero):
                explicit_positions.setdefault(0, node.position)
            elif isinstance(node, SpriteOperation) and node.arguments:
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
                if isinstance(node, SpriteCreate)
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
                if isinstance(node, MetaspriteCreate)
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
        statements: tuple[
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
        runtime_started: bool,
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
            elif isinstance(statement, SetSpriteZero):
                if len(statement.arguments) != 4:
                    self._error(
                        statement.position,
                        DiagnosticCode.INVALID_SPRITE_ZERO_ARGUMENT_COUNT,
                        "nes.set_sprite_zero expects exactly 4 arguments "
                        "(x, y, tile, attributes), but "
                        f"{len(statement.arguments)} were provided.",
                        "Pass x, y, tile, and attributes as byte values.",
                        len("nes.set_sprite_zero"),
                    )
                x, y, tile, attributes = (
                    self._resolve_value(
                        argument,
                        BuiltInType.BYTE,
                        constants,
                        variables,
                        current_assignments,
                    )
                    for argument in statement.arguments
                )
                resolved_statements.append(
                    ResolvedSetSpriteZero(x, y, tile, attributes)
                )
            elif isinstance(statement, SpriteOperation):
                command = f"nes.sprite_{statement.kind.value}"
                unary = statement.kind in (
                    SpriteOperationKind.HIDE,
                    SpriteOperationKind.SHOW,
                )
                set_position = (
                    statement.kind is SpriteOperationKind.SET_POSITION
                )
                expected_count = 1 if unary else (3 if set_position else 2)
                if len(statement.arguments) != expected_count:
                    self._error(
                        statement.position,
                        DiagnosticCode.INVALID_SPRITE_ARGUMENT_COUNT,
                        f"{command} expects exactly {expected_count} argument(s), "
                        f"but {len(statement.arguments)} were provided.",
                        (
                            "Pass one sprite value."
                            if unary
                            else (
                            "Pass one sprite value followed by x and y."
                            if set_position
                            else (
                                "Pass one sprite value followed by the property "
                                "value."
                            )
                            )
                        ),
                        len(command),
                    )
                sprite = self._resolve_value(
                    statement.arguments[0],
                    BuiltInType.SPRITE,
                    constants,
                    variables,
                    current_assignments,
                )
                value: ResolvedValue | None = None
                secondary_value: ResolvedValue | None = None
                if not unary:
                    value_type = (
                        BuiltInType.BOOLEAN
                        if statement.kind
                        in (
                            SpriteOperationKind.SET_FLIP_HORIZONTAL,
                            SpriteOperationKind.SET_FLIP_VERTICAL,
                            SpriteOperationKind.SET_BEHIND_BACKGROUND,
                        )
                        else BuiltInType.BYTE
                    )
                    value = self._resolve_value(
                        statement.arguments[1],
                        value_type,
                        constants,
                        variables,
                        current_assignments,
                    )
                    if set_position:
                        secondary_value = self._resolve_value(
                            statement.arguments[2],
                            BuiltInType.BYTE,
                            constants,
                            variables,
                            current_assignments,
                        )
                    if (
                        statement.kind is SpriteOperationKind.SET_PALETTE
                        and isinstance(value, ImmediateValue)
                        and value.value > 3
                    ):
                        argument = statement.arguments[1]
                        text = getattr(
                            argument,
                            "text",
                            getattr(argument, "name", str(value.value)),
                        )
                        self._error(
                            argument.position,
                            DiagnosticCode.INVALID_SPRITE_PALETTE,
                            f"Sprite palette {text} is outside the valid range $00..$03.",
                            "Use sprite palette $00, $01, $02, or $03.",
                            len(text),
                        )
                resolved_statements.append(
                    ResolvedSpriteOperation(
                        statement.kind,
                        sprite,
                        value,
                        secondary_value,
                    )
                )
            elif isinstance(statement, ImportMetasprite):
                reference = statement.arguments[0]
                assert isinstance(reference, (ConstantReference, VariableReference))
                resolved_statements.append(
                    ResolvedImportMetasprite(reference.name.lower())
                )
            elif isinstance(statement, MetaspriteOperation):
                command = f"nes.metasprite_{statement.kind.value}"
                unary = statement.kind in (
                    MetaspriteOperationKind.HIDE,
                    MetaspriteOperationKind.SHOW,
                    MetaspriteOperationKind.RESTART_ANIMATION,
                )
                set_position = (
                    statement.kind is MetaspriteOperationKind.SET_POSITION
                )
                expected_count = 1 if unary else (3 if set_position else 2)
                if len(statement.arguments) != expected_count:
                    self._error(
                        statement.position,
                        DiagnosticCode.INVALID_METASPRITE_ARGUMENT_COUNT,
                        f"{command} expects exactly {expected_count} argument(s), "
                        f"but {len(statement.arguments)} were provided.",
                        "Pass the metasprite followed by the documented value(s).",
                        len(command),
                    )
                instance = self._resolve_value(
                    statement.arguments[0],
                    BuiltInType.METASPRITE,
                    constants,
                    variables,
                    current_assignments,
                )
                value: ResolvedValue | None = None
                secondary_value: ResolvedValue | None = None
                if set_position:
                    value = self._resolve_value(
                        statement.arguments[1],
                        BuiltInType.BYTE,
                        constants,
                        variables,
                        current_assignments,
                    )
                    secondary_value = self._resolve_value(
                        statement.arguments[2],
                        BuiltInType.BYTE,
                        constants,
                        variables,
                        current_assignments,
                    )
                elif statement.kind is MetaspriteOperationKind.SET_FRAME:
                    frame = self._static_metasprite_frame(
                        statement.arguments[1],
                        constants,
                        command,
                    )
                    value = ImmediateValue(frame.id, BuiltInType.METASPRITE_FRAME)
                    if isinstance(instance, ResolvedMetaspriteCreate):
                        created = self.sprite_allocation_plan.metasprite_instances[
                            instance.instance_index
                        ]
                        if created.asset_name != frame.asset_name:
                            self._error(
                                statement.arguments[1].position,
                                DiagnosticCode.INCOMPATIBLE_METASPRITE_FRAME,
                                f"Frame {frame.symbol} belongs to asset "
                                f"{frame.asset_name}, but this instance owns "
                                f"asset {created.asset_name}.",
                                "Select a frame from the same imported asset.",
                                len(frame.symbol),
                            )
                elif statement.kind is MetaspriteOperationKind.SET_ANIMATION:
                    animation = self._static_metasprite_animation(
                        statement.arguments[1],
                        constants,
                        command,
                    )
                    value = ImmediateValue(
                        animation.id,
                        BuiltInType.METASPRITE_ANIMATION,
                    )
                    if isinstance(instance, ResolvedMetaspriteCreate):
                        created = self.sprite_allocation_plan.metasprite_instances[
                            instance.instance_index
                        ]
                        if created.asset_name != animation.asset_name:
                            self._error(
                                statement.arguments[1].position,
                                DiagnosticCode.INVALID_METASPRITE_ANIMATION,
                                f"Animation {animation.symbol} belongs to asset "
                                f"{animation.asset_name}, but this instance owns "
                                f"asset {created.asset_name}.",
                                "Select an animation from the same imported asset.",
                                len(animation.symbol),
                            )
                elif not unary:
                    value = self._resolve_value(
                        statement.arguments[1],
                        BuiltInType.BOOLEAN,
                        constants,
                        variables,
                        current_assignments,
                    )
                resolved_statements.append(
                    ResolvedMetaspriteOperation(
                        statement.kind,
                        instance,
                        value,
                        secondary_value,
                    )
                )
            elif isinstance(statement, SetBackgroundColor):
                resolved_statements.append(
                    ResolvedSetBackgroundColor(
                        self._resolve_value(
                            statement.argument,
                            BuiltInType.NES_COLOR,
                            constants,
                            variables,
                            current_assignments,
                        ),
                        queued=runtime_started or inside_procedure,
                    )
                )
            elif isinstance(statement, SetTile):
                self._require_background_argument_count(
                    statement.position,
                    "nes.set_tile",
                    statement.arguments,
                    3,
                    DiagnosticCode.INVALID_SET_TILE_ARGUMENT_COUNT,
                    "Pass x, y, and tile as byte values.",
                )
                x, y, tile = (
                    self._resolve_value(
                        argument,
                        BuiltInType.BYTE,
                        constants,
                        variables,
                        current_assignments,
                    )
                    for argument in statement.arguments
                )
                self._validate_immediate_coordinate(
                    x,
                    31,
                    "tile X",
                    statement.position,
                    DiagnosticCode.INVALID_TILE_COORDINATE,
                )
                self._validate_immediate_coordinate(
                    y,
                    29,
                    "tile Y",
                    statement.position,
                    DiagnosticCode.INVALID_TILE_COORDINATE,
                )
                resolved_statements.append(ResolvedSetTile(x, y, tile))
            elif isinstance(statement, SetAttribute):
                self._require_background_argument_count(
                    statement.position,
                    "nes.set_attribute",
                    statement.arguments,
                    3,
                    DiagnosticCode.INVALID_SET_ATTRIBUTE_ARGUMENT_COUNT,
                    "Pass attribute X, attribute Y, and value as byte values.",
                )
                x, y, value = (
                    self._resolve_value(
                        argument,
                        BuiltInType.BYTE,
                        constants,
                        variables,
                        current_assignments,
                    )
                    for argument in statement.arguments
                )
                self._validate_immediate_coordinate(
                    x,
                    7,
                    "attribute X",
                    statement.position,
                    DiagnosticCode.INVALID_ATTRIBUTE_COORDINATE,
                )
                self._validate_immediate_coordinate(
                    y,
                    7,
                    "attribute Y",
                    statement.position,
                    DiagnosticCode.INVALID_ATTRIBUTE_COORDINATE,
                )
                resolved_statements.append(ResolvedSetAttribute(x, y, value))
            elif isinstance(statement, SetScroll):
                self._require_background_argument_count(
                    statement.position,
                    "nes.set_scroll",
                    statement.arguments,
                    2,
                    DiagnosticCode.INVALID_SET_SCROLL_ARGUMENT_COUNT,
                    "Pass horizontal and vertical scroll as byte values.",
                )
                x, y = (
                    self._resolve_value(
                        argument,
                        BuiltInType.BYTE,
                        constants,
                        variables,
                        current_assignments,
                    )
                    for argument in statement.arguments
                )
                resolved_statements.append(ResolvedSetScroll(x, y))
            elif isinstance(statement, ClearBackgroundUpdates):
                self._require_background_argument_count(
                    statement.position,
                    "nes.clear_background_updates",
                    statement.arguments,
                    0,
                    DiagnosticCode.INVALID_CLEAR_BACKGROUND_UPDATES_ARGUMENT_COUNT,
                    "Call nes.clear_background_updates(); without arguments.",
                )
                resolved_statements.append(ResolvedClearBackgroundUpdates())
            elif isinstance(statement, ClearBackgroundUpdateOverflow):
                self._require_background_argument_count(
                    statement.position,
                    "nes.clear_background_update_overflow",
                    statement.arguments,
                    0,
                    DiagnosticCode.INVALID_BACKGROUND_OVERFLOW_CLEAR_ARGUMENT_COUNT,
                    "Call nes.clear_background_update_overflow(); without arguments.",
                )
                resolved_statements.append(
                    ResolvedClearBackgroundUpdateOverflow()
                )
            elif isinstance(statement, SetPalette):
                command = f"nes.set_{statement.kind.value}_palette"
                if len(statement.arguments) != 5:
                    self._palette_argument_count_error(
                        statement.position,
                        command,
                        5,
                        len(statement.arguments),
                    )
                palette_index = self._resolve_palette_index(
                    statement.arguments[0],
                    statement.kind,
                    constants,
                    variables,
                    command,
                )
                colors = tuple(
                    self._resolve_palette_color(
                        argument,
                        constants,
                        variables,
                        current_assignments,
                        command,
                    )
                    for argument in statement.arguments[1:]
                )
                assert len(colors) == 4
                resolved_statements.append(
                    ResolvedSetPalette(
                        statement.kind,
                        palette_index,
                        colors,
                        queued=runtime_started or inside_procedure,
                    )
                )
            elif isinstance(statement, SetPaletteColor):
                command = f"nes.set_{statement.kind.value}_palette_color"
                if len(statement.arguments) != 3:
                    self._palette_argument_count_error(
                        statement.position,
                        command,
                        3,
                        len(statement.arguments),
                    )
                palette_index = self._resolve_palette_index(
                    statement.arguments[0],
                    statement.kind,
                    constants,
                    variables,
                    command,
                )
                color_index = self._resolve_palette_color_index(
                    statement.arguments[1],
                    constants,
                    variables,
                    command,
                )
                color = self._resolve_palette_color(
                    statement.arguments[2],
                    constants,
                    variables,
                    current_assignments,
                    command,
                )
                resolved_statements.append(
                    ResolvedSetPaletteColor(
                        statement.kind,
                        palette_index,
                        color_index,
                        color,
                        queued=runtime_started or inside_procedure,
                    )
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
            elif isinstance(statement, WaitFrame):
                if inside_procedure:
                    self._procedure_runtime_command_error(
                        statement.position,
                        "nes.wait_frame",
                    )
                resolved_statements.append(WaitFrame())
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
            if isinstance(statement, Assignment):
                if not self._vblank_expression_is_safe(statement.value):
                    self._vblank_unsafe_expression(statement.value, owner)
                return
            if isinstance(statement, SetSpriteZero):
                self._error(
                    statement.position,
                    DiagnosticCode.VBLANK_UNSAFE_OPERATION,
                    f"VBlank callback path through {owner} reaches unsupported "
                    "operation nes.set_sprite_zero.",
                    "Stage sprite 0 from the update callback; the runtime "
                    "commits it safely during NMI.",
                    len("nes.set_sprite_zero"),
                )
            if isinstance(statement, SpriteOperation):
                command = f"nes.sprite_{statement.kind.value}"
                self._error(
                    statement.position,
                    DiagnosticCode.VBLANK_UNSAFE_OPERATION,
                    f"VBlank callback path through {owner} reaches unsupported "
                    f"operation {command}.",
                    "Update the OAM shadow from main code or the update callback; "
                    "NMI owns OAM DMA.",
                    len(command),
                )
            if isinstance(statement, MetaspriteOperation):
                command = f"nes.metasprite_{statement.kind.value}"
                self._error(
                    statement.position,
                    DiagnosticCode.VBLANK_UNSAFE_OPERATION,
                    f"VBlank callback path through {owner} reaches unsupported "
                    f"operation {command}.",
                    "Update metasprites from main code or the update callback; "
                    "NMI owns OAM DMA.",
                    len(command),
                )
            if isinstance(
                statement,
                (
                    SetBackgroundColor,
                    SetPalette,
                    SetPaletteColor,
                    SetScroll,
                ),
            ):
                values = (
                    (statement.argument,)
                    if isinstance(statement, SetBackgroundColor)
                    else statement.arguments
                )
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
        if isinstance(value, (ControllerQuery, GetTile)):
            return False
        if isinstance(value, (BinaryExpression, ComparisonExpression)):
            return False
        if isinstance(value, (UnaryExpression, BooleanNotExpression)):
            return self._vblank_expression_is_safe(value.operand)
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
            command = f"nes.controller_{controller_query.kind.value}"
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
    ) -> ControllerQuery | None:
        if isinstance(value, ControllerQuery):
            return value
        if isinstance(value, (UnaryExpression, BooleanNotExpression)):
            return self._first_controller_query(value.operand)
        if isinstance(
            value,
            (BinaryExpression, BooleanBinaryExpression, ComparisonExpression),
        ):
            return self._first_controller_query(
                value.left
            ) or self._first_controller_query(value.right)
        return None

    def _first_get_tile(self, value: ValueExpression) -> GetTile | None:
        if isinstance(value, GetTile):
            return value
        if isinstance(value, (UnaryExpression, BooleanNotExpression)):
            return self._first_get_tile(value.operand)
        if isinstance(
            value,
            (BinaryExpression, BooleanBinaryExpression, ComparisonExpression),
        ):
            return self._first_get_tile(value.left) or self._first_get_tile(value.right)
        return None

    def _statement_position_for_callback(self, statement: Statement) -> SourcePosition:
        if isinstance(statement, Assignment):
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
        if isinstance(statement, WaitFrame):
            return "nes.wait_frame"
        if isinstance(statement, Run):
            return "nes.run"
        if isinstance(statement, SetBackgroundColor):
            return "nes.set_background_color"
        if isinstance(statement, SetPalette):
            return f"nes.set_{statement.kind.value}_palette"
        if isinstance(statement, SetPaletteColor):
            return f"nes.set_{statement.kind.value}_palette_color"
        if isinstance(statement, SetSpriteZero):
            return "nes.set_sprite_zero"
        if isinstance(statement, SpriteOperation):
            return f"nes.sprite_{statement.kind.value}"
        if isinstance(statement, MetaspriteOperation):
            return f"nes.metasprite_{statement.kind.value}"
        if isinstance(statement, ImportMetasprite):
            return "nes.import_metasprite"
        if isinstance(statement, LoadBackground):
            return "nes.load_background"
        if isinstance(statement, SetTile):
            return "nes.set_tile"
        if isinstance(statement, SetAttribute):
            return "nes.set_attribute"
        if isinstance(statement, SetScroll):
            return "nes.set_scroll"
        if isinstance(statement, ClearBackgroundUpdates):
            return "nes.clear_background_updates"
        if isinstance(statement, ClearBackgroundUpdateOverflow):
            return "nes.clear_background_update_overflow"
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
        if isinstance(expression, MetaspriteAnimationFinished):
            self._require_expression_result_type(
                expression.position,
                BuiltInType.BOOLEAN,
                expected_type,
                "nes.metasprite_animation_finished result",
                assignment_target,
            )
            if len(expression.arguments) != 1:
                self._error(
                    expression.position,
                    DiagnosticCode.INVALID_METASPRITE_ARGUMENT_COUNT,
                    "nes.metasprite_animation_finished expects exactly one "
                    f"argument, but {len(expression.arguments)} were provided.",
                    "Pass the metasprite instance to query.",
                    len("nes.metasprite_animation_finished"),
                )
            return ResolvedMetaspriteAnimationFinished(
                self._resolve_value(
                    expression.arguments[0],
                    BuiltInType.METASPRITE,
                    constants,
                    variables,
                    assigned_variables,
                )
            )
        if isinstance(expression, MetaspriteCreate):
            self._require_expression_result_type(
                expression.position,
                BuiltInType.METASPRITE,
                expected_type,
                "nes.metasprite_create result",
                assignment_target,
            )
            if len(expression.arguments) != 1:
                self._error(
                    expression.position,
                    DiagnosticCode.INVALID_METASPRITE_CREATE,
                    "nes.metasprite_create expects exactly one symbolic frame, "
                    f"but {len(expression.arguments)} arguments were provided.",
                    "Pass an imported frame such as player.idle_0.",
                    len("nes.metasprite_create"),
                )
            frame = self._static_metasprite_frame(
                expression.arguments[0],
                constants,
                "nes.metasprite_create",
            )
            instance_index = (
                self.sprite_allocation_plan.metasprite_create_indexes[
                    expression.position
                ]
            )
            return ResolvedMetaspriteCreate(instance_index, frame.id)
        if isinstance(expression, SpriteCreate):
            self._require_expression_result_type(
                expression.position,
                BuiltInType.SPRITE,
                expected_type,
                "nes.sprite_create result",
                assignment_target,
            )
            if expression.arguments:
                self._error(
                    expression.position,
                    DiagnosticCode.INVALID_SPRITE_CREATE_ARGUMENT_COUNT,
                    "nes.sprite_create expects exactly 0 arguments, but "
                    f"{len(expression.arguments)} were provided.",
                    "Call nes.sprite_create() without arguments.",
                    len("nes.sprite_create"),
                )
            index = self.sprite_allocation_plan.create_indexes[expression.position]
            return ResolvedSpriteCreate(index)
        if isinstance(expression, BackgroundUpdatesOverflowed):
            self._require_expression_result_type(
                expression.position,
                BuiltInType.BOOLEAN,
                expected_type,
                "nes.background_updates_overflowed result",
                assignment_target,
            )
            self._require_background_argument_count(
                expression.position,
                "nes.background_updates_overflowed",
                expression.arguments,
                0,
                DiagnosticCode.INVALID_BACKGROUND_OVERFLOW_QUERY_ARGUMENT_COUNT,
                "Call nes.background_updates_overflowed() without arguments.",
            )
            return ResolvedBackgroundUpdatesOverflowed()
        if isinstance(expression, GetTile):
            self._require_expression_result_type(
                expression.position,
                BuiltInType.BYTE,
                expected_type,
                "nes.get_tile result",
                assignment_target,
            )
            self._require_background_argument_count(
                expression.position,
                "nes.get_tile",
                expression.arguments,
                2,
                DiagnosticCode.INVALID_GET_TILE_ARGUMENT_COUNT,
                "Pass x and y as byte values.",
            )
            x, y = (
                self._resolve_value(
                    argument,
                    BuiltInType.BYTE,
                    constants,
                    variables,
                    assigned_variables,
                )
                for argument in expression.arguments
            )
            self._validate_immediate_coordinate(
                x,
                31,
                "tile X",
                expression.position,
                DiagnosticCode.INVALID_TILE_COORDINATE,
            )
            self._validate_immediate_coordinate(
                y,
                29,
                "tile Y",
                expression.position,
                DiagnosticCode.INVALID_TILE_COORDINATE,
            )
            return ResolvedGetTile(x, y)
        if isinstance(expression, ControllerQuery):
            return self._resolve_controller_query(
                expression,
                expected_type,
                constants,
                variables,
                assignment_target,
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

    def _resolve_controller_query(
        self,
        expression: ControllerQuery,
        expected_type: BuiltInType,
        constants: dict[str, TypedConstant],
        variables: dict[str, ResolvedVariable],
        assignment_target: ResolvedVariable | None,
    ) -> ResolvedControllerQuery:
        command = f"nes.controller_{expression.kind.value}"
        self._require_expression_result_type(
            expression.position,
            BuiltInType.BOOLEAN,
            expected_type,
            f"{command} result",
            assignment_target,
        )
        if len(expression.arguments) != 2:
            self._error(
                expression.position,
                DiagnosticCode.INVALID_CONTROLLER_ARGUMENT_COUNT,
                f"{command} expects exactly 2 arguments, but "
                f"{len(expression.arguments)} were provided.",
                f"Use {command}($01, nes.button_a) with one controller "
                "index and one button constant.",
                len(command),
            )

        controller_argument, button_argument = expression.arguments
        controller_index = self._resolve_controller_index(
            controller_argument,
            constants,
            variables,
            command,
        )
        button_name, button_mask = self._resolve_controller_button(
            button_argument,
            constants,
            variables,
            command,
        )
        return ResolvedControllerQuery(
            expression.kind,
            controller_index,
            button_mask,
            button_name,
        )

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

    def _require_background_argument_count(
        self,
        position: SourcePosition,
        command: str,
        arguments: tuple[ValueExpression, ...],
        expected: int,
        code: DiagnosticCode,
        suggestion: str,
    ) -> None:
        if len(arguments) == expected:
            return
        self._error(
            position,
            code,
            f"{command} expects exactly {expected} arguments, but "
            f"{len(arguments)} were provided.",
            suggestion,
            len(command),
        )

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

    def _palette_argument_count_error(
        self,
        position: SourcePosition,
        command: str,
        expected: int,
        actual: int,
    ) -> None:
        self._error(
            position,
            DiagnosticCode.INVALID_PALETTE_ARGUMENT_COUNT,
            f"{command} expects exactly {expected} arguments, but {actual} "
            "were provided.",
            (
                "Pass a byte palette index followed by four nes_color values."
                if expected == 5
                else "Pass byte palette and color indexes followed by one "
                "nes_color value."
            ),
            len(command),
        )

    def _resolve_palette_index(
        self,
        argument: ValueExpression,
        kind: PaletteKind,
        constants: dict[str, TypedConstant],
        variables: dict[str, ResolvedVariable],
        command: str,
    ) -> int:
        code = (
            DiagnosticCode.INVALID_BACKGROUND_PALETTE_INDEX
            if kind is PaletteKind.BACKGROUND
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
                ControllerQuery,
                GetTile,
                BackgroundUpdatesOverflowed,
                MetaspriteAnimationFinished,
            ),
        ):
            return (
                BuiltInType.BYTE
                if isinstance(expression, GetTile)
                else BuiltInType.BOOLEAN
            )
        if isinstance(expression, SpriteCreate):
            return BuiltInType.SPRITE
        if isinstance(expression, MetaspriteCreate):
            return BuiltInType.METASPRITE
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
            if isinstance(statement, SetBackgroundColor) and index < run_index
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
    ) -> WaitFrame | None:
        for statement in statements:
            if isinstance(statement, WaitFrame):
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
        statement: (
            Assignment
            | SetBackgroundColor
            | SetPalette
            | SetPaletteColor
            | LoadBackground
            | Run
            | WaitFrame
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
                WaitFrame,
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
