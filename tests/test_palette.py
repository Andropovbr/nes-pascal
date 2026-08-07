from pathlib import Path
import unittest

from nes_pascal.ast import (
    PaletteKind,
    ResolvedSetBackgroundColor,
    ResolvedSetPalette,
    ResolvedSetPaletteColor,
    SetPalette,
    SetPaletteColor,
)
from nes_pascal.backend_ca65 import generate
from nes_pascal.diagnostics import CompilerError
from nes_pascal.memory_layout import build_memory_layout, generate_linker_config
from nes_pascal.parser import parse
from nes_pascal.semantic import analyze


def analyze_source(source: str, filename: str = "palette.nsp"):
    return analyze(parse(source, filename), source, filename)


def program_with(statements: str, declarations: str = "") -> str:
    return f"""program Palette;
{declarations}begin
{statements}
end.
"""


class PaletteParserTests(unittest.TestCase):
    def test_parses_full_and_individual_palette_calls(self) -> None:
        source = program_with(
            """    nes.set_background_palette($00, $0F, $01, $11, $21);
    nes.set_sprite_palette($03, $0F, $06, $16, $26);
    nes.set_background_palette_color($02, $03, $30);
    nes.set_sprite_palette_color($01, $02, $27);
    nes.set_background_color($0F);
    nes.run;"""
        )

        parsed = parse(source)

        self.assertIsInstance(parsed.statements[0], SetPalette)
        self.assertIsInstance(parsed.statements[1], SetPalette)
        self.assertIsInstance(parsed.statements[2], SetPaletteColor)
        self.assertIsInstance(parsed.statements[3], SetPaletteColor)
        self.assertEqual(parsed.statements[0].kind, PaletteKind.BACKGROUND)
        self.assertEqual(parsed.statements[1].kind, PaletteKind.SPRITE)


class PaletteSemanticTests(unittest.TestCase):
    def test_each_palette_diagnostic_has_a_focused_fixture(self) -> None:
        fixtures = {
            "invalid_background_palette_index.nsp": "E3031",
            "invalid_sprite_palette_index.nsp": "E3032",
            "invalid_palette_color_index.nsp": "E3033",
            "invalid_palette_argument_count.nsp": "E3034",
            "invalid_palette_argument_type.nsp": "E4007",
            "invalid_palette_color.nsp": "E4002",
        }
        directory = Path(__file__).resolve().parent / "fixtures" / "diagnostics"
        for filename, code in fixtures.items():
            with self.subTest(filename=filename):
                path = directory / filename
                source = path.read_text(encoding="utf-8")
                with self.assertRaises(CompilerError) as raised:
                    analyze_source(source, str(path))
                self.assertEqual(raised.exception.code, code)

    def test_initialization_and_runtime_calls_are_distinguished(self) -> None:
        source = program_with(
            """    Color := $30;
    nes.set_background_palette($00, $0F, $01, $11, $21);
    nes.set_background_color($0F);
    nes.run;
    nes.set_sprite_palette($03, $0F, $06, $16, Color);
    nes.set_background_palette_color($02, $03, Color);""",
            """var
    Color: nes_color;
""",
        )

        resolved = analyze_source(source)

        full = [s for s in resolved.statements if isinstance(s, ResolvedSetPalette)]
        individual = [
            s for s in resolved.statements if isinstance(s, ResolvedSetPaletteColor)
        ]
        self.assertEqual([statement.queued for statement in full], [False, True])
        self.assertTrue(individual[0].queued)

    def test_palette_calls_in_procedures_are_queued(self) -> None:
        source = program_with(
            """    Color := $21;
    nes.set_background_color($0F);
    nes.on_update(Update);
    nes.run;""",
            """var
    Color: nes_color;
procedure Update;
begin
    nes.set_background_color(Color);
    nes.set_sprite_palette_color($00, $03, Color);
end;
""",
        )

        resolved = analyze_source(source)
        palette_statements = [
            statement
            for statement in resolved.procedures[0].body
            if isinstance(
                statement,
                (ResolvedSetBackgroundColor, ResolvedSetPaletteColor),
            )
        ]
        self.assertTrue(all(statement.queued for statement in palette_statements))

    def test_nes_color_boundaries_are_accepted_by_palette_apis(self) -> None:
        source = program_with(
            """    nes.set_background_palette($00, $00, $3F, $00, $3F);
    nes.set_sprite_palette($03, $3F, $00, $3F, $00);
    nes.set_background_color($00);
    nes.run;"""
        )
        analyze_source(source)

    def test_invalid_palette_color_reuses_nes_color_diagnostic(self) -> None:
        source = program_with(
            """    nes.set_background_palette($00, $00, $40, $10, $20);
    nes.set_background_color($0F);
    nes.run;"""
        )
        with self.assertRaises(CompilerError) as raised:
            analyze_source(source)
        self.assertEqual(raised.exception.code, "E4002")
        self.assertIn("$00..$3F", str(raised.exception))

    def test_negative_byte_expression_is_not_implicitly_a_nes_color(self) -> None:
        source = program_with(
            """    nes.set_background_palette_color($00, $01, -$01);
    nes.set_background_color($0F);
    nes.run;"""
        )
        with self.assertRaises(CompilerError) as raised:
            analyze_source(source)
        self.assertEqual(raised.exception.code, "E4007")

    def test_palette_index_boundaries_and_color_index_boundaries_are_accepted(self) -> None:
        source = program_with(
            """    nes.set_background_palette($00, $0F, $01, $11, $21);
    nes.set_sprite_palette($03, $0F, $06, $16, $26);
    nes.set_background_palette_color($03, $00, $30);
    nes.set_sprite_palette_color($00, $03, $27);
    nes.set_background_color($0F);
    nes.run;"""
        )
        analyze_source(source)

    def test_invalid_background_and_sprite_palette_indexes_are_distinct(self) -> None:
        calls = (
            ("nes.set_background_palette($04, $0F, $01, $11, $21);", "E3031"),
            ("nes.set_sprite_palette($04, $0F, $01, $11, $21);", "E3032"),
        )
        for call, code in calls:
            with self.subTest(call=call):
                source = program_with(
                    f"    {call}\n    nes.set_background_color($0F);\n    nes.run;"
                )
                with self.assertRaises(CompilerError) as raised:
                    analyze_source(source)
                self.assertEqual(raised.exception.code, code)

    def test_invalid_color_index_is_rejected(self) -> None:
        source = program_with(
            """    nes.set_sprite_palette_color($00, $04, $21);
    nes.set_background_color($0F);
    nes.run;"""
        )
        with self.assertRaises(CompilerError) as raised:
            analyze_source(source)
        self.assertEqual(raised.exception.code, "E3033")

    def test_dynamic_palette_index_is_rejected_by_the_fixed_builtin_model(self) -> None:
        source = program_with(
            """    Index := $00;
    nes.set_background_palette(Index, $0F, $01, $11, $21);
    nes.set_background_color($0F);
    nes.run;""",
            """var
    Index: byte;
""",
        )
        with self.assertRaises(CompilerError) as raised:
            analyze_source(source)
        self.assertEqual(raised.exception.code, "E3031")
        self.assertIn("compile-time", str(raised.exception))

    def test_wrong_argument_counts_are_rejected(self) -> None:
        calls = (
            "nes.set_background_palette($00, $0F, $01, $11);",
            "nes.set_sprite_palette_color($00, $01);",
        )
        for call in calls:
            with self.subTest(call=call):
                source = program_with(
                    f"    {call}\n    nes.set_background_color($0F);\n    nes.run;"
                )
                with self.assertRaises(CompilerError) as raised:
                    analyze_source(source)
                self.assertEqual(raised.exception.code, "E3034")

    def test_wrong_index_and_color_types_are_rejected(self) -> None:
        sources = (
            program_with(
                """    nes.set_background_palette(true, $0F, $01, $11, $21);
    nes.set_background_color($0F);
    nes.run;"""
            ),
            program_with(
                """    Value := $01;
    nes.set_sprite_palette($00, $0F, Value, $11, $21);
    nes.set_background_color($0F);
    nes.run;""",
                """var
    Value: byte;
""",
            ),
        )
        for source in sources:
            with self.subTest(source=source):
                with self.assertRaises(CompilerError) as raised:
                    analyze_source(source)
                self.assertEqual(raised.exception.code, "E4007")


class PaletteBackendAndMemoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = program_with(
            """    Color := $30;
    nes.set_background_palette($01, $0F, $01, $11, $21);
    nes.set_sprite_palette($02, $0F, $06, $16, $26);
    nes.set_background_palette_color($03, $02, $27);
    nes.set_background_color($0F);
    nes.on_update(Update);
    nes.on_vblank(VBlank);
    nes.run;
    nes.set_background_color(Color);""",
            """var
    Color: nes_color;
procedure Update;
begin
    nes.set_background_palette($03, $16, $06, $17, $27);
    nes.set_sprite_palette_color($00, $03, Color);
end;
procedure VBlank;
begin
    nes.set_background_palette_color($00, $01, Color);
end;
""",
        )
        cls.program = analyze_source(cls.source)
        cls.layout = build_memory_layout(cls.program)
        cls.assembly = generate(cls.program, cls.layout)

    def test_initialization_writes_correct_addresses_before_rendering(self) -> None:
        initialization = self.assembly.split("; Source: nes.set_background_palette", 1)[1]
        initialization = initialization.split("; Source: nes.run", 1)[0]
        self.assertIn("lda #$00\n    sta $2006", initialization)
        self.assertIn("lda #$05\n    sta $2006", initialization)
        self.assertIn("lda #$19\n    sta $2006", initialization)
        self.assertIn("lda #$0E\n    sta $2006", initialization)
        self.assertNotIn("sta $2001", initialization)

    def test_runtime_paths_only_stage_ram_and_nmi_owns_ppu_writes(self) -> None:
        runtime_call = self.assembly.split(
            "; Source: nes.set_background_color(value)", 2
        )[2].split("; Runtime: frame-synchronized", 1)[0]
        self.assertIn("runtime_palette_universal_dirty", runtime_call)
        self.assertNotIn("$2006", runtime_call)
        self.assertNotIn("$2007", runtime_call)
        nmi = self.assembly.split("NMI:", 1)[1].split("IRQ:", 1)[0]
        self.assertEqual(nmi.count("jsr runtime_upload_queued_palettes"), 1)
        self.assertLess(
            nmi.index("jsr runtime_upload_queued_palettes"),
            nmi.index("jsr procedure_VBlank"),
        )

    def test_uploader_consumes_dirty_state_and_skips_unchanged_palettes(self) -> None:
        uploader = self.assembly.split("runtime_upload_queued_palettes:", 1)[1]
        uploader = uploader.split("; Source: procedure declarations", 1)[0]
        self.assertIn("beq @skip_background_palette_0", uploader)
        self.assertIn("sta runtime_palette_background_0_dirty", uploader)
        self.assertIn("beq @skip_sprite_palette_3", uploader)
        self.assertIn("sta runtime_palette_universal_dirty", uploader)
        self.assertEqual(uploader.count("jsr runtime_upload_palette_triplet"), 8)

    def test_nmi_restores_compiler_owned_ppu_state_after_uploader(self) -> None:
        run_setup = self.assembly.split("; Source: nes.run", 1)[1]
        run_setup = run_setup.split("; Runtime: frame-synchronized", 1)[0]
        self.assertIn(
            "lda runtime_ppuctrl_shadow\n"
            "    ora #$80\n"
            "    sta runtime_ppuctrl_shadow ; preserve bits and enable NMI",
            run_setup,
        )
        nmi = self.assembly.split("NMI:", 1)[1].split("IRQ:", 1)[0]
        self.assertLess(nmi.index("jsr procedure_VBlank"), nmi.index("lda runtime_ppuctrl_shadow"))
        self.assertIn("lda runtime_ppuctrl_shadow\n    sta $2000", nmi)
        self.assertIn("lda runtime_scroll_x_shadow\n    sta $2005", nmi)
        self.assertIn("lda runtime_scroll_y_shadow\n    sta $2005", nmi)
        self.assertIn("lda runtime_ppumask_shadow\n    sta $2001", nmi)

    def test_runtime_publication_invalidates_before_staging_and_publishes_last(self) -> None:
        procedure = self.assembly.split("procedure_Update:", 1)[1].split("    rts", 1)[0]
        dirty = "runtime_palette_background_3_dirty"
        self.assertLess(procedure.index(f"sta {dirty}"), procedure.index("sta runtime_palette_shadow"))
        self.assertLess(procedure.index("sta runtime_palette_shadow"), procedure.rindex(f"sta {dirty}"))

    def test_palette_runtime_state_uses_regular_ram_without_overlap(self) -> None:
        symbols = {symbol.assembly_symbol: symbol for symbol in self.layout.runtime_symbols}
        shadow = symbols["runtime_palette_shadow"]
        self.assertEqual(shadow.size, 32)
        self.assertEqual(shadow.region_name, self.layout.runtime_data.name)
        self.assertEqual(self.layout.runtime_data.size, 45)
        self.assertEqual(
            symbols["runtime_ppuctrl_shadow"].address,
            shadow.address + 41,
        )
        self.assertEqual(
            symbols["runtime_ppumask_shadow"].address,
            shadow.address + 42,
        )
        self.assertEqual(
            symbols["runtime_scroll_x_shadow"].address,
            shadow.address + 43,
        )
        self.assertEqual(symbols["runtime_scroll_y_shadow"].address, shadow.address + 44)
        addresses = [
            (symbol.address, symbol.address + symbol.size)
            for symbol in self.layout.runtime_symbols
            if symbol.region_name == self.layout.runtime_data.name
        ]
        self.assertEqual(addresses, sorted(addresses))
        for previous, current in zip(addresses, addresses[1:]):
            self.assertLessEqual(previous[1], current[0])

    def test_linker_output_remains_deterministic(self) -> None:
        second = build_memory_layout(analyze_source(self.source))
        self.assertEqual(
            generate_linker_config(self.layout),
            generate_linker_config(second),
        )

    def test_fixed_sprite_default_palette_seeds_runtime_shadow_when_needed(self) -> None:
        source = program_with(
            """    nes.set_background_color($21);
    nes.set_sprite_zero($78, $70, $01, $00);
    nes.run;
    nes.set_sprite_palette_color($00, $03, $20);"""
        )
        program = analyze_source(source)
        assembly = generate(program, build_memory_layout(program))

        self.assertIn("sta runtime_palette_shadow + 17", assembly)
        self.assertIn("sta runtime_palette_shadow + 18", assembly)
        self.assertIn("sta runtime_palette_shadow + 19", assembly)


if __name__ == "__main__":
    unittest.main()
