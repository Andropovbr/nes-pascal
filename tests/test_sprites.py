from pathlib import Path
import unittest

from nes_pascal.ast import (
    BuiltInType,
    ResolvedSpriteOperation,
    SpriteOperation,
    SpriteOperationKind,
)
from nes_pascal.backend_ca65 import generate
from nes_pascal.diagnostics import CompilerError
from nes_pascal.memory_layout import build_memory_layout
from nes_pascal.parser import parse
from nes_pascal.semantic import analyze


ROOT = Path(__file__).resolve().parents[1]


def sprite_program(body: str, declarations: str = "") -> str:
    variable_section = f"var\n{declarations}" if declarations else ""
    return f"""program SpriteTest;
{variable_section}
begin
    {body}
    nes.set_background_color($0F);
    nes.run;
end.
"""


def resolved_source(source: str, filename: str = "sprite_test.nsp"):
    return analyze(parse(source, filename), source, filename)


class SpriteLanguageTests(unittest.TestCase):
    def test_parser_models_every_sprite_operation_and_sprite_type(self) -> None:
        source = """program SpriteParser;
const
    First: sprite = $00;
var
    Current: sprite;
begin
    Current := First;
    nes.sprite_set_position(Current, $08, $18);
    nes.sprite_set_x(Current, $10);
    nes.sprite_set_y(Current, $20);
    nes.sprite_set_tile(Current, $03);
    nes.sprite_set_palette(Current, $02);
    nes.sprite_set_attributes(Current, $E3);
    nes.sprite_hide(Current);
    nes.sprite_show(Current);
    nes.sprite_set_flip_horizontal(Current, true);
    nes.sprite_set_flip_vertical(Current, false);
    nes.sprite_set_behind_background(Current, true);
    nes.set_background_color($0F);
    nes.run;
end.
"""
        parsed = parse(source)
        self.assertIs(parsed.constants[0].type, BuiltInType.SPRITE)
        self.assertIs(parsed.variables[0].type, BuiltInType.SPRITE)
        operations = [
            statement
            for statement in parsed.statements
            if isinstance(statement, SpriteOperation)
        ]
        self.assertEqual(
            [operation.kind for operation in operations],
            list(SpriteOperationKind),
        )

        resolved = resolved_source(source)
        resolved_operations = [
            statement
            for statement in resolved.statements
            if isinstance(statement, ResolvedSpriteOperation)
        ]
        self.assertEqual(len(resolved_operations), 11)

    def test_accepts_sprite_boundaries_and_palette_boundaries(self) -> None:
        source = sprite_program(
            "nes.sprite_set_x($00, $00);\n"
            "    nes.sprite_set_palette($00, $00);\n"
            "    nes.sprite_set_x($3F, $FF);\n"
            "    nes.sprite_set_palette($3F, $03);"
        )
        resolved_source(source)

    def test_sprite_type_is_exact_and_not_arithmetic(self) -> None:
        source = sprite_program(
            "Index := $00;\n    nes.sprite_show(Index);",
            "    Index: byte;\n",
        )
        with self.assertRaises(CompilerError) as context:
            resolved_source(source)
        self.assertEqual(context.exception.code, "E4004")

    def test_focused_sprite_diagnostics_are_stable(self) -> None:
        fixtures = {
            "sprite_argument_count.nsp": "E3047",
            "invalid_sprite_palette.nsp": "E3048",
            "invalid_sprite_value.nsp": "E4008",
        }
        directory = ROOT / "tests" / "fixtures" / "diagnostics"
        for filename, code in fixtures.items():
            with self.subTest(filename=filename):
                path = directory / filename
                source = path.read_text(encoding="utf-8")
                with self.assertRaises(CompilerError) as context:
                    resolved_source(source, str(path))
                self.assertEqual(context.exception.code, code)

    def test_sprite_operations_are_rejected_from_vblank_call_graph(self) -> None:
        source = """program SpriteVBlank;
procedure VBlank;
begin
    nes.sprite_set_x($00, $10);
end;
begin
    nes.set_background_color($0F);
    nes.on_vblank(VBlank);
    nes.run;
end.
"""
        with self.assertRaises(CompilerError) as context:
            resolved_source(source)
        self.assertEqual(context.exception.code, "E3023")
        self.assertIn("NMI owns OAM DMA", str(context.exception))


class SpriteMemoryAndBackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        path = ROOT / "examples" / "sprite_support.nsp"
        cls.source = path.read_text(encoding="utf-8")
        cls.resolved = resolved_source(cls.source, str(path))
        cls.layout = build_memory_layout(cls.resolved)
        cls.assembly = generate(cls.resolved, cls.layout)

    def test_oam_shadow_is_exact_page_aligned_and_non_overlapping(self) -> None:
        self.assertEqual(self.layout.oam_shadow.start, 0x0200)
        self.assertEqual(self.layout.oam_shadow.end, 0x02FF)
        self.assertEqual(self.layout.oam_shadow.size, 256)
        self.assertEqual(self.layout.oam_shadow.start % 256, 0)
        self.assertFalse(self.layout.oam_shadow.overlaps(self.layout.runtime_data))
        symbols = {
            symbol.assembly_symbol: (symbol.address, symbol.size)
            for symbol in self.layout.runtime_symbols
        }
        self.assertEqual(symbols["runtime_oam_shadow"], (0x0200, 256))
        self.assertEqual(symbols["runtime_sprite_logical_y"], (0x0300, 64))
        self.assertEqual(symbols["runtime_sprite_value"], (0x0340, 1))
        self.assertEqual(
            symbols["runtime_sprite_secondary_value"],
            (0x0341, 1),
        )

    def test_reset_hides_every_sprite_before_source_initialization(self) -> None:
        reset = self.assembly.split("RESET:", 1)[1].split(
            "; Source: nes.sprite_set_x", 1
        )[0]
        self.assertIn("lda #$FF", reset)
        self.assertIn("ldx #$00", reset)
        self.assertIn("sta runtime_oam_shadow, x", reset)
        hide_loop = reset.split("@hide_all_sprites:", 1)[1].split(
            "bne @hide_all_sprites", 1
        )[0]
        self.assertEqual(hide_loop.count("    inx\n"), 4)

    def test_nmi_resets_oam_address_and_dmas_the_shadow_page(self) -> None:
        nmi = self.assembly.split("NMI:", 1)[1].split("IRQ:", 1)[0]
        address_reset = nmi.index("sta $2003")
        page_load = nmi.index("lda #>runtime_oam_shadow")
        dma = nmi.index("sta $4014")
        self.assertLess(address_reset, page_load)
        self.assertLess(page_load, dma)
        self.assertIn("$0200-$02FF", self.assembly)

    def test_normal_rendering_includes_the_leftmost_sprite_pixels(self) -> None:
        run = self.assembly.split("; Source: nes.run", 1)[1].split(
            "; Runtime: implicit",
            1,
        )[0]
        self.assertIn(
            "lda runtime_ppumask_shadow\n"
            "    ora #$1E\n"
            "    sta runtime_ppumask_shadow ; preserve bits and enable rendering\n"
            "    sta $2001",
            run,
        )
        position = self.assembly.split(
            "; Source: nes.sprite_set_position(...)",
            1,
        )[1].split("; Source:", 1)[0]
        self.assertIn(
            "lda #$00\n    sta runtime_sprite_value ; evaluate the property once",
            position,
        )
        self.assertIn("jsr runtime_sprite_set_position", position)

    def test_constant_indexes_use_direct_oam_offsets_including_63(self) -> None:
        source = sprite_program(
            "nes.sprite_set_x($00, $11);\n"
            "    nes.sprite_set_x($3F, $22);"
        )
        assembly = generate(resolved_source(source))
        self.assertIn("sta runtime_oam_shadow + 3", assembly)
        self.assertIn("sta runtime_oam_shadow + 252 + 3", assembly)

    def test_dynamic_index_uses_two_shifts_instead_of_multiplication(self) -> None:
        source = sprite_program(
            "Current := $3F;\n    nes.sprite_set_x(Current, $22);",
            "    Current: sprite;\n",
        )
        assembly = generate(resolved_source(source))
        routine = assembly.split("runtime_sprite_set_x:", 1)[1].split("rts", 1)[0]
        self.assertEqual(routine.count("asl a"), 2)
        self.assertNotIn("mul", routine.lower())

    def test_all_attribute_helpers_preserve_unrelated_bits(self) -> None:
        assembly = self.assembly
        self.assertIn("and #$FC", assembly)
        self.assertIn("ora #$40", assembly)
        self.assertIn("and #$BF", assembly)
        self.assertIn("ora #$80", assembly)
        self.assertIn("and #$7F", assembly)
        self.assertIn("ora #$20", assembly)
        self.assertIn("and #$DF", assembly)

    def test_raw_attributes_write_the_attribute_byte(self) -> None:
        assembly = generate(
            resolved_source(sprite_program("nes.sprite_set_attributes($00, $E3);"))
        )
        block = assembly.split("; Source: nes.sprite_set_attributes", 1)[1]
        self.assertIn("sta runtime_oam_shadow + 2", block)

    def test_hide_show_preserve_and_restore_logical_y(self) -> None:
        source = sprite_program(
            "nes.sprite_set_y($00, $40);\n"
            "    nes.sprite_show($00);\n"
            "    nes.sprite_hide($00);\n"
            "    nes.sprite_set_y($00, $50);\n"
            "    nes.sprite_show($00);"
        )
        assembly = generate(resolved_source(source))
        self.assertIn("sta runtime_sprite_logical_y", assembly)
        self.assertIn("cmp #$FF", assembly)
        self.assertIn("lda runtime_sprite_logical_y", assembly)
        self.assertIn("sta runtime_oam_shadow", assembly)

    def test_palette_combinations_keep_all_flags_available(self) -> None:
        source = sprite_program(
            "nes.sprite_set_attributes($00, $00);\n"
            "    nes.sprite_set_palette($00, $03);\n"
            "    nes.sprite_set_flip_horizontal($00, true);\n"
            "    nes.sprite_set_flip_vertical($00, true);\n"
            "    nes.sprite_set_behind_background($00, true);"
        )
        assembly = generate(resolved_source(source))
        for expected in ("ora runtime_sprite_value", "ora #$40", "ora #$80", "ora #$20"):
            self.assertIn(expected, assembly)


if __name__ == "__main__":
    unittest.main()
