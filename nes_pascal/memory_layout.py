"""Deterministic NES CPU RAM layout, allocation, and artifact generation."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from .ast import (
    ResolvedAssignment,
    ResolvedBackgroundUpdatesOverflowed,
    ResolvedBinaryExpression,
    ResolvedBooleanBinaryExpression,
    ResolvedBooleanNotExpression,
    ResolvedComparisonExpression,
    ResolvedClearBackgroundUpdates,
    ResolvedClearBackgroundUpdateOverflow,
    ResolvedDecrementStatement,
    ResolvedForStatement,
    ResolvedGetTile,
    ResolvedIfStatement,
    ResolvedIncrementStatement,
    ResolvedProcedureCall,
    ResolvedProgram,
    ResolvedRepeatStatement,
    ResolvedSetBackgroundColor,
    ResolvedSetAttribute,
    ResolvedSetPalette,
    ResolvedSetPaletteColor,
    ResolvedSetSpriteZero,
    ResolvedSetTile,
    ResolvedStatement,
    ResolvedUnaryExpression,
    ResolvedValue,
    ResolvedVariable,
    ResolvedWhileStatement,
    SourcePosition,
    VariableValue,
)
from .diagnostics import CompilerError, DiagnosticCode, SourceLocation


class RegionKind(StrEnum):
    """Ownership classification for a physical RAM region."""

    RESERVED = "Reserved"
    RUNTIME = "Runtime"
    COMPILER = "Compiler"
    USER = "User"
    FREE = "Free"


class SymbolKind(StrEnum):
    """Ownership classification for an allocated RAM symbol."""

    RUNTIME = "Runtime"
    COMPILER = "Compiler"
    USER = "User"


@dataclass(frozen=True, slots=True)
class MemoryRange:
    """A named contiguous range within the NES physical address space."""

    name: str
    start: int
    size: int
    kind: RegionKind

    @property
    def end(self) -> int | None:
        return self.start + self.size - 1 if self.size else None

    def overlaps(self, other: MemoryRange) -> bool:
        if self.size == 0 or other.size == 0:
            return False
        assert self.end is not None
        assert other.end is not None
        return self.start <= other.end and other.start <= self.end


@dataclass(frozen=True, slots=True)
class MemorySymbol:
    """One deterministic RAM allocation represented by an Assembly symbol."""

    assembly_symbol: str
    address: int
    size: int
    kind: SymbolKind
    region_name: str
    purpose: str
    source_name: str | None = None
    type_name: str | None = None
    position: SourcePosition | None = None


@dataclass(frozen=True, slots=True)
class MemoryLayoutSettings:
    """Internal NROM memory defaults for the current runtime ABI."""

    physical_ram_start: int = 0x0000
    physical_ram_size: int = 0x0800
    zero_page_start: int = 0x0000
    zero_page_size: int = 0x0100
    zero_page_runtime_size: int = 0x0010
    temporary_storage_size: int = 0x0010
    zero_page_explicit_reserve_size: int = 0x0060
    zero_page_automatic_size: int = 0x0080
    automatic_promotion_min_references: int = 3
    hardware_stack_start: int = 0x0100
    hardware_stack_size: int = 0x0100
    oam_shadow_start: int = 0x0200
    oam_shadow_size: int = 0x0100
    general_ram_start: int = 0x0300
    runtime_data_size: int = 0
    mapper_number: int = 0
    horizontal_mirroring: bool = True
    prg_rom_banks: int = 2
    chr_rom_banks: int = 1
    prg_rom_start: int = 0x8000
    chr_rom_start: int = 0x0000

    @property
    def prg_rom_size(self) -> int:
        return self.prg_rom_banks * 0x4000

    @property
    def chr_rom_size(self) -> int:
        return self.chr_rom_banks * 0x2000


DEFAULT_MEMORY_LAYOUT_SETTINGS = MemoryLayoutSettings()


@dataclass(frozen=True, slots=True)
class BackgroundRuntimeFeatures:
    """Direct background API use and the small runtime dependencies it enables."""

    set_tile: bool = False
    get_tile: bool = False
    set_attribute: bool = False
    clear_updates: bool = False
    inspect_overflow: bool = False
    clear_overflow: bool = False

    @property
    def queue(self) -> bool:
        return self.set_tile or self.set_attribute or self.clear_updates

    @property
    def queue_writer(self) -> bool:
        return self.set_tile or self.set_attribute

    @property
    def overflow_flag(self) -> bool:
        return self.queue_writer or self.inspect_overflow or self.clear_overflow

    @property
    def cancellation_lock(self) -> bool:
        return self.clear_updates

    @property
    def shadow(self) -> bool:
        return self.get_tile

    @property
    def coordinate_inputs(self) -> bool:
        return self.set_tile or self.get_tile or self.set_attribute

    @property
    def tile_index(self) -> bool:
        return self.set_tile or self.get_tile


@dataclass(frozen=True, slots=True)
class ProgramMemoryLayout:
    """Validated regions and concrete symbol allocations for one program."""

    settings: MemoryLayoutSettings
    physical_ram: MemoryRange
    zero_page: MemoryRange
    zero_page_runtime: MemoryRange
    temporary_storage: MemoryRange
    zero_page_explicit_reserve: MemoryRange
    zero_page_automatic: MemoryRange
    zero_page_unallocated: MemoryRange
    hardware_stack: MemoryRange
    oam_shadow: MemoryRange
    runtime_data: MemoryRange
    user_capacity: MemoryRange
    runtime_symbols: tuple[MemorySymbol, ...]
    temporary_symbols: tuple[MemorySymbol, ...]
    user_symbols: tuple[MemorySymbol, ...]

    @property
    def user_variables(self) -> MemoryRange:
        regular_symbols = self.regular_user_symbols
        return MemoryRange(
            "Regular user variables",
            self.user_capacity.start,
            sum(symbol.size for symbol in regular_symbols),
            RegionKind.USER,
        )

    @property
    def promoted_user_symbols(self) -> tuple[MemorySymbol, ...]:
        return tuple(
            symbol
            for symbol in self.user_symbols
            if symbol.region_name == self.zero_page_automatic.name
        )

    @property
    def regular_user_symbols(self) -> tuple[MemorySymbol, ...]:
        return tuple(
            symbol
            for symbol in self.user_symbols
            if symbol.region_name == self.user_capacity.name
        )

    @property
    def free_ram(self) -> MemoryRange:
        used = self.user_variables.size
        return MemoryRange(
            "General free RAM",
            self.user_capacity.start + used,
            self.user_capacity.size - used,
            RegionKind.FREE,
        )

    @property
    def display_regions(self) -> tuple[MemoryRange, ...]:
        regions = (
            self.zero_page_runtime,
            self.temporary_storage,
            self.zero_page_explicit_reserve,
            self.zero_page_automatic,
            self.zero_page_unallocated,
            self.hardware_stack,
            self.oam_shadow,
            self.runtime_data,
            self.user_variables,
            self.free_ram,
        )
        return tuple(
            region
            for region in regions
            if region.size or region == self.runtime_data
        )

    @property
    def temporary_bytes_used(self) -> int:
        return sum(symbol.size for symbol in self.temporary_symbols)

    @property
    def reserved_or_used_bytes(self) -> int:
        return self.physical_ram.size - self.available_bytes

    @property
    def promoted_bytes_used(self) -> int:
        return sum(symbol.size for symbol in self.promoted_user_symbols)

    @property
    def available_bytes(self) -> int:
        automatic_available = (
            self.zero_page_automatic.size - self.promoted_bytes_used
        )
        return (
            self.free_ram.size
            + automatic_available
            + self.zero_page_unallocated.size
        )


def build_memory_layout(
    program: ResolvedProgram,
    settings: MemoryLayoutSettings = DEFAULT_MEMORY_LAYOUT_SETTINGS,
    *,
    source: str = "",
    filename: str = "<input>",
) -> ProgramMemoryLayout:
    """Validate settings and allocate every RAM-backed program symbol."""

    sprite_zero_enabled = _uses_sprite_zero(program)
    palette_runtime_enabled = _uses_runtime_palette(program)
    background_features = detect_background_runtime_features(program)
    background_queue_enabled = background_features.queue
    background_shadow_enabled = background_features.shadow
    sprite_runtime_size = 5 if sprite_zero_enabled else 0
    palette_runtime_size = 41 if palette_runtime_enabled else 0
    ppu_state_size = 3 if palette_runtime_enabled or background_queue_enabled else 0
    background_shadow_size = 960 if background_shadow_enabled else 0
    background_runtime_size = (
        (16 if background_features.queue else 0)
        + (1 if background_features.overflow_flag else 0)
        + (1 if background_features.cancellation_lock else 0)
        + (2 if background_features.coordinate_inputs else 0)
        + (1 if background_features.queue_writer else 0)
        + (2 if background_features.tile_index else 0)
    )
    required_runtime_size = (
        sprite_runtime_size
        + palette_runtime_size
        + ppu_state_size
        + background_shadow_size
        + background_runtime_size
    )
    if settings.runtime_data_size < required_runtime_size:
        settings = replace(settings, runtime_data_size=required_runtime_size)

    regions = _validated_regions(
        settings,
        source,
        filename,
        oam_shadow_enabled=sprite_zero_enabled,
    )
    (
        physical_ram,
        zero_page,
        zero_page_runtime,
        temporary_storage,
        zero_page_explicit_reserve,
        zero_page_automatic,
        zero_page_unallocated,
        hardware_stack,
        oam_shadow,
        runtime_data,
        user_capacity,
    ) = regions

    temporary_names = _temporary_symbol_names(program)
    if len(temporary_names) > temporary_storage.size:
        _raise_error(
            DiagnosticCode.TEMPORARY_RAM_EXHAUSTED,
            "Expression and loop code requires "
            f"{len(temporary_names)} temporary bytes, but the "
            f"{temporary_storage.name} region has only "
            f"{temporary_storage.size} bytes available.",
            filename,
            source,
            suggestion=(
                "Simplify nested expressions or loops. Mandatory temporary "
                "allocations cannot borrow optional promotion space."
            ),
        )

    background_runtime_symbols: list[MemorySymbol] = []
    next_background_address = (
        runtime_data.start
        + sprite_runtime_size
        + palette_runtime_size
        + ppu_state_size
        + background_shadow_size
    )

    def add_background_symbol(name: str, size: int, purpose: str) -> None:
        nonlocal next_background_address
        background_runtime_symbols.append(
            MemorySymbol(
                name,
                next_background_address,
                size,
                SymbolKind.RUNTIME,
                runtime_data.name,
                purpose,
            )
        )
        next_background_address += size

    if background_features.queue:
        for field, purpose in (
            ("ready", "atomic publication flags"),
            ("high", "PPU address high bytes"),
            ("low", "PPU address low bytes"),
            ("value", "PPU data bytes"),
        ):
            add_background_symbol(
                f"runtime_background_queue_{field}",
                4,
                f"four-slot background update queue {purpose}",
            )
    if background_features.overflow_flag:
        add_background_symbol(
            "runtime_background_queue_overflow",
            1,
            "sticky flag set when all four update slots are occupied",
        )
    if background_features.cancellation_lock:
        add_background_symbol(
            "runtime_background_queue_cancel_lock",
            1,
            "atomic cancellation lock checked by the NMI uploader",
        )
    if background_features.coordinate_inputs:
        add_background_symbol(
            "runtime_background_x",
            1,
            "background helper X input",
        )
        add_background_symbol(
            "runtime_background_y",
            1,
            "background helper Y input",
        )
    if background_features.queue_writer:
        add_background_symbol(
            "runtime_background_pending_value",
            1,
            "background helper byte input",
        )
    if background_features.tile_index:
        offset_purpose = "computed nametable tile offset"
        page_purpose = "computed nametable address page"
        if background_features.shadow:
            offset_purpose += " and confirmed-shadow byte offset"
            page_purpose += " and confirmed-shadow page index"
        add_background_symbol(
            "runtime_background_index_low",
            1,
            offset_purpose,
        )
        add_background_symbol(
            "runtime_background_index_page",
            1,
            page_purpose,
        )

    runtime_symbols = (
        MemorySymbol(
            "runtime_frame_counter",
            zero_page_runtime.start,
            1,
            SymbolKind.RUNTIME,
            zero_page_runtime.name,
            "volatile 8-bit counter incremented once by each NMI",
        ),
        MemorySymbol(
            "runtime_frame_ready",
            zero_page_runtime.start + 1,
            1,
            SymbolKind.RUNTIME,
            zero_page_runtime.name,
            "advisory frame-ready signal consumed by main frame waits",
        ),
        MemorySymbol(
            "runtime_last_processed_frame",
            zero_page_runtime.start + 2,
            1,
            SymbolKind.RUNTIME,
            zero_page_runtime.name,
            "persistent update-loop frame baseline",
        ),
        MemorySymbol(
            "runtime_controller_1_current",
            zero_page_runtime.start + 3,
            1,
            SymbolKind.RUNTIME,
            zero_page_runtime.name,
            "controller 1 state for the newest processed frame",
        ),
        MemorySymbol(
            "runtime_controller_1_previous",
            zero_page_runtime.start + 4,
            1,
            SymbolKind.RUNTIME,
            zero_page_runtime.name,
            "controller 1 state for the preceding processed frame",
        ),
        MemorySymbol(
            "runtime_controller_2_current",
            zero_page_runtime.start + 5,
            1,
            SymbolKind.RUNTIME,
            zero_page_runtime.name,
            "controller 2 state for the newest processed frame",
        ),
        MemorySymbol(
            "runtime_controller_2_previous",
            zero_page_runtime.start + 6,
            1,
            SymbolKind.RUNTIME,
            zero_page_runtime.name,
            "controller 2 state for the preceding processed frame",
        ),
        MemorySymbol(
            "runtime_controller_polled_frame",
            zero_page_runtime.start + 7,
            1,
            SymbolKind.RUNTIME,
            zero_page_runtime.name,
            "frame counter value of the most recent controller poll",
        ),
        MemorySymbol(
            "runtime_controller_poll_valid",
            zero_page_runtime.start + 8,
            1,
            SymbolKind.RUNTIME,
            zero_page_runtime.name,
            "distinguishes an initial zero byte from a completed frame-zero poll",
        ),
        *(
            (
                MemorySymbol(
                    "runtime_oam_shadow",
                    oam_shadow.start,
                    oam_shadow.size,
                    SymbolKind.RUNTIME,
                    oam_shadow.name,
                    "256-byte page copied to PPU OAM by runtime sprite support",
                ),
            )
            if sprite_zero_enabled
            else ()
        ),
        *(
            (
                MemorySymbol(
                    "runtime_sprite_zero_pending_x",
                    runtime_data.start,
                    1,
                    SymbolKind.RUNTIME,
                    runtime_data.name,
                    "staged sprite 0 X coordinate",
                ),
                MemorySymbol(
                    "runtime_sprite_zero_pending_y",
                    runtime_data.start + 1,
                    1,
                    SymbolKind.RUNTIME,
                    runtime_data.name,
                    "staged sprite 0 Y coordinate",
                ),
                MemorySymbol(
                    "runtime_sprite_zero_pending_tile",
                    runtime_data.start + 2,
                    1,
                    SymbolKind.RUNTIME,
                    runtime_data.name,
                    "staged sprite 0 tile index",
                ),
                MemorySymbol(
                    "runtime_sprite_zero_pending_attributes",
                    runtime_data.start + 3,
                    1,
                    SymbolKind.RUNTIME,
                    runtime_data.name,
                    "staged sprite 0 attributes",
                ),
                MemorySymbol(
                    "runtime_sprite_zero_ready",
                    runtime_data.start + 4,
                    1,
                    SymbolKind.RUNTIME,
                    runtime_data.name,
                    "atomic sprite 0 staging commit flag",
                ),
            )
            if sprite_zero_enabled
            else ()
        ),
        *(
            (
                MemorySymbol(
                    "runtime_palette_shadow",
                    runtime_data.start + sprite_runtime_size,
                    32,
                    SymbolKind.RUNTIME,
                    runtime_data.name,
                    "canonical 32-byte background and sprite palette shadow",
                ),
                *(
                    MemorySymbol(
                        f"runtime_palette_background_{index}_dirty",
                        runtime_data.start + sprite_runtime_size + 32 + index,
                        1,
                        SymbolKind.RUNTIME,
                        runtime_data.name,
                        f"atomic publish flag for background palette {index}",
                    )
                    for index in range(4)
                ),
                *(
                    MemorySymbol(
                        f"runtime_palette_sprite_{index}_dirty",
                        runtime_data.start + sprite_runtime_size + 36 + index,
                        1,
                        SymbolKind.RUNTIME,
                        runtime_data.name,
                        f"atomic publish flag for sprite palette {index}",
                    )
                    for index in range(4)
                ),
                MemorySymbol(
                    "runtime_palette_universal_dirty",
                    runtime_data.start + sprite_runtime_size + 40,
                    1,
                    SymbolKind.RUNTIME,
                    runtime_data.name,
                    "atomic publish flag for the universal background color",
                ),
            )
            if palette_runtime_enabled
            else ()
        ),
        *(
            tuple(
                MemorySymbol(
                    name,
                    runtime_data.start
                    + sprite_runtime_size
                    + palette_runtime_size
                    + index,
                    1,
                    SymbolKind.RUNTIME,
                    runtime_data.name,
                    purpose,
                )
                for index, (name, purpose) in enumerate(
                    (
                        (
                            "runtime_ppuctrl_shadow",
                            "PPUCTRL value restored after bounded PPU uploads",
                        ),
                        (
                            "runtime_scroll_x_shadow",
                            "horizontal scroll restored after bounded PPU uploads",
                        ),
                        (
                            "runtime_scroll_y_shadow",
                            "vertical scroll restored after bounded PPU uploads",
                        ),
                    )
                )
            )
            if ppu_state_size
            else ()
        ),
        *(
            (
                MemorySymbol(
                    "runtime_background_shadow",
                    runtime_data.start
                    + sprite_runtime_size
                    + palette_runtime_size
                    + ppu_state_size,
                    960,
                    SymbolKind.RUNTIME,
                    runtime_data.name,
                    "960-byte confirmed PPU tile shadow for nametable 0",
                ),
            )
            if background_shadow_enabled
            else ()
        ),
        *background_runtime_symbols,
    )
    temporary_symbols = tuple(
        MemorySymbol(
            name,
            temporary_storage.start + index,
            1,
            SymbolKind.COMPILER,
            temporary_storage.name,
            (
                "reusable expression evaluation byte"
                if name.startswith("expression_temporary_")
                else "cached for-loop final value"
            ),
        )
        for index, name in enumerate(temporary_names)
    )

    reference_counts = _global_variable_reference_counts(program)
    promoted_labels = {
        variable.label
        for variable in program.variables
        if reference_counts.get(variable.label, 0)
        >= settings.automatic_promotion_min_references
    }

    user_symbols: list[MemorySymbol] = []
    next_zero_page_address = zero_page_automatic.start
    next_user_address = user_capacity.start
    for source_name, variable, purpose, promotion_allowed in _user_variables(program):
        promote = (
            promotion_allowed
            and variable.label in promoted_labels
            and next_zero_page_address
            < zero_page_automatic.start + zero_page_automatic.size
        )
        if promote:
            user_symbols.append(
                MemorySymbol(
                    variable.label,
                    next_zero_page_address,
                    1,
                    SymbolKind.USER,
                    zero_page_automatic.name,
                    f"{purpose}; automatically promoted after "
                    f"{reference_counts[variable.label]} source references",
                    source_name,
                    variable.type.value,
                    variable.position,
                )
            )
            next_zero_page_address += 1
            continue

        available = user_capacity.start + user_capacity.size - next_user_address
        if available < 1:
            _raise_error(
                DiagnosticCode.USER_RAM_EXHAUSTED,
                f"User RAM cannot allocate {source_name}: requested 1 byte, "
                f"but {available} bytes remain in {user_capacity.name}.",
                filename,
                source,
                variable.position,
                f"Reduce user variables or compiler-owned storage; {source_name} "
                "would extend beyond physical RAM at $07FF.",
                len(variable.name),
            )
        user_symbols.append(
            MemorySymbol(
                variable.label,
                next_user_address,
                1,
                SymbolKind.USER,
                user_capacity.name,
                purpose,
                source_name,
                variable.type.value,
                variable.position,
            )
        )
        next_user_address += 1

    layout = ProgramMemoryLayout(
        settings,
        physical_ram,
        zero_page,
        zero_page_runtime,
        temporary_storage,
        zero_page_explicit_reserve,
        zero_page_automatic,
        zero_page_unallocated,
        hardware_stack,
        oam_shadow,
        runtime_data,
        user_capacity,
        runtime_symbols,
        temporary_symbols,
        tuple(user_symbols),
    )
    validate_segment_capacities(layout, source=source, filename=filename)
    return layout


def validate_segment_capacities(
    layout: ProgramMemoryLayout,
    *,
    source: str = "",
    filename: str = "<input>",
) -> None:
    """Reject any generated segment whose declarations exceed its region."""

    all_symbols = (
        *layout.runtime_symbols,
        *layout.temporary_symbols,
        *layout.user_symbols,
    )
    checked_regions = (
        layout.zero_page_runtime,
        layout.temporary_storage,
        layout.zero_page_automatic,
        layout.oam_shadow,
        layout.runtime_data,
        layout.user_capacity,
    )
    known_region_names = {region.name for region in checked_regions}
    for symbol in all_symbols:
        if symbol.region_name not in known_region_names:
            _raise_error(
                DiagnosticCode.RAM_SEGMENT_OVERFLOW,
                f"Generated symbol {symbol.assembly_symbol} refers to unknown "
                f"RAM region {symbol.region_name}.",
                filename,
                source,
                suggestion="Correct the internal memory layout before linking.",
            )
    checks = tuple(
        (
            region,
            tuple(
                symbol for symbol in all_symbols if symbol.region_name == region.name
            ),
        )
        for region in checked_regions
    )
    for region, symbols in checks:
        requested = sum(symbol.size for symbol in symbols)
        if requested > region.size:
            _raise_error(
                DiagnosticCode.RAM_SEGMENT_OVERFLOW,
                f"Generated segment for {region.name} requires {requested} "
                f"bytes, but its RAM region contains {region.size} bytes.",
                filename,
                source,
                suggestion="Correct the internal memory layout before linking.",
            )
        previous_end: int | None = None
        for symbol in sorted(symbols, key=lambda item: item.address):
            symbol_end = symbol.address + symbol.size - 1
            region_end = region.end
            if (
                symbol.size <= 0
                or region_end is None
                or symbol.address < region.start
                or symbol_end > region_end
                or (previous_end is not None and symbol.address <= previous_end)
            ):
                _raise_error(
                    DiagnosticCode.RAM_SEGMENT_OVERFLOW,
                    f"Generated symbol {symbol.assembly_symbol} does not fit "
                    f"without overlap in {region.name}.",
                    filename,
                    source,
                    suggestion="Correct the internal memory layout before linking.",
                )
            previous_end = symbol_end


def generate_linker_config(layout: ProgramMemoryLayout) -> str:
    """Generate a deterministic ld65 NROM configuration from the layout."""

    validate_segment_capacities(layout)
    settings = layout.settings
    memory_lines = [
        _linker_memory_line("ZP_RUNTIME", layout.zero_page_runtime),
        _linker_memory_line("ZP_TEMP", layout.temporary_storage),
        _linker_memory_line("ZP_EXPLICIT", layout.zero_page_explicit_reserve),
        _linker_memory_line("ZP_AUTO", layout.zero_page_automatic),
        _linker_memory_line("STACK", layout.hardware_stack),
        _linker_memory_line("RUNTIME", layout.runtime_data),
    ]
    if layout.oam_shadow.size:
        memory_lines.insert(5, _linker_memory_line("OAM", layout.oam_shadow))
    if layout.zero_page_unallocated.size:
        memory_lines.append(
            _linker_memory_line("ZP_FREE", layout.zero_page_unallocated)
        )
    memory_lines.extend(
        [
            _linker_memory_line("USER", layout.user_capacity),
            "    HEADER: start = $0000, size = $0010, file = %O, fill = yes;",
            f"    PRG:    start = ${settings.prg_rom_start:04X}, "
            f"size = ${settings.prg_rom_size:04X}, file = %O, fill = yes, "
            "fillval = $00;",
            f"    CHR:    start = ${settings.chr_rom_start:04X}, "
            f"size = ${settings.chr_rom_size:04X}, file = %O, fill = yes, "
            "fillval = $00;",
        ]
    )
    segment_lines = [
        "    ZERO_PAGE_RUNTIME:     load = ZP_RUNTIME, type = zp;",
        "    ZERO_PAGE_TEMPORARIES: load = ZP_TEMP,    type = zp;",
        "    ZERO_PAGE_VARIABLES:   load = ZP_AUTO,    type = zp;",
        "    RUNTIME_DATA:        load = RUNTIME, type = bss;",
    ]
    if layout.oam_shadow.size:
        segment_lines.insert(
            3,
            "    OAM_SHADOW:          load = OAM,    type = bss;",
        )
    segment_lines.extend(
        [
            "    USER_VARIABLES:      load = USER,   type = bss;",
            "    HEADER:               load = HEADER, type = ro;",
            "    CODE:                 load = PRG,    type = ro;",
            "    VECTORS:              load = PRG,    type = ro, start = $FFFA;",
            "    CHR:                  load = CHR,    type = ro;",
        ]
    )
    return "\n".join(
        [
            "# Generated by nes-pascal; do not edit.",
            "MEMORY {",
            *memory_lines,
            "}",
            "",
            "SEGMENTS {",
            *segment_lines,
            "}",
            "",
        ]
    )


def generate_memory_map(layout: ProgramMemoryLayout) -> str:
    """Generate the stable human-readable CPU RAM map artifact."""

    physical_end = layout.physical_ram.end
    assert physical_end is not None
    lines = [
        "NES Pascal CPU Memory Map",
        "=========================",
        "",
        f"Physical CPU RAM: ${layout.physical_ram.start:04X}-"
        f"${physical_end:04X} ({layout.physical_ram.size} bytes)",
        "Mirrors: $0800-$1FFF mirror $0000-$07FF and are not allocatable.",
        "Zero Page: $0000-$00FF (256 bytes)",
        "",
        "Regions",
        "-------",
        "",
        "Start  End    Size  Owner     Region",
    ]
    temporary_detail = (
        f" ({layout.temporary_bytes_used} used, "
        f"{layout.temporary_storage.size - layout.temporary_bytes_used} reserved)"
    )
    promotion_detail = (
        f" ({layout.promoted_bytes_used} used, "
        f"{layout.zero_page_automatic.size - layout.promoted_bytes_used} available)"
    )
    for region in layout.display_regions:
        if region == layout.temporary_storage:
            detail = temporary_detail
        elif region == layout.zero_page_automatic:
            detail = promotion_detail
        else:
            detail = ""
        end = f"${region.end:04X}" if region.end is not None else "----"
        lines.append(
            f"${region.start:04X}  {end:5}  {region.size:4}  "
            f"{region.kind.value:8}  {region.name}{detail}"
        )
    lines.extend(
        [
            "",
            f"Reserved or used: {layout.reserved_or_used_bytes} bytes",
            f"Available:        {layout.available_bytes} bytes",
            "",
            "User Symbols",
            "------------",
            "",
            "Address  Size  Storage     Type       "
            "Source name                 Assembly symbol",
        ]
    )
    if layout.user_symbols:
        for symbol in layout.user_symbols:
            storage = (
                "Zero Page"
                if symbol.region_name == layout.zero_page_automatic.name
                else "Regular RAM"
            )
            lines.append(
                f"${symbol.address:04X}    {symbol.size:4}  "
                f"{storage:11} "
                f"{(symbol.type_name or '-'):10} "
                f"{(symbol.source_name or '-'):27} {symbol.assembly_symbol}"
            )
    else:
        lines.append("(none)")
    lines.extend(
        [
            "",
            "Runtime Symbols",
            "---------------",
            "",
            "Address  Size  Assembly symbol       Purpose",
        ]
    )
    for symbol in layout.runtime_symbols:
        lines.append(
            f"${symbol.address:04X}    {symbol.size:4}  "
            f"{symbol.assembly_symbol:21} {symbol.purpose}"
        )
    lines.extend(
        [
            "",
            "Compiler Symbols",
            "----------------",
            "",
            "Address  Size  Assembly symbol       Purpose",
        ]
    )
    if layout.temporary_symbols:
        for symbol in layout.temporary_symbols:
            lines.append(
                f"${symbol.address:04X}    {symbol.size:4}  "
                f"{symbol.assembly_symbol:21} {symbol.purpose}"
            )
    else:
        lines.append("(none)")
    lines.append("")
    return "\n".join(lines)


def _validated_regions(
    settings: MemoryLayoutSettings,
    source: str,
    filename: str,
    *,
    oam_shadow_enabled: bool,
) -> tuple[MemoryRange, ...]:
    if (
        settings.mapper_number != 0
        or not settings.horizontal_mirroring
        or settings.prg_rom_banks != 2
        or settings.chr_rom_banks != 1
        or settings.prg_rom_start != 0x8000
        or settings.chr_rom_start != 0
    ):
        _invalid_layout(
            "Only mapper 0 NROM-256 with 32 KiB PRG-ROM and 8 KiB CHR-ROM "
            "is supported.",
            source,
            filename,
        )
    if (settings.physical_ram_start, settings.physical_ram_size) != (0, 0x800):
        _invalid_layout(
            "Physical CPU RAM must be exactly $0000-$07FF (2048 bytes).",
            source,
            filename,
        )
    if (settings.zero_page_start, settings.zero_page_size) != (0, 0x100):
        _invalid_layout(
            "Zero Page must remain reserved at $0000-$00FF.", source, filename
        )
    if (settings.hardware_stack_start, settings.hardware_stack_size) != (
        0x100,
        0x100,
    ):
        _invalid_layout(
            "The 6502 hardware stack must remain reserved at $0100-$01FF.",
            source,
            filename,
        )
    if settings.oam_shadow_size != 0x100:
        _invalid_layout(
            "The OAM shadow region must occupy exactly 256 bytes.",
            source,
            filename,
        )
    if settings.oam_shadow_start % 0x100 != 0:
        _invalid_layout(
            "The OAM shadow region must start on a 256-byte page boundary.",
            source,
            filename,
        )
    if settings.oam_shadow_start != 0x200:
        _invalid_layout(
            "The OAM shadow region must remain at $0200-$02FF.", source, filename
        )
    if settings.general_ram_start != 0x300:
        _invalid_layout(
            "General compiler-managed RAM must begin at $0300.", source, filename
        )
    zero_page_sizes = (
        settings.zero_page_runtime_size,
        settings.temporary_storage_size,
        settings.zero_page_explicit_reserve_size,
        settings.zero_page_automatic_size,
    )
    if settings.runtime_data_size < 0 or any(size < 0 for size in zero_page_sizes):
        _invalid_layout("RAM region sizes cannot be negative.", source, filename)
    if settings.automatic_promotion_min_references < 1:
        _invalid_layout(
            "The automatic-promotion reference threshold must be at least 1.",
            source,
            filename,
        )
    if sum(zero_page_sizes) > settings.zero_page_size:
        _invalid_layout(
            "Zero Page runtime, temporary, explicit-reserve, and automatic "
            "regions exceed $0000-$00FF.",
            source,
            filename,
        )

    physical = MemoryRange(
        "Physical CPU RAM",
        settings.physical_ram_start,
        settings.physical_ram_size,
        RegionKind.RESERVED,
    )
    zero_page = MemoryRange(
        "Zero Page",
        settings.zero_page_start,
        settings.zero_page_size,
        RegionKind.RESERVED,
    )
    zero_page_runtime = MemoryRange(
        "Zero Page runtime",
        zero_page.start,
        settings.zero_page_runtime_size,
        RegionKind.RUNTIME,
    )
    temporary = MemoryRange(
        "Zero Page temporaries",
        zero_page_runtime.start + zero_page_runtime.size,
        settings.temporary_storage_size,
        RegionKind.COMPILER,
    )
    zero_page_explicit_reserve = MemoryRange(
        "Future explicit Zero Page",
        temporary.start + temporary.size,
        settings.zero_page_explicit_reserve_size,
        RegionKind.RESERVED,
    )
    zero_page_automatic = MemoryRange(
        "Automatic Zero Page variables",
        zero_page_explicit_reserve.start + zero_page_explicit_reserve.size,
        settings.zero_page_automatic_size,
        RegionKind.USER,
    )
    zero_page_end = zero_page.end
    assert zero_page_end is not None
    zero_page_unallocated_start = (
        zero_page_automatic.start + zero_page_automatic.size
    )
    zero_page_unallocated = MemoryRange(
        "Unallocated Zero Page",
        zero_page_unallocated_start,
        zero_page_end + 1 - zero_page_unallocated_start,
        RegionKind.FREE,
    )
    stack = MemoryRange(
        "6502 hardware stack",
        settings.hardware_stack_start,
        settings.hardware_stack_size,
        RegionKind.RESERVED,
    )
    oam = MemoryRange(
        "OAM shadow",
        settings.oam_shadow_start,
        settings.oam_shadow_size if oam_shadow_enabled else 0,
        RegionKind.RUNTIME,
    )
    fixed_regions = (zero_page, stack, oam)
    for index, region in enumerate(fixed_regions):
        if not _within(region, physical):
            _invalid_layout(
                f"{region.name} extends beyond physical RAM at $07FF.",
                source,
                filename,
            )
        for other in fixed_regions[index + 1 :]:
            if region.overlaps(other):
                _invalid_layout(
                    f"{region.name} overlaps {other.name}.", source, filename
                )

    runtime = MemoryRange(
        "Runtime data",
        settings.general_ram_start if oam_shadow_enabled else settings.oam_shadow_start,
        settings.runtime_data_size,
        RegionKind.RUNTIME,
    )
    user_start = runtime.start + runtime.size
    physical_end = physical.end
    assert physical_end is not None
    if user_start > physical_end + 1:
        _invalid_layout(
            "Runtime data extends beyond physical RAM at $07FF.",
            source,
            filename,
        )
    user = MemoryRange(
        "User RAM",
        user_start,
        physical_end + 1 - user_start,
        RegionKind.USER,
    )
    return (
        physical,
        zero_page,
        zero_page_runtime,
        temporary,
        zero_page_explicit_reserve,
        zero_page_automatic,
        zero_page_unallocated,
        stack,
        oam,
        runtime,
        user,
    )


def _within(region: MemoryRange, container: MemoryRange) -> bool:
    if region.size == 0:
        return container.start <= region.start <= (container.end or 0) + 1
    assert region.end is not None
    assert container.end is not None
    return container.start <= region.start and region.end <= container.end


def _invalid_layout(message: str, source: str, filename: str) -> None:
    _raise_error(
        DiagnosticCode.INVALID_MEMORY_LAYOUT,
        message,
        filename,
        source,
        suggestion="Use the supported NROM memory settings.",
    )


def _raise_error(
    code: DiagnosticCode,
    message: str,
    filename: str,
    source: str,
    position: SourcePosition | None = None,
    suggestion: str | None = None,
    highlight_length: int = 1,
) -> None:
    position = position or SourcePosition(1, 1)
    source_lines = source.splitlines()
    source_line = (
        source_lines[position.line - 1]
        if 0 < position.line <= len(source_lines)
        else ""
    )
    raise CompilerError(
        code,
        message,
        SourceLocation(filename, position.line, position.column),
        source_line,
        suggestion,
        highlight_length,
    )


def _linker_memory_line(name: str, region: MemoryRange) -> str:
    return (
        f"    {name + ':':8} start = ${region.start:04X}, "
        f"size = ${region.size:04X}, type = rw, file = \"\";"
    )


def _user_variables(
    program: ResolvedProgram,
) -> tuple[tuple[str, ResolvedVariable, str, bool], ...]:
    variables = [
        (variable.name, variable, "source variable", True)
        for variable in program.variables
    ]
    variables.extend(
        (
            f"{procedure.name}.{parameter.name}",
            parameter,
            f"value parameter for {procedure.name}",
            False,
        )
        for procedure in program.procedures
        for parameter in procedure.parameters
    )
    return tuple(variables)


def _global_variable_reference_counts(program: ResolvedProgram) -> dict[str, int]:
    """Count static source operations without estimating runtime frequency."""

    counts = {variable.label: 0 for variable in program.variables}
    statements = (
        *program.statements,
        *(
            statement
            for procedure in program.procedures
            for statement in procedure.body
        ),
    )
    for statement in statements:
        _count_statement_variable_references(statement, counts)
    return counts


def _uses_sprite_zero(program: ResolvedProgram) -> bool:
    def contains(statements: tuple[ResolvedStatement, ...]) -> bool:
        for statement in statements:
            if isinstance(statement, ResolvedSetSpriteZero):
                return True
            if isinstance(statement, ResolvedIfStatement):
                if contains(statement.then_branch):
                    return True
                if statement.else_branch is not None and contains(
                    statement.else_branch
                ):
                    return True
            elif isinstance(
                statement,
                (ResolvedWhileStatement, ResolvedRepeatStatement, ResolvedForStatement),
            ) and contains(statement.body):
                return True
        return False

    return contains(program.statements) or any(
        contains(procedure.body) for procedure in program.procedures
    )


def _uses_runtime_palette(program: ResolvedProgram) -> bool:
    def contains(statements: tuple[ResolvedStatement, ...]) -> bool:
        for statement in statements:
            if isinstance(
                statement,
                (ResolvedSetBackgroundColor, ResolvedSetPalette, ResolvedSetPaletteColor),
            ) and statement.queued:
                return True
            if isinstance(statement, ResolvedIfStatement):
                if contains(statement.then_branch):
                    return True
                if statement.else_branch is not None and contains(
                    statement.else_branch
                ):
                    return True
            elif isinstance(
                statement,
                (ResolvedWhileStatement, ResolvedRepeatStatement, ResolvedForStatement),
            ) and contains(statement.body):
                return True
        return False

    return contains(program.statements) or any(
        contains(procedure.body) for procedure in program.procedures
    )


def detect_background_runtime_features(
    program: ResolvedProgram,
) -> BackgroundRuntimeFeatures:
    """Collect direct background API use before deriving runtime dependencies."""

    used = {
        "set_tile": False,
        "get_tile": False,
        "set_attribute": False,
        "clear_updates": False,
        "inspect_overflow": False,
        "clear_overflow": False,
    }

    def visit_value(value: ResolvedValue) -> None:
        if isinstance(value, ResolvedGetTile):
            used["get_tile"] = True
            visit_value(value.x)
            visit_value(value.y)
        elif isinstance(value, ResolvedBackgroundUpdatesOverflowed):
            used["inspect_overflow"] = True
        elif isinstance(
            value,
            (ResolvedUnaryExpression, ResolvedBooleanNotExpression),
        ):
            visit_value(value.operand)
        elif isinstance(
            value,
            (
                ResolvedBinaryExpression,
                ResolvedComparisonExpression,
                ResolvedBooleanBinaryExpression,
            ),
        ):
            visit_value(value.left)
            visit_value(value.right)

    def visit_statements(statements: tuple[ResolvedStatement, ...]) -> None:
        for statement in statements:
            values: tuple[ResolvedValue, ...] = ()
            if isinstance(statement, ResolvedSetTile):
                used["set_tile"] = True
            elif isinstance(statement, ResolvedSetAttribute):
                used["set_attribute"] = True
            elif isinstance(statement, ResolvedClearBackgroundUpdates):
                used["clear_updates"] = True
            elif isinstance(statement, ResolvedClearBackgroundUpdateOverflow):
                used["clear_overflow"] = True
            if isinstance(statement, ResolvedAssignment):
                values = (statement.value,)
            elif isinstance(statement, ResolvedSetBackgroundColor):
                values = (statement.argument,)
            elif isinstance(statement, ResolvedSetPalette):
                values = statement.colors
            elif isinstance(statement, ResolvedSetPaletteColor):
                values = (statement.color,)
            elif isinstance(statement, ResolvedSetSpriteZero):
                values = (
                    statement.x,
                    statement.y,
                    statement.tile,
                    statement.attributes,
                )
            elif isinstance(statement, ResolvedSetTile):
                values = (statement.x, statement.y, statement.tile)
            elif isinstance(statement, ResolvedSetAttribute):
                values = (statement.x, statement.y, statement.value)
            elif isinstance(
                statement,
                (ResolvedIncrementStatement, ResolvedDecrementStatement),
            ):
                values = (statement.amount,) if statement.amount is not None else ()
            elif isinstance(statement, ResolvedIfStatement):
                visit_value(statement.condition)
                visit_statements(statement.then_branch)
                if statement.else_branch is not None:
                    visit_statements(statement.else_branch)
                continue
            elif isinstance(
                statement,
                (ResolvedWhileStatement, ResolvedRepeatStatement),
            ):
                visit_value(statement.condition)
                visit_statements(statement.body)
                continue
            elif isinstance(statement, ResolvedForStatement):
                visit_value(statement.initial)
                visit_value(statement.final)
                visit_statements(statement.body)
                continue
            elif isinstance(statement, ResolvedProcedureCall):
                values = tuple(argument.value for argument in statement.arguments)
            for value in values:
                visit_value(value)

    visit_statements(program.statements)
    for procedure in program.procedures:
        visit_statements(procedure.body)
    return BackgroundRuntimeFeatures(**used)


def _count_statement_variable_references(
    statement: ResolvedStatement,
    counts: dict[str, int],
) -> None:
    if isinstance(statement, ResolvedAssignment):
        _count_variable(statement.target, counts)
        _count_value_variable_references(statement.value, counts)
    elif isinstance(statement, ResolvedSetBackgroundColor):
        _count_value_variable_references(statement.argument, counts)
    elif isinstance(statement, ResolvedSetPalette):
        for value in statement.colors:
            _count_value_variable_references(value, counts)
    elif isinstance(statement, ResolvedSetPaletteColor):
        _count_value_variable_references(statement.color, counts)
    elif isinstance(statement, ResolvedSetSpriteZero):
        for value in (
            statement.x,
            statement.y,
            statement.tile,
            statement.attributes,
        ):
            _count_value_variable_references(value, counts)
    elif isinstance(statement, ResolvedSetTile):
        for value in (statement.x, statement.y, statement.tile):
            _count_value_variable_references(value, counts)
    elif isinstance(statement, ResolvedSetAttribute):
        for value in (statement.x, statement.y, statement.value):
            _count_value_variable_references(value, counts)
    elif isinstance(
        statement,
        (ResolvedIncrementStatement, ResolvedDecrementStatement),
    ):
        _count_variable(statement.target, counts)
        if statement.amount is not None:
            _count_value_variable_references(statement.amount, counts)
    elif isinstance(statement, ResolvedIfStatement):
        _count_value_variable_references(statement.condition, counts)
        for item in statement.then_branch:
            _count_statement_variable_references(item, counts)
        if statement.else_branch is not None:
            for item in statement.else_branch:
                _count_statement_variable_references(item, counts)
    elif isinstance(statement, (ResolvedWhileStatement, ResolvedRepeatStatement)):
        _count_value_variable_references(statement.condition, counts)
        for item in statement.body:
            _count_statement_variable_references(item, counts)
    elif isinstance(statement, ResolvedForStatement):
        _count_variable(statement.target, counts)
        _count_value_variable_references(statement.initial, counts)
        _count_value_variable_references(statement.final, counts)
        for item in statement.body:
            _count_statement_variable_references(item, counts)
    elif isinstance(statement, ResolvedProcedureCall):
        for argument in statement.arguments:
            _count_value_variable_references(argument.value, counts)


def _count_value_variable_references(
    value: ResolvedValue,
    counts: dict[str, int],
) -> None:
    if isinstance(value, VariableValue):
        _count_variable(value.variable, counts)
    elif isinstance(value, (ResolvedUnaryExpression, ResolvedBooleanNotExpression)):
        _count_value_variable_references(value.operand, counts)
    elif isinstance(value, ResolvedGetTile):
        _count_value_variable_references(value.x, counts)
        _count_value_variable_references(value.y, counts)
    elif isinstance(
        value,
        (
            ResolvedBinaryExpression,
            ResolvedComparisonExpression,
            ResolvedBooleanBinaryExpression,
        ),
    ):
        _count_value_variable_references(value.left, counts)
        _count_value_variable_references(value.right, counts)


def _count_variable(variable: ResolvedVariable, counts: dict[str, int]) -> None:
    if variable.label in counts:
        counts[variable.label] += 1


def _temporary_symbol_names(program: ResolvedProgram) -> tuple[str, ...]:
    all_statements = (
        *program.statements,
        *(
            statement
            for procedure in program.procedures
            for statement in procedure.body
        ),
    )
    expression_count = max(
        (_statement_expression_depth(statement) for statement in all_statements),
        default=0,
    )
    for_count = sum(_count_for_statements(statement) for statement in all_statements)
    return (
        *(f"expression_temporary_{index}" for index in range(expression_count)),
        *(f"for_limit_{index}" for index in range(for_count)),
    )


def _expression_depth(value: ResolvedValue) -> int:
    if isinstance(value, ResolvedGetTile):
        return max(_expression_depth(value.x), _expression_depth(value.y))
    if isinstance(value, (ResolvedBinaryExpression, ResolvedComparisonExpression)):
        return 1 + max(_expression_depth(value.left), _expression_depth(value.right))
    if isinstance(value, (ResolvedUnaryExpression, ResolvedBooleanNotExpression)):
        return _expression_depth(value.operand)
    if isinstance(value, ResolvedBooleanBinaryExpression):
        return max(_expression_depth(value.left), _expression_depth(value.right))
    return 0


def _statement_expression_depth(statement: ResolvedStatement) -> int:
    if isinstance(statement, ResolvedAssignment):
        return _expression_depth(statement.value)
    if isinstance(statement, ResolvedSetBackgroundColor):
        return _expression_depth(statement.argument)
    if isinstance(statement, ResolvedSetPalette):
        return max(_expression_depth(value) for value in statement.colors)
    if isinstance(statement, ResolvedSetPaletteColor):
        return _expression_depth(statement.color)
    if isinstance(statement, ResolvedSetSpriteZero):
        return max(
            _expression_depth(statement.x),
            _expression_depth(statement.y),
            _expression_depth(statement.tile),
            _expression_depth(statement.attributes),
        )
    if isinstance(statement, ResolvedSetTile):
        return max(
            _expression_depth(statement.x),
            _expression_depth(statement.y),
            _expression_depth(statement.tile),
        )
    if isinstance(statement, ResolvedSetAttribute):
        return max(
            _expression_depth(statement.x),
            _expression_depth(statement.y),
            _expression_depth(statement.value),
        )
    if isinstance(statement, ResolvedIncrementStatement):
        return _expression_depth(statement.amount) if statement.amount else 0
    if isinstance(statement, ResolvedDecrementStatement):
        return max(1, _expression_depth(statement.amount)) if statement.amount else 0
    if isinstance(statement, ResolvedIfStatement):
        branches = [
            _statement_expression_depth(item) for item in statement.then_branch
        ]
        if statement.else_branch is not None:
            branches.extend(
                _statement_expression_depth(item) for item in statement.else_branch
            )
        return max([_expression_depth(statement.condition), *branches])
    if isinstance(statement, (ResolvedWhileStatement, ResolvedRepeatStatement)):
        body = [_statement_expression_depth(item) for item in statement.body]
        return max([_expression_depth(statement.condition), *body])
    if isinstance(statement, ResolvedForStatement):
        body = [_statement_expression_depth(item) for item in statement.body]
        return max(
            [
                _expression_depth(statement.initial),
                _expression_depth(statement.final),
                *body,
            ]
        )
    if isinstance(statement, ResolvedProcedureCall):
        return max(
            (_expression_depth(argument.value) for argument in statement.arguments),
            default=0,
        )
    return 0


def _count_for_statements(statement: ResolvedStatement) -> int:
    if isinstance(statement, ResolvedForStatement):
        return 1 + sum(_count_for_statements(item) for item in statement.body)
    if isinstance(statement, ResolvedIfStatement):
        count = sum(_count_for_statements(item) for item in statement.then_branch)
        if statement.else_branch is not None:
            count += sum(_count_for_statements(item) for item in statement.else_branch)
        return count
    if isinstance(statement, (ResolvedWhileStatement, ResolvedRepeatStatement)):
        return sum(_count_for_statements(item) for item in statement.body)
    return 0
