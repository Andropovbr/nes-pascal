from pathlib import Path
import shutil
import tempfile
import unittest

from nes_pascal.ast import BuiltinCall, ResolvedBuiltinCall
from nes_pascal.builtins import BuiltinId
from nes_pascal.backend_ca65 import generate
from nes_pascal.cli import compile_source
from nes_pascal.diagnostics import CompilerError
from nes_pascal.memory_layout import build_memory_layout, generate_linker_config
from nes_pascal.parser import parse
from nes_pascal.semantic import analyze


TOOLCHAIN_AVAILABLE = shutil.which("ca65") is not None and shutil.which("ld65") is not None


def program_with(body: str, declarations: str = "") -> str:
    return f"""program ScrollTest;
{declarations}begin
    nes.set_background_color($0F);
    nes.run;
{body}
end.
"""


def compile_assembly(source: str) -> tuple[str, object]:
    program = analyze(parse(source, "scroll_test.nsp"), source, "scroll_test.nsp")
    layout = build_memory_layout(program)
    return generate(program, layout), layout


class ScrollParserAndSemanticTests(unittest.TestCase):
    def test_parses_and_resolves_two_byte_arguments(self) -> None:
        source = program_with(
            "    nes.set_scroll(X, $F0);",
            """var
    X: byte;
""",
        ).replace("    nes.set_background_color", "    X := $10;\n    nes.set_background_color")
        parsed = parse(source)
        self.assertIsInstance(parsed.statements[-1], BuiltinCall)
        self.assertEqual(parsed.statements[-1].name, "nes.set_scroll")
        resolved = analyze(parsed, source, "scroll_test.nsp")
        self.assertIsInstance(resolved.statements[-1], ResolvedBuiltinCall)
        self.assertIs(resolved.statements[-1].builtin, BuiltinId.SET_SCROLL)

    def test_invalid_argument_count_has_stable_diagnostic(self) -> None:
        path = Path(__file__).parent / "fixtures" / "diagnostics" / "invalid_set_scroll_argument_count.nsp"
        source = path.read_text(encoding="utf-8")
        with self.assertRaises(CompilerError) as raised:
            analyze(parse(source, str(path)), source, str(path))
        self.assertEqual(raised.exception.code, "E3046")

    def test_boolean_scroll_argument_reuses_strict_type_diagnostic(self) -> None:
        source = program_with("    nes.set_scroll(true, $00);")
        with self.assertRaises(CompilerError) as raised:
            analyze(parse(source), source)
        self.assertEqual(raised.exception.code, "E4004")


class ScrollBackendTests(unittest.TestCase):
    def test_default_state_and_four_authoritative_shadows_are_emitted(self) -> None:
        assembly, layout = compile_assembly(program_with(""))
        symbols = {symbol.assembly_symbol for symbol in layout.runtime_symbols}
        self.assertTrue(
            {
                "runtime_ppuctrl_shadow",
                "runtime_ppumask_shadow",
                "runtime_scroll_x_shadow",
                "runtime_scroll_y_shadow",
            }.issubset(symbols)
        )
        run = assembly.split("; Source: nes.run", 1)[1].split("; Runtime: implicit", 1)[0]
        self.assertIn("lda runtime_scroll_x_shadow ; zero-filled default scroll X", run)
        self.assertIn("lda runtime_scroll_y_shadow ; zero-filled default scroll Y", run)
        self.assertIn("lda runtime_ppumask_shadow\n    ora #$1E", run)
        self.assertNotIn("lda #$1E\n    sta $2001", run)

    def test_runtime_call_only_stages_complete_pair_and_last_call_wins(self) -> None:
        assembly, _ = compile_assembly(
            program_with("    nes.set_scroll($10, $20);\n    nes.set_scroll($30, $40);")
        )
        calls = assembly.split("; Source: nes.set_scroll(x, y)")[1:]
        self.assertEqual(len(calls), 2)
        for call in calls:
            staged = call.split("; Source:", 1)[0]
            self.assertNotIn("$2005", staged)
            self.assertLess(staged.index("sta runtime_scroll_pending_x"), staged.index("sta runtime_scroll_pending_y"))
            self.assertLess(staged.index("sta runtime_scroll_pending_y"), staged.rindex("sta runtime_scroll_ready"))
        self.assertIn("lda #$30\n    sta runtime_scroll_pending_x", calls[1])
        self.assertIn("lda #$40\n    sta runtime_scroll_pending_y", calls[1])

    def test_nmi_commits_scroll_and_restores_ppu_state_once_after_callback(self) -> None:
        source = """program ScrollCallback;
var
    Color: nes_color;
procedure VBlank;
begin
    nes.set_background_palette_color($00, $01, Color);
end;
begin
    Color := $11;
    nes.set_background_color($0F);
    nes.on_vblank(VBlank);
    nes.run;
    nes.set_scroll($10, $20);
end.
"""
        assembly, _ = compile_assembly(source)
        nmi = assembly.split("NMI:", 1)[1].split("IRQ:", 1)[0]
        restore = nmi.split("; Runtime: authoritative final PPU state", 1)[1]
        self.assertLess(nmi.index("jsr runtime_upload_queued_palettes"), nmi.index("jsr procedure_VBlank"))
        self.assertLess(nmi.index("jsr procedure_VBlank"), nmi.index("@skip_scroll_commit:"))
        self.assertEqual(restore.count("sta $2005"), 2)
        self.assertLess(restore.index("sta $2000"), restore.index("sta $2005"))
        self.assertLess(restore.rindex("sta $2005"), restore.index("sta $2001"))
        self.assertIn("bit $2002", restore)
        palette_uploader = assembly.split("runtime_upload_queued_palettes:", 1)[1].split("runtime_upload_palette_triplet:", 1)[0]
        self.assertNotIn("sta $2000", palette_uploader)
        self.assertNotIn("sta $2005", palette_uploader)

    def test_palette_and_background_uploaders_share_one_final_restoration(self) -> None:
        source = program_with(
            "    nes.set_background_palette_color($00, $01, $11);\n"
            "    nes.set_tile($00, $00, $01);\n"
            "    nes.set_attribute($00, $00, $E4);\n"
            "    nes.set_scroll($08, $04);"
        )
        assembly, _ = compile_assembly(source)
        nmi = assembly.split("NMI:", 1)[1].split("IRQ:", 1)[0]
        self.assertEqual(nmi.count("sta $2000"), 1)
        self.assertEqual(nmi.count("sta $2001"), 1)
        self.assertEqual(nmi.count("sta $2005"), 2)
        self.assertLess(nmi.index("jsr runtime_upload_queued_palettes"), nmi.index("jsr runtime_upload_queued_background"))
        self.assertLess(nmi.index("jsr runtime_upload_queued_background"), nmi.index("sta $2000"))

    def test_scroll_layout_and_linker_output_are_deterministic(self) -> None:
        source = program_with("    nes.set_scroll($10, $20);")
        first_program = analyze(parse(source), source)
        first = build_memory_layout(first_program)
        second = build_memory_layout(analyze(parse(source), source))
        self.assertEqual(first, second)
        self.assertEqual(generate_linker_config(first), generate_linker_config(second))
        symbols = {symbol.assembly_symbol for symbol in first.runtime_symbols}
        self.assertTrue({"runtime_scroll_pending_x", "runtime_scroll_pending_y", "runtime_scroll_ready"}.issubset(symbols))


@unittest.skipUnless(TOOLCHAIN_AVAILABLE, "integration skipped: ca65 and/or ld65 are not installed")
class MirroringIntegrationTests(unittest.TestCase):
    def test_scrolling_example_builds_a_valid_nrom(self) -> None:
        source = Path(__file__).resolve().parents[1] / "examples" / "scrolling_ppu_state.nsp"
        with tempfile.TemporaryDirectory() as temporary_directory:
            rom = Path(temporary_directory) / "scrolling_ppu_state.nes"
            compile_source(source, rom)
            data = rom.read_bytes()
        self.assertEqual(data[:6], b"NES\x1a\x02\x01")
        self.assertEqual(len(data), 16 + 32768 + 8192)

    def test_horizontal_default_and_vertical_header_bits(self) -> None:
        source = Path(__file__).resolve().parents[1] / "examples" / "minimal.nsp"
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            horizontal = directory / "horizontal.nes"
            horizontal_again = directory / "horizontal_again.nes"
            vertical = directory / "vertical.nes"
            compile_source(source, horizontal)
            compile_source(source, horizontal_again, mirroring="horizontal")
            compile_source(source, vertical, mirroring="vertical")
            self.assertEqual(horizontal.read_bytes()[6] & 1, 0)
            self.assertEqual(vertical.read_bytes()[6] & 1, 1)
            self.assertEqual(horizontal.read_bytes(), horizontal_again.read_bytes())
            self.assertEqual(horizontal.with_suffix(".asm").read_bytes(), horizontal_again.with_suffix(".asm").read_bytes())
            self.assertEqual(horizontal.with_suffix(".cfg").read_bytes(), vertical.with_suffix(".cfg").read_bytes())

    def test_invalid_mirroring_has_stable_diagnostic(self) -> None:
        source = Path(__file__).resolve().parents[1] / "examples" / "minimal.nsp"
        with tempfile.TemporaryDirectory() as temporary_directory:
            with self.assertRaises(CompilerError) as raised:
                compile_source(source, Path(temporary_directory) / "bad.nes", mirroring="four-screen")
        self.assertEqual(raised.exception.code, "E6010")
        self.assertIn("horizontal", str(raised.exception))
        self.assertIn("vertical", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
