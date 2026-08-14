"""Deterministic NES CPU RAM layout, allocation, and artifact generation."""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
from enum import StrEnum

from .ast import (
    ArrayType,
    ImmediateValue,
    OamOwnerKind,
    ResolvedArrayElement,
    ResolvedArrayElementAssignment,
    ResolvedAssignment,
    ResolvedBinaryExpression,
    ResolvedBooleanBinaryExpression,
    ResolvedBooleanNotExpression,
    ResolvedComparisonExpression,
    ResolvedDecrementStatement,
    ResolvedForStatement,
    ResolvedIfStatement,
    ResolvedIncrementStatement,
    ResolvedBuiltinCall,
    ResolvedProcedureCall,
    ResolvedProgram,
    ResolvedRepeatStatement,
    ResolvedRecordField,
    ResolvedRecordFieldAssignment,
    ResolvedStatement,
    ResolvedUnaryExpression,
    ResolvedValue,
    ResolvedVariable,
    ResolvedWhileStatement,
    RecordType,
    SourcePosition,
    VariableType,
    VariableValue,
)
from .builtins import BuiltinId, RuntimeFeature, builtin_by_id
from .codegen_analysis import TemporaryRequirements, analyze_program_temporaries
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
    # Maximum combined capacity for expression temporaries and compiler caches.
    # Each program reserves only its measured requirement within this limit.
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
class SpriteRuntimeFeatures:
    """Sprite entry points and the runtime storage they require."""

    legacy_sprite_zero: bool = False
    sprite_api: bool = False
    set_position: bool = False
    metasprite_instances: int = 0
    metasprite_animation: bool = False

    @property
    def oam_shadow(self) -> bool:
        return (
            self.legacy_sprite_zero
            or self.sprite_api
            or self.metasprite_instances > 0
        )

    @property
    def metasprite_api(self) -> bool:
        return self.metasprite_instances > 0

    @property
    def individual_runtime_size(self) -> int:
        return (
            (5 if self.legacy_sprite_zero else 0)
            + (65 if self.sprite_api else 0)
            + (1 if self.set_position else 0)
        )

    @property
    def metasprite_runtime_size(self) -> int:
        if not self.metasprite_api:
            return 0
        instance_bytes = 8 if self.metasprite_animation else 4
        return self.metasprite_instances * instance_bytes + 8

    @property
    def runtime_size(self) -> int:
        return self.individual_runtime_size + self.metasprite_runtime_size


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
            self.expression_temporary_storage,
            self.compiler_cache_storage,
            self.zero_page_recovered,
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
            if region.size
            or region in (self.expression_temporary_storage, self.runtime_data)
        )

    @property
    def expression_temporary_symbols(self) -> tuple[MemorySymbol, ...]:
        return tuple(
            symbol
            for symbol in self.temporary_symbols
            if symbol.assembly_symbol.startswith("expression_temporary_")
        )

    @property
    def compiler_cache_symbols(self) -> tuple[MemorySymbol, ...]:
        return tuple(
            symbol
            for symbol in self.temporary_symbols
            if not symbol.assembly_symbol.startswith("expression_temporary_")
        )

    @property
    def expression_temporary_storage(self) -> MemoryRange:
        return MemoryRange(
            "Expression temporaries",
            self.temporary_storage.start,
            sum(symbol.size for symbol in self.expression_temporary_symbols),
            RegionKind.COMPILER,
        )

    @property
    def compiler_cache_storage(self) -> MemoryRange:
        expression_storage = self.expression_temporary_storage
        return MemoryRange(
            "Compiler caches",
            expression_storage.start + expression_storage.size,
            sum(symbol.size for symbol in self.compiler_cache_symbols),
            RegionKind.COMPILER,
        )

    @property
    def zero_page_recovered(self) -> MemoryRange:
        return MemoryRange(
            "Recovered temporary Zero Page",
            self.temporary_storage.start + self.temporary_storage.size,
            self.settings.temporary_storage_size - self.temporary_storage.size,
            RegionKind.FREE,
        )

    @property
    def temporary_bytes_used(self) -> int:
        return sum(symbol.size for symbol in self.temporary_symbols)

    @property
    def expression_temporary_bytes(self) -> int:
        return self.expression_temporary_storage.size

    @property
    def compiler_cache_bytes(self) -> int:
        return self.compiler_cache_storage.size

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
            + self.zero_page_recovered.size
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

    sprite_features = detect_sprite_runtime_features(program)
    sprite_zero_enabled = sprite_features.legacy_sprite_zero
    sprite_api_enabled = sprite_features.sprite_api
    metasprite_api_enabled = sprite_features.metasprite_api
    palette_runtime_enabled = _uses_runtime_palette(program)
    scroll_runtime_enabled = _uses_set_scroll(program)
    background_features = detect_background_runtime_features(program)
    background_queue_enabled = background_features.queue
    background_shadow_enabled = background_features.shadow
    sprite_zero_runtime_size = 5 if sprite_zero_enabled else 0
    individual_sprite_runtime_size = sprite_features.individual_runtime_size
    sprite_runtime_size = sprite_features.runtime_size
    palette_runtime_size = 41 if palette_runtime_enabled else 0
    ppu_state_size = 4
    scroll_staging_size = 3 if scroll_runtime_enabled else 0
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
        + scroll_staging_size
        + background_shadow_size
        + background_runtime_size
    )
    if settings.runtime_data_size < required_runtime_size:
        settings = replace(settings, runtime_data_size=required_runtime_size)

    temporary_requirements = analyze_program_temporaries(program)
    if temporary_requirements.total_bytes > settings.temporary_storage_size:
        _raise_error(
            DiagnosticCode.TEMPORARY_RAM_EXHAUSTED,
            "Compiler-managed Zero Page storage requires "
            f"{temporary_requirements.total_bytes} bytes "
            f"({temporary_requirements.expression_temporaries} expression "
            f"temporaries and {temporary_requirements.compiler_caches} compiler "
            f"caches), but only {settings.temporary_storage_size} bytes are "
            "available.",
            filename,
            source,
            suggestion=(
                "Simplify nested expressions or loops. Mandatory temporary "
                "allocations cannot borrow optional promotion space."
            ),
        )

    regions = _validated_regions(
        settings,
        source,
        filename,
        oam_shadow_enabled=sprite_features.oam_shadow,
        temporary_storage_size=temporary_requirements.total_bytes,
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

    temporary_names = _temporary_symbol_names(temporary_requirements)

    background_runtime_symbols: list[MemorySymbol] = []
    next_background_address = (
        runtime_data.start
        + sprite_runtime_size
        + palette_runtime_size
        + ppu_state_size
        + scroll_staging_size
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

    metasprite_base = runtime_data.start + individual_sprite_runtime_size
    metasprite_count = sprite_features.metasprite_instances
    metasprite_animation_base = metasprite_base + metasprite_count * 4
    metasprite_scratch_base = metasprite_animation_base + (
        metasprite_count * 4 if sprite_features.metasprite_animation else 0
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
                    "runtime_metasprite_frame_pointer",
                    zero_page_runtime.start + 9,
                    2,
                    SymbolKind.RUNTIME,
                    zero_page_runtime.name,
                    "indirect pointer into immutable metasprite frame data",
                ),
                MemorySymbol(
                    "runtime_metasprite_slot_pointer",
                    zero_page_runtime.start + 11,
                    2,
                    SymbolKind.RUNTIME,
                    zero_page_runtime.name,
                    "indirect pointer into one metasprite OAM ownership table",
                ),
            )
            if metasprite_api_enabled
            else ()
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
            if sprite_features.oam_shadow
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
                    "runtime_sprite_logical_y",
                    runtime_data.start + sprite_zero_runtime_size,
                    64,
                    SymbolKind.RUNTIME,
                    runtime_data.name,
                    "logical Y coordinates restored by nes.sprite_show",
                ),
                MemorySymbol(
                    "runtime_sprite_value",
                    runtime_data.start + sprite_zero_runtime_size + 64,
                    1,
                    SymbolKind.RUNTIME,
                    runtime_data.name,
                    "temporary property value for sprite runtime helpers",
                ),
                *(
                    (
                        MemorySymbol(
                            "runtime_sprite_secondary_value",
                            runtime_data.start + sprite_zero_runtime_size + 65,
                            1,
                            SymbolKind.RUNTIME,
                            runtime_data.name,
                            "second property value for nes.sprite_set_position",
                        ),
                    )
                    if sprite_features.set_position
                    else ()
                ),
            )
            if sprite_api_enabled
            else ()
        ),
        *(
            (
                MemorySymbol(
                    "runtime_metasprite_x",
                    metasprite_base,
                    metasprite_count,
                    SymbolKind.RUNTIME,
                    runtime_data.name,
                    "logical screen X for each metasprite instance",
                ),
                MemorySymbol(
                    "runtime_metasprite_y",
                    metasprite_base + metasprite_count,
                    metasprite_count,
                    SymbolKind.RUNTIME,
                    runtime_data.name,
                    "logical screen Y for each metasprite instance",
                ),
                MemorySymbol(
                    "runtime_metasprite_frame",
                    metasprite_base + metasprite_count * 2,
                    metasprite_count,
                    SymbolKind.RUNTIME,
                    runtime_data.name,
                    "selected symbolic frame for each metasprite instance",
                ),
                MemorySymbol(
                    "runtime_metasprite_flags",
                    metasprite_base + metasprite_count * 3,
                    metasprite_count,
                    SymbolKind.RUNTIME,
                    runtime_data.name,
                    "visibility and whole-metasprite flip flags",
                ),
                *(
                    (
                        MemorySymbol(
                            "runtime_metasprite_animation",
                            metasprite_animation_base,
                            metasprite_count,
                            SymbolKind.RUNTIME,
                            runtime_data.name,
                            "selected animation identifier",
                        ),
                        MemorySymbol(
                            "runtime_metasprite_animation_frame",
                            metasprite_animation_base + metasprite_count,
                            metasprite_count,
                            SymbolKind.RUNTIME,
                            runtime_data.name,
                            "current frame index inside each active animation",
                        ),
                        MemorySymbol(
                            "runtime_metasprite_animation_timer",
                            metasprite_animation_base + metasprite_count * 2,
                            metasprite_count,
                            SymbolKind.RUNTIME,
                            runtime_data.name,
                            "remaining logical frame ticks for each animation frame",
                        ),
                        MemorySymbol(
                            "runtime_metasprite_animation_flags",
                            metasprite_animation_base + metasprite_count * 3,
                            metasprite_count,
                            SymbolKind.RUNTIME,
                            runtime_data.name,
                            "animation active and completion flags",
                        ),
                    )
                    if sprite_features.metasprite_animation
                    else ()
                ),
                *(
                    MemorySymbol(
                        f"runtime_metasprite_{name}",
                        metasprite_scratch_base + offset,
                        1,
                        SymbolKind.RUNTIME,
                        runtime_data.name,
                        purpose,
                    )
                    for offset, (name, purpose) in enumerate(
                        (
                            ("current_instance", "instance currently being rendered"),
                            ("frame_remaining", "components left in selected frame"),
                            ("slots_remaining", "reserved OAM slots left to visit"),
                            ("oam_offset", "current OAM shadow byte offset"),
                            ("offset_x", "signed component X offset"),
                            ("offset_y", "signed component Y offset"),
                            ("tile", "current component CHR tile"),
                            ("attributes", "current component attributes"),
                        )
                    )
                ),
            )
            if metasprite_api_enabled
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
                            "authoritative PPUCTRL value restored each NMI",
                        ),
                        (
                            "runtime_ppumask_shadow",
                            "authoritative PPUMASK value restored each NMI",
                        ),
                        (
                            "runtime_scroll_x_shadow",
                            "authoritative horizontal scroll restored each NMI",
                        ),
                        (
                            "runtime_scroll_y_shadow",
                            "authoritative vertical scroll restored each NMI",
                        ),
                    )
                )
            )
        ),
        *(
            tuple(
                MemorySymbol(
                    name,
                    runtime_data.start
                    + sprite_runtime_size
                    + palette_runtime_size
                    + ppu_state_size
                    + index,
                    1,
                    SymbolKind.RUNTIME,
                    runtime_data.name,
                    purpose,
                )
                for index, (name, purpose) in enumerate(
                    (
                        ("runtime_scroll_pending_x", "staged horizontal scroll"),
                        ("runtime_scroll_pending_y", "staged vertical scroll"),
                        ("runtime_scroll_ready", "atomic scroll publication flag"),
                    )
                )
            )
            if scroll_staging_size
            else ()
        ),
        *(
            (
                MemorySymbol(
                    "runtime_background_shadow",
                    runtime_data.start
                    + sprite_runtime_size
                    + palette_runtime_size
                    + ppu_state_size
                    + scroll_staging_size,
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
    expression_storage = MemoryRange(
        "Expression temporaries",
        temporary_storage.start,
        temporary_requirements.expression_temporaries,
        RegionKind.COMPILER,
    )
    compiler_cache_storage = MemoryRange(
        "Compiler caches",
        expression_storage.start + expression_storage.size,
        temporary_requirements.compiler_caches,
        RegionKind.COMPILER,
    )
    temporary_symbols = tuple(
        MemorySymbol(
            name,
            temporary_storage.start + index,
            1,
            SymbolKind.COMPILER,
            (
                expression_storage.name
                if name.startswith("expression_temporary_")
                else compiler_cache_storage.name
            ),
            (
                "scoped reusable expression evaluation byte"
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
        if not isinstance(variable.type, (ArrayType, RecordType))
        if reference_counts.get(variable.label, 0)
        >= settings.automatic_promotion_min_references
    }

    user_symbols: list[MemorySymbol] = []
    next_zero_page_address = zero_page_automatic.start
    next_user_address = user_capacity.start
    for source_name, variable, purpose, promotion_allowed in _user_variables(program):
        size = _type_storage_size(variable.type)
        promote = (
            promotion_allowed
            and size == 1
            and variable.label in promoted_labels
            and next_zero_page_address
            < zero_page_automatic.start + zero_page_automatic.size
        )
        if promote:
            user_symbols.append(
                MemorySymbol(
                    variable.label,
                    next_zero_page_address,
                    size,
                    SymbolKind.USER,
                    zero_page_automatic.name,
                    f"{purpose}; automatically promoted after "
                    f"{reference_counts[variable.label]} source references",
                    source_name,
                    variable.type.value,
                    variable.position,
                )
            )
            next_zero_page_address += size
            continue

        available = user_capacity.start + user_capacity.size - next_user_address
        if available < size:
            _raise_error(
                DiagnosticCode.USER_RAM_EXHAUSTED,
                f"User RAM cannot allocate {source_name}: requested {size} "
                f"{'byte' if size == 1 else 'bytes'}, "
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
                size,
                SymbolKind.USER,
                user_capacity.name,
                purpose,
                source_name,
                variable.type.value,
                variable.position,
            )
        )
        next_user_address += size

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
        layout.expression_temporary_storage,
        layout.compiler_cache_storage,
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
    if layout.zero_page_recovered.size:
        memory_lines.insert(
            2,
            _linker_memory_line("ZP_TEMP_FREE", layout.zero_page_recovered),
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
        f"Expression temporary reservation: "
        f"{layout.expression_temporary_bytes} "
        f"{'byte' if layout.expression_temporary_bytes == 1 else 'bytes'} "
        "(maximum simultaneously live)",
        f"Other compiler caches: {layout.compiler_cache_bytes} "
        f"{'byte' if layout.compiler_cache_bytes == 1 else 'bytes'}",
        "",
        "Regions",
        "-------",
        "",
        "Start  End    Size  Owner     Region",
    ]
    promotion_detail = (
        f" ({layout.promoted_bytes_used} used, "
        f"{layout.zero_page_automatic.size - layout.promoted_bytes_used} available)"
    )
    for region in layout.display_regions:
        if region == layout.zero_page_automatic:
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
            "Address range  Size  Storage     Type       "
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
            address_range = (
                f"${symbol.address:04X}"
                if symbol.size == 1
                else f"${symbol.address:04X}-${symbol.address + symbol.size - 1:04X}"
            )
            lines.append(
                f"{address_range:13}  {symbol.size:4}  "
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
    temporary_storage_size: int,
) -> tuple[MemoryRange, ...]:
    if (
        settings.mapper_number != 0
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
        temporary_storage_size,
        RegionKind.COMPILER,
    )
    zero_page_explicit_reserve = MemoryRange(
        "Future explicit Zero Page",
        zero_page_runtime.start
        + zero_page_runtime.size
        + settings.temporary_storage_size,
        settings.zero_page_explicit_reserve_size,
        RegionKind.RESERVED,
    )
    zero_page_automatic = MemoryRange(
        "Automatic Zero Page variables",
        zero_page_explicit_reserve.start + zero_page_explicit_reserve.size,
        settings.zero_page_automatic_size,
        RegionKind.USER,
    )
    zero_page_unallocated = MemoryRange(
        "Unallocated Zero Page",
        zero_page_automatic.start + zero_page_automatic.size,
        zero_page.start
        + zero_page.size
        - zero_page_automatic.start
        - zero_page_automatic.size,
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


def collect_runtime_features(
    program: ResolvedProgram,
) -> frozenset[RuntimeFeature]:
    """Collect descriptor-declared runtime dependencies recursively."""

    features: set[RuntimeFeature] = set()

    def visit(value: object) -> None:
        if isinstance(value, ResolvedBuiltinCall):
            descriptor = builtin_by_id(value.builtin)
            features.update(descriptor.runtime_features)
            if value.queued:
                features.update(descriptor.queued_runtime_features)
            for argument in value.arguments:
                visit(argument)
            return
        if isinstance(value, tuple):
            for item in value:
                visit(item)
            return
        if is_dataclass(value):
            for field in fields(value):
                visit(getattr(value, field.name))

    visit(program.statements)
    for procedure in program.procedures:
        visit(procedure.body)
    return frozenset(features)


def detect_sprite_runtime_features(program: ResolvedProgram) -> SpriteRuntimeFeatures:
    """Derive sprite storage from resolved builtin dependencies."""

    features = collect_runtime_features(program)
    sprite_api = (
        RuntimeFeature.SPRITE_API in features
        or any(
            reservation.owner is OamOwnerKind.INDIVIDUAL_CREATED
            for reservation in program.oam_reservations
        )
    )
    return SpriteRuntimeFeatures(
        legacy_sprite_zero=RuntimeFeature.LEGACY_SPRITE_ZERO in features,
        sprite_api=sprite_api,
        set_position=RuntimeFeature.SPRITE_SET_POSITION in features,
        metasprite_instances=len(program.metasprite_instances),
        metasprite_animation=RuntimeFeature.METASPRITE_ANIMATION in features,
    )


def _uses_runtime_palette(program: ResolvedProgram) -> bool:
    return RuntimeFeature.PALETTE_QUEUE in collect_runtime_features(program)


def _uses_set_scroll(program: ResolvedProgram) -> bool:
    return RuntimeFeature.SCROLL in collect_runtime_features(program)


def detect_background_runtime_features(
    program: ResolvedProgram,
) -> BackgroundRuntimeFeatures:
    """Derive isolated background storage from registry dependencies."""

    features = collect_runtime_features(program)
    return BackgroundRuntimeFeatures(
        set_tile=RuntimeFeature.BACKGROUND_SET_TILE in features,
        get_tile=RuntimeFeature.BACKGROUND_GET_TILE in features,
        set_attribute=RuntimeFeature.BACKGROUND_SET_ATTRIBUTE in features,
        clear_updates=RuntimeFeature.BACKGROUND_CLEAR_UPDATES in features,
        inspect_overflow=RuntimeFeature.BACKGROUND_INSPECT_OVERFLOW in features,
        clear_overflow=RuntimeFeature.BACKGROUND_CLEAR_OVERFLOW in features,
    )


def _count_statement_variable_references(
    statement: ResolvedStatement,
    counts: dict[str, int],
) -> None:
    if isinstance(statement, ResolvedRecordFieldAssignment):
        _count_variable(statement.target, counts)
        if statement.index is not None:
            _count_value_variable_references(statement.index, counts)
        _count_value_variable_references(statement.value, counts)
    elif isinstance(statement, ResolvedArrayElementAssignment):
        _count_variable(statement.target, counts)
        _count_value_variable_references(statement.index, counts)
        _count_value_variable_references(statement.value, counts)
    elif isinstance(statement, ResolvedAssignment):
        _count_variable(statement.target, counts)
        _count_value_variable_references(statement.value, counts)
    elif isinstance(statement, ResolvedBuiltinCall):
        for value in statement.arguments:
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
    if isinstance(value, ResolvedRecordField):
        _count_variable(value.variable, counts)
        if value.index is not None:
            _count_value_variable_references(value.index, counts)
    elif isinstance(value, ResolvedArrayElement):
        _count_variable(value.array, counts)
        _count_value_variable_references(value.index, counts)
    elif isinstance(value, VariableValue):
        _count_variable(value.variable, counts)
    elif isinstance(value, (ResolvedUnaryExpression, ResolvedBooleanNotExpression)):
        _count_value_variable_references(value.operand, counts)
    elif isinstance(value, ResolvedBuiltinCall):
        for argument in value.arguments:
            _count_value_variable_references(argument, counts)
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


def _temporary_symbol_names(
    requirements: TemporaryRequirements,
) -> tuple[str, ...]:
    return (
        *(
            f"expression_temporary_{index}"
            for index in range(requirements.expression_temporaries)
        ),
        *(f"for_limit_{index}" for index in range(requirements.compiler_caches)),
    )


def _type_storage_size(type_: VariableType) -> int:
    if isinstance(type_, RecordType):
        return type_.size
    if isinstance(type_, ArrayType):
        element_size = (
            type_.element_type.size
            if isinstance(type_.element_type, RecordType)
            else 1
        )
        return type_.element_count * element_size
    return 1
