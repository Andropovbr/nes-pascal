from pathlib import Path
import shutil
import unittest

from nes_pascal.ast import (
    ArrayElementAssignment,
    ArrayIndexExpression,
    ArrayType,
    BinaryExpression,
    BuiltInType,
    ImmediateValue,
    ResolvedArrayElement,
    ResolvedArrayElementAssignment,
    ResolvedAssignment,
    ResolvedIfStatement,
    VariableReference,
)
from nes_pascal.backend_ca65 import generate
from nes_pascal.diagnostics import CompilerError
from nes_pascal.memory_layout import build_memory_layout, generate_memory_map
from nes_pascal.parser import parse
from nes_pascal.semantic import analyze
from nes_pascal.lexer import TokenKind, tokenize


ROOT = Path(__file__).resolve().parents[1]
DIAGNOSTICS = ROOT / "tests" / "fixtures" / "diagnostics"


def program_with(body: str, variables: str) -> str:
    return f"""program Arrays;
var
{variables}
begin
{body}
    nes.set_background_color($0F);
    nes.run;
end.
"""


def resolve(source: str, filename: str = "arrays.nsp"):
    return analyze(parse(source, filename), source, filename)


class ArrayParserTests(unittest.TestCase):
    def test_lexer_recognizes_array_keywords_brackets_and_range_dots(self) -> None:
        tokens = tokenize("Values: array[$00..$07] of byte;")
        self.assertEqual(
            [token.kind for token in tokens],
            [
                TokenKind.IDENTIFIER,
                TokenKind.COLON,
                TokenKind.ARRAY,
                TokenKind.LEFT_BRACKET,
                TokenKind.HEX_LITERAL,
                TokenKind.DOT,
                TokenKind.DOT,
                TokenKind.HEX_LITERAL,
                TokenKind.RIGHT_BRACKET,
                TokenKind.OF,
                TokenKind.IDENTIFIER,
                TokenKind.SEMICOLON,
                TokenKind.EOF,
            ],
        )

    def test_parses_array_types_reads_writes_and_nested_expressions(self) -> None:
        source = program_with(
            """    Index := $01;
    Values[Index] := Values[$00] + $01;
    Enabled := Flags[Index];""",
            """    Values: array[$00..$07] of byte;
    Flags: array[$00..$03] of boolean;
    Index: byte;
    Enabled: boolean;""",
        )

        program = parse(source, "arrays-parser.nsp")

        self.assertEqual(
            program.variables[0].type,
            ArrayType(BuiltInType.BYTE, 0, 7),
        )
        self.assertEqual(
            program.variables[1].type,
            ArrayType(BuiltInType.BOOLEAN, 0, 3),
        )
        write = program.statements[1]
        self.assertIsInstance(write, ArrayElementAssignment)
        assert isinstance(write, ArrayElementAssignment)
        self.assertIsInstance(write.index, VariableReference)
        self.assertEqual(write.target, "Values")
        self.assertIsInstance(write.value, BinaryExpression)
        assert isinstance(write.value, BinaryExpression)
        self.assertIsInstance(write.value.left, ArrayIndexExpression)
        self.assertIsInstance(program.statements[2].value, ArrayIndexExpression)

    def test_rejects_malformed_range_missing_bracket_and_missing_element_type(self) -> None:
        malformed = (
            "Values: array[$00.$07] of byte;",
            "Values: array[$00..$07 of byte;",
            "Values: array[$00..$07] of ;",
        )
        for declaration in malformed:
            with self.subTest(declaration=declaration):
                with self.assertRaises(CompilerError) as context:
                    parse(
                        program_with(
                            "    Values[$00] := $01;",
                            f"    {declaration}",
                        ),
                        "malformed-array.nsp",
                    )
                self.assertEqual(context.exception.code, "E2102")


class ArraySemanticTests(unittest.TestCase):
    def test_resolves_typed_byte_and_boolean_array_elements(self) -> None:
        source = program_with(
            """    Index := $01;
    Values[$00] := $10;
    Values[Index] := Values[$00] + $01;
    Flags[$00] := true;
    if Flags[Index] then
        Values[$01] := $20;""",
            """    Values: array[$00..$07] of byte;
    Flags: array[$00..$03] of boolean;
    Index: byte;""",
        )

        resolved = resolve(source)

        constant_write = resolved.statements[1]
        self.assertIsInstance(constant_write, ResolvedArrayElementAssignment)
        assert isinstance(constant_write, ResolvedArrayElementAssignment)
        self.assertEqual(constant_write.index, ImmediateValue(0, BuiltInType.BYTE))
        variable_write = resolved.statements[2]
        assert isinstance(variable_write, ResolvedArrayElementAssignment)
        self.assertIs(variable_write.target.type.element_type, BuiltInType.BYTE)
        condition = resolved.statements[4]
        self.assertIsInstance(condition, ResolvedIfStatement)
        assert isinstance(condition, ResolvedIfStatement)
        self.assertIsInstance(condition.condition, ResolvedArrayElement)
        assert isinstance(condition.condition, ResolvedArrayElement)
        self.assertIs(
            condition.condition.array.type.element_type,
            BuiltInType.BOOLEAN,
        )

    def test_constant_expression_indexes_are_folded_and_bounds_checked(self) -> None:
        valid = program_with(
            "    Values[$01 + $02] := $10;",
            "    Values: array[$00..$03] of byte;",
        )
        resolved = resolve(valid)
        write = resolved.statements[0]
        assert isinstance(write, ResolvedArrayElementAssignment)
        self.assertEqual(write.index, ImmediateValue(3, BuiltInType.BYTE))

        invalid = program_with(
            "    Values[$02 + $02] := $10;",
            "    Values: array[$00..$03] of byte;",
        )
        with self.assertRaises(CompilerError) as context:
            resolve(invalid)
        self.assertEqual(context.exception.code, "E4012")

    def test_wrong_element_assignment_type_uses_strict_type_rules(self) -> None:
        cases = (
            (
                "Values[$00] := true;",
                "Values: array[$00..$03] of byte;",
            ),
            (
                "Flags[$00] := $10;",
                "Flags: array[$00..$03] of boolean;",
            ),
        )
        for statement, declaration in cases:
            with self.subTest(statement=statement):
                with self.assertRaises(CompilerError) as context:
                    resolve(program_with(f"    {statement}", f"    {declaration}"))
                self.assertEqual(context.exception.code, "E4004")

    def test_array_diagnostic_fixtures_are_focused_and_stable(self) -> None:
        expected = {
            "invalid_array_element_type.nsp": "E4010",
            "invalid_array_index_type.nsp": "E4011",
            "array_index_out_of_bounds.nsp": "E4012",
            "invalid_array_usage.nsp": "E4013",
            "invalid_array_bounds.nsp": "E4014",
        }
        for name, code in expected.items():
            with self.subTest(name=name):
                path = DIAGNOSTICS / name
                source = path.read_text(encoding="utf-8")
                with self.assertRaises(CompilerError) as context:
                    resolve(source, str(path))
                self.assertEqual(context.exception.code, code)
                self.assertEqual(str(context.exception).count(code), 1)

    def test_rejects_scalar_index_unknown_array_and_array_as_scalar(self) -> None:
        cases = (
            (
                "Counter[$00] := $01;",
                "Counter: byte;",
                "E4013",
            ),
            (
                "Unknown[$00] := $01;",
                "Counter: byte;",
                "E3007",
            ),
            (
                "Counter := Unknown[$00];",
                "Counter: byte;",
                "E3005",
            ),
            (
                "Values[$00] := $01;\n    Counter := Values;",
                "Values: array[$00..$03] of byte;\n    Counter: byte;",
                "E4013",
            ),
        )
        for body, variables, code in cases:
            with self.subTest(code=code, body=body):
                with self.assertRaises(CompilerError) as context:
                    resolve(program_with(f"    {body}", f"    {variables}"))
                self.assertEqual(context.exception.code, code)


class ArrayMemoryAndBackendTests(unittest.TestCase):
    def test_arrays_are_contiguous_regular_ram_symbols_with_explicit_ranges(self) -> None:
        source = program_with(
            """    Values[$00] := $10;
    Flags[$00] := true;""",
            """    Values: array[$00..$07] of byte;
    Flags: array[$00..$03] of boolean;""",
        )
        resolved = resolve(source)
        layout = build_memory_layout(resolved, source=source, filename="arrays.nsp")
        values, flags = layout.user_symbols

        self.assertEqual((values.size, flags.size), (8, 4))
        self.assertEqual(flags.address, values.address + values.size)
        self.assertEqual(values.region_name, layout.user_capacity.name)
        self.assertEqual(flags.region_name, layout.user_capacity.name)
        self.assertEqual(layout.temporary_bytes_used, 0)
        memory_map = generate_memory_map(layout)
        self.assertIn(
            f"${values.address:04X}-${values.address + 7:04X}",
            memory_map,
        )
        self.assertIn("array[$00..$07] of byte", memory_map)

    def test_large_arrays_reuse_existing_user_ram_exhaustion_diagnostic(self) -> None:
        declarations = "\n".join(
            f"    Values{index}: array[$00..$FF] of byte;"
            for index in range(7)
        )
        source = program_with("", declarations)
        resolved = resolve(source)

        with self.assertRaises(CompilerError) as context:
            build_memory_layout(resolved, source=source, filename="large-arrays.nsp")

        self.assertEqual(context.exception.code, "E5003")
        self.assertIn("requested 256 bytes", str(context.exception))

    def test_array_addressing_core_matches_focused_golden(self) -> None:
        path = ROOT / "tests" / "fixtures" / "codegen" / "arrays.nsp"
        source = path.read_text(encoding="utf-8")
        assembly = generate(resolve(source, str(path)))
        core = assembly.split("; Source: Index := value", 1)[1].split(
            "; Source: nes.set_background_color(value)", 1
        )[0]
        actual = ("; Source: Index := value" + core).rstrip() + "\n"
        expected = (ROOT / "tests" / "golden" / "arrays-addressing.asm").read_text(
            encoding="utf-8"
        )

        self.assertEqual(actual, expected)
        self.assertIn("variable_Values: .res 8", assembly)
        self.assertIn("variable_Flags: .res 4", assembly)
        self.assertNotIn("array_index_temp", assembly)
        self.assertNotIn("expression_temporary_", assembly)

    def test_minimum_array_boundary_allocation_addressing_and_semantics(self) -> None:
        source = program_with(
            "    Values[$00] := $42;",
            "    Values: array[$00..$00] of byte;",
        )
        resolved = resolve(source)
        layout = build_memory_layout(resolved, source=source, filename="min_array.nsp")
        values = layout.user_symbols[0]

        self.assertEqual(values.size, 1)
        self.assertEqual(resolved.variables[0].type, ArrayType(BuiltInType.BYTE, 0, 0))
        memory_map = generate_memory_map(layout)
        self.assertIn(f"${values.address:04X}", memory_map)
        self.assertIn("array[$00..$00] of byte", memory_map)

        assembly = generate(resolved, layout)
        self.assertIn("sta variable_Values", assembly)
        self.assertNotIn("variable_Values + 0", assembly)
        self.assertNotIn("array_index_temp", assembly)
        self.assertNotIn("expression_temporary_", assembly)

        # Verify out-of-bounds constant is rejected
        invalid_source = program_with(
            "    Values[$01] := $42;",
            "    Values: array[$00..$00] of byte;",
        )
        with self.assertRaises(CompilerError) as context:
            resolve(invalid_source)
        self.assertEqual(context.exception.code, "E4012")

    def test_maximum_array_boundary_allocation_and_indexing(self) -> None:
        source = program_with(
            """    Values[$00] := $10;
    Values[$FF] := $20;""",
            "    Values: array[$00..$FF] of byte;",
        )
        resolved = resolve(source)
        layout = build_memory_layout(resolved, source=source, filename="max_array.nsp")
        values = layout.user_symbols[0]

        self.assertEqual(values.size, 256)
        self.assertEqual(resolved.variables[0].type, ArrayType(BuiltInType.BYTE, 0, 255))
        memory_map = generate_memory_map(layout)
        self.assertIn(f"${values.address:04X}-${values.address + 255:04X}", memory_map)
        self.assertIn("array[$00..$FF] of byte", memory_map)

        assembly = generate(resolved, layout)
        self.assertIn("sta variable_Values", assembly)
        self.assertIn("sta variable_Values + 255", assembly)
        self.assertIn("variable_Values: .res 256", assembly)

        # Verify upper-bound boundary out-of-bounds is rejected when end < $FF
        invalid_upper = program_with(
            "    Values[$FE + $01] := $30;",
            "    Values: array[$00..$FE] of byte;",
        )
        with self.assertRaises(CompilerError) as context:
            resolve(invalid_upper)
        self.assertEqual(context.exception.code, "E4012")

        # Verify invalid array bounds where start != $00 triggers E4014
        invalid_start = program_with(
            "    Values[$01] := $30;",
            "    Values: array[$01..$FF] of byte;",
        )
        with self.assertRaises(CompilerError) as context:
            resolve(invalid_start)
        self.assertEqual(context.exception.code, "E4014")

    def test_variable_index_at_upper_boundary_preserves_native_range(self) -> None:
        source = program_with(
            """    Index := $FF;
    Values[Index] := $55;
    Result := Values[Index];""",
            """    Values: array[$00..$FF] of byte;
    Index: byte;
    Result: byte;""",
        )
        resolved = resolve(source)
        assembly = generate(resolved)

        self.assertIn("; Source: Values[index] := value", assembly)
        self.assertIn("tax                     ; native array index", assembly)
        self.assertIn("sta variable_Values,x", assembly)
        self.assertIn("lda variable_Values,x", assembly)
        self.assertIn("sta variable_Result", assembly)
        self.assertNotIn("and #$7F", assembly)
        self.assertNotIn("and #$0F", assembly)

    def test_indexed_assignment_with_expression_preserves_order_and_temporaries(self) -> None:
        source = program_with(
            """    Values[$00] := $10;
    Values[$01] := $20;
    Index := $02;
    Values[Index] := Values[$00] + (Values[$01] + $03);""",
            """    Values: array[$00..$07] of byte;
    Index: byte;""",
        )
        resolved = resolve(source)
        layout = build_memory_layout(resolved)
        assembly = generate(resolved, layout)

        block = assembly.split("; Source: Values[index] := value", 1)[1].split(
            "; Source: nes.set_background_color(value)", 1
        )[0]
        pha_idx = block.index("pha")
        pla_idx = block.index("pla")
        self.assertLess(pha_idx, pla_idx)
        self.assertIn("tay                     ; preserve assigned value", block)
        self.assertIn("sta variable_Values,x", block)
        self.assertEqual(block.count("pha"), 1)
        self.assertEqual(block.count("pla"), 1)
        self.assertEqual(layout.temporary_storage.size, 16)
        self.assertNotIn("array_index_temp", assembly)

    @unittest.skipUnless(
        shutil.which("ca65") is not None and shutil.which("ld65") is not None,
        "array benchmark measurement requires ca65 and ld65",
    )
    def test_array_benchmark_reports_focused_resource_accounting(self) -> None:
        from tools.measure_benchmarks import BENCHMARKS, measure_benchmark

        spec = next(item for item in BENCHMARKS if item.name == "arrays")
        metrics = measure_benchmark(spec)

        self.assertEqual(metrics.prg_code_bytes, 382)
        self.assertEqual(metrics.prg_total_used_bytes, 388)
        self.assertEqual(metrics.pattern_stats.total_instructions, 182)
        self.assertEqual(metrics.estimated_static_base_cycles, 569)
        self.assertEqual(metrics.max_expression_tree_depth, 2)
        self.assertEqual(metrics.max_live_temporaries, 1)
        self.assertEqual(metrics.memory.zp_temporary_reserved_bytes, 16)
        self.assertEqual(metrics.memory.zp_temporary_required_bytes, 3)
        self.assertEqual(metrics.memory.regular_user_bytes, 16)
        self.assertEqual(metrics.memory.zp_promoted_user_bytes, 3)
        self.assertEqual(metrics.runtime_features, ())


if __name__ == "__main__":
    unittest.main()
