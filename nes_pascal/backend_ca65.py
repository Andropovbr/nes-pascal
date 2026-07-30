"""ca65 Assembly generation for an NROM-256 image."""

from .ast import (
    BinaryOperator,
    BooleanOperator,
    BuiltInType,
    CallbackKind,
    ControllerQueryKind,
    ComparisonOperator,
    ForDirection,
    ImmediateValue,
    ResolvedAssignment,
    ResolvedBinaryExpression,
    ResolvedBooleanBinaryExpression,
    ResolvedBooleanNotExpression,
    ResolvedBreakStatement,
    ResolvedCallbackRegistration,
    ResolvedComparisonExpression,
    ResolvedControllerQuery,
    ResolvedContinueStatement,
    ResolvedDecrementStatement,
    ResolvedForStatement,
    ResolvedIfStatement,
    ResolvedIncrementStatement,
    ResolvedProgram,
    ResolvedProcedure,
    ResolvedProcedureCall,
    ResolvedRepeatStatement,
    ResolvedSetBackgroundColor,
    ResolvedSetSpriteZero,
    ResolvedStatement,
    ResolvedUnaryExpression,
    ResolvedValue,
    ResolvedWhileStatement,
    Run,
    UnaryOperator,
    VariableValue,
    WaitFrame,
)
from .memory_layout import ProgramMemoryLayout, build_memory_layout


def generate(
    program: ResolvedProgram,
    layout: ProgramMemoryLayout | None = None,
) -> str:
    layout = layout or build_memory_layout(program)
    color_commands = [
        statement
        for statement in program.statements
        if isinstance(statement, ResolvedSetBackgroundColor)
    ]
    run_commands = [
        statement for statement in program.statements if isinstance(statement, Run)
    ]
    if len(color_commands) != 1 or len(run_commands) != 1:
        raise ValueError("invalid resolved AST for the current milestone")
    callback_registrations = {
        statement.kind: statement
        for statement in program.statements
        if isinstance(statement, ResolvedCallbackRegistration)
    }
    update_callback = callback_registrations.get(CallbackKind.UPDATE)
    vblank_callback = callback_registrations.get(CallbackKind.VBLANK)

    temporary_lines = [
        f"{symbol.assembly_symbol}: .res {symbol.size}"
        f" ; ${symbol.address:04X}: {symbol.purpose}"
        for symbol in layout.temporary_symbols
    ] or ["    ; no compiler temporaries required"]
    runtime_zero_page_lines = [
        f"{symbol.assembly_symbol}: .res {symbol.size}"
        f" ; ${symbol.address:04X}: {symbol.purpose}"
        for symbol in layout.runtime_symbols
        if symbol.region_name == layout.zero_page_runtime.name
    ]
    promoted_user_lines = [
        f"{symbol.assembly_symbol}: .res {symbol.size}"
        f" ; ${symbol.address:04X}: {symbol.source_name}: {symbol.type_name}"
        for symbol in layout.promoted_user_symbols
    ] or ["    ; no globals selected for automatic promotion"]
    regular_user_lines = [
        f"{symbol.assembly_symbol}: .res {symbol.size}"
        f" ; ${symbol.address:04X}: {symbol.source_name}: {symbol.type_name}"
        for symbol in layout.regular_user_symbols
    ] or ["    ; no user variables"]
    oam_symbol = next(
        symbol
        for symbol in layout.runtime_symbols
        if symbol.region_name == layout.oam_shadow.name
    )
    oam_declaration = (
        f"{oam_symbol.assembly_symbol}: .res {oam_symbol.size}"
        f" ; ${oam_symbol.address:04X}: {oam_symbol.purpose}"
    )
    runtime_data_lines = [
        f"{symbol.assembly_symbol}: .res {symbol.size}"
        f" ; ${symbol.address:04X}: {symbol.purpose}"
        for symbol in layout.runtime_symbols
        if symbol.region_name == layout.runtime_data.name
    ] or ["    ; no scalar regular-RAM runtime symbols required"]
    sprite_zero_enabled = any(
        symbol.assembly_symbol == "runtime_sprite_zero_ready"
        for symbol in layout.runtime_symbols
    )

    label_counter = [0]
    for_counter = [0]
    statement_lines = _generate_statements(
        program.statements,
        label_counter,
        (),
        for_counter,
        sprite_zero_enabled,
    )
    procedure_lines = _generate_procedures(
        program.procedures,
        label_counter,
        for_counter,
        sprite_zero_enabled,
    )

    temporaries = "\n".join(temporary_lines)
    runtime_zero_page_storage = "\n".join(runtime_zero_page_lines)
    promoted_user_storage = "\n".join(promoted_user_lines)
    regular_user_storage = "\n".join(regular_user_lines)
    runtime_data_storage = "\n".join(runtime_data_lines)
    statements = "\n".join(statement_lines)
    procedures = (
        "\n\n; Source: procedure declarations\n"
        + "\n".join(procedure_lines)
        if procedure_lines
        else ""
    )
    settings = layout.settings
    mapper_low = (settings.mapper_number & 0x0F) << 4
    mirroring_bit = 0 if settings.horizontal_mirroring else 1
    flags_6 = mapper_low | mirroring_bit
    flags_7 = settings.mapper_number & 0xF0
    clear_ram_lines = "\n".join(
        f"    sta ${address:04X}, x"
        for address in range(
            layout.physical_ram.start,
            layout.physical_ram.start + layout.physical_ram.size,
            0x100,
        )
    )
    vblank_callback_call = (
        "\n\n"
        "    ; Runtime: user VBlank callback after frame bookkeeping\n"
        f"    jsr {vblank_callback.procedure_label}"
        if vblank_callback is not None
        else ""
    )
    if update_callback is None:
        runtime_main_loop = """; Runtime: implicit stable loop after the main program finishes
@runtime_idle_loop:
    jmp @runtime_idle_loop"""
    else:
        runtime_main_loop = f"""; Runtime: frame-synchronized update callback loop
    ; Establish the frame baseline once when the callback loop starts.
    lda runtime_frame_counter
    sta runtime_last_processed_frame
@runtime_update_loop:
    lda runtime_frame_counter
    cmp runtime_last_processed_frame
    beq @runtime_update_loop
    ; Accept only the newest pending frame; never replay a backlog.
    sta runtime_last_processed_frame
    lda #$00
    sta runtime_frame_ready ; advisory latch only; counter comparison is authoritative
    lda runtime_last_processed_frame
    jsr runtime_update_controllers ; exactly once for the accepted frame
    jsr {update_callback.procedure_label}
    jmp @runtime_update_loop"""

    sprite_nmi_work = (
        """

    ; Runtime: commit a complete staged sprite 0, then upload OAM in VBlank
    lda runtime_sprite_zero_ready
    beq @skip_sprite_zero_commit
    lda #$00
    sta runtime_sprite_zero_ready
    lda runtime_sprite_zero_pending_y
    sta runtime_oam_shadow
    lda runtime_sprite_zero_pending_tile
    sta runtime_oam_shadow + 1
    lda runtime_sprite_zero_pending_attributes
    sta runtime_oam_shadow + 2
    lda runtime_sprite_zero_pending_x
    sta runtime_oam_shadow + 3
@skip_sprite_zero_commit:
    lda #$00
    sta $2003               ; OAM address
    lda #>runtime_oam_shadow
    sta $4014               ; page-aligned OAM DMA"""
        if sprite_zero_enabled
        else ""
    )
    chr_storage = _generate_chr_storage(settings.chr_rom_size, sprite_zero_enabled)
    return f"""; Generated by nes-pascal for program {program.name}
; Mapper {settings.mapper_number}, {settings.prg_rom_size // 1024} KiB PRG-ROM, {settings.chr_rom_size // 1024} KiB CHR-ROM

.segment "HEADER"
    .byte "NES", $1A
    .byte {settings.prg_rom_banks}                  ; PRG-ROM banks, 16 KiB each
    .byte {settings.chr_rom_banks}                  ; CHR-ROM banks, 8 KiB each
    .byte ${flags_6:02X}                ; mapper and mirroring flags
    .byte ${flags_7:02X}                ; mapper upper bits
    .byte $00, $00, $00, $00, $00, $00, $00, $00

.segment "ZERO_PAGE_RUNTIME": zeropage
; Runtime: frame synchronization state, isolated from compiler temporaries
{runtime_zero_page_storage}

.segment "ZERO_PAGE_TEMPORARIES": zeropage
; Compiler: mandatory expression and loop storage in Zero Page
{temporaries}

.segment "ZERO_PAGE_VARIABLES": zeropage
; Source: optional global-variable promotion with regular-RAM fallback
{promoted_user_storage}

.segment "OAM_SHADOW"
; Runtime: page-aligned OAM DMA shadow at ${layout.oam_shadow.start:04X}-${layout.oam_shadow.end:04X}
{oam_declaration}

.segment "RUNTIME_DATA"
; Runtime: regular-RAM state kept separate from user variables
{runtime_data_storage}

.segment "USER_VARIABLES"
; Source: non-promoted variables and all parameters in regular CPU RAM
{regular_user_storage}

.segment "CODE"

; Interrupt handlers
NMI:
    pha
    txa
    pha
    tya
    pha

    inc runtime_frame_counter ; volatile 8-bit counter, wraps modulo 256
    lda #$01
    sta runtime_frame_ready   ; advisory; frame counter is authoritative{vblank_callback_call}{sprite_nmi_work}

    pla
    tay
    pla
    tax
    pla
    rti

IRQ:
    rti

; Source: implicit NES runtime initialization
RESET:
    sei
    cld
    ldx #$40
    stx $4017               ; disable frame counter IRQ
    ldx #$FF
    txs
    inx                     ; X = 0
    stx $2000               ; disable NMI
    stx $2001               ; disable rendering
    stx $4010               ; disable DMC IRQ
    bit $2002               ; clear the vblank latch

@wait_vblank_1:
    bit $2002
    bpl @wait_vblank_1

    txa
@clear_ram:
{clear_ram_lines}
    inx
    bne @clear_ram

@wait_vblank_2:
    bit $2002
    bpl @wait_vblank_2
{statements}

{runtime_main_loop}

; Runtime: idempotent controller update for one newly processed frame
runtime_update_controllers:
    tax                     ; X keeps the caller's accepted frame value
    lda runtime_controller_poll_valid
    beq @controllers_need_poll
    txa
    cmp runtime_controller_polled_frame
    beq @controllers_already_current
@controllers_need_poll:
    lda #$01
    sta runtime_controller_poll_valid
    txa
    sta runtime_controller_polled_frame
    lda runtime_controller_1_current
    sta runtime_controller_1_previous
    lda runtime_controller_2_current
    sta runtime_controller_2_previous
    jsr runtime_read_controller_ports
@controllers_already_current:
    rts

; Runtime: isolated standard NES serial controller protocol
; Bit layout: A, B, Select, Start, Up, Down, Left, Right = bits 0..7.
runtime_read_controller_ports:
    lda #$01
    sta $4016               ; latch both controllers
    lda #$00
    sta $4016               ; begin serial reads
    sta runtime_controller_1_current
    sta runtime_controller_2_current
    ldx #$08
@read_controller_bits:
    lda $4016
    lsr a                   ; controller 1 serial bit -> carry
    ror runtime_controller_1_current
    lda $4017
    lsr a                   ; controller 2 serial bit -> carry
    ror runtime_controller_2_current
    dex
    bne @read_controller_bits
    rts
{procedures}

.segment "VECTORS"
    .word NMI
    .word RESET
    .word IRQ

.segment "CHR"
{chr_storage}
"""


def _generate_statements(
    statements: tuple[ResolvedStatement, ...],
    label_counter: list[int],
    loop_targets: tuple[tuple[str, str], ...],
    for_counter: list[int],
    sprite_zero_enabled: bool,
) -> list[str]:
    statement_lines: list[str] = []
    for statement in statements:
        if isinstance(statement, ResolvedAssignment):
            statement_lines.extend(
                [
                    "",
                    f"; Source: {statement.target.name} := value",
                    *_load_value(statement.value, label_counter),
                    f"    sta {statement.target.label}",
                ]
            )
        elif isinstance(statement, ResolvedSetBackgroundColor):
            statement_lines.extend(
                [
                    "",
                    "; Source: nes.set_background_color(value)",
                    "    lda #$3F",
                    "    sta $2006               ; universal palette address, high byte",
                    "    lda #$00",
                    "    sta $2006               ; low byte",
                    *_load_value(statement.argument, label_counter),
                    "    sta $2007",
                ]
            )
        elif isinstance(statement, Run):
            wait_vblank_label = _new_label(
                label_counter,
                "wait_render_vblank",
            )
            sprite_palette_lines = (
                [
                    "    ; Runtime: minimal palette for fixed sprite 0 support",
                    "    lda #$3F",
                    "    sta $2006",
                    "    lda #$11",
                    "    sta $2006",
                    "    lda #$16",
                    "    sta $2007",
                    "    lda #$27",
                    "    sta $2007",
                    "    lda #$30",
                    "    sta $2007",
                ]
                if sprite_zero_enabled
                else []
            )
            rendering_mask = 0x18 if sprite_zero_enabled else 0x08
            statement_lines.extend(
                [
                    "",
                    "; Source: nes.run",
                    "; Runtime: defer rendering-sensitive setup to VBlank",
                    f"{wait_vblank_label}:",
                    "    bit $2002",
                    f"    bpl {wait_vblank_label}",
                    *sprite_palette_lines,
                    "    lda #$00",
                    "    sta $2005               ; scroll X",
                    "    sta $2005               ; scroll Y",
                    "    lda #$80",
                    "    sta $2000               ; enable NMI after initialization",
                    f"    lda #${rendering_mask:02X}",
                    "    sta $2001               ; enable selected rendering layers",
                ]
            )
        elif isinstance(statement, WaitFrame):
            wait_frame_label = _new_label(label_counter, "wait_frame")
            statement_lines.extend(
                [
                    "",
                    "; Source: nes.wait_frame",
                    "; Runtime: wait for the volatile frame counter to change",
                    "    lda runtime_frame_counter",
                    f"{wait_frame_label}:",
                    "    cmp runtime_frame_counter",
                    f"    beq {wait_frame_label}",
                    "    lda #$00",
                    "    sta runtime_frame_ready ; consume advisory signal",
                    "    lda runtime_frame_counter ; accepted frame for polling",
                    "    jsr runtime_update_controllers ; fresh state for this frame",
                ]
            )
        elif isinstance(statement, ResolvedSetSpriteZero):
            statement_lines.extend(
                [
                    "",
                    "; Source: nes.set_sprite_zero(x, y, tile, attributes)",
                    "; Runtime: invalidate, stage all bytes, then publish atomically",
                    "    lda #$00",
                    "    sta runtime_sprite_zero_ready",
                    *_load_value(statement.x, label_counter),
                    "    sta runtime_sprite_zero_pending_x",
                    *_load_value(statement.y, label_counter),
                    "    sta runtime_sprite_zero_pending_y",
                    *_load_value(statement.tile, label_counter),
                    "    sta runtime_sprite_zero_pending_tile",
                    *_load_value(statement.attributes, label_counter),
                    "    sta runtime_sprite_zero_pending_attributes",
                    "    lda #$01",
                    "    sta runtime_sprite_zero_ready",
                ]
            )
        elif isinstance(statement, ResolvedIfStatement):
            then_label = _new_label(label_counter, "if_then")
            end_label = _new_label(label_counter, "if_end")
            else_label = (
                _new_label(label_counter, "if_else")
                if statement.else_branch is not None
                else end_label
            )
            statement_lines.extend(
                [
                    "",
                    "; Source: if condition then",
                    *_load_value(statement.condition, label_counter),
                    "    cmp #$00",
                    f"    bne {then_label}",
                    f"    jmp {else_label}       ; long-branch-safe false path",
                    f"{then_label}:",
                    *_generate_statements(
                        statement.then_branch,
                        label_counter,
                        loop_targets,
                        for_counter,
                        sprite_zero_enabled,
                    ),
                ]
            )
            if statement.else_branch is not None:
                statement_lines.extend(
                    [
                        f"    jmp {end_label}",
                        f"{else_label}:",
                        *_generate_statements(
                            statement.else_branch,
                            label_counter,
                            loop_targets,
                            for_counter,
                            sprite_zero_enabled,
                        ),
                    ]
                )
            statement_lines.append(f"{end_label}:")
        elif isinstance(statement, ResolvedWhileStatement):
            condition_label = _new_label(label_counter, "while_condition")
            body_label = _new_label(label_counter, "while_body")
            end_label = _new_label(label_counter, "while_end")
            statement_lines.extend(
                [
                    "",
                    "; Source: while condition do",
                    f"{condition_label}:",
                    *_load_value(statement.condition, label_counter),
                    "    cmp #$00",
                    f"    bne {body_label}",
                    f"    jmp {end_label}       ; long-branch-safe loop exit",
                    f"{body_label}:",
                    *_generate_statements(
                        statement.body,
                        label_counter,
                        (*loop_targets, (end_label, condition_label)),
                        for_counter,
                        sprite_zero_enabled,
                    ),
                    f"    jmp {condition_label}",
                    f"{end_label}:",
                ]
            )
        elif isinstance(statement, ResolvedRepeatStatement):
            body_label = _new_label(label_counter, "repeat_body")
            condition_label = _new_label(label_counter, "repeat_condition")
            end_label = _new_label(label_counter, "repeat_end")
            statement_lines.extend(
                [
                    "",
                    "; Source: repeat until condition",
                    f"{body_label}:",
                    *_generate_statements(
                        statement.body,
                        label_counter,
                        (*loop_targets, (end_label, condition_label)),
                        for_counter,
                        sprite_zero_enabled,
                    ),
                    f"{condition_label}:",
                    *_load_value(statement.condition, label_counter),
                    "    cmp #$00",
                    f"    bne {end_label}",
                    f"    jmp {body_label}       ; long-branch-safe repeat",
                    f"{end_label}:",
                ]
            )
        elif isinstance(statement, ResolvedIncrementStatement):
            statement_lines.extend(
                _generate_increment(statement, label_counter)
            )
        elif isinstance(statement, ResolvedDecrementStatement):
            statement_lines.extend(
                _generate_decrement(statement, label_counter)
            )
        elif isinstance(statement, ResolvedForStatement):
            for_index = for_counter[0]
            for_counter[0] += 1
            limit_temporary = f"for_limit_{for_index}"
            condition_label = _new_label(label_counter, "for_condition")
            body_label = _new_label(label_counter, "for_body")
            step_label = _new_label(label_counter, "for_step")
            end_label = _new_label(label_counter, "for_end")
            condition_branches = (
                [
                    f"    bcc {body_label}",
                    f"    beq {body_label}",
                ]
                if statement.direction is ForDirection.TO
                else [f"    bcs {body_label}"]
            )
            step_instruction = (
                f"    inc {statement.target.label}"
                if statement.direction is ForDirection.TO
                else f"    dec {statement.target.label}"
            )
            statement_lines.extend(
                [
                    "",
                    f"; Source: for variable := initial "
                    f"{statement.direction.value} final do",
                    *_load_value(statement.initial, label_counter),
                    f"    sta {statement.target.label}",
                    *_load_value(statement.final, label_counter),
                    f"    sta {limit_temporary}   ; evaluate final value once",
                    f"{condition_label}:",
                    f"    lda {statement.target.label}",
                    f"    cmp {limit_temporary}",
                    *condition_branches,
                    f"    jmp {end_label}       ; long-branch-safe loop exit",
                    f"{body_label}:",
                    *_generate_statements(
                        statement.body,
                        label_counter,
                        (*loop_targets, (end_label, step_label)),
                        for_counter,
                        sprite_zero_enabled,
                    ),
                    f"{step_label}:",
                    f"    lda {statement.target.label}",
                    f"    cmp {limit_temporary}",
                    f"    beq {end_label}        ; stop before byte wraparound",
                    step_instruction,
                    f"    jmp {condition_label}",
                    f"{end_label}:",
                ]
            )
        elif isinstance(statement, ResolvedProcedureCall):
            statement_lines.extend(["", f"; Source: {statement.name}"])
            for index, argument in enumerate(statement.arguments, start=1):
                statement_lines.extend(
                    [
                        f"    ; argument {index}: {argument.parameter.name}",
                        *_load_value(argument.value, label_counter),
                        f"    sta {argument.parameter.label}",
                    ]
                )
            statement_lines.append(f"    jsr {statement.label}")
        elif isinstance(statement, ResolvedCallbackRegistration):
            statement_lines.extend(
                [
                    "",
                    f"; Source: nes.on_{statement.kind.value}"
                    f"({statement.procedure_name})",
                    "; Runtime: static callback registration; no state emitted",
                ]
            )
        elif isinstance(statement, ResolvedBreakStatement):
            assert loop_targets
            break_label, _ = loop_targets[-1]
            statement_lines.extend(
                [
                    "",
                    "; Source: break",
                    f"    jmp {break_label}",
                ]
            )
        else:
            assert isinstance(statement, ResolvedContinueStatement)
            assert loop_targets
            _, continue_label = loop_targets[-1]
            statement_lines.extend(
                [
                    "",
                    "; Source: continue",
                    f"    jmp {continue_label}",
                ]
            )

    return statement_lines


def _generate_procedures(
    procedures: tuple[ResolvedProcedure, ...],
    label_counter: list[int],
    for_counter: list[int],
    sprite_zero_enabled: bool,
) -> list[str]:
    lines: list[str] = []
    for procedure in procedures:
        if lines:
            lines.append("")
        lines.extend(
            [
                f"; Procedure: {procedure.name}",
                f"{procedure.label}:",
                *_generate_statements(
                    procedure.body,
                    label_counter,
                    (),
                    for_counter,
                    sprite_zero_enabled,
                ),
                "    rts",
            ]
        )
    return lines


def _generate_increment(
    statement: ResolvedIncrementStatement,
    label_counter: list[int],
) -> list[str]:
    if statement.amount is None:
        return [
            "",
            f"; Source: inc({statement.target.name})",
            f"    inc {statement.target.label}",
        ]
    return [
        "",
        f"; Source: inc({statement.target.name}, amount)",
        *_load_value(statement.amount, label_counter),
        "    clc",
        f"    adc {statement.target.label}",
        f"    sta {statement.target.label}",
    ]


def _generate_decrement(
    statement: ResolvedDecrementStatement,
    label_counter: list[int],
) -> list[str]:
    if statement.amount is None:
        return [
            "",
            f"; Source: dec({statement.target.name})",
            f"    dec {statement.target.label}",
        ]
    return [
        "",
        f"; Source: dec({statement.target.name}, amount)",
        *_load_value(statement.amount, label_counter),
        "    sta expression_temporary_0",
        f"    lda {statement.target.label}",
        "    sec",
        "    sbc expression_temporary_0",
        f"    sta {statement.target.label}",
    ]


def _load_value(value: ResolvedValue, label_counter: list[int]) -> list[str]:
    if isinstance(value, ImmediateValue):
        if value.type is BuiltInType.BOOLEAN:
            description = "true" if value.value else "false"
            return [f"    lda #${value.value:02X}              ; {description}"]
        return [f"    lda #${value.value:02X}"]
    if isinstance(value, VariableValue):
        return [f"    lda {value.variable.label}"]
    if isinstance(value, ResolvedControllerQuery):
        return _load_controller_query(value, label_counter)
    if isinstance(value, ResolvedUnaryExpression):
        lines = _load_value(value.operand, label_counter)
        if value.operator is UnaryOperator.PLUS:
            return [*lines, "    ; unary + leaves the byte unchanged"]
        return [
            *lines,
            "    eor #$FF                ; unary -: two's complement",
            "    clc",
            "    adc #$01",
        ]

    if isinstance(value, ResolvedBinaryExpression):
        return _load_binary_expression(value, 0, label_counter)
    if isinstance(value, ResolvedComparisonExpression):
        return _load_comparison_expression(value, 0, label_counter)
    if isinstance(value, ResolvedBooleanNotExpression):
        return _load_boolean_not_expression(value, 0, label_counter)
    assert isinstance(value, ResolvedBooleanBinaryExpression)
    return _load_boolean_binary_expression(value, 0, label_counter)


def _load_controller_query(
    query: ResolvedControllerQuery,
    label_counter: list[int],
) -> list[str]:
    current = f"runtime_controller_{query.controller_index}_current"
    previous = f"runtime_controller_{query.controller_index}_previous"
    true_label = _new_label(label_counter, "controller_true")
    false_label = _new_label(label_counter, "controller_false")
    end_label = _new_label(label_counter, "controller_end")
    prefix = [
        f"    ; nes.controller_{query.kind.value}"
        f"(${query.controller_index:02X}, {query.button_name})",
    ]
    if query.kind is ControllerQueryKind.DOWN:
        checks = [
            f"    lda {current}",
            f"    and #${query.button_mask:02X}",
            f"    bne {true_label}",
        ]
    elif query.kind is ControllerQueryKind.PRESSED:
        checks = [
            f"    lda {current}",
            f"    and #${query.button_mask:02X}",
            f"    beq {false_label}",
            f"    lda {previous}",
            f"    and #${query.button_mask:02X}",
            f"    beq {true_label}",
        ]
    else:
        checks = [
            f"    lda {current}",
            f"    and #${query.button_mask:02X}",
            f"    bne {false_label}",
            f"    lda {previous}",
            f"    and #${query.button_mask:02X}",
            f"    bne {true_label}",
        ]
    return [
        *prefix,
        *checks,
        f"{false_label}:",
        "    lda #$00              ; false",
        f"    jmp {end_label}",
        f"{true_label}:",
        "    lda #$01              ; true",
        f"{end_label}:",
    ]


def _load_binary_expression(
    expression: ResolvedBinaryExpression,
    depth: int,
    label_counter: list[int],
) -> list[str]:
    temporary = f"expression_temporary_{depth}"
    lines = [
        f"    ; binary {expression.operator.value}: evaluate right operand",
        *_load_value_at_depth(expression.right, depth + 1, label_counter),
        f"    sta {temporary}",
        "    ; evaluate left operand",
        *_load_value_at_depth(expression.left, depth + 1, label_counter),
    ]
    if expression.operator is BinaryOperator.ADD:
        return [*lines, "    clc", f"    adc {temporary}"]
    return [*lines, "    sec", f"    sbc {temporary}"]


def _load_value_at_depth(
    value: ResolvedValue,
    depth: int,
    label_counter: list[int],
) -> list[str]:
    if isinstance(value, ResolvedBinaryExpression):
        return _load_binary_expression(value, depth, label_counter)
    if isinstance(value, ResolvedComparisonExpression):
        return _load_comparison_expression(value, depth, label_counter)
    if isinstance(value, ResolvedBooleanNotExpression):
        return _load_boolean_not_expression(value, depth, label_counter)
    if isinstance(value, ResolvedBooleanBinaryExpression):
        return _load_boolean_binary_expression(value, depth, label_counter)
    if isinstance(value, ResolvedUnaryExpression):
        lines = _load_value_at_depth(value.operand, depth, label_counter)
        if value.operator is UnaryOperator.PLUS:
            return [*lines, "    ; unary + leaves the byte unchanged"]
        return [
            *lines,
            "    eor #$FF                ; unary -: two's complement",
            "    clc",
            "    adc #$01",
        ]
    return _load_value(value, label_counter)


def _load_comparison_expression(
    expression: ResolvedComparisonExpression,
    depth: int,
    label_counter: list[int],
) -> list[str]:
    temporary = f"expression_temporary_{depth}"
    true_label = _new_label(label_counter, "comparison_true")
    false_label = _new_label(label_counter, "comparison_false")
    end_label = _new_label(label_counter, "comparison_end")
    lines = [
        f"    ; comparison {expression.operator.value}: evaluate right operand",
        *_load_value_at_depth(expression.right, depth + 1, label_counter),
        f"    sta {temporary}",
        "    ; evaluate left operand",
        *_load_value_at_depth(expression.left, depth + 1, label_counter),
        f"    cmp {temporary}",
    ]
    branches = {
        ComparisonOperator.EQUAL: [f"    beq {true_label}"],
        ComparisonOperator.NOT_EQUAL: [f"    bne {true_label}"],
        ComparisonOperator.LESS: [f"    bcc {true_label}"],
        ComparisonOperator.GREATER: [
            f"    beq {false_label}",
            f"    bcs {true_label}",
        ],
        ComparisonOperator.LESS_EQUAL: [
            f"    bcc {true_label}",
            f"    beq {true_label}",
        ],
        ComparisonOperator.GREATER_EQUAL: [f"    bcs {true_label}"],
    }
    return [
        *lines,
        *branches[expression.operator],
        f"{false_label}:",
        "    lda #$00              ; false",
        f"    jmp {end_label}",
        f"{true_label}:",
        "    lda #$01              ; true",
        f"{end_label}:",
    ]


def _load_boolean_not_expression(
    expression: ResolvedBooleanNotExpression,
    depth: int,
    label_counter: list[int],
) -> list[str]:
    true_label = _new_label(label_counter, "not_true")
    end_label = _new_label(label_counter, "not_end")
    return [
        "    ; boolean not",
        *_load_value_at_depth(expression.operand, depth, label_counter),
        "    cmp #$00",
        f"    beq {true_label}",
        "    lda #$00              ; false",
        f"    jmp {end_label}",
        f"{true_label}:",
        "    lda #$01              ; true",
        f"{end_label}:",
    ]


def _load_boolean_binary_expression(
    expression: ResolvedBooleanBinaryExpression,
    depth: int,
    label_counter: list[int],
) -> list[str]:
    evaluate_right_label = _new_label(label_counter, "boolean_evaluate_right")
    true_label = _new_label(label_counter, "boolean_true")
    false_label = _new_label(label_counter, "boolean_false")
    end_label = _new_label(label_counter, "boolean_end")
    lines = [
        f"    ; boolean {expression.operator.value}: evaluate left operand",
        *_load_value_at_depth(expression.left, depth, label_counter),
        "    cmp #$00",
    ]
    if expression.operator is BooleanOperator.AND:
        lines.extend(
            [
                f"    bne {evaluate_right_label}",
                f"    jmp {false_label}       ; short-circuit false",
            ]
        )
    else:
        lines.extend(
            [
                f"    beq {evaluate_right_label}",
                f"    jmp {true_label}        ; short-circuit true",
            ]
        )
    return [
        *lines,
        f"{evaluate_right_label}:",
        "    ; evaluate right operand",
        *_load_value_at_depth(expression.right, depth, label_counter),
        "    cmp #$00",
        f"    bne {true_label}",
        f"{false_label}:",
        "    lda #$00              ; false",
        f"    jmp {end_label}",
        f"{true_label}:",
        "    lda #$01              ; true",
        f"{end_label}:",
    ]


def _generate_chr_storage(chr_rom_size: int, sprite_zero_enabled: bool) -> str:
    if not sprite_zero_enabled:
        return f"    .res {chr_rom_size}, $00          ; empty CHR-ROM"

    tile_1_plane_0 = (0x3C, 0x7E, 0xDB, 0xFF, 0xFF, 0xBD, 0x66, 0x3C)
    tile_1_plane_1 = (0x00, 0x24, 0x24, 0x00, 0x00, 0x42, 0x18, 0x00)
    tile_2_plane_0 = (0x7E, 0xFF, 0xA5, 0xFF, 0xBD, 0xC3, 0x7E, 0x24)
    tile_2_plane_1 = (0x00, 0x5A, 0x5A, 0x00, 0x42, 0x3C, 0x00, 0x18)

    def byte_line(values: tuple[int, ...], comment: str) -> str:
        encoded = ", ".join(f"${value:02X}" for value in values)
        return f"    .byte {encoded} ; {comment}"

    used = 0x30
    return "\n".join(
        [
            "    ; Runtime example asset: transparent tile 0 and two player tiles",
            "    .res $0010, $00",
            byte_line(tile_1_plane_0, "tile 1 plane 0"),
            byte_line(tile_1_plane_1, "tile 1 plane 1"),
            byte_line(tile_2_plane_0, "tile 2 plane 0"),
            byte_line(tile_2_plane_1, "tile 2 plane 1"),
            f"    .res {chr_rom_size - used}, $00",
        ]
    )


def _new_label(label_counter: list[int], prefix: str) -> str:
    label = f"@{prefix}_{label_counter[0]}"
    label_counter[0] += 1
    return label
