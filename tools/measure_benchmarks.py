"""Measurement and pattern analysis tooling for Milestone 0.5.5.

Collects deterministic resource metrics, analyzes generated assembly patterns,
computes AST tree depth and live expression temporaries, and analyzes RAM breakdowns.
"""

from dataclasses import dataclass, field
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nes_pascal.assets import load_background_data, load_chr_rom
from nes_pascal.ast import (
    BinaryExpression,
    BooleanBinaryExpression,
    BooleanNotExpression,
    ComparisonExpression,
    Program,
    ResolvedAssignment,
    ResolvedBinaryExpression,
    ResolvedBooleanBinaryExpression,
    ResolvedBooleanNotExpression,
    ResolvedBuiltinCall,
    ResolvedComparisonExpression,
    ResolvedForStatement,
    ResolvedIfStatement,
    ResolvedProcedure,
    ResolvedProcedureCall,
    ResolvedProgram,
    ResolvedRepeatStatement,
    ResolvedStatement,
    ResolvedUnaryExpression,
    ResolvedValue,
    ResolvedWhileStatement,
    UnaryExpression,
    ValueExpression,
)
from nes_pascal.builtins import BuiltinId
from nes_pascal.backend_ca65 import generate
from nes_pascal.memory_layout import (
    DEFAULT_MEMORY_LAYOUT_SETTINGS,
    MemoryLayoutSettings,
    ProgramMemoryLayout,
    build_memory_layout,
    generate_linker_config,
    generate_memory_map,
)
from nes_pascal.metasprite_assets import load_metasprite_assets
from nes_pascal.parser import parse
from nes_pascal.semantic import analyze


@dataclass(frozen=True)
class BenchmarkSpec:
    name: str
    category: str
    source_file: str
    chr_path: str | None = None
    nametable_path: str | None = None
    metasprite_paths: tuple[str, ...] = ()


BENCHMARKS: tuple[BenchmarkSpec, ...] = (
    BenchmarkSpec("minimal", "Minimal Runtime", "examples/minimal.nsp"),
    BenchmarkSpec("arithmetic", "Arithmetic", "examples/arithmetic.nsp"),
    BenchmarkSpec("boolean_expressions", "Boolean Expressions", "examples/boolean_expressions.nsp"),
    BenchmarkSpec("conditionals", "Conditionals", "examples/conditionals.nsp"),
    BenchmarkSpec("loops", "Loops (while/repeat)", "examples/loops.nsp"),
    BenchmarkSpec("counting", "Counting & for-loops", "examples/counting.nsp"),
    BenchmarkSpec("procedures", "Procedures", "examples/procedures.nsp"),
    BenchmarkSpec("procedure_parameters", "Procedure Parameters", "examples/procedure_parameters.nsp"),
    BenchmarkSpec("controller_input", "Controller Input", "examples/controller_input.nsp"),
    BenchmarkSpec(
        "sprite_support",
        "Individual Sprites",
        "examples/sprite_support.nsp",
        chr_path="assets/chr_asset.chr",
    ),
    BenchmarkSpec(
        "metasprite_player",
        "Metasprites",
        "examples/metasprite_player.nsp",
        chr_path="assets/game.chr",
        metasprite_paths=("assets/player_idle.json",),
    ),
    BenchmarkSpec(
        "sprite_animation",
        "Sprite Animation",
        "examples/sprite_animation.nsp",
        chr_path="assets/game.chr",
        metasprite_paths=("assets/player_consolidated.json",),
    ),
    BenchmarkSpec(
        "palette_support",
        "Palettes",
        "examples/palette_support.nsp",
        chr_path="assets/chr_asset.chr",
    ),
    BenchmarkSpec(
        "background_updates",
        "Background Updates",
        "examples/background_updates.nsp",
        chr_path="assets/chr_asset.chr",
        nametable_path="assets/nametable_loading.nam",
    ),
    BenchmarkSpec(
        "frame_callbacks",
        "Frame Callbacks",
        "examples/frame_callbacks.nsp",
    ),
    BenchmarkSpec(
        "gameplay_full_stack",
        "Full-Stack Gameplay (Combined RAM Pressure)",
        "examples/gameplay_full_stack.nsp",
        chr_path="assets/game.chr",
        nametable_path="assets/nametable_loading.nam",
        metasprite_paths=("assets/player_consolidated.json",),
    ),
)


def get_expression_metrics(val: ResolvedValue) -> tuple[int, int]:
    """Compute (tree_depth, max_simultaneous_live_temporaries) for an expression.

    - tree_depth: height of the expression tree (0 for leaf literals/variables).
    - live_temporaries: number of simultaneous expression_temporary_X required during lowering.
      Under current backend ca65 lowering:
      Right operand is evaluated first into temp_D, then left operand is evaluated.
      For simple leaves (e.g. A + B), 1 temporary (temp_0) is used while A is loaded.
    """
    if isinstance(val, (ResolvedBinaryExpression, ResolvedComparisonExpression, ResolvedBooleanBinaryExpression)):
        d_l, t_l = get_expression_metrics(val.left)
        d_r, t_r = get_expression_metrics(val.right)
        tree_depth = 1 + max(d_l, d_r)
        # Right evaluated first, then stored in temp_D while left is evaluated:
        live_temps = max(t_r, 1 + t_l)
        return tree_depth, live_temps
    if isinstance(val, (ResolvedBooleanNotExpression, ResolvedUnaryExpression)):
        d, t = get_expression_metrics(val.operand)
        return 1 + d, t
    if isinstance(val, ResolvedBuiltinCall):
        metrics = [get_expression_metrics(argument) for argument in val.arguments]
        if not metrics:
            return 0, 0
        depth = max(item[0] for item in metrics)
        temporaries = max(item[1] for item in metrics)
        if val.builtin is BuiltinId.GET_TILE:
            return 1 + depth, max(
                metrics[0][1],
                1 + metrics[1][1],
            )
        return depth, temporaries
    return 0, 0


def collect_statement_metrics(stmts: tuple[ResolvedStatement, ...]) -> tuple[int, int]:
    max_d, max_t = 0, 0
    for s in stmts:
        if isinstance(s, ResolvedAssignment):
            d, t = get_expression_metrics(s.value)
            max_d, max_t = max(max_d, d), max(max_t, t)
        elif isinstance(s, ResolvedBuiltinCall):
            for value in s.arguments:
                d, t = get_expression_metrics(value)
                max_d, max_t = max(max_d, d), max(max_t, t)
        elif isinstance(s, ResolvedIfStatement):
            d, t = get_expression_metrics(s.condition)
            max_d, max_t = max(max_d, d), max(max_t, t)
            td, tt = collect_statement_metrics(s.then_branch)
            max_d, max_t = max(max_d, td), max(max_t, tt)
            if s.else_branch:
                ed, et = collect_statement_metrics(s.else_branch)
                max_d, max_t = max(max_d, ed), max(max_t, et)
        elif isinstance(s, (ResolvedWhileStatement, ResolvedRepeatStatement)):
            d, t = get_expression_metrics(s.condition)
            max_d, max_t = max(max_d, d), max(max_t, t)
            bd, bt = collect_statement_metrics(s.body)
            max_d, max_t = max(max_d, bd), max(max_t, bt)
        elif isinstance(s, ResolvedForStatement):
            d1, t1 = get_expression_metrics(s.initial)
            d2, t2 = get_expression_metrics(s.final)
            max_d, max_t = max(max_d, d1, d2), max(max_t, t1, t2)
            bd, bt = collect_statement_metrics(s.body)
            max_d, max_t = max(max_d, bd), max(max_t, bt)
        elif isinstance(s, ResolvedProcedureCall):
            for arg in s.arguments:
                d, t = get_expression_metrics(arg.value)
                max_d, max_t = max(max_d, d), max(max_t, t)
    return max_d, max_t


def collect_program_metrics(program: ResolvedProgram) -> tuple[int, int]:
    all_stmts = list(program.statements)
    for proc in program.procedures:
        all_stmts.extend(proc.body)
    return collect_statement_metrics(tuple(all_stmts))


@dataclass
class AssemblyPatternStats:
    boolean_materializations: int = 0
    redundant_temp_stores: int = 0
    redundant_cmp_zero: int = 0
    sta_then_lda_roundtrips: int = 0
    immediate_loads: int = 0
    total_instructions: int = 0


def analyze_assembly_patterns(assembly: str) -> AssemblyPatternStats:
    lines = [line.strip() for line in assembly.splitlines() if line.strip() and not line.strip().startswith(";")]
    stats = AssemblyPatternStats()

    for i, line in enumerate(lines):
        if re.match(r"^(?:lda|ldx|ldy|sta|stx|sty|tax|tay|txa|tya|pha|pla|clc|sec|adc|sbc|cmp|cpx|cpy|and|ora|eor|asl|lsr|rol|ror|inc|dec|inx|iny|dex|dey|bit|jmp|jsr|rts|rti|bcc|bcs|beq|bmi|bne|bpl|bvc|bvs|sei|cli|cld|sed|nop)\b", line, re.I):
            stats.total_instructions += 1

        if line.startswith("lda #$00") or line.startswith("lda #$01"):
            stats.immediate_loads += 1

        if line.startswith("cmp #$00"):
            stats.redundant_cmp_zero += 1

        if "sta expression_temporary_" in line:
            stats.redundant_temp_stores += 1

        if "lda #$00              ; false" in line or "lda #$01              ; true" in line:
            stats.boolean_materializations += 1

        if i + 1 < len(lines):
            sta_match = re.match(r"sta\s+([a-zA-Z0-9_]+)", line)
            next_line = lines[i + 1]
            if sta_match:
                var_name = sta_match.group(1)
                if next_line.startswith(f"lda {var_name}"):
                    stats.sta_then_lda_roundtrips += 1

    return stats


@dataclass
class BenchmarkMetrics:
    spec: BenchmarkSpec
    prg_code_bytes: int
    prg_vectors_bytes: int
    prg_header_bytes: int
    prg_total_used_bytes: int
    memory: "MemoryAccounting"
    max_expression_tree_depth: int
    max_live_temporaries: int
    assembly_line_count: int
    pattern_stats: AssemblyPatternStats
    emitted_runtime_symbols: list[str] = field(default_factory=list)
    emitted_runtime_routines: list[str] = field(default_factory=list)
    ram_symbol_breakdown: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class MemoryAccounting:
    """Explicit ownership and availability totals within the NES 2 KiB RAM."""

    zp_runtime_symbol_bytes: int
    zp_temporary_reserved_bytes: int
    zp_temporary_required_bytes: int
    zp_promoted_user_bytes: int
    zp_benchmark_allocated_or_reserved_bytes: int
    zp_policy_reserved_unavailable_bytes: int
    zp_allocator_visible_free_bytes: int
    regular_runtime_bytes: int
    regular_user_bytes: int
    regular_runtime_user_allocated_bytes: int
    oam_shadow_allocated_bytes: int
    non_zp_allocated_bytes: int
    hardware_stack_reserved_bytes: int
    regular_allocator_visible_free_bytes: int
    total_allocator_visible_free_bytes: int
    compiler_runtime_user_allocated_or_reserved_bytes: int
    total_committed_or_reserved_address_space_bytes: int


def measure_memory_accounting(layout: ProgramMemoryLayout) -> MemoryAccounting:
    """Measure allocated, policy-reserved, hardware-reserved, and free RAM."""

    zp_runtime = sum(
        symbol.size
        for symbol in layout.runtime_symbols
        if symbol.region_name == layout.zero_page_runtime.name
    )
    zp_temporary_reserved = layout.temporary_storage.size
    zp_temporary_required = layout.temporary_bytes_used
    zp_promoted = layout.promoted_bytes_used
    zp_benchmark_allocated_or_reserved = (
        zp_runtime + zp_temporary_reserved + zp_promoted
    )

    # The current policy keeps the unused tail of the fixed runtime partition
    # and the future explicit-ZP partition unavailable to the normal allocator.
    # Unused temporary bytes are already included in the benchmark reservation
    # above, while unused automatic-promotion bytes remain allocator-visible.
    zp_policy_reserved_unavailable = (
        layout.zero_page_runtime.size
        - zp_runtime
        + layout.zero_page_explicit_reserve.size
    )
    zp_allocator_visible_free = (
        layout.zero_page_automatic.size
        - zp_promoted
        + layout.zero_page_unallocated.size
    )

    regular_runtime = sum(
        symbol.size
        for symbol in layout.runtime_symbols
        if symbol.region_name == layout.runtime_data.name
    )
    regular_user = sum(symbol.size for symbol in layout.regular_user_symbols)
    regular_runtime_user = regular_runtime + regular_user
    oam_shadow = layout.oam_shadow.size
    non_zp_allocated = regular_runtime_user + oam_shadow
    stack_reserved = layout.hardware_stack.size
    regular_allocator_visible_free = layout.free_ram.size
    total_allocator_visible_free = (
        regular_allocator_visible_free + zp_allocator_visible_free
    )
    compiler_runtime_user_allocated_or_reserved = (
        zp_benchmark_allocated_or_reserved + non_zp_allocated
    )
    total_committed_or_reserved = (
        compiler_runtime_user_allocated_or_reserved
        + stack_reserved
        + zp_policy_reserved_unavailable
    )

    assert (
        zp_benchmark_allocated_or_reserved
        + zp_policy_reserved_unavailable
        + zp_allocator_visible_free
        == layout.zero_page.size
    ), "Zero Page accounting must reconcile to 256 bytes"
    assert (
        regular_runtime_user
        + oam_shadow
        + stack_reserved
        + regular_allocator_visible_free
        == layout.physical_ram.size - layout.zero_page.size
    ), "non-Zero-Page accounting must reconcile to 1,792 bytes"
    assert (
        total_committed_or_reserved + total_allocator_visible_free
        == layout.physical_ram.size
    ), "CPU RAM accounting must reconcile to the NES 2 KiB physical RAM"

    return MemoryAccounting(
        zp_runtime_symbol_bytes=zp_runtime,
        zp_temporary_reserved_bytes=zp_temporary_reserved,
        zp_temporary_required_bytes=zp_temporary_required,
        zp_promoted_user_bytes=zp_promoted,
        zp_benchmark_allocated_or_reserved_bytes=(
            zp_benchmark_allocated_or_reserved
        ),
        zp_policy_reserved_unavailable_bytes=zp_policy_reserved_unavailable,
        zp_allocator_visible_free_bytes=zp_allocator_visible_free,
        regular_runtime_bytes=regular_runtime,
        regular_user_bytes=regular_user,
        regular_runtime_user_allocated_bytes=regular_runtime_user,
        oam_shadow_allocated_bytes=oam_shadow,
        non_zp_allocated_bytes=non_zp_allocated,
        hardware_stack_reserved_bytes=stack_reserved,
        regular_allocator_visible_free_bytes=regular_allocator_visible_free,
        total_allocator_visible_free_bytes=total_allocator_visible_free,
        compiler_runtime_user_allocated_or_reserved_bytes=(
            compiler_runtime_user_allocated_or_reserved
        ),
        total_committed_or_reserved_address_space_bytes=(
            total_committed_or_reserved
        ),
    )


def parse_ld65_map(map_content: str) -> dict[str, int]:
    segment_sizes: dict[str, int] = {}
    in_segment_list = False
    for line in map_content.splitlines():
        if line.strip().startswith("Segment list:"):
            in_segment_list = True
            continue
        if in_segment_list:
            if line.startswith("---") or not line.strip():
                if line.strip().startswith("Exports list:"):
                    break
                continue
            parts = line.split()
            if len(parts) >= 4 and parts[1].startswith("00") and parts[2].startswith("00"):
                name = parts[0]
                try:
                    size = int(parts[3], 16)
                    segment_sizes[name] = size
                except ValueError:
                    pass
    return segment_sizes


def analyze_assembly_text(assembly: str) -> tuple[list[str], list[str]]:
    lines = assembly.splitlines()
    routines: list[str] = []
    symbols: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped.endswith(":") and not stripped.startswith(";"):
            label = stripped[:-1].strip()
            if label.startswith("runtime_") or label.startswith("wait_") or label.startswith("nmi_"):
                routines.append(label)
        if re.search(r"runtime_[a-z0-9_]+", line):
            for match in re.findall(r"runtime_[a-z0-9_]+", line):
                if match not in symbols:
                    symbols.append(match)

    return routines, symbols


def measure_benchmark(spec: BenchmarkSpec) -> BenchmarkMetrics:
    source_path = ROOT / spec.source_file
    source = source_path.read_text(encoding="utf-8")
    program = parse(source, str(source_path))

    chr_path = ROOT / "examples" / spec.chr_path if spec.chr_path else None
    chr_rom = load_chr_rom(chr_path, source_path, source)

    metasprite_paths = tuple(ROOT / "examples" / p for p in spec.metasprite_paths)
    metasprite_assets = load_metasprite_assets(
        metasprite_paths,
        source_path,
        source,
        chr_rom,
    )
    resolved = analyze(
        program,
        source,
        str(source_path),
        metasprite_assets=metasprite_assets,
    )

    tree_depth, live_temps = collect_program_metrics(resolved)

    layout = build_memory_layout(resolved)
    assembly = generate(
        resolved,
        layout,
        chr_rom=chr_rom,
        background_data=(
            (ROOT / "examples" / spec.nametable_path).read_bytes()
            if spec.nametable_path
            else None
        ),
    )
    linker_config = generate_linker_config(layout)

    ca65 = shutil.which("ca65")
    ld65 = shutil.which("ld65")
    assert ca65 and ld65, "ca65 and ld65 required for benchmark measurement"

    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        asm_p = tdp / "bench.asm"
        cfg_p = tdp / "bench.cfg"
        obj_p = tdp / "bench.o"
        map_p = tdp / "bench.ld65.map"
        rom_p = tdp / "bench.nes"

        asm_p.write_text(assembly, encoding="utf-8")
        cfg_p.write_text(linker_config, encoding="utf-8")

        subprocess.run([ca65, str(asm_p), "-o", str(obj_p)], check=True, capture_output=True)
        subprocess.run(
            [ld65, "-C", str(cfg_p), str(obj_p), "-m", str(map_p), "-o", str(rom_p)],
            check=True,
            capture_output=True,
        )

        map_content = map_p.read_text(encoding="utf-8")
        segment_sizes = parse_ld65_map(map_content)

    code_size = segment_sizes.get("CODE", 0)
    vectors_size = segment_sizes.get("VECTORS", 6)
    header_size = segment_sizes.get("HEADER", 16)
    total_prg_used = code_size + vectors_size

    memory = measure_memory_accounting(layout)

    routines, symbols = analyze_assembly_text(assembly)
    patterns = analyze_assembly_patterns(assembly)

    all_symbols = (*layout.runtime_symbols, *layout.temporary_symbols, *layout.user_symbols)
    ram_breakdown = {s.assembly_symbol: s.size for s in all_symbols}

    return BenchmarkMetrics(
        spec=spec,
        prg_code_bytes=code_size,
        prg_vectors_bytes=vectors_size,
        prg_header_bytes=header_size,
        prg_total_used_bytes=total_prg_used,
        memory=memory,
        max_expression_tree_depth=tree_depth,
        max_live_temporaries=live_temps,
        assembly_line_count=len(assembly.splitlines()),
        pattern_stats=patterns,
        emitted_runtime_symbols=symbols,
        emitted_runtime_routines=routines,
        ram_symbol_breakdown=ram_breakdown,
    )


def run_all_benchmarks() -> list[BenchmarkMetrics]:
    results: list[BenchmarkMetrics] = []
    for spec in BENCHMARKS:
        metrics = measure_benchmark(spec)
        results.append(metrics)
    return results


def format_markdown_report(metrics_list: list[BenchmarkMetrics]) -> str:
    lines: list[str] = [
        "# NES Pascal 0.5.5 Compiler Optimization & Architecture Benchmark Results",
        "",
        "## 1. CPU RAM Accounting Baseline",
        "",
        "| Benchmark | ZP Runtime Symbols | ZP Temp Reserved | ZP Temp Required | ZP Promoted | ZP Benchmark Alloc./Reserved | ZP Policy Reserved | ZP Allocator Free | Regular Runtime/User | OAM Shadow | Non-ZP Allocated | Stack Reserved | Regular Allocator Free | Total Allocator Free | Compiler/Runtime/User Alloc./Reserved | Total Committed/Reserved |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]
    for m in metrics_list:
        memory = m.memory
        lines.append(
            f"| `{m.spec.name}` | {memory.zp_runtime_symbol_bytes} B | "
            f"{memory.zp_temporary_reserved_bytes} B | {memory.zp_temporary_required_bytes} B | "
            f"{memory.zp_promoted_user_bytes} B | {memory.zp_benchmark_allocated_or_reserved_bytes} B | "
            f"{memory.zp_policy_reserved_unavailable_bytes} B | {memory.zp_allocator_visible_free_bytes} B | "
            f"{memory.regular_runtime_user_allocated_bytes} B | {memory.oam_shadow_allocated_bytes} B | "
            f"{memory.non_zp_allocated_bytes} B | {memory.hardware_stack_reserved_bytes} B | "
            f"{memory.regular_allocator_visible_free_bytes} B | {memory.total_allocator_visible_free_bytes} B | "
            f"{memory.compiler_runtime_user_allocated_or_reserved_bytes} B | "
            f"{memory.total_committed_or_reserved_address_space_bytes} B |"
        )
    lines.extend([
        "",
        "Definitions: `ZP Benchmark Alloc./Reserved` includes the fixed compiler temporary "
        "reservation; `ZP Temp Required` reports the bytes backed by generated temporary "
        "symbols. `ZP Policy Reserved` is unavailable by memory policy but is not program "
        "consumption. `Total Committed/Reserved` includes compiler/runtime/user storage, "
        "hardware stack reservation, and policy-reserved Zero Page.",
        "",
        "## 2. Code and Expression Baseline",
        "",
        "| Benchmark | Category | PRG Code | PRG Occupied | Tree Depth | Max Live Temps | Instructions |",
        "| :--- | :--- | :---: | :---: | :---: | :---: | :---: |",
    ])
    for m in metrics_list:
        lines.append(
            f"| `{m.spec.name}` | {m.spec.category} | {m.prg_code_bytes} B | "
            f"{m.prg_total_used_bytes} B | {m.max_expression_tree_depth} | "
            f"{m.max_live_temporaries} | {m.pattern_stats.total_instructions} |"
        )
    lines.extend([
        "",
        "## 3. Inefficient Assembly Pattern Frequency",
        "",
        "| Benchmark | Redundant Temp Stores | Boolean Materializations ($00/$01) | Redundant CMP #$00 | STA->LDA Roundtrips | Total Instructions |",
        "| :--- | :---: | :---: | :---: | :---: | :---: |",
    ])
    for m in metrics_list:
        p = m.pattern_stats
        lines.append(
            f"| `{m.spec.name}` | {p.redundant_temp_stores} | {p.boolean_materializations} | {p.redundant_cmp_zero} | {p.sta_then_lda_roundtrips} | {p.total_instructions} |"
        )
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    results = run_all_benchmarks()
    print(format_markdown_report(results))
