from dataclasses import replace
from pathlib import Path
import unittest

from nes_pascal.diagnostics import CompilerError, DiagnosticCode
from nes_pascal.memory_layout import (
    MemoryLayoutSettings,
    build_memory_layout,
    generate_linker_config,
    generate_memory_map,
    validate_segment_capacities,
)
from nes_pascal.parser import parse
from nes_pascal.semantic import analyze


ROOT = Path(__file__).resolve().parents[1]


def resolved_program(source: str, filename: str = "<input>"):
    return analyze(parse(source, filename), source, filename)


def small_program(variable_names: tuple[str, ...] = ("Counter",)) -> str:
    declarations = "\n".join(f"    {name}: byte;" for name in variable_names)
    return f"""program MemoryTest;
var
{declarations}
begin
    {variable_names[0]} := $00;
    nes.set_background_color($21);
    nes.run;
end.
"""


class MemoryLayoutTests(unittest.TestCase):
    def test_physical_and_reserved_ranges_match_nes_internal_ram(self) -> None:
        layout = build_memory_layout(resolved_program(small_program()))

        self.assertEqual(
            (layout.physical_ram.start, layout.physical_ram.end),
            (0, 0x07FF),
        )
        self.assertEqual((layout.zero_page.start, layout.zero_page.end), (0, 0x00FF))
        self.assertEqual(
            (layout.hardware_stack.start, layout.hardware_stack.end),
            (0x0100, 0x01FF),
        )
        self.assertEqual(
            (layout.oam_shadow.start, layout.oam_shadow.end),
            (0x0200, 0x02FF),
        )
        self.assertEqual(layout.oam_shadow.size, 256)
        self.assertEqual(layout.oam_shadow.start % 256, 0)

    def test_runtime_temporary_and_user_regions_are_deterministic(self) -> None:
        program = resolved_program(small_program(("First", "Second", "Third")))
        first = build_memory_layout(program)
        second = build_memory_layout(program)

        self.assertEqual(first, second)
        self.assertEqual(first.runtime_data.start, 0x0300)
        self.assertEqual(first.runtime_data.size, 0)
        self.assertEqual(
            (first.temporary_storage.start, first.temporary_storage.end),
            (0x0010, 0x001F),
        )
        self.assertEqual(
            [symbol.address for symbol in first.user_symbols],
            [0x0300, 0x0301, 0x0302],
        )
        self.assertEqual(
            first.runtime_symbols[0].assembly_symbol,
            "runtime_oam_shadow",
        )
        self.assertEqual(first.runtime_symbols[0].address, 0x0200)

    def test_temporary_symbol_allocation_is_deterministic(self) -> None:
        path = ROOT / "examples" / "memory_layout.nsp"
        source = path.read_text(encoding="utf-8")
        program = resolved_program(source, str(path))

        first = build_memory_layout(program)
        second = build_memory_layout(program)

        expected = [
            ("expression_temporary_0", 0x0010),
            ("for_limit_0", 0x0011),
        ]
        self.assertEqual(
            [
                (symbol.assembly_symbol, symbol.address)
                for symbol in first.temporary_symbols
            ],
            expected,
        )
        self.assertEqual(first.temporary_symbols, second.temporary_symbols)

    def test_allocations_stay_within_their_owned_physical_regions(self) -> None:
        layout = build_memory_layout(
            resolved_program(small_program(("First", "Second")))
        )
        for symbol in layout.temporary_symbols:
            with self.subTest(symbol=symbol.assembly_symbol):
                self.assertGreaterEqual(symbol.address, 0x0010)
                self.assertLessEqual(symbol.address + symbol.size - 1, 0x001F)
        for symbol in layout.regular_user_symbols:
            with self.subTest(symbol=symbol.assembly_symbol):
                self.assertGreaterEqual(symbol.address, 0x0300)
                self.assertLessEqual(symbol.address + symbol.size - 1, 0x07FF)

    def test_consecutive_user_allocations_do_not_overlap(self) -> None:
        layout = build_memory_layout(
            resolved_program(small_program(("First", "Second", "Third")))
        )
        addresses = [symbol.address for symbol in layout.user_symbols]
        self.assertEqual(addresses, list(range(addresses[0], addresses[0] + 3)))

    def test_exact_final_byte_succeeds_and_one_more_fails(self) -> None:
        settings = MemoryLayoutSettings(runtime_data_size=1279)
        one_source = small_program(("FinalByte",))
        layout = build_memory_layout(
            resolved_program(one_source),
            settings,
            source=one_source,
        )
        self.assertEqual(layout.user_symbols[-1].address, 0x07FF)
        self.assertEqual(layout.free_ram.size, 0)

        two_source = small_program(("FinalByte", "TooFar"))
        with self.assertRaises(CompilerError) as context:
            build_memory_layout(
                resolved_program(two_source),
                settings,
                source=two_source,
                filename="ram_limit.nsp",
            )
        self.assertEqual(context.exception.code, DiagnosticCode.USER_RAM_EXHAUSTED)
        self.assertEqual(context.exception.location.line, 4)
        self.assertEqual(context.exception.location.column, 5)
        self.assertIn("TooFar", str(context.exception))
        self.assertIn("0 bytes remain", str(context.exception))

    def test_multiple_variables_collectively_exhaust_user_ram(self) -> None:
        path = ROOT / "tests" / "fixtures" / "diagnostics" / "user_ram_exhausted.nsp"
        source = path.read_text(encoding="utf-8")
        with self.assertRaises(CompilerError) as context:
            build_memory_layout(
                resolved_program(source, str(path)),
                MemoryLayoutSettings(runtime_data_size=1279),
                source=source,
                filename=str(path),
            )
        self.assertEqual(context.exception.code, DiagnosticCode.USER_RAM_EXHAUSTED)
        self.assertEqual(context.exception.location.line, 5)
        self.assertEqual(context.exception.location.column, 5)

    def test_temporary_pool_exhaustion_is_a_compiler_diagnostic(self) -> None:
        path = (
            ROOT
            / "tests"
            / "fixtures"
            / "diagnostics"
            / "temporary_ram_exhausted.nsp"
        )
        source = path.read_text(encoding="utf-8")
        program = resolved_program(source, str(path))

        with self.assertRaises(CompilerError) as context:
            build_memory_layout(program, source=source, filename=str(path))
        self.assertEqual(
            context.exception.code,
            DiagnosticCode.TEMPORARY_RAM_EXHAUSTED,
        )
        self.assertIn("17 temporary bytes", str(context.exception))

    def test_malformed_internal_layouts_fail_cleanly(self) -> None:
        cases = (
            MemoryLayoutSettings(oam_shadow_start=0x0210),
            MemoryLayoutSettings(oam_shadow_start=0x0100),
            MemoryLayoutSettings(runtime_data_size=1281),
            MemoryLayoutSettings(physical_ram_size=0x2000),
            MemoryLayoutSettings(mapper_number=1),
            MemoryLayoutSettings(zero_page_runtime_size=17),
            MemoryLayoutSettings(automatic_promotion_min_references=0),
        )
        program = resolved_program(small_program())
        for settings in cases:
            with self.subTest(settings=settings):
                with self.assertRaises(CompilerError) as context:
                    build_memory_layout(program, settings)
                self.assertEqual(
                    context.exception.code,
                    DiagnosticCode.INVALID_MEMORY_LAYOUT,
                )

    def test_generated_segment_overflow_fails_before_linking(self) -> None:
        layout = build_memory_layout(resolved_program(small_program()))
        oversized = replace(
            layout.user_symbols[0],
            size=layout.user_capacity.size + 1,
        )
        invalid_layout = replace(layout, user_symbols=(oversized,))

        with self.assertRaises(CompilerError) as context:
            validate_segment_capacities(invalid_layout)
        self.assertEqual(
            context.exception.code,
            DiagnosticCode.RAM_SEGMENT_OVERFLOW,
        )

    def test_linker_configuration_is_derived_from_the_memory_model(self) -> None:
        layout = build_memory_layout(resolved_program(small_program()))
        config = generate_linker_config(layout)

        self.assertIn("ZP_RUNTIME: start = $0000, size = $0010", config)
        self.assertIn("ZP_TEMP: start = $0010, size = $0010", config)
        self.assertIn("ZP_EXPLICIT: start = $0020, size = $0060", config)
        self.assertIn("ZP_AUTO: start = $0080, size = $0080", config)
        self.assertIn("STACK:   start = $0100, size = $0100", config)
        self.assertIn("OAM:     start = $0200, size = $0100", config)
        self.assertIn("RUNTIME: start = $0300, size = $0000", config)
        self.assertIn("USER:    start = $0300, size = $0500", config)
        self.assertIn("ZERO_PAGE_TEMPORARIES: load = ZP_TEMP", config)
        self.assertIn("ZERO_PAGE_VARIABLES:   load = ZP_AUTO", config)
        self.assertIn("OAM_SHADOW:          load = OAM", config)
        self.assertIn("USER_VARIABLES:      load = USER", config)

        custom_layout = build_memory_layout(
            resolved_program(small_program()),
            MemoryLayoutSettings(runtime_data_size=4, temporary_storage_size=8),
        )
        custom_config = generate_linker_config(custom_layout)
        self.assertIn("RUNTIME: start = $0300, size = $0004", custom_config)
        self.assertIn("ZP_TEMP: start = $0010, size = $0008", custom_config)
        self.assertIn("ZP_AUTO: start = $0078, size = $0080", custom_config)
        self.assertIn("USER:    start = $0304, size = $04FC", custom_config)

    def test_memory_map_contains_regions_totals_and_allocated_symbols(self) -> None:
        source = small_program(("Counter", "Limit"))
        layout = build_memory_layout(resolved_program(source))
        report = generate_memory_map(layout)

        self.assertIn("Physical CPU RAM: $0000-$07FF (2048 bytes)", report)
        self.assertIn("$0000  $000F    16  Runtime   Zero Page runtime", report)
        self.assertIn("$0010  $001F    16  Compiler  Zero Page temporaries", report)
        self.assertIn("$0080  $00FF   128  User      Automatic Zero Page", report)
        self.assertIn("$0200  $02FF   256  Runtime   OAM shadow", report)
        self.assertIn("$0300  ----      0  Runtime   Runtime data", report)
        self.assertIn("General free RAM", report)
        self.assertIn("Counter", report)
        self.assertIn("variable_Counter", report)
        self.assertIn("runtime_oam_shadow", report)
        self.assertIn("Available:", report)

    def test_linker_configuration_and_memory_map_are_reproducible(self) -> None:
        program = resolved_program(small_program(("Counter", "Limit")))
        first = build_memory_layout(program)
        second = build_memory_layout(program)

        self.assertEqual(generate_linker_config(first), generate_linker_config(second))
        self.assertEqual(generate_memory_map(first), generate_memory_map(second))


if __name__ == "__main__":
    unittest.main()
