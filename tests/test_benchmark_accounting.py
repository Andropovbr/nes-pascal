from pathlib import Path
import unittest

from nes_pascal.memory_layout import build_memory_layout
from nes_pascal.parser import parse
from nes_pascal.semantic import analyze
from tools.measure_benchmarks import (
    compare_legacy_temporary_accounting,
    format_markdown_report,
    measure_memory_accounting,
)


ROOT = Path(__file__).resolve().parents[1]


def layout_for_example(name: str):
    path = ROOT / "examples" / f"{name}.nsp"
    source = path.read_text(encoding="utf-8")
    program = analyze(parse(source, str(path)), source, str(path))
    return build_memory_layout(program)


class BenchmarkTemporaryAccountingTests(unittest.TestCase):
    def test_zero_temp_accounting_recovers_the_full_legacy_window(self) -> None:
        memory = measure_memory_accounting(layout_for_example("arithmetic"))
        comparison = compare_legacy_temporary_accounting(memory, 0)

        self.assertEqual(memory.zp_expression_temporary_reserved_bytes, 0)
        self.assertEqual(memory.zp_compiler_cache_bytes, 0)
        self.assertEqual(memory.zp_allocator_visible_free_bytes, 144)
        self.assertEqual(comparison.net_zero_page_saved_bytes, 16)
        self.assertEqual(comparison.legacy_zp_allocated_or_reserved_bytes, 25)
        self.assertEqual(comparison.current_zp_allocated_or_reserved_bytes, 9)
        self.assertEqual(comparison.legacy_zp_allocator_visible_free_bytes, 128)

    def test_loop_caches_are_not_reported_as_expression_temporaries(self) -> None:
        layout = layout_for_example("counting")
        memory = measure_memory_accounting(layout)
        comparison = compare_legacy_temporary_accounting(memory, 0)

        self.assertEqual(layout.expression_temporary_bytes, 0)
        self.assertEqual(layout.compiler_cache_bytes, 6)
        self.assertEqual(memory.zp_expression_temporary_reserved_bytes, 0)
        self.assertEqual(memory.zp_compiler_cache_bytes, 6)
        self.assertEqual(comparison.expression_reservation_reduction_bytes, 16)
        self.assertEqual(comparison.net_zero_page_saved_bytes, 10)

    def test_cpu_ram_categories_reconcile_to_exactly_two_kibibytes(self) -> None:
        for name in ("arithmetic", "counting", "arrays", "records"):
            with self.subTest(name=name):
                memory = measure_memory_accounting(layout_for_example(name))
                self.assertEqual(
                    memory.total_committed_or_reserved_address_space_bytes
                    + memory.total_allocator_visible_free_bytes,
                    2048,
                )

    def test_report_uses_explicit_temporary_and_cache_terminology(self) -> None:
        # Formatting is exercised with the full BenchmarkMetrics shape elsewhere;
        # these labels are stable public accounting terminology.
        source = Path("tools/measure_benchmarks.py").read_text(encoding="utf-8")
        self.assertIn("Expression Temp Reserved", source)
        self.assertIn("Other Compiler Caches", source)
        self.assertIn("Net ZP Saved", source)
        self.assertNotIn("RAM Total", source)
        self.assertTrue(callable(format_markdown_report))


if __name__ == "__main__":
    unittest.main()
