from pathlib import Path
import unittest

from nes_pascal.backend_ca65 import generate
from nes_pascal.parser import parse
from nes_pascal.semantic import analyze


ROOT = Path(__file__).resolve().parents[1]


class BackendGoldenTests(unittest.TestCase):
    def test_frame_callbacks_program_matches_golden_assembly(self) -> None:
        source_path = ROOT / "examples" / "frame_callbacks.nsp"
        source = source_path.read_text(encoding="utf-8")
        filename = str(source_path)
        actual = generate(analyze(parse(source, filename), source, filename))
        expected = (ROOT / "tests" / "golden" / "frame_callbacks.asm").read_text(
            encoding="utf-8"
        )
        self.assertEqual(actual, expected)

    def test_minimal_program_matches_golden_assembly(self) -> None:
        source_path = ROOT / "examples" / "minimal.nsp"
        source = source_path.read_text(encoding="utf-8")
        filename = str(source_path)
        actual = generate(analyze(parse(source, filename), source, filename))
        expected = (ROOT / "tests" / "golden" / "minimal.asm").read_text(
            encoding="utf-8"
        )
        self.assertEqual(actual, expected)

    def test_configured_chr_rom_is_emitted_once_without_default_storage(self) -> None:
        source_path = ROOT / "examples" / "minimal.nsp"
        source = source_path.read_text(encoding="utf-8")
        filename = str(source_path)
        chr_rom = bytes(range(256)) * 32

        assembly = generate(
            analyze(parse(source, filename), source, filename),
            chr_rom=chr_rom,
        )

        chr_segment = assembly.split('.segment "CHR"\n', 1)[1]
        self.assertEqual(chr_segment.count("; Asset: configured CHR-ROM bytes"), 1)
        self.assertEqual(chr_segment.count("    .byte "), 512)
        self.assertNotIn("empty CHR-ROM", chr_segment)
        self.assertNotIn("Runtime example asset", chr_segment)
        self.assertIn("$00, $01, $02, $03", chr_segment)
        self.assertTrue(chr_segment.rstrip().endswith("$FC, $FD, $FE, $FF"))

    def test_memory_segments_and_variable_loads_are_emitted(self) -> None:
        source_path = ROOT / "examples" / "minimal.nsp"
        source = source_path.read_text(encoding="utf-8")
        filename = str(source_path)
        assembly = generate(analyze(parse(source, filename), source, filename))
        self.assertNotIn('.segment "OAM_SHADOW"', assembly)
        self.assertIn('.segment "ZERO_PAGE_RUNTIME": zeropage', assembly)
        self.assertIn('.segment "ZERO_PAGE_TEMPORARIES": zeropage', assembly)
        self.assertIn('.segment "ZERO_PAGE_VARIABLES": zeropage', assembly)
        self.assertIn('.segment "USER_VARIABLES"', assembly)
        self.assertNotIn("runtime_oam_shadow", assembly)
        self.assertIn("runtime_frame_counter: .res 1", assembly)
        self.assertIn("runtime_frame_ready: .res 1", assembly)
        self.assertIn("runtime_last_processed_frame: .res 1", assembly)
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
        self.assertEqual(actual.count("    rts"), 7)

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

    def test_memory_layout_program_matches_golden_assembly(self) -> None:
        source_path = ROOT / "examples" / "memory_layout.nsp"
        source = source_path.read_text(encoding="utf-8")
        filename = str(source_path)
        actual = generate(analyze(parse(source, filename), source, filename))
        expected = (ROOT / "tests" / "golden" / "memory_layout.asm").read_text(
            encoding="utf-8"
        )
        self.assertEqual(actual, expected)
        self.assertNotIn("runtime_oam_shadow", actual)
        self.assertIn("; $0010: reusable expression evaluation byte", actual)
        self.assertIn("; $0080: BackgroundColor: nes_color", actual)

    def test_zero_page_program_matches_golden_assembly(self) -> None:
        source_path = ROOT / "examples" / "zero_page.nsp"
        source = source_path.read_text(encoding="utf-8")
        filename = str(source_path)
        actual = generate(analyze(parse(source, filename), source, filename))
        expected = (ROOT / "tests" / "golden" / "zero_page.asm").read_text(
            encoding="utf-8"
        )
        self.assertEqual(actual, expected)
        self.assertIn("; $0080: Counter: byte", actual)
        self.assertIn("; $0081: BackgroundColor: nes_color", actual)
        self.assertIn("; $0200: Matches: boolean", actual)

    def test_frame_synchronization_program_matches_golden_assembly(self) -> None:
        source_path = ROOT / "examples" / "frame_synchronization.nsp"
        source = source_path.read_text(encoding="utf-8")
        filename = str(source_path)
        actual = generate(analyze(parse(source, filename), source, filename))
        expected = (
            ROOT / "tests" / "golden" / "frame_synchronization.asm"
        ).read_text(encoding="utf-8")

        self.assertEqual(actual, expected)
        nmi_handler = actual.split("NMI:\n", 1)[1].split("IRQ:\n", 1)[0]
        self.assertIn(
            "    pha\n"
            "    txa\n"
            "    pha\n"
            "    tya\n"
            "    pha",
            nmi_handler,
        )
        self.assertIn(
            "    pla\n"
            "    tay\n"
            "    pla\n"
            "    tax\n"
            "    pla\n"
            "    rti",
            nmi_handler,
        )
        self.assertIn("inc runtime_frame_counter", nmi_handler)
        self.assertIn("sta runtime_frame_ready", nmi_handler)
        self.assertNotIn("jsr", nmi_handler)
        self.assertNotIn("$200", nmi_handler)
        self.assertNotIn("variable_", nmi_handler)
        self.assertIn("cmp runtime_frame_counter", actual)
        self.assertIn("beq @wait_frame_", actual)
        self.assertIn("@runtime_idle_loop:", actual)
        run_block = actual.split("; Source: nes.run\n", 1)[1].split(
            "; Source: while condition do",
            1,
        )[0]
        self.assertLess(run_block.index("bit $2002"), run_block.index("sta $2000"))
        self.assertLess(run_block.index("sta $2000"), run_block.index("sta $2001"))
        self.assertLess(
            actual.index("sta $2007"),
            actual.index("; Source: nes.run"),
        )


if __name__ == "__main__":
    unittest.main()
