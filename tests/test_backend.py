from pathlib import Path
import unittest

from nes_pascal.backend_ca65 import generate
from nes_pascal.parser import parse
from nes_pascal.semantic import analyze


ROOT = Path(__file__).resolve().parents[1]


class BackendGoldenTests(unittest.TestCase):
    def test_minimal_program_matches_golden_assembly(self) -> None:
        source_path = ROOT / "examples" / "minimal.nsp"
        source = source_path.read_text(encoding="utf-8")
        filename = str(source_path)
        actual = generate(analyze(parse(source, filename), source, filename))
        expected = (ROOT / "tests" / "golden" / "minimal.asm").read_text(
            encoding="utf-8"
        )
        self.assertEqual(actual, expected)

    def test_variables_use_regular_ram_and_runtime_loads(self) -> None:
        source_path = ROOT / "examples" / "minimal.nsp"
        source = source_path.read_text(encoding="utf-8")
        filename = str(source_path)
        assembly = generate(analyze(parse(source, filename), source, filename))
        self.assertIn('.segment "BSS"', assembly)
        self.assertIn("variable_BackgroundColor: .res 1", assembly)
        self.assertIn("sta variable_BackgroundColor", assembly)
        self.assertIn("lda variable_BackgroundColor", assembly)

    def test_arithmetic_program_matches_golden_assembly(self) -> None:
        source_path = ROOT / "examples" / "arithmetic.nsp"
        source = source_path.read_text(encoding="utf-8")
        filename = str(source_path)
        actual = generate(analyze(parse(source, filename), source, filename))
        expected = (ROOT / "tests" / "golden" / "arithmetic.asm").read_text(
            encoding="utf-8"
        )
        self.assertEqual(actual, expected)
        self.assertIn("expression_temporary_0: .res 1", actual)
        self.assertIn("expression_temporary_1: .res 1", actual)
        self.assertIn("adc expression_temporary_1", actual)
        self.assertIn("sbc expression_temporary_0", actual)
        self.assertIn("eor #$FF", actual)

    def test_boolean_expression_program_matches_golden_assembly(self) -> None:
        source_path = ROOT / "examples" / "boolean_expressions.nsp"
        source = source_path.read_text(encoding="utf-8")
        filename = str(source_path)
        actual = generate(analyze(parse(source, filename), source, filename))
        expected = (
            ROOT / "tests" / "golden" / "boolean_expressions.asm"
        ).read_text(encoding="utf-8")
        self.assertEqual(actual, expected)
        self.assertIn("cmp expression_temporary_0", actual)
        self.assertIn("; short-circuit false", actual)
        self.assertIn("; short-circuit true", actual)
        self.assertIn("lda #$00              ; false", actual)
        self.assertIn("lda #$01              ; true", actual)

    def test_conditional_program_matches_golden_assembly(self) -> None:
        source_path = ROOT / "examples" / "conditionals.nsp"
        source = source_path.read_text(encoding="utf-8")
        filename = str(source_path)
        actual = generate(analyze(parse(source, filename), source, filename))
        expected = (ROOT / "tests" / "golden" / "conditionals.asm").read_text(
            encoding="utf-8"
        )
        self.assertEqual(actual, expected)
        self.assertIn("; long-branch-safe false path", actual)
        self.assertIn("@if_then_", actual)
        self.assertIn("@if_else_", actual)
        self.assertIn("@if_end_", actual)

    def test_loop_program_matches_golden_assembly(self) -> None:
        source_path = ROOT / "examples" / "loops.nsp"
        source = source_path.read_text(encoding="utf-8")
        filename = str(source_path)
        actual = generate(analyze(parse(source, filename), source, filename))
        expected = (ROOT / "tests" / "golden" / "loops.asm").read_text(
            encoding="utf-8"
        )
        self.assertEqual(actual, expected)
        self.assertIn("; Source: while condition do", actual)
        self.assertIn("; Source: repeat until condition", actual)
        self.assertIn("; Source: break", actual)
        self.assertIn("; Source: continue", actual)
        self.assertIn("; long-branch-safe loop exit", actual)

    def test_counting_program_matches_golden_assembly(self) -> None:
        source_path = ROOT / "examples" / "counting.nsp"
        source = source_path.read_text(encoding="utf-8")
        filename = str(source_path)
        actual = generate(analyze(parse(source, filename), source, filename))
        expected = (ROOT / "tests" / "golden" / "counting.asm").read_text(
            encoding="utf-8"
        )
        self.assertEqual(actual, expected)
        self.assertIn("    inc variable_Counter", actual)
        self.assertIn("    dec variable_Counter", actual)
        self.assertIn("; Source: inc(Sum, amount)", actual)
        self.assertIn("; Source: dec(Counter, amount)", actual)
        self.assertIn("; evaluate final value once", actual)
        self.assertIn("; stop before byte wraparound", actual)
        self.assertIn("; long-branch-safe loop exit", actual)

    def test_for_break_and_continue_target_innermost_loop(self) -> None:
        source = """program ForControl;
var
    Index: byte;
begin
    for Index := $00 to $03 do
    begin
        if Index = $01 then
            continue;
        if Index = $02 then
            break;
    end;
    nes.set_background_color($21);
    nes.run;
end.
"""
        assembly = generate(analyze(parse(source), source))
        self.assertRegex(assembly, r"; Source: continue\n    jmp @for_step_\d+")
        self.assertRegex(assembly, r"; Source: break\n    jmp @for_end_\d+")

    def test_for_final_value_is_loaded_once_before_the_loop(self) -> None:
        source = """program CachedLimit;
var
    Index: byte;
    Limit: byte;
    Total: byte;
begin
    Limit := $03;
    Total := $00;
    for Index := $00 to Limit do
    begin
        Limit := $00;
        inc(Total);
    end;
    nes.set_background_color($21);
    nes.run;
end.
"""
        assembly = generate(analyze(parse(source), source))
        self.assertEqual(assembly.count("    lda variable_Limit"), 1)
        self.assertIn("    sta for_limit_0   ; evaluate final value once", assembly)

    def test_procedure_program_matches_golden_assembly(self) -> None:
        source_path = ROOT / "examples" / "procedures.nsp"
        source = source_path.read_text(encoding="utf-8")
        filename = str(source_path)
        actual = generate(analyze(parse(source, filename), source, filename))
        expected = (ROOT / "tests" / "golden" / "procedures.asm").read_text(
            encoding="utf-8"
        )
        self.assertEqual(actual, expected)
        self.assertIn("    jsr procedure_BuildState", actual)
        self.assertIn("    jsr procedure_InitializeState", actual)
        self.assertIn("procedure_ChooseColor:", actual)
        self.assertIn("@if_then_", actual)
        self.assertEqual(actual.count("    rts"), 5)

    def test_procedure_parameter_program_matches_golden_assembly(self) -> None:
        source_path = ROOT / "examples" / "procedure_parameters.nsp"
        source = source_path.read_text(encoding="utf-8")
        filename = str(source_path)
        actual = generate(analyze(parse(source, filename), source, filename))
        expected = (
            ROOT / "tests" / "golden" / "procedure_parameters.asm"
        ).read_text(encoding="utf-8")
        self.assertEqual(actual, expected)
        self.assertIn("parameter_Initialize_Start: .res 1", actual)
        self.assertIn("sta parameter_Initialize_Start", actual)
        self.assertIn("lda parameter_Initialize_Start", actual)
        self.assertIn("jsr procedure_ApplyStep", actual)
        self.assertLess(
            actual.index("sta parameter_Initialize_Start"),
            actual.index("sta parameter_Initialize_Step"),
        )
        self.assertLess(
            actual.index("sta parameter_Initialize_Step"),
            actual.index("sta parameter_Initialize_EnabledValue"),
        )


if __name__ == "__main__":
    unittest.main()
