"""Deterministic NES CPU RAM layout, allocation, and artifact generation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .ast import (
    ResolvedAssignment,
    ResolvedBinaryExpression,
    ResolvedBooleanBinaryExpression,
    ResolvedBooleanNotExpression,
    ResolvedDecrementStatement,
    ResolvedForStatement,
    ResolvedIfStatement,
    ResolvedIncrementStatement,
    ResolvedProcedureCall,
    ResolvedProgram,
    ResolvedRepeatStatement,
    ResolvedSetBackgroundColor,
    ResolvedStatement,
    ResolvedUnaryExpression,
    ResolvedValue,
    ResolvedVariable,
    ResolvedWhileStatement,
    ResolvedComparisonExpression,
    SourcePosition,
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
    """Internal NROM memory defaults for milestone 0.3.1."""

    physical_ram_start: int = 0x0000
    physical_ram_size: int = 0x0800
    zero_page_start: int = 0x0000
    zero_page_size: int = 0x0100
    hardware_stack_start: int = 0x0100
    hardware_stack_size: int = 0x0100
    oam_shadow_start: int = 0x0200
    oam_shadow_size: int = 0x0100
    general_ram_start: int = 0x0300
    runtime_data_size: int = 0
    temporary_storage_size: int = 16
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
class ProgramMemoryLayout:
    """Validated regions and concrete symbol allocations for one program."""

    settings: MemoryLayoutSettings
    physical_ram: MemoryRange
    zero_page: MemoryRange
    hardware_stack: MemoryRange
    oam_shadow: MemoryRange
    runtime_data: MemoryRange
    temporary_storage: MemoryRange
    user_capacity: MemoryRange
    runtime_symbols: tuple[MemorySymbol, ...]
    temporary_symbols: tuple[MemorySymbol, ...]
    user_symbols: tuple[MemorySymbol, ...]

    @property
    def user_variables(self) -> MemoryRange:
        return MemoryRange(
            "User variables",
            self.user_capacity.start,
            sum(symbol.size for symbol in self.user_symbols),
            RegionKind.USER,
        )

    @property
    def free_ram(self) -> MemoryRange:
        used = self.user_variables.size
        return MemoryRange(
            "Free RAM",
            self.user_capacity.start + used,
            self.user_capacity.size - used,
            RegionKind.FREE,
        )

    @property
    def display_regions(self) -> tuple[MemoryRange, ...]:
        return (
            self.zero_page,
            self.hardware_stack,
            self.oam_shadow,
            self.runtime_data,
            self.temporary_storage,
            self.user_variables,
            self.free_ram,
        )

    @property
    def temporary_bytes_used(self) -> int:
        return sum(symbol.size for symbol in self.temporary_symbols)

    @property
    def reserved_or_used_bytes(self) -> int:
        return self.physical_ram.size - self.free_ram.size


def build_memory_layout(
    program: ResolvedProgram,
    settings: MemoryLayoutSettings = DEFAULT_MEMORY_LAYOUT_SETTINGS,
    *,
    source: str = "",
    filename: str = "<input>",
) -> ProgramMemoryLayout:
    """Validate settings and allocate every RAM-backed program symbol."""

    regions = _validated_regions(settings, source, filename)
    (
        physical_ram,
        zero_page,
        hardware_stack,
        oam_shadow,
        runtime_data,
        temporary_storage,
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
                "Simplify nested expressions or loops, or increase the internal "
                "temporary-storage setting."
            ),
        )

    runtime_symbols = (
        MemorySymbol(
            "runtime_oam_shadow",
            oam_shadow.start,
            oam_shadow.size,
            SymbolKind.RUNTIME,
            oam_shadow.name,
            "256-byte page copied to PPU OAM by future sprite runtime support",
        ),
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

    user_symbols: list[MemorySymbol] = []
    next_user_address = user_capacity.start
    for source_name, variable, purpose in _user_variables(program):
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
        hardware_stack,
        oam_shadow,
        runtime_data,
        temporary_storage,
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
        layout.oam_shadow,
        layout.runtime_data,
        layout.temporary_storage,
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
        _linker_memory_line("ZEROPAGE", layout.zero_page),
        _linker_memory_line("STACK", layout.hardware_stack),
        _linker_memory_line("OAM", layout.oam_shadow),
        _linker_memory_line("RUNTIME", layout.runtime_data),
    ]
    memory_lines.extend(
        [
            _linker_memory_line("TEMP", layout.temporary_storage),
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
        "    OAM_SHADOW:          load = OAM,    type = bss;",
        "    RUNTIME_DATA:        load = RUNTIME, type = bss;",
    ]
    segment_lines.extend(
        [
            "    TEMPORARIES:         load = TEMP,   type = bss;",
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
        "",
        "Regions",
        "-------",
        "",
        "Start  End    Size  Owner     Region",
    ]
    temporary_detail = (
        f" ({layout.temporary_bytes_used} used, "
        f"{layout.temporary_storage.size - layout.temporary_bytes_used} available)"
    )
    for region in layout.display_regions:
        detail = temporary_detail if region == layout.temporary_storage else ""
        end = f"${region.end:04X}" if region.end is not None else "----"
        lines.append(
            f"${region.start:04X}  {end:5}  {region.size:4}  "
            f"{region.kind.value:8}  {region.name}{detail}"
        )
    lines.extend(
        [
            "",
            f"Reserved or used: {layout.reserved_or_used_bytes} bytes",
            f"Available:        {layout.free_ram.size} bytes",
            "",
            "User Symbols",
            "------------",
            "",
            "Address  Size  Type       Source name                 Assembly symbol",
        ]
    )
    if layout.user_symbols:
        for symbol in layout.user_symbols:
            lines.append(
                f"${symbol.address:04X}    {symbol.size:4}  "
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
    if settings.runtime_data_size < 0 or settings.temporary_storage_size < 0:
        _invalid_layout("RAM region sizes cannot be negative.", source, filename)

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
    stack = MemoryRange(
        "6502 hardware stack",
        settings.hardware_stack_start,
        settings.hardware_stack_size,
        RegionKind.RESERVED,
    )
    oam = MemoryRange(
        "OAM shadow",
        settings.oam_shadow_start,
        settings.oam_shadow_size,
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
        settings.general_ram_start,
        settings.runtime_data_size,
        RegionKind.RUNTIME,
    )
    temporary = MemoryRange(
        "Expression temporaries",
        runtime.start + runtime.size,
        settings.temporary_storage_size,
        RegionKind.COMPILER,
    )
    user_start = temporary.start + temporary.size
    physical_end = physical.end
    assert physical_end is not None
    if user_start > physical_end + 1:
        _invalid_layout(
            "Runtime data and temporary storage extend beyond physical RAM at "
            "$07FF.",
            source,
            filename,
        )
    user = MemoryRange(
        "User RAM",
        user_start,
        physical_end + 1 - user_start,
        RegionKind.USER,
    )
    return physical, zero_page, stack, oam, runtime, temporary, user


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
        suggestion="Use the supported milestone 0.3.1 NROM memory settings.",
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
) -> tuple[tuple[str, ResolvedVariable, str], ...]:
    variables = [
        (variable.name, variable, "source variable")
        for variable in program.variables
    ]
    variables.extend(
        (
            f"{procedure.name}.{parameter.name}",
            parameter,
            f"value parameter for {procedure.name}",
        )
        for procedure in program.procedures
        for parameter in procedure.parameters
    )
    return tuple(variables)


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
