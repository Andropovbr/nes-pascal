from pathlib import Path
import tempfile
import unittest

from nes_pascal.ast import (
    BackgroundUpdatesOverflowed,
    ClearBackgroundUpdateOverflow,
    ClearBackgroundUpdates,
    GetTile,
    ResolvedBackgroundUpdatesOverflowed,
    ResolvedClearBackgroundUpdateOverflow,
    ResolvedClearBackgroundUpdates,
    ResolvedGetTile,
    ResolvedSetAttribute,
    ResolvedSetTile,
    SetAttribute,
    SetTile,
)
from nes_pascal.backend_ca65 import generate
from nes_pascal.cli import compile_source
from nes_pascal.diagnostics import CompilerError
from nes_pascal.memory_layout import (
    build_memory_layout,
    generate_linker_config,
    generate_memory_map,
)
from nes_pascal.parser import parse
from nes_pascal.semantic import analyze


ROOT = Path(__file__).resolve().parents[1]


SOURCE = """program BackgroundUpdates;
var
    X: byte;
    Y: byte;
    Tile: byte;
    Overflowed: boolean;
begin
    X := $01;
    Y := $02;
    Tile := $03;
    nes.set_background_color($0F);
    nes.run;
    nes.set_tile(X, Y, Tile);
    Tile := nes.get_tile(X, Y);
    nes.set_attribute($00, $00, $E4);
    Overflowed := nes.background_updates_overflowed();
    nes.clear_background_updates();
    nes.clear_background_update_overflow();
end.
"""


def analyze_source(source: str = SOURCE, filename: str = "background_updates.nsp"):
    return analyze(parse(source, filename), source, filename)


class BackgroundUpdateLanguageTests(unittest.TestCase):
    def test_parser_and_semantic_model_all_background_update_operations(self) -> None:
        parsed = parse(SOURCE)
        self.assertIsInstance(parsed.statements[5], SetTile)
        assignment = parsed.statements[6]
        self.assertIsInstance(assignment.value, GetTile)
        self.assertIsInstance(parsed.statements[7], SetAttribute)
        overflow_assignment = parsed.statements[8]
        self.assertIsInstance(
            overflow_assignment.value, BackgroundUpdatesOverflowed
        )
        self.assertIsInstance(parsed.statements[9], ClearBackgroundUpdates)
        self.assertIsInstance(
            parsed.statements[10], ClearBackgroundUpdateOverflow
        )

        resolved = analyze_source()
        self.assertIsInstance(resolved.statements[5], ResolvedSetTile)
        self.assertIsInstance(resolved.statements[6].value, ResolvedGetTile)
        self.assertIsInstance(resolved.statements[7], ResolvedSetAttribute)
        self.assertIsInstance(
            resolved.statements[8].value,
            ResolvedBackgroundUpdatesOverflowed,
        )
        self.assertIsInstance(
            resolved.statements[9], ResolvedClearBackgroundUpdates
        )
        self.assertIsInstance(
            resolved.statements[10], ResolvedClearBackgroundUpdateOverflow
        )

    def test_dynamic_coordinates_and_boundaries_are_accepted(self) -> None:
        source = SOURCE.replace(
            "nes.set_tile(X, Y, Tile);",
            "nes.set_tile($1F, $1D, Tile);",
        ).replace(
            "nes.set_attribute($00, $00, $E4);",
            "nes.set_attribute($07, $07, $E4);",
        )
        analyze_source(source)

    def test_invalid_forms_have_stable_focused_diagnostics(self) -> None:
        fixtures = {
            "set_tile_argument_count.nsp": "E3038",
            "get_tile_argument_count.nsp": "E3039",
            "set_attribute_argument_count.nsp": "E3040",
            "clear_background_updates_argument_count.nsp": "E3041",
            "invalid_tile_coordinate.nsp": "E3042",
            "invalid_attribute_coordinate.nsp": "E3043",
            "background_updates_overflowed_argument_count.nsp": "E3044",
            "clear_background_update_overflow_argument_count.nsp": "E3045",
        }
        directory = Path(__file__).resolve().parent / "fixtures" / "diagnostics"
        for filename, expected_code in fixtures.items():
            with self.subTest(filename=filename):
                path = directory / filename
                source = path.read_text(encoding="utf-8")
                with self.assertRaises(CompilerError) as raised:
                    analyze_source(source, str(path))
                self.assertEqual(raised.exception.code, expected_code)

    def test_background_update_values_require_exact_byte_types(self) -> None:
        source = SOURCE.replace(
            "nes.set_tile(X, Y, Tile);", "nes.set_tile(true, Y, Tile);"
        )
        with self.assertRaises(CompilerError) as raised:
            analyze_source(source)
        self.assertEqual(raised.exception.code, "E4004")

    def test_get_tile_is_rejected_on_a_vblank_callback_path(self) -> None:
        source = """program UnsafeTileRead;
var
    Tile: byte;
procedure VBlank;
begin
    Tile := nes.get_tile($00, $00);
end;
begin
    Tile := $00;
    nes.set_background_color($0F);
    nes.on_vblank(VBlank);
    nes.run;
end.
"""
        with self.assertRaises(CompilerError) as raised:
            analyze_source(source)
        self.assertEqual(raised.exception.code, "E3023")
        self.assertIn("nes.get_tile", str(raised.exception))


class BackgroundUpdateBackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.program = analyze_source()
        cls.layout = build_memory_layout(cls.program)
        cls.assembly = generate(cls.program, cls.layout)

    def test_fixed_queue_and_shadow_use_deterministic_storage(self) -> None:
        symbols = {
            symbol.assembly_symbol: symbol
            for symbol in self.layout.runtime_symbols
        }
        self.assertEqual(symbols["runtime_background_shadow"].size, 960)
        for field in ("ready", "high", "low", "value"):
            self.assertEqual(symbols[f"runtime_background_queue_{field}"].size, 4)
        self.assertEqual(symbols["runtime_background_queue_overflow"].size, 1)
        self.assertEqual(symbols["runtime_background_queue_cancel_lock"].size, 1)
        self.assertEqual(self.layout.runtime_data.size, 987)
        self.assertGreaterEqual(self.layout.user_capacity.start, 0x0200 + 987)

    def test_queue_publishes_last_limits_to_four_and_marks_overflow(self) -> None:
        routine = self.assembly.split("runtime_queue_background_write:", 1)[1]
        routine = routine.split("runtime_prepare_tile_index:", 1)[0]
        self.assertIn("cpx #$04", routine)
        self.assertIn("sta runtime_background_queue_overflow", routine)
        self.assertLess(
            routine.index("sta runtime_background_queue_value, x"),
            routine.index("sta runtime_background_queue_ready, x ; atomic"),
        )

    def test_nmi_consumes_each_slot_once_before_user_vblank_work(self) -> None:
        nmi = self.assembly.split("NMI:", 1)[1].split("IRQ:", 1)[0]
        self.assertEqual(nmi.count("jsr runtime_upload_queued_background"), 1)
        uploader = self.assembly.split("runtime_upload_queued_background:", 1)[1]
        uploader = uploader.split("runtime_queue_background_write:", 1)[0]
        self.assertIn("sta runtime_background_queue_ready, x", uploader)
        self.assertIn("sta $2007", uploader)
        self.assertNotIn("lda runtime_ppuctrl_shadow", uploader)
        self.assertIn("lda runtime_ppuctrl_shadow", nmi)
        self.assertIn("lda runtime_scroll_x_shadow", nmi)
        self.assertIn("lda runtime_scroll_y_shadow", nmi)
        self.assertLess(
            uploader.index("sta $2007"),
            uploader.index("sta runtime_background_shadow"),
        )

    def test_get_tile_reads_shadow_and_dynamic_invalid_values_return_zero(self) -> None:
        get_tile = self.assembly.split("runtime_get_tile:", 1)[1]
        get_tile = get_tile.split("runtime_set_attribute:", 1)[0]
        self.assertEqual(get_tile.count("runtime_background_shadow"), 4)
        self.assertIn("@get_tile_invalid:\n    lda #$00", get_tile)

    def test_pending_cancellation_and_overflow_clear_are_separate(self) -> None:
        clear = self.assembly.split(
            "; Source: nes.clear_background_updates()", 1
        )[1].split("; Source: nes.clear_background_update_overflow()", 1)[0]
        self.assertEqual(clear.count("runtime_background_queue_ready"), 4)
        self.assertNotIn("runtime_background_queue_overflow", clear)
        self.assertEqual(clear.count("sta runtime_background_queue_cancel_lock"), 2)
        self.assertLess(
            clear.index("sta runtime_background_queue_cancel_lock"),
            clear.index("sta runtime_background_queue_ready"),
        )
        self.assertLess(
            clear.rindex("sta runtime_background_queue_ready"),
            clear.rindex("sta runtime_background_queue_cancel_lock"),
        )
        overflow_clear = self.assembly.split(
            "; Source: nes.clear_background_update_overflow()", 1
        )[1].split("; Runtime: implicit", 1)[0]
        self.assertIn("sta runtime_background_queue_overflow", overflow_clear)

    def test_nmi_checks_cancel_lock_before_reading_any_queue_slot(self) -> None:
        uploader = self.assembly.split("runtime_upload_queued_background:", 1)[1]
        uploader = uploader.split("runtime_queue_background_write:", 1)[0]
        self.assertLess(
            uploader.index("lda runtime_background_queue_cancel_lock"),
            uploader.index("lda runtime_background_queue_ready, x"),
        )
        self.assertIn(
            "bne @background_upload_locked ; cancellation owns the whole queue",
            uploader,
        )
        self.assertGreater(
            uploader.index("@background_upload_locked:"),
            uploader.index("sta runtime_background_queue_ready, x"),
        )

    def test_rejected_update_never_changes_shadow_in_main_context(self) -> None:
        set_tile = self.assembly.split("runtime_set_tile:", 1)[1]
        set_tile = set_tile.split("runtime_set_attribute:", 1)[0]
        self.assertNotIn("runtime_background_shadow", set_tile)
        queue = self.assembly.split("runtime_queue_background_write:", 1)[1]
        queue = queue.split("runtime_prepare_tile_index:", 1)[0]
        self.assertIn("sec                     ; rejected", queue)
        self.assertIn("clc                     ; accepted", queue)

    def test_shadow_is_omitted_for_write_only_background_updates(self) -> None:
        from tools.measure_benchmarks import measure_memory_accounting

        source = """program WriteOnlyBackground;
begin
    nes.set_background_color($0F);
    nes.run;
    nes.set_tile($00, $00, $01);
    nes.set_attribute($00, $00, $E4);
end.
"""
        program = analyze_source(source)
        layout = build_memory_layout(program)
        names = {symbol.assembly_symbol for symbol in layout.runtime_symbols}
        self.assertNotIn("runtime_background_shadow", names)
        self.assertIn("runtime_background_queue_ready", names)
        self.assertEqual(layout.runtime_data.size, 26)
        accounting = measure_memory_accounting(layout)
        self.assertEqual(accounting.regular_runtime_user_allocated_bytes, 26)
        self.assertEqual(accounting.oam_shadow_allocated_bytes, 0)
        self.assertEqual(accounting.regular_allocator_visible_free_bytes, 1510)
        self.assertEqual(accounting.zp_allocator_visible_free_bytes, 128)
        self.assertEqual(accounting.total_allocator_visible_free_bytes, 1638)
        self.assertEqual(
            accounting.total_committed_or_reserved_address_space_bytes,
            410,
        )
        assembly = generate(program, layout)
        self.assertNotIn("runtime_background_shadow", assembly)
        self.assertNotIn("runtime_background_queue_cancel_lock", assembly)
        report = generate_memory_map(layout)
        self.assertIn("runtime_background_queue_ready", report)
        self.assertNotIn("runtime_background_shadow", report)

    def test_tile_only_write_emits_only_its_reachable_runtime(self) -> None:
        source = """program TileOnly;
begin
    nes.set_background_color($0F);
    nes.run;
    nes.set_tile($00, $00, $01);
end.
"""
        program = analyze_source(source)
        layout = build_memory_layout(program)
        assembly = generate(program, layout)
        report = generate_memory_map(layout)

        self.assertEqual(layout.runtime_data.size, 26)
        self.assertIn("runtime_upload_queued_background:", assembly)
        self.assertIn("runtime_queue_background_write:", assembly)
        self.assertIn("runtime_prepare_tile_index:", assembly)
        self.assertIn("runtime_set_tile:", assembly)
        self.assertNotIn("runtime_set_attribute:", assembly)
        self.assertNotIn("runtime_get_tile:", assembly)
        self.assertNotIn("runtime_background_shadow", assembly)
        self.assertNotIn("runtime_background_queue_cancel_lock", assembly)
        self.assertNotIn("cancellation owns the whole queue", assembly)
        self.assertNotIn("runtime_oam_shadow", assembly)
        self.assertIn("computed nametable tile offset", report)
        self.assertNotIn("tile-shadow", report)

    def test_attribute_only_write_omits_tile_and_cancellation_helpers(self) -> None:
        source = """program AttributeOnly;
begin
    nes.set_background_color($0F);
    nes.run;
    nes.set_attribute($00, $00, $E4);
end.
"""
        program = analyze_source(source)
        layout = build_memory_layout(program)
        assembly = generate(program, layout)

        self.assertEqual(layout.runtime_data.size, 24)
        self.assertIn("runtime_upload_queued_background:", assembly)
        self.assertIn("runtime_queue_background_write:", assembly)
        self.assertIn("runtime_set_attribute:", assembly)
        self.assertNotIn("runtime_prepare_tile_index:", assembly)
        self.assertNotIn("runtime_set_tile:", assembly)
        self.assertNotIn("runtime_get_tile:", assembly)
        self.assertNotIn("runtime_background_index_low", assembly)
        self.assertNotIn("runtime_background_queue_cancel_lock", assembly)

    def test_read_write_tile_runtime_omits_unrelated_attribute_and_lock(self) -> None:
        source = """program ReadWriteTile;
var
    Tile: byte;
begin
    nes.set_background_color($0F);
    nes.run;
    nes.set_tile($00, $00, $01);
    Tile := nes.get_tile($00, $00);
end.
"""
        program = analyze_source(source)
        layout = build_memory_layout(program)
        assembly = generate(program, layout)

        self.assertEqual(layout.runtime_data.size, 986)
        self.assertIn("runtime_background_shadow", assembly)
        self.assertIn("sta runtime_background_shadow", assembly)
        self.assertIn("runtime_set_tile:", assembly)
        self.assertIn("runtime_get_tile:", assembly)
        self.assertNotIn("runtime_set_attribute:", assembly)
        self.assertNotIn("runtime_background_queue_cancel_lock", assembly)

    def test_cancellation_alone_retains_atomic_lock_check(self) -> None:
        source = """program CancelTile;
begin
    nes.set_background_color($0F);
    nes.run;
    nes.set_tile($00, $00, $01);
    nes.clear_background_updates();
end.
"""
        program = analyze_source(source)
        layout = build_memory_layout(program)
        assembly = generate(program, layout)

        self.assertEqual(layout.runtime_data.size, 27)
        self.assertIn("runtime_background_queue_cancel_lock", assembly)
        self.assertIn("cancellation owns the whole queue", assembly)
        self.assertEqual(
            assembly.count("sta runtime_background_queue_cancel_lock"),
            2,
        )
        self.assertNotIn("runtime_set_attribute:", assembly)
        self.assertNotIn("runtime_get_tile:", assembly)

    def test_overflow_only_apis_allocate_only_the_sticky_flag(self) -> None:
        source = """program OverflowOnly;
var
    Overflowed: boolean;
begin
    nes.set_background_color($0F);
    nes.run;
    Overflowed := nes.background_updates_overflowed();
    nes.clear_background_update_overflow();
end.
"""
        program = analyze_source(source)
        layout = build_memory_layout(program)
        assembly = generate(program, layout)
        names = {symbol.assembly_symbol for symbol in layout.runtime_symbols}

        self.assertEqual(layout.runtime_data.size, 5)
        self.assertIn("runtime_background_queue_overflow", names)
        self.assertNotIn("runtime_background_queue_ready", names)
        self.assertNotIn("runtime_background_queue_cancel_lock", names)
        self.assertNotIn("runtime_upload_queued_background:", assembly)
        self.assertNotIn("runtime_queue_background_write:", assembly)
        self.assertNotIn("runtime_prepare_tile_index:", assembly)
        self.assertNotIn("runtime_set_tile:", assembly)
        self.assertNotIn("runtime_set_attribute:", assembly)
        self.assertNotIn("runtime_get_tile:", assembly)
        self.assertNotIn("runtime_oam_shadow", assembly)

    def test_each_overflow_api_omits_queue_and_cancellation_support(self) -> None:
        sources = {
            "inspect": """program InspectOverflow;
var
    Overflowed: boolean;
begin
    nes.set_background_color($0F);
    nes.run;
    Overflowed := nes.background_updates_overflowed();
end.
""",
            "clear": """program ClearOverflow;
begin
    nes.set_background_color($0F);
    nes.run;
    nes.clear_background_update_overflow();
end.
""",
        }
        for name, source in sources.items():
            with self.subTest(api=name):
                program = analyze_source(source)
                layout = build_memory_layout(program)
                assembly = generate(program, layout)
                symbols = {
                    symbol.assembly_symbol for symbol in layout.runtime_symbols
                }
                self.assertEqual(layout.runtime_data.size, 5)
                self.assertIn("runtime_background_queue_overflow", symbols)
                self.assertNotIn("runtime_background_queue_ready", symbols)
                self.assertNotIn(
                    "runtime_background_queue_cancel_lock",
                    symbols,
                )
                self.assertNotIn("runtime_upload_queued_background:", assembly)

    def test_get_tile_only_links_shadow_without_queue_or_nmi_uploader(self) -> None:
        source = """program ReadOnlyBackground;
var
    Tile: byte;
begin
    nes.set_background_color($0F);
    nes.run;
    Tile := nes.get_tile($00, $00);
end.
"""
        program = analyze_source(source)
        layout = build_memory_layout(program)
        names = {symbol.assembly_symbol for symbol in layout.runtime_symbols}
        self.assertIn("runtime_background_shadow", names)
        self.assertNotIn("runtime_background_queue_ready", names)
        self.assertEqual(layout.runtime_data.size, 968)
        report = generate_memory_map(layout)
        self.assertIn("runtime_background_shadow", report)
        self.assertNotIn("runtime_background_queue_ready", report)
        assembly = generate(program, layout)
        self.assertNotIn("runtime_upload_queued_background", assembly)
        self.assertIn(
            "Runtime: establish a zeroed nametable matching the confirmed shadow",
            assembly,
        )
        initialization = assembly.split(
            "Runtime: establish a zeroed nametable matching the confirmed shadow",
            1,
        )[1].split("; Source: nes.set_background_color", 1)[0]
        self.assertEqual(initialization.count("sta $2007"), 4)

    def test_loaded_background_initializes_960_byte_tile_shadow(self) -> None:
        source = SOURCE.replace(
            "    nes.set_background_color($0F);",
            "    nes.load_background();\n    nes.set_background_color($0F);",
        )
        program = analyze_source(source)
        data = bytes(range(256)) * 4
        assembly = generate(program, build_memory_layout(program), background_data=data)
        upload = assembly.split("; Source: nes.load_background()", 1)[1]
        upload = upload.split("; Source: nes.set_background_color", 1)[0]
        self.assertEqual(upload.count("sta $2007"), 5)
        self.assertEqual(upload.count("sta runtime_background_shadow"), 4)
        self.assertIn("cpx #$C0", upload)

    def test_assembly_and_linker_configuration_are_deterministic(self) -> None:
        second_layout = build_memory_layout(analyze_source())
        self.assertEqual(generate(analyze_source(), second_layout), self.assembly)
        self.assertEqual(
            generate_linker_config(self.layout),
            generate_linker_config(second_layout),
        )

    def test_nested_get_tile_expressions_balance_argument_staging(self) -> None:
        source = SOURCE.replace(
            "Tile := nes.get_tile(X, Y);",
            "Tile := nes.get_tile(nes.get_tile($00, $00), Y) + $01;",
        )
        assembly = generate(analyze_source(source))
        self.assertEqual(assembly.count("jsr runtime_get_tile"), 2)


class BackgroundUpdateIntegrationTests(unittest.TestCase):
    def test_focused_loaded_background_programs_compile(self) -> None:
        cases = {
            "tile_only": {
                "runtime_size": "$001A",
                "present": ("runtime_set_tile:",),
                "absent": (
                    "runtime_set_attribute:",
                    "runtime_get_tile:",
                    "runtime_background_queue_cancel_lock",
                    "runtime_oam_shadow",
                ),
            },
            "attribute_only": {
                "runtime_size": "$0018",
                "present": ("runtime_set_attribute:",),
                "absent": (
                    "runtime_set_tile:",
                    "runtime_get_tile:",
                    "runtime_background_queue_cancel_lock",
                    "runtime_oam_shadow",
                ),
            },
            "tile_cancellation": {
                "runtime_size": "$001B",
                "present": (
                    "runtime_set_tile:",
                    "runtime_background_queue_cancel_lock",
                    "cancellation owns the whole queue",
                ),
                "absent": (
                    "runtime_set_attribute:",
                    "runtime_get_tile:",
                    "runtime_oam_shadow",
                ),
            },
        }
        fixture_directory = ROOT / "tests" / "fixtures" / "background_updates"
        nametable_path = ROOT / "examples" / "assets" / "nametable_loading.nam"

        with tempfile.TemporaryDirectory() as temporary_directory:
            output_directory = Path(temporary_directory)
            for name, expected in cases.items():
                with self.subTest(program=name):
                    rom_path = output_directory / f"{name}.nes"
                    assembly_path, _ = compile_source(
                        fixture_directory / f"{name}.nsp",
                        rom_path,
                        nametable_path=nametable_path,
                    )
                    assembly = assembly_path.read_text(encoding="utf-8")
                    config = rom_path.with_suffix(".cfg").read_text(
                        encoding="utf-8"
                    )
                    rom = rom_path.read_bytes()

                    self.assertEqual(rom[:6], b"NES\x1a\x02\x01")
                    self.assertEqual(len(rom), 16 + 32768 + 8192)
                    self.assertIn(
                        f"RUNTIME: start = $0200, size = {expected['runtime_size']}",
                        config,
                    )
                    for text in expected["present"]:
                        self.assertIn(text, assembly)
                    for text in expected["absent"]:
                        self.assertNotIn(text, assembly)

    def test_compiler_builds_a_valid_nrom_with_runtime_background_updates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            source_path = directory / "updates.nsp"
            rom_path = directory / "updates.nes"
            source_path.write_text(SOURCE, encoding="utf-8")
            compile_source(source_path, rom_path)
            rom = rom_path.read_bytes()
        self.assertEqual(rom[:6], b"NES\x1a\x02\x01")
        self.assertEqual(len(rom), 16 + 32768 + 8192)


if __name__ == "__main__":
    unittest.main()
