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
    PaletteKind,
    ResolvedLoadBackground,
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
    ResolvedProgram,
    ResolvedProcedure,
    ResolvedProcedureCall,
    ResolvedRepeatStatement,
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
    ResolvedUnaryExpression,
    ResolvedValue,
    ResolvedWhileStatement,
    Run,
    SpriteOperationKind,
    UnaryOperator,
    VariableValue,
    WaitFrame,
)
from .memory_layout import (
    BackgroundRuntimeFeatures,
    ProgramMemoryLayout,
    build_memory_layout,
    detect_background_runtime_features,
    detect_sprite_runtime_features,
)


def generate(
    program: ResolvedProgram,
    layout: ProgramMemoryLayout | None = None,
    chr_rom: bytes | None = None,
    background_data: bytes | None = None,
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
    background_loads = [
        statement
        for statement in program.statements
        if isinstance(statement, ResolvedLoadBackground)
    ]
    initialization_colors = [command for command in color_commands if not command.queued]
    if (
        len(initialization_colors) != 1
        or len(run_commands) != 1
        or len(background_loads) > 1
        or bool(background_loads) != (background_data is not None)
    ):
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
    oam_symbols = tuple(
        symbol
        for symbol in layout.runtime_symbols
        if symbol.region_name == layout.oam_shadow.name
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
    sprite_features = detect_sprite_runtime_features(program)
    sprite_api_enabled = sprite_features.sprite_api
    oam_enabled = bool(oam_symbols)
    palette_runtime_enabled = any(
        symbol.assembly_symbol == "runtime_palette_shadow"
        for symbol in layout.runtime_symbols
    )
    oam_storage = (
        '.segment "OAM_SHADOW"\n'
        f"; Runtime: page-aligned OAM DMA shadow at "
        f"${layout.oam_shadow.start:04X}-${layout.oam_shadow.end:04X}\n"
        f"{oam_symbols[0].assembly_symbol}: .res {oam_symbols[0].size}"
        f" ; ${oam_symbols[0].address:04X}: {oam_symbols[0].purpose}\n"
        if oam_symbols
        else ""
    )
    background_features = detect_background_runtime_features(program)
    background_shadow_enabled = background_features.shadow
    background_queue_enabled = background_features.queue
    ppu_state_enabled = any(
        symbol.assembly_symbol == "runtime_ppuctrl_shadow"
        for symbol in layout.runtime_symbols
    )
    scroll_runtime_enabled = any(
        symbol.assembly_symbol == "runtime_scroll_ready"
        for symbol in layout.runtime_symbols
    )
    custom_sprite_palette_initialized = _has_initial_sprite_palette(
        program.statements
    )

    label_counter = [0]
    for_counter = [0]
    statement_lines = _generate_statements(
        program.statements,
        label_counter,
        (),
        for_counter,
        oam_enabled,
        palette_runtime_enabled,
        background_queue_enabled,
        background_shadow_enabled,
        ppu_state_enabled,
        sprite_zero_enabled and not custom_sprite_palette_initialized,
    )
    procedure_lines = _generate_procedures(
        program.procedures,
        label_counter,
        for_counter,
        oam_enabled,
        palette_runtime_enabled,
        background_queue_enabled,
        background_shadow_enabled,
        ppu_state_enabled,
        sprite_zero_enabled and not custom_sprite_palette_initialized,
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
    background_storage = (
        _generate_background_storage(background_data)
        if background_data is not None
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

    sprite_zero_commit = (
        """

    ; Runtime: commit the legacy helper's complete staged sprite 0
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
@skip_sprite_zero_commit:"""
        if sprite_zero_enabled
        else ""
    )
    sprite_nmi_work = (
        f"""{sprite_zero_commit}
    ; Runtime: upload the complete OAM shadow during VBlank
    lda #$00
    sta $2003               ; OAM address
    lda #>runtime_oam_shadow
    sta $4014               ; page-aligned OAM DMA"""
        if oam_enabled
        else ""
    )
    oam_initialization = (
        """
    ; Runtime: hide all 64 sprites before the first OAM DMA
    lda #$FF
    ldx #$00
@hide_all_sprites:
    sta runtime_oam_shadow, x
    inx
    inx
    inx
    inx
    bne @hide_all_sprites
"""
        if oam_enabled
        else ""
    )
    palette_nmi_work = (
        "\n\n    ; Runtime: consume bounded queued palette updates before user VBlank work\n"
        "    jsr runtime_upload_queued_palettes"
        if palette_runtime_enabled
        else ""
    )
    empty_background_initialization = (
        _generate_empty_background_initialization()
        if background_shadow_enabled and background_data is None
        else ""
    )
    background_nmi_work = (
        "\n\n    ; Runtime: consume at most four queued background writes in VBlank\n"
        "    jsr runtime_upload_queued_background"
        if background_queue_enabled
        else ""
    )
    scroll_commit = (
        """

    ; Runtime: atomically commit the latest complete scroll pair
    lda runtime_scroll_ready
    beq @skip_scroll_commit
    lda #$00
    sta runtime_scroll_ready
    lda runtime_scroll_pending_x
    sta runtime_scroll_x_shadow
    lda runtime_scroll_pending_y
    sta runtime_scroll_y_shadow
@skip_scroll_commit:"""
        if scroll_runtime_enabled
        else ""
    )
    ppu_state_restore = """

    ; Runtime: authoritative final PPU state after all VBlank work
    bit $2002               ; reset the shared PPU write latch
    lda runtime_ppuctrl_shadow
    sta $2000
    lda runtime_scroll_x_shadow
    sta $2005               ; scroll X (first write)
    lda runtime_scroll_y_shadow
    sta $2005               ; scroll Y (second write)
    lda runtime_ppumask_shadow
    sta $2001"""
    nmi_work = (
        f"{sprite_nmi_work}{palette_nmi_work}{background_nmi_work}"
        f"{vblank_callback_call}{scroll_commit}{ppu_state_restore}"
    )
    palette_runtime_routine = (
        _generate_palette_upload_routine() if palette_runtime_enabled else ""
    )
    background_runtime_routines = (
        _generate_background_runtime_routines(background_features)
        if background_queue_enabled or background_shadow_enabled
        else ""
    )
    sprite_runtime_routines = (
        _generate_sprite_runtime_routines(sprite_features.set_position)
        if sprite_api_enabled
        else ""
    )
    chr_storage = _generate_chr_storage(
        settings.chr_rom_size,
        sprite_zero_enabled,
        chr_rom,
    )
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

{oam_storage}
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
    sta runtime_frame_ready   ; advisory; frame counter is authoritative{nmi_work}

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
{oam_initialization}{empty_background_initialization}{statements}

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
    rts{sprite_runtime_routines}{palette_runtime_routine}{background_runtime_routines}
{procedures}{background_storage}

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
    palette_runtime_enabled: bool,
    background_queue_enabled: bool,
    background_shadow_enabled: bool,
    ppu_state_enabled: bool,
    default_sprite_palette_enabled: bool,
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
            if statement.queued:
                statement_lines.extend(
                    _queue_universal_color(statement.argument, label_counter)
                )
            else:
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
                        *(
                            ["    sta runtime_palette_shadow"]
                            if palette_runtime_enabled
                            else []
                        ),
                    ]
                )
        elif isinstance(statement, ResolvedSetPalette):
            statement_lines.extend(
                _generate_set_palette(
                    statement,
                    label_counter,
                    palette_runtime_enabled,
                )
            )
        elif isinstance(statement, ResolvedSetPaletteColor):
            statement_lines.extend(
                _generate_set_palette_color(
                    statement,
                    label_counter,
                    palette_runtime_enabled,
                )
            )
        elif isinstance(statement, ResolvedLoadBackground):
            statement_lines.extend(
                _generate_background_upload(background_shadow_enabled)
            )
        elif isinstance(statement, Run):
            wait_vblank_label = _new_label(
                label_counter,
                "wait_render_vblank",
            )
            sprite_palette_lines = (
                (
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
                    + (
                        [
                            "    lda #$16",
                            "    sta runtime_palette_shadow + 17",
                            "    lda #$27",
                            "    sta runtime_palette_shadow + 18",
                            "    lda #$30",
                            "    sta runtime_palette_shadow + 19",
                        ]
                        if palette_runtime_enabled
                        else []
                    )
                )
                if default_sprite_palette_enabled
                else []
            )
            rendering_mask = 0x18 if sprite_zero_enabled else 0x08
            ppu_state_lines = [
                "    lda runtime_ppuctrl_shadow",
                "    ora #$80",
                "    sta runtime_ppuctrl_shadow ; preserve bits and enable NMI",
                "    sta $2000",
                "    lda runtime_scroll_x_shadow ; zero-filled default scroll X",
                "    sta $2005",
                "    lda runtime_scroll_y_shadow ; zero-filled default scroll Y",
                "    sta $2005",
                "    lda runtime_ppumask_shadow",
                f"    ora #${rendering_mask:02X}",
                "    sta runtime_ppumask_shadow ; preserve bits and enable rendering",
                "    sta $2001",
            ]
            statement_lines.extend(
                [
                    "",
                    "; Source: nes.run",
                    "; Runtime: defer rendering-sensitive setup to VBlank",
                    f"{wait_vblank_label}:",
                    "    bit $2002",
                    f"    bpl {wait_vblank_label}",
                    *sprite_palette_lines,
                    *ppu_state_lines,
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
        elif isinstance(statement, ResolvedSpriteOperation):
            statement_lines.extend(
                _generate_sprite_operation(statement, label_counter)
            )
        elif isinstance(statement, ResolvedSetTile):
            statement_lines.extend(
                [
                    "",
                    "; Source: nes.set_tile(x, y, tile)",
                    *_load_value(statement.x, label_counter),
                    "    pha                     ; preserve X across expressions",
                    *_load_value(statement.y, label_counter),
                    "    pha                     ; preserve Y across tile expression",
                    *_load_value(statement.tile, label_counter),
                    "    sta runtime_background_pending_value",
                    "    pla",
                    "    sta runtime_background_y",
                    "    pla",
                    "    sta runtime_background_x",
                    "    jsr runtime_set_tile",
                ]
            )
        elif isinstance(statement, ResolvedSetAttribute):
            statement_lines.extend(
                [
                    "",
                    "; Source: nes.set_attribute(x, y, value)",
                    *_load_value(statement.x, label_counter),
                    "    pha                     ; preserve X across expressions",
                    *_load_value(statement.y, label_counter),
                    "    pha                     ; preserve Y across value expression",
                    *_load_value(statement.value, label_counter),
                    "    sta runtime_background_pending_value",
                    "    pla",
                    "    sta runtime_background_y",
                    "    pla",
                    "    sta runtime_background_x",
                    "    jsr runtime_set_attribute",
                ]
            )
        elif isinstance(statement, ResolvedSetScroll):
            statement_lines.extend(
                [
                    "",
                    "; Source: nes.set_scroll(x, y)",
                    "; Runtime: invalidate, stage both axes, then publish atomically",
                    "    lda #$00",
                    "    sta runtime_scroll_ready",
                    *_load_value(statement.x, label_counter),
                    "    sta runtime_scroll_pending_x",
                    *_load_value(statement.y, label_counter),
                    "    sta runtime_scroll_pending_y",
                    "    lda #$01",
                    "    sta runtime_scroll_ready",
                ]
            )
        elif isinstance(statement, ResolvedClearBackgroundUpdates):
            statement_lines.extend(
                [
                    "",
                    "; Source: nes.clear_background_updates()",
                    "    lda #$01",
                    "    sta runtime_background_queue_cancel_lock ; block whole-queue NMI consumption",
                    "    lda #$00",
                    "    sta runtime_background_queue_ready",
                    "    sta runtime_background_queue_ready + 1",
                    "    sta runtime_background_queue_ready + 2",
                    "    sta runtime_background_queue_ready + 3",
                    "    sta runtime_background_queue_cancel_lock ; release after every slot is cancelled",
                ]
            )
        elif isinstance(statement, ResolvedClearBackgroundUpdateOverflow):
            statement_lines.extend(
                [
                    "",
                    "; Source: nes.clear_background_update_overflow()",
                    "    lda #$00",
                    "    sta runtime_background_queue_overflow",
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
                        palette_runtime_enabled,
                        background_queue_enabled,
                        background_shadow_enabled,
                        ppu_state_enabled,
                        default_sprite_palette_enabled,
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
                            palette_runtime_enabled,
                            background_queue_enabled,
                            background_shadow_enabled,
                            ppu_state_enabled,
                            default_sprite_palette_enabled,
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
                        palette_runtime_enabled,
                        background_queue_enabled,
                        background_shadow_enabled,
                        ppu_state_enabled,
                        default_sprite_palette_enabled,
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
                        palette_runtime_enabled,
                        background_queue_enabled,
                        background_shadow_enabled,
                        ppu_state_enabled,
                        default_sprite_palette_enabled,
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
                        palette_runtime_enabled,
                        background_queue_enabled,
                        background_shadow_enabled,
                        ppu_state_enabled,
                        default_sprite_palette_enabled,
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


def _has_initial_sprite_palette(
    statements: tuple[ResolvedStatement, ...],
) -> bool:
    for statement in statements:
        if isinstance(
            statement,
            (ResolvedSetPalette, ResolvedSetPaletteColor),
        ) and statement.kind is PaletteKind.SPRITE and not statement.queued:
            return True
        if isinstance(statement, ResolvedIfStatement):
            if _has_initial_sprite_palette(statement.then_branch):
                return True
            if statement.else_branch is not None and _has_initial_sprite_palette(
                statement.else_branch
            ):
                return True
        elif isinstance(
            statement,
            (ResolvedWhileStatement, ResolvedRepeatStatement, ResolvedForStatement),
        ) and _has_initial_sprite_palette(statement.body):
            return True
    return False


def _generate_sprite_operation(
    statement: ResolvedSpriteOperation,
    label_counter: list[int],
) -> list[str]:
    command = f"nes.sprite_{statement.kind.value}"
    lines = ["", f"; Source: {command}(...)"]
    if statement.value is not None:
        lines.extend(
            [
                *_load_value(statement.value, label_counter),
                "    sta runtime_sprite_value ; evaluate the property once",
            ]
        )
    if statement.secondary_value is not None:
        lines.extend(
            [
                *_load_value(statement.secondary_value, label_counter),
                "    sta runtime_sprite_secondary_value ; evaluate Y once",
            ]
        )

    if not isinstance(statement.sprite, (ImmediateValue, ResolvedSpriteCreate)):
        lines.extend(
            [
                *_load_value(statement.sprite, label_counter),
                f"    jsr runtime_sprite_{statement.kind.value}",
            ]
        )
        return lines

    sprite_index = (
        statement.sprite.value
        if isinstance(statement.sprite, ImmediateValue)
        else statement.sprite.index
    )
    oam_offset = sprite_index * 4
    oam = (
        "runtime_oam_shadow"
        if oam_offset == 0
        else f"runtime_oam_shadow + {oam_offset}"
    )
    logical_y = (
        "runtime_sprite_logical_y"
        if sprite_index == 0
        else f"runtime_sprite_logical_y + {sprite_index}"
    )
    kind = statement.kind
    if kind is SpriteOperationKind.SET_POSITION:
        skip = _new_label(label_counter, "sprite_hidden")
        lines.extend(
            [
                "    lda runtime_sprite_value",
                f"    sta {oam} + 3",
                "    lda runtime_sprite_secondary_value",
                f"    sta {logical_y}",
                f"    lda {oam}",
                "    cmp #$FF",
                f"    beq {skip}",
                "    lda runtime_sprite_secondary_value",
                f"    sta {oam}",
                f"{skip}:",
            ]
        )
    elif kind is SpriteOperationKind.SET_X:
        lines.extend(["    lda runtime_sprite_value", f"    sta {oam} + 3"])
    elif kind is SpriteOperationKind.SET_TILE:
        lines.extend(["    lda runtime_sprite_value", f"    sta {oam} + 1"])
    elif kind is SpriteOperationKind.SET_ATTRIBUTES:
        lines.extend(["    lda runtime_sprite_value", f"    sta {oam} + 2"])
    elif kind is SpriteOperationKind.SET_Y:
        skip = _new_label(label_counter, "sprite_hidden")
        lines.extend(
            [
                "    lda runtime_sprite_value",
                f"    sta {logical_y}",
                f"    lda {oam}",
                "    cmp #$FF",
                f"    beq {skip}",
                "    lda runtime_sprite_value",
                f"    sta {oam}",
                f"{skip}:",
            ]
        )
    elif kind is SpriteOperationKind.HIDE:
        skip = _new_label(label_counter, "sprite_already_hidden")
        lines.extend(
            [
                f"    lda {oam}",
                "    cmp #$FF",
                f"    beq {skip}",
                f"    sta {logical_y}",
                "    lda #$FF",
                f"    sta {oam}",
                f"{skip}:",
            ]
        )
    elif kind is SpriteOperationKind.SHOW:
        lines.extend([f"    lda {logical_y}", f"    sta {oam}"])
    elif kind is SpriteOperationKind.SET_PALETTE:
        skip = _new_label(label_counter, "sprite_invalid_palette")
        lines.extend(
            [
                "    lda runtime_sprite_value",
                "    cmp #$04",
                f"    bcs {skip}             ; ignore invalid dynamic palettes",
                f"    lda {oam} + 2",
                "    and #$FC               ; preserve priority and flip bits",
                "    ora runtime_sprite_value",
                f"    sta {oam} + 2",
                f"{skip}:",
            ]
        )
    else:
        masks = {
            SpriteOperationKind.SET_FLIP_HORIZONTAL: 0x40,
            SpriteOperationKind.SET_FLIP_VERTICAL: 0x80,
            SpriteOperationKind.SET_BEHIND_BACKGROUND: 0x20,
        }
        mask = masks[kind]
        clear = _new_label(label_counter, "sprite_clear_attribute")
        store = _new_label(label_counter, "sprite_store_attribute")
        lines.extend(
            [
                "    lda runtime_sprite_value",
                "    beq " + clear,
                f"    lda {oam} + 2",
                f"    ora #${mask:02X}",
                f"    jmp {store}",
                f"{clear}:",
                f"    lda {oam} + 2",
                f"    and #${0xFF ^ mask:02X}",
                f"{store}:",
                f"    sta {oam} + 2",
            ]
        )
    return lines


def _generate_sprite_runtime_routines(set_position: bool) -> str:
    """Generate bounded helpers for dynamic hardware-sprite indexes."""

    def offset_prelude() -> list[str]:
        return [
            "    asl a                   ; sprite index * 4",
            "    asl a",
            "    tax",
        ]

    lines = [
        "",
        "",
        "; Runtime: hardware sprite primitives over the OAM shadow",
        "runtime_sprite_set_x:",
        *offset_prelude(),
        "    lda runtime_sprite_value",
        "    sta runtime_oam_shadow + 3, x",
        "    rts",
        "",
        "runtime_sprite_set_tile:",
        *offset_prelude(),
        "    lda runtime_sprite_value",
        "    sta runtime_oam_shadow + 1, x",
        "    rts",
        "",
        "runtime_sprite_set_attributes:",
        *offset_prelude(),
        "    lda runtime_sprite_value",
        "    sta runtime_oam_shadow + 2, x",
        "    rts",
        "",
        "runtime_sprite_set_y:",
        "    tay                     ; retain sprite index for logical Y",
        *offset_prelude(),
        "    lda runtime_sprite_value",
        "    sta runtime_sprite_logical_y, y",
        "    lda runtime_oam_shadow, x",
        "    cmp #$FF",
        "    beq @sprite_set_y_done  ; setting Y does not implicitly show",
        "    lda runtime_sprite_value",
        "    sta runtime_oam_shadow, x",
        "@sprite_set_y_done:",
        "    rts",
        "",
        "runtime_sprite_hide:",
        "    tay                     ; retain sprite index for logical Y",
        *offset_prelude(),
        "    lda runtime_oam_shadow, x",
        "    cmp #$FF",
        "    beq @sprite_hide_done",
        "    sta runtime_sprite_logical_y, y",
        "    lda #$FF",
        "    sta runtime_oam_shadow, x",
        "@sprite_hide_done:",
        "    rts",
        "",
        "runtime_sprite_show:",
        "    tay                     ; retain sprite index for logical Y",
        *offset_prelude(),
        "    lda runtime_sprite_logical_y, y",
        "    sta runtime_oam_shadow, x",
        "    rts",
        "",
        "runtime_sprite_set_palette:",
        *offset_prelude(),
        "    lda runtime_sprite_value",
        "    cmp #$04",
        "    bcs @sprite_palette_done ; reject invalid dynamic palettes",
        "    lda runtime_oam_shadow + 2, x",
        "    and #$FC                 ; preserve priority and flip bits",
        "    ora runtime_sprite_value",
        "    sta runtime_oam_shadow + 2, x",
        "@sprite_palette_done:",
        "    rts",
    ]
    if set_position:
        lines.extend(
            [
                "",
                "runtime_sprite_set_position:",
                "    tay                     ; retain sprite index for logical Y",
                *offset_prelude(),
                "    lda runtime_sprite_value",
                "    sta runtime_oam_shadow + 3, x",
                "    lda runtime_sprite_secondary_value",
                "    sta runtime_sprite_logical_y, y",
                "    lda runtime_oam_shadow, x",
                "    cmp #$FF",
                "    beq @sprite_set_position_done",
                "    lda runtime_sprite_secondary_value",
                "    sta runtime_oam_shadow, x",
                "@sprite_set_position_done:",
                "    rts",
            ]
        )
    for name, mask in (
        ("set_flip_horizontal", 0x40),
        ("set_flip_vertical", 0x80),
        ("set_behind_background", 0x20),
    ):
        lines.extend(
            [
                "",
                f"runtime_sprite_{name}:",
                *offset_prelude(),
                "    lda runtime_sprite_value",
                f"    beq @sprite_{name}_clear",
                "    lda runtime_oam_shadow + 2, x",
                f"    ora #${mask:02X}",
                f"    jmp @sprite_{name}_store",
                f"@sprite_{name}_clear:",
                "    lda runtime_oam_shadow + 2, x",
                f"    and #${0xFF ^ mask:02X}",
                f"@sprite_{name}_store:",
                "    sta runtime_oam_shadow + 2, x",
                "    rts",
            ]
        )
    return "\n".join(lines)


def _palette_shadow_base(kind: PaletteKind, palette_index: int) -> int:
    return (0 if kind is PaletteKind.BACKGROUND else 16) + palette_index * 4


def _palette_dirty_symbol(kind: PaletteKind, palette_index: int) -> str:
    return f"runtime_palette_{kind.value}_{palette_index}_dirty"


def _direct_palette_write(
    low_address: int,
    values: tuple[ResolvedValue, ...],
    label_counter: list[int],
) -> list[str]:
    lines = [
        "    bit $2002               ; reset PPU address latch",
        "    lda #$3F",
        "    sta $2006               ; palette address, high byte",
        f"    lda #${low_address:02X}",
        "    sta $2006               ; palette address, low byte",
    ]
    for value in values:
        lines.extend([*_load_value(value, label_counter), "    sta $2007"])
    return lines


def _queue_universal_color(
    value: ResolvedValue,
    label_counter: list[int],
) -> list[str]:
    return [
        "",
        "; Source: nes.set_background_color(value)",
        "; Runtime: invalidate, stage, then publish for the next VBlank",
        "    lda #$00",
        "    sta runtime_palette_universal_dirty",
        *_load_value(value, label_counter),
        "    sta runtime_palette_shadow",
        "    lda #$01",
        "    sta runtime_palette_universal_dirty",
    ]


def _generate_set_palette(
    statement: ResolvedSetPalette,
    label_counter: list[int],
    palette_runtime_enabled: bool,
) -> list[str]:
    command = f"nes.set_{statement.kind.value}_palette"
    base = _palette_shadow_base(statement.kind, statement.palette_index)
    if not statement.queued:
        lines = [
            "",
            f"; Source: {command}(index, color0, color1, color2, color3)",
            "; Initialization: color 0 uses the canonical universal color",
            *_direct_palette_write(0x00, (statement.colors[0],), label_counter),
            *_direct_palette_write(
                base + 1,
                statement.colors[1:],
                label_counter,
            ),
        ]
        if palette_runtime_enabled:
            lines.extend(
                [
                    *_load_value(statement.colors[0], label_counter),
                    "    sta runtime_palette_shadow",
                ]
            )
            for index, value in enumerate(statement.colors[1:], start=1):
                lines.extend(
                    [
                        *_load_value(value, label_counter),
                        f"    sta runtime_palette_shadow + {base + index}",
                    ]
                )
        return lines

    dirty = _palette_dirty_symbol(statement.kind, statement.palette_index)
    lines = [
        "",
        f"; Source: {command}(index, color0, color1, color2, color3)",
        "; Runtime: invalidate both publications before staging any bytes",
        "    lda #$00",
        f"    sta {dirty}",
        "    sta runtime_palette_universal_dirty",
        *_load_value(statement.colors[0], label_counter),
        "    sta runtime_palette_shadow ; canonical universal color",
    ]
    for index, value in enumerate(statement.colors[1:], start=1):
        lines.extend(
            [
                *_load_value(value, label_counter),
                f"    sta runtime_palette_shadow + {base + index}",
            ]
        )
    lines.extend(
        [
            "    lda #$01",
            "    sta runtime_palette_universal_dirty",
            f"    sta {dirty}",
        ]
    )
    return lines


def _generate_set_palette_color(
    statement: ResolvedSetPaletteColor,
    label_counter: list[int],
    palette_runtime_enabled: bool,
) -> list[str]:
    command = f"nes.set_{statement.kind.value}_palette_color"
    if statement.color_index == 0:
        if statement.queued:
            lines = _queue_universal_color(statement.color, label_counter)
            lines[1] = f"; Source: {command}(palette, color, value)"
            return lines
        lines = [
            "",
            f"; Source: {command}(palette, color, value)",
            "; Initialization: color 0 uses the canonical universal color",
            *_direct_palette_write(0x00, (statement.color,), label_counter),
        ]
        if palette_runtime_enabled:
            lines.extend(
                [
                    *_load_value(statement.color, label_counter),
                    "    sta runtime_palette_shadow",
                ]
            )
        return lines

    base = _palette_shadow_base(statement.kind, statement.palette_index)
    offset = base + statement.color_index
    if not statement.queued:
        lines = [
            "",
            f"; Source: {command}(palette, color, value)",
            *_direct_palette_write(offset, (statement.color,), label_counter),
        ]
        if palette_runtime_enabled:
            lines.extend(
                [
                    *_load_value(statement.color, label_counter),
                    f"    sta runtime_palette_shadow + {offset}",
                ]
            )
        return lines

    dirty = _palette_dirty_symbol(statement.kind, statement.palette_index)
    return [
        "",
        f"; Source: {command}(palette, color, value)",
        "; Runtime: invalidate, stage one color, then publish the palette",
        "    lda #$00",
        f"    sta {dirty}",
        *_load_value(statement.color, label_counter),
        f"    sta runtime_palette_shadow + {offset}",
        "    lda #$01",
        f"    sta {dirty}",
    ]


def _generate_palette_upload_routine() -> str:
    lines = [
        "",
        "",
        "; Runtime: bounded VBlank palette uploader (at most eight triplets and one universal color)",
        "runtime_upload_queued_palettes:",
    ]
    for kind in (PaletteKind.BACKGROUND, PaletteKind.SPRITE):
        for palette_index in range(4):
            dirty = _palette_dirty_symbol(kind, palette_index)
            skip = f"@skip_{kind.value}_palette_{palette_index}"
            base = _palette_shadow_base(kind, palette_index)
            low_address = base + 1
            lines.extend(
                [
                    f"    lda {dirty}",
                    f"    beq {skip}",
                    "    lda #$00",
                    f"    sta {dirty}            ; consume complete staged palette",
                    f"    lda #${low_address:02X}",
                    f"    ldx #${base + 1:02X}",
                    "    jsr runtime_upload_palette_triplet",
                    f"{skip}:",
                ]
            )
    lines.extend(
        [
            "    lda runtime_palette_universal_dirty",
            "    beq @skip_universal_palette_color",
            "    lda #$00",
            "    sta runtime_palette_universal_dirty ; consume complete staged color",
            "    bit $2002               ; reset PPU address latch",
            "    lda #$3F",
            "    sta $2006",
            "    lda #$00",
            "    sta $2006",
            "    lda runtime_palette_shadow",
            "    sta $2007",
            "@skip_universal_palette_color:",
            "    rts",
            "",
            "runtime_upload_palette_triplet:",
            "    tay                     ; preserve target low address",
            "    bit $2002               ; reset PPU address latch",
            "    lda #$3F",
            "    sta $2006",
            "    tya",
            "    sta $2006",
            "    ldy #$03",
            "@palette_triplet_loop:",
            "    lda runtime_palette_shadow, x",
            "    sta $2007",
            "    inx",
            "    dey",
            "    bne @palette_triplet_loop",
            "    rts",
        ]
    )
    return "\n".join(lines)


def _generate_background_runtime_routines(
    features: BackgroundRuntimeFeatures,
) -> str:
    sections: list[str] = []
    if features.queue:
        shadow_confirmation = (
            """
    ; Confirm a tile only after its PPU write has completed.
    lda runtime_background_queue_high, x
    cmp #$23
    bcc @confirm_tile_lower_page
    bne @background_upload_next
    lda runtime_background_queue_low, x
    cmp #$C0
    bcs @background_upload_next ; $23C0-$23FF contains attributes
    ldy runtime_background_queue_low, x
    lda runtime_background_queue_value, x
    sta runtime_background_shadow + $0300, y
    jmp @background_upload_next
@confirm_tile_lower_page:
    ldy runtime_background_queue_low, x
    cmp #$20
    beq @confirm_tile_page_0
    cmp #$21
    beq @confirm_tile_page_1
    lda runtime_background_queue_value, x
    sta runtime_background_shadow + $0200, y
    jmp @background_upload_next
@confirm_tile_page_0:
    lda runtime_background_queue_value, x
    sta runtime_background_shadow, y
    jmp @background_upload_next
@confirm_tile_page_1:
    lda runtime_background_queue_value, x
    sta runtime_background_shadow + $0100, y"""
            if features.shadow
            else ""
        )
        lock_check = (
            "    lda runtime_background_queue_cancel_lock\n"
            "    bne @background_upload_locked ; cancellation owns the whole queue\n"
            if features.cancellation_lock
            else ""
        )
        locked_label = (
            "@background_upload_locked:\n"
            if features.cancellation_lock
            else ""
        )
        queue_writer_routine = (
            """

; Runtime: publish one PPU write only after every slot byte is complete
runtime_queue_background_write:
    ldx #$00
@background_find_slot:
    lda runtime_background_queue_ready, x
    beq @background_slot_found
    inx
    cpx #$04
    bne @background_find_slot
    lda #$01
    sta runtime_background_queue_overflow ; sticky until explicitly cleared
    sec                     ; rejected: no queue slot was modified
    rts
@background_slot_found:
    lda runtime_background_x
    sta runtime_background_queue_high, x
    lda runtime_background_y
    sta runtime_background_queue_low, x
    lda runtime_background_pending_value
    sta runtime_background_queue_value, x
    lda #$01
    sta runtime_background_queue_ready, x ; atomic publication is last
    clc                     ; accepted for the next NMI
    rts"""
            if features.queue_writer
            else ""
        )
        sections.append(
            f"""

; Runtime: bounded four-slot background update uploader
runtime_upload_queued_background:
{lock_check}    ldx #$00
@background_upload_loop:
    lda runtime_background_queue_ready, x
    beq @background_upload_next
    lda #$00
    sta runtime_background_queue_ready, x ; consume only a published slot
    bit $2002               ; reset PPU address latch
    lda runtime_background_queue_high, x
    sta $2006
    lda runtime_background_queue_low, x
    sta $2006
    lda runtime_background_queue_value, x
    sta $2007{shadow_confirmation}
@background_upload_next:
    inx
    cpx #$04
    bne @background_upload_loop
{locked_label}    rts{queue_writer_routine}"""
        )

    if features.tile_index:
        sections.append(
            """

; Runtime: validate (x: 0..31, y: 0..29) and compute y * 32 + x
runtime_prepare_tile_index:
    lda runtime_background_y
    cmp #$1E
    bcs @tile_coordinate_invalid
    and #$07
    asl a
    asl a
    asl a
    asl a
    asl a
    clc
    adc runtime_background_x
    sta runtime_background_index_low
    lda runtime_background_x
    cmp #$20
    bcs @tile_coordinate_invalid
    lda runtime_background_y
    lsr a
    lsr a
    lsr a
    sta runtime_background_index_page
    clc
    rts
@tile_coordinate_invalid:
    sec
    rts"""
        )

    if features.set_tile:
        sections.append(
            """

runtime_set_tile:
    jsr runtime_prepare_tile_index
    bcs @set_tile_done
    lda runtime_background_index_page
    clc
    adc #$20
    sta runtime_background_x ; queue PPU address high byte
    lda runtime_background_index_low
    sta runtime_background_y ; queue PPU address low byte
    jsr runtime_queue_background_write
@set_tile_done:
    rts"""
        )

    if features.set_attribute:
        sections.append(
            """

runtime_set_attribute:
    lda runtime_background_x
    cmp #$08
    bcs @set_attribute_done
    lda runtime_background_y
    cmp #$08
    bcs @set_attribute_done
    asl a
    asl a
    asl a
    clc
    adc runtime_background_x
    clc
    adc #$C0
    sta runtime_background_y ; queue PPU address low byte
    lda #$23
    sta runtime_background_x ; queue PPU address high byte
    jsr runtime_queue_background_write
@set_attribute_done:
    rts"""
        )

    if features.get_tile:
        sections.append(
            """

runtime_get_tile:
    jsr runtime_prepare_tile_index
    bcs @get_tile_invalid
    ldx runtime_background_index_low
    lda runtime_background_index_page
    beq @get_tile_page_0
    cmp #$01
    beq @get_tile_page_1
    cmp #$02
    beq @get_tile_page_2
    lda runtime_background_shadow + $0300, x
    rts
@get_tile_page_0:
    lda runtime_background_shadow, x
    rts
@get_tile_page_1:
    lda runtime_background_shadow + $0100, x
    rts
@get_tile_page_2:
    lda runtime_background_shadow + $0200, x
    rts
@get_tile_invalid:
    lda #$00
    rts"""
        )
    return "".join(sections)


def _generate_empty_background_initialization() -> str:
    lines = [
        "",
        "; Runtime: establish a zeroed nametable matching the confirmed shadow",
        "    bit $2002               ; reset PPU address latch",
        "    lda #$20",
        "    sta $2006",
        "    lda #$00",
        "    sta $2006",
        "    ldx #$00",
    ]
    for page in range(4):
        label = f"@clear_background_page_{page}"
        lines.extend(
            [
                f"{label}:",
                "    sta $2007",
                "    inx",
                f"    bne {label}",
            ]
        )
    return "\n".join(lines)


def _generate_background_upload(background_shadow_enabled: bool) -> list[str]:
    lines = [
        "",
        "; Source: nes.load_background()",
        "; Initialization: upload one complete nametable while rendering is disabled",
        "    lda #$00",
        "    sta runtime_ppumask_shadow ; keep authoritative mask disabled",
        "    sta $2001               ; keep rendering disabled during bulk upload",
        "    bit $2002               ; reset PPU address latch",
        "    lda #$20",
        "    sta $2006               ; nametable 0 address, high byte",
        "    lda #$00",
        "    sta $2006               ; nametable 0 address, low byte",
        "    ldx #$00",
    ]
    for page in range(3 if background_shadow_enabled else 4):
        offset = "" if page == 0 else f" + ${page * 0x100:04X}"
        label = f"@upload_background_page_{page}"
        lines.extend(
            [
                f"{label}:",
                f"    lda background_nametable_data{offset}, x",
                "    sta $2007",
                *(
                    [f"    sta runtime_background_shadow{offset}, x"]
                    if background_shadow_enabled
                    else []
                ),
                "    inx",
                f"    bne {label}",
            ]
        )
    if background_shadow_enabled:
        lines.extend(
            [
                "@upload_background_page_3_tiles:",
                "    lda background_nametable_data + $0300, x",
                "    sta $2007",
                "    sta runtime_background_shadow + $0300, x",
                "    inx",
                "    cpx #$C0",
                "    bne @upload_background_page_3_tiles",
                "@upload_background_attributes:",
                "    lda background_nametable_data + $0300, x",
                "    sta $2007",
                "    inx",
                "    bne @upload_background_attributes",
            ]
        )
    return lines


def _generate_background_storage(background_data: bytes) -> str:
    if len(background_data) != 1024:
        raise ValueError("validated background data must contain exactly 1024 bytes")
    lines = [
        "",
        "",
        "; Asset: configured 1 KiB nametable (960 tile bytes and 64 attributes)",
        "background_nametable_data:",
    ]
    for start in range(0, len(background_data), 16):
        chunk = background_data[start : start + 16]
        values = ", ".join(f"${value:02X}" for value in chunk)
        lines.append(f"    .byte {values}")
    return "\n".join(lines)


def _generate_procedures(
    procedures: tuple[ResolvedProcedure, ...],
    label_counter: list[int],
    for_counter: list[int],
    sprite_zero_enabled: bool,
    palette_runtime_enabled: bool,
    background_queue_enabled: bool,
    background_shadow_enabled: bool,
    ppu_state_enabled: bool,
    default_sprite_palette_enabled: bool,
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
                    palette_runtime_enabled,
                    background_queue_enabled,
                    background_shadow_enabled,
                    ppu_state_enabled,
                    default_sprite_palette_enabled,
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
    if isinstance(value, ResolvedSpriteCreate):
        return [
            f"    lda #${value.index:02X}              ; static sprite reservation"
        ]
    if isinstance(value, ImmediateValue):
        if value.type is BuiltInType.BOOLEAN:
            description = "true" if value.value else "false"
            return [f"    lda #${value.value:02X}              ; {description}"]
        return [f"    lda #${value.value:02X}"]
    if isinstance(value, VariableValue):
        return [f"    lda {value.variable.label}"]
    if isinstance(value, ResolvedControllerQuery):
        return _load_controller_query(value, label_counter)
    if isinstance(value, ResolvedBackgroundUpdatesOverflowed):
        return [
            "    ; nes.background_updates_overflowed(): sticky queue state",
            "    lda runtime_background_queue_overflow",
        ]
    if isinstance(value, ResolvedGetTile):
        return _load_get_tile(value, 0, label_counter)
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


def _load_get_tile(
    query: ResolvedGetTile,
    depth: int,
    label_counter: list[int],
) -> list[str]:
    return [
        "    ; nes.get_tile(x, y): read the confirmed PPU tile shadow",
        *_load_value_at_depth(query.x, depth, label_counter),
        "    pha                     ; preserve X across Y expression",
        *_load_value_at_depth(query.y, depth, label_counter),
        "    sta runtime_background_y",
        "    pla",
        "    sta runtime_background_x",
        "    jsr runtime_get_tile",
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
    if isinstance(value, ResolvedGetTile):
        return _load_get_tile(value, depth, label_counter)
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


def _generate_chr_storage(
    chr_rom_size: int,
    sprite_zero_enabled: bool,
    chr_rom: bytes | None = None,
) -> str:
    if chr_rom is not None:
        if len(chr_rom) != chr_rom_size:
            raise ValueError("validated CHR-ROM size does not match the memory layout")
        lines = ["    ; Asset: configured CHR-ROM bytes"]
        for offset in range(0, len(chr_rom), 16):
            encoded = ", ".join(
                f"${value:02X}" for value in chr_rom[offset : offset + 16]
            )
            lines.append(f"    .byte {encoded}")
        return "\n".join(lines)

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
