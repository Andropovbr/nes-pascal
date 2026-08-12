from pathlib import Path
import unittest

from nes_pascal.backend_ca65 import generate
from nes_pascal.parser import parse
from nes_pascal.semantic import analyze


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "codegen" / "low_risk_codegen.nsp"
GOLDEN = ROOT / "tests" / "golden" / "low_risk_codegen.asm"


def generate_source(source: str, filename: str = "optimization_test.nsp") -> str:
    return generate(analyze(parse(source, filename), source, filename))


def source_block(assembly: str, source_comment: str) -> str:
    start = assembly.index(source_comment)
    end = assembly.find("\n\n; Source:", start + len(source_comment))
    if end < 0:
        end = len(assembly)
    return assembly[start:end]


class LowRiskCodegenGoldenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = FIXTURE.read_text(encoding="utf-8")
        cls.assembly = generate_source(cls.source, str(FIXTURE))

    def test_fixture_matches_golden_assembly(self) -> None:
        self.assertEqual(self.assembly, GOLDEN.read_text(encoding="utf-8"))

    def test_immediate_arithmetic_operand_is_consumed_directly(self) -> None:
        block = source_block(self.assembly, "; Source: Result := value")
        self.assertIn(
            "    lda variable_Left\n"
            "    clc\n"
            "    adc #$01\n"
            "    sta variable_Result",
            block,
        )
        self.assertNotIn("expression_temporary", block)

    def test_variable_arithmetic_operand_is_consumed_directly(self) -> None:
        blocks = self.assembly.split("; Source: Result := value")
        block = blocks[2].split("\n\n; Source:", 1)[0]
        self.assertIn(
            "    lda variable_Result\n"
            "    sec\n"
            "    sbc variable_Right\n"
            "    sta variable_Result",
            block,
        )
        self.assertNotIn("expression_temporary", block)

    def test_immediate_and_variable_comparisons_use_direct_operands(self) -> None:
        stored = source_block(self.assembly, "; Source: Stored := value")
        other = source_block(self.assembly, "; Source: Other := value")
        self.assertIn("lda variable_Left\n    cmp #$08", stored)
        self.assertIn("lda variable_Left\n    cmp variable_Right", other)
        self.assertNotIn("expression_temporary", stored + other)

    def test_stored_comparisons_still_materialize_canonical_booleans(self) -> None:
        stored = source_block(self.assembly, "; Source: Stored := value")
        self.assertIn("lda #$00              ; false", stored)
        self.assertIn("lda #$01              ; true", stored)
        self.assertTrue(stored.rstrip().endswith("sta variable_Stored"))

    def test_branch_comparison_does_not_materialize_a_boolean(self) -> None:
        branch = self.assembly.split("; Source: if condition then", 1)[1]
        branch = branch.split("@if_then_", 1)[0]
        self.assertIn("cmp variable_Right", branch)
        self.assertNotIn("lda #$00              ; false", branch)
        self.assertNotIn("lda #$01              ; true", branch)
        self.assertNotIn("cmp #$00", branch)

    def test_boolean_variable_branch_uses_lda_flags_without_zero_compare(self) -> None:
        second_if = self.assembly.split("; Source: if condition then", 2)[2]
        second_if = second_if.split("@if_then_", 1)[0]
        self.assertRegex(second_if, r"lda variable_Stored\n    bne @boolean_branch_true_")
        self.assertNotIn("cmp #$00", second_if)

    def test_short_circuit_and_or_and_not_have_explicit_branch_paths(self) -> None:
        self.assertIn("; boolean and: branch left operand", self.assembly)
        self.assertIn("; boolean and: branch right operand", self.assembly)
        self.assertIn("; boolean or: branch left operand", self.assembly)
        self.assertIn("; boolean or: branch right operand", self.assembly)
        self.assertIn("; boolean not: branch result", self.assembly)
        self.assertIn("; short-circuit true", self.assembly)

    def test_runtime_builtin_result_uses_builtin_aware_branch_lowering(self) -> None:
        source = """program BuiltinBranch;
var
    Seen: boolean;
begin
    Seen := false;
    nes.set_background_color($0F);
    nes.run;
    if nes.controller_down($01, nes.button_a) then
        Seen := true;
end.
"""
        assembly = generate_source(source)
        branch = assembly.split("; Source: if condition then", 1)[1]
        branch = branch.split("@if_then_", 1)[0]
        self.assertIn("; nes.controller_down($01, nes.button_a): branch result", branch)
        self.assertIn("and #$01", branch)
        self.assertNotIn("controller_true", branch)
        self.assertNotIn("lda #$01              ; true", branch)

    def test_complex_left_side_preserves_right_first_temporary_staging(self) -> None:
        source = """program StableOrder;
var
    X: byte;
    Y: byte;
    Offset: byte;
    Result: byte;
begin
    X := $00;
    Y := $00;
    Offset := $01;
    nes.set_background_color($0F);
    nes.run;
    Result := nes.get_tile(X, Y) + Offset;
end.
"""
        assembly = generate_source(source)
        block = source_block(assembly, "; Source: Result := value")
        self.assertLess(block.index("lda variable_Offset"), block.index("jsr runtime_get_tile"))
        self.assertIn("sta expression_temporary_0", block)
        self.assertIn("adc expression_temporary_0", block)

    def test_large_branch_keeps_relative_target_local_and_false_path_absolute(self) -> None:
        repeated_body = "\n".join("        inc(Value);" for _ in range(96))
        source = f"""program LongOptimizedBranch;
var
    Value: byte;
begin
    Value := $00;
    if Value = $00 then
    begin
{repeated_body}
    end;
    nes.set_background_color($0F);
    nes.run;
end.
"""
        assembly = generate_source(source)
        condition = "\n".join(
            assembly.split("; Source: if condition then\n", 1)[1].splitlines()[:5]
        )
        self.assertRegex(condition, r"beq @if_then_\d+\n    jmp @if_end_\d+")
        self.assertNotIn("lda #$00              ; false", condition)


if __name__ == "__main__":
    unittest.main()
