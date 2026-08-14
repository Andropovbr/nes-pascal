from pathlib import Path
import unittest

from nes_pascal.backend_ca65 import generate
from nes_pascal.codegen_analysis import (
    TemporaryPool,
    TemporaryPoolExhausted,
    analyze_program_temporaries,
)
from nes_pascal.memory_layout import build_memory_layout, generate_memory_map
from nes_pascal.parser import parse
from nes_pascal.semantic import analyze


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "runtime" / "expression_temporaries.nsp"


def resolve(source: str, filename: str = "<input>"):
    return analyze(parse(source, filename), source, filename)


def array_expression_program(expression: str, *, repeat: bool = False) -> str:
    second = f"    Second := {expression};\n" if repeat else ""
    return f"""program TemporaryRequirement;
var
    Values: array[$00..$03] of byte;
    I: byte;
    J: byte;
    K: byte;
    L: byte;
    Result: byte;
    Second: byte;
begin
    Values[$00] := $10;
    Values[$01] := $20;
    Values[$02] := $30;
    Values[$03] := $40;
    I := $00;
    J := $01;
    K := $02;
    L := $03;
    Result := {expression};
{second}    nes.set_background_color($0F);
    nes.run;
end.
"""


class ScopedTemporaryPoolTests(unittest.TestCase):
    def test_lowest_slot_reuse_and_call_scope_are_deterministic(self) -> None:
        pool = TemporaryPool(2)
        with pool.acquire() as caller:
            self.assertEqual((caller.index, caller.name), (0, "expression_temporary_0"))
            with pool.call_scope():
                with pool.acquire() as nested:
                    self.assertEqual(nested.index, 1)
                with pool.acquire() as reused_nested:
                    self.assertEqual(reused_nested.index, 1)
        with pool.acquire() as reused_caller:
            self.assertEqual(reused_caller.index, 0)
        pool.assert_all_released()
        self.assertEqual(pool.max_live, 2)

    def test_pool_exhaustion_never_reuses_a_live_slot(self) -> None:
        pool = TemporaryPool(1)
        with pool.acquire():
            with self.assertRaises(TemporaryPoolExhausted):
                pool.acquire()


class ExpressionTemporaryAllocationTests(unittest.TestCase):
    def test_zero_temp_program_reserves_and_emits_no_expression_slot(self) -> None:
        path = ROOT / "examples" / "arithmetic.nsp"
        source = path.read_text(encoding="utf-8")
        program = resolve(source, str(path))
        layout = build_memory_layout(program)
        assembly = generate(program, layout)
        memory_map = generate_memory_map(layout)

        self.assertEqual(layout.expression_temporary_bytes, 0)
        self.assertEqual(layout.compiler_cache_bytes, 0)
        self.assertEqual(layout.zero_page_recovered.size, 16)
        self.assertNotIn("expression_temporary_0", assembly)
        self.assertIn("Expression temporary reservation: 0 bytes", memory_map)

    def test_one_two_and_deeper_requirements_match_actual_liveness(self) -> None:
        cases = (
            ("Values[I] + Values[J]", 1),
            ("(Values[I] + Values[J]) + Values[K]", 2),
            ("((Values[I] + Values[J]) + Values[K]) + Values[L]", 3),
        )
        for expression, expected in cases:
            with self.subTest(expression=expression):
                program = resolve(array_expression_program(expression))
                requirements = analyze_program_temporaries(program)
                layout = build_memory_layout(program)
                assembly = generate(program, layout)

                self.assertEqual(requirements.expression_temporaries, expected)
                self.assertEqual(layout.expression_temporary_bytes, expected)
                self.assertEqual(len(layout.expression_temporary_symbols), expected)
                self.assertNotIn(f"expression_temporary_{expected}", assembly)
                if expected == 1:
                    block = assembly.split("; Source: Result := value", 1)[1].split(
                        "; Source: nes.set_background_color(value)", 1
                    )[0]
                    self.assertLess(
                        block.index("lda variable_J"),
                        block.index("lda variable_I"),
                    )

    def test_sequential_deep_expressions_reuse_three_slots(self) -> None:
        expression = "((Values[I] + Values[J]) + Values[K]) + Values[L]"
        program = resolve(array_expression_program(expression, repeat=True))
        layout = build_memory_layout(program)
        assembly = generate(program, layout)

        self.assertEqual(layout.expression_temporary_bytes, 3)
        self.assertEqual(layout.compiler_cache_bytes, 0)
        self.assertGreaterEqual(assembly.count("sta expression_temporary_0"), 2)
        self.assertNotIn("expression_temporary_3", assembly)

    def test_arrays_records_procedure_arguments_and_builtins_share_one_pool(self) -> None:
        source = FIXTURE.read_text(encoding="utf-8")
        program = resolve(source, str(FIXTURE))
        layout = build_memory_layout(program)
        assembly = generate(program, layout)
        memory_map = generate_memory_map(layout)

        self.assertEqual(layout.expression_temporary_bytes, 3)
        self.assertEqual(layout.compiler_cache_bytes, 0)
        self.assertEqual(layout.zero_page_recovered.size, 13)
        self.assertIn("Expression temporary reservation: 3 bytes", memory_map)
        self.assertIn("Other compiler caches: 0 bytes", memory_map)

        nested_index = assembly.split(
            "; Source: NestedIndexResult := value", 1
        )[1].split("; Source: RecordResult := value", 1)[0]
        self.assertGreaterEqual(nested_index.count("tax"), 2)

        indexed_write = assembly.split(
            "; Source: Values[index] := value", 1
        )[1].split("; Source: Enemies[index].X := value", 1)[0]
        self.assertLess(indexed_write.index("pha"), indexed_write.index("pla"))
        self.assertIn("expression_temporary_1", indexed_write)
        self.assertEqual(indexed_write.count("pha"), 1)
        self.assertEqual(indexed_write.count("pla"), 1)

        record_expression = assembly.split(
            "; Source: RecordResult := value", 1
        )[1].split("; Source: ComparisonResult := value", 1)[0]
        self.assertIn("expression_temporary_0", record_expression)
        self.assertIn("scale record index", record_expression)

        comparison = assembly.split(
            "; Source: ComparisonResult := value", 1
        )[1].split("; Source: Values[index] := value", 1)[0]
        self.assertIn("expression_temporary_1", comparison)
        self.assertIn("cmp expression_temporary_0", comparison)

        procedure_call = assembly.split("; Source: Capture", 1)[1].split(
            "; Source: nes.set_background_color(value)", 1
        )[0]
        self.assertLess(
            procedure_call.index("sta parameter_Capture_First"),
            procedure_call.index("; argument 2: Second"),
        )
        self.assertNotIn("expression_temporary_2", procedure_call)

        builtin_call = assembly.split("; Source: nes.set_scroll(x, y)", 1)[1]
        self.assertIn("expression_temporary_1", builtin_call)
        self.assertNotIn("expression_temporary_2", builtin_call)

    def test_representative_temporary_sequence_matches_focused_golden(self) -> None:
        source = FIXTURE.read_text(encoding="utf-8")
        assembly = generate(resolve(source, str(FIXTURE)))
        actual = "\n".join(
            line.strip()
            for line in assembly.splitlines()
            if "expression_temporary_" in line
        ) + "\n"
        expected = (
            ROOT / "tests" / "golden" / "expression-temporaries.asm"
        ).read_text(encoding="utf-8")
        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
