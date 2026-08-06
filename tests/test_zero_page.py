from pathlib import Path
import unittest

from nes_pascal.diagnostics import CompilerError, DiagnosticCode
from nes_pascal.memory_layout import (
    MemoryLayoutSettings,
    build_memory_layout,
    generate_memory_map,
)
from nes_pascal.parser import parse
from nes_pascal.semantic import analyze


ROOT = Path(__file__).resolve().parents[1]


def resolve(source: str, filename: str = "<input>"):
    return analyze(parse(source, filename), source, filename)


def promotion_program() -> str:
    return """program Promotion;
var
    First: byte;
    Second: byte;
    Cold: byte;
begin
    First := $00;
    Second := $00;
    Cold := $00;
    inc(First);
    inc(Second);
    inc(Second);
    inc(Second);
    First := First + Second;
    nes.set_background_color($21);
    nes.run;
end.
"""


class ZeroPageAllocationTests(unittest.TestCase):
    def test_default_zero_page_partitions_are_fixed_and_non_overlapping(self) -> None:
        layout = build_memory_layout(resolve(promotion_program()))

        self.assertEqual(
            (layout.zero_page_runtime.start, layout.zero_page_runtime.end),
            (0x0000, 0x000F),
        )
        self.assertEqual(
            (layout.temporary_storage.start, layout.temporary_storage.end),
            (0x0010, 0x001F),
        )
        self.assertEqual(
            (
                layout.zero_page_explicit_reserve.start,
                layout.zero_page_explicit_reserve.end,
            ),
            (0x0020, 0x007F),
        )
        self.assertEqual(
            (layout.zero_page_automatic.start, layout.zero_page_automatic.end),
            (0x0080, 0x00FF),
        )

    def test_global_promotion_uses_threshold_then_declaration_order(self) -> None:
        layout = build_memory_layout(resolve(promotion_program()))

        self.assertEqual(
            [
                (symbol.source_name, symbol.address)
                for symbol in layout.promoted_user_symbols
            ],
            [("First", 0x0080), ("Second", 0x0081)],
        )
        self.assertEqual(
            [
                (symbol.source_name, symbol.address)
                for symbol in layout.regular_user_symbols
            ],
            [("Cold", 0x0200)],
        )

    def test_optional_promotion_falls_back_to_regular_ram(self) -> None:
        layout = build_memory_layout(
            resolve(promotion_program()),
            MemoryLayoutSettings(zero_page_automatic_size=1),
        )

        self.assertEqual(
            [(symbol.source_name, symbol.address) for symbol in layout.user_symbols],
            [("First", 0x0080), ("Second", 0x0200), ("Cold", 0x0201)],
        )
        self.assertEqual(layout.free_ram.start, 0x0202)

    def test_mandatory_temporaries_do_not_borrow_optional_space(self) -> None:
        path = ROOT / "examples" / "memory_layout.nsp"
        source = path.read_text(encoding="utf-8")
        settings = MemoryLayoutSettings(temporary_storage_size=1)

        with self.assertRaises(CompilerError) as context:
            build_memory_layout(
                resolve(source, str(path)),
                settings,
                source=source,
                filename=str(path),
            )

        self.assertEqual(
            context.exception.code,
            DiagnosticCode.TEMPORARY_RAM_EXHAUSTED,
        )
        self.assertIn("cannot borrow optional promotion space", str(context.exception))

    def test_procedure_parameters_are_never_automatically_promoted(self) -> None:
        path = ROOT / "examples" / "procedure_parameters.nsp"
        source = path.read_text(encoding="utf-8")
        layout = build_memory_layout(resolve(source, str(path)))

        parameter_symbols = [
            symbol
            for symbol in layout.user_symbols
            if "." in (symbol.source_name or "")
        ]
        self.assertTrue(parameter_symbols)
        self.assertTrue(
            all(
                symbol.region_name == layout.user_capacity.name
                for symbol in parameter_symbols
            )
        )

    def test_promotion_policy_does_not_change_resolved_program_semantics(self) -> None:
        program = resolve(promotion_program())
        full_layout = build_memory_layout(program)
        fallback_layout = build_memory_layout(
            program,
            MemoryLayoutSettings(zero_page_automatic_size=0),
        )

        self.assertEqual(full_layout.user_symbols[0].assembly_symbol, "variable_First")
        self.assertEqual(
            fallback_layout.user_symbols[0].assembly_symbol,
            "variable_First",
        )
        self.assertEqual(program, resolve(promotion_program()))

    def test_memory_map_identifies_mandatory_and_optional_zero_page_use(self) -> None:
        layout = build_memory_layout(resolve(promotion_program()))
        report = generate_memory_map(layout)

        self.assertIn("Zero Page runtime", report)
        self.assertIn("Zero Page temporaries", report)
        self.assertIn("Future explicit Zero Page", report)
        self.assertIn("Automatic Zero Page variables (2 used, 126 available)", report)
        self.assertIn("$0080", report)
        self.assertIn("Zero Page", report)
        self.assertIn("$0200", report)
        self.assertIn("Regular RAM", report)


if __name__ == "__main__":
    unittest.main()
