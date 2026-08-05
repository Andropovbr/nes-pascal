import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from nes_pascal.assets import (
    ATTRIBUTE_TABLE_SIZE,
    NAMETABLE_TILE_SIZE,
    NROM_CHR_ROM_SIZE,
)
from nes_pascal.cli import compile_source
from nes_pascal.memory_layout import MemoryLayoutSettings


ROOT = Path(__file__).resolve().parents[1]
TOOLCHAIN_AVAILABLE = (
    shutil.which("ca65") is not None
    and shutil.which("ld65") is not None
)


def _mesen_executable() -> Path | None:
    configured = os.environ.get("MESEN_PATH")
    if configured is None:
        return None
    path = Path(configured)
    if path.is_file():
        return path
    if path.is_dir():
        for name in ("Mesen.exe", "Mesen"):
            candidate = path / name
            if candidate.is_file():
                return candidate
    return None


MESEN_EXECUTABLE = _mesen_executable()


@unittest.skipUnless(
    TOOLCHAIN_AVAILABLE,
    "integration skipped: ca65 and/or ld65 are not installed",
)
class ToolchainIntegrationTests(unittest.TestCase):
    def _assert_valid_nrom_image(
        self,
        example_name: str,
        expected_vectors: tuple[int, int, int] = (0x8000, 0x8012, 0x8011),
        expected_empty_chr: bool = True,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            rom_path = Path(temporary_directory) / f"{example_name}.nes"
            compile_source(ROOT / "examples" / f"{example_name}.nsp", rom_path)
            rom = rom_path.read_bytes()

        self.assertEqual(rom[:4], b"NES\x1a")
        self.assertEqual(rom[4], 2, "header must declare 32 KiB of PRG-ROM")
        self.assertEqual(rom[5], 1, "header must declare 8 KiB of CHR-ROM")
        self.assertEqual(rom[6] & 0xF0, 0, "lower mapper bits must be zero")
        self.assertEqual(rom[7] & 0xF0, 0, "upper mapper bits must be zero")
        self.assertEqual(len(rom), 16 + 32 * 1024 + 8 * 1024)
        if expected_empty_chr:
            self.assertEqual(rom[-8 * 1024 :], bytes(8 * 1024))
        else:
            self.assertNotEqual(rom[-8 * 1024 :], bytes(8 * 1024))

        vector_offset = 16 + 0x7FFA
        nmi = int.from_bytes(rom[vector_offset : vector_offset + 2], "little")
        reset = int.from_bytes(rom[vector_offset + 2 : vector_offset + 4], "little")
        irq = int.from_bytes(rom[vector_offset + 4 : vector_offset + 6], "little")
        self.assertEqual((nmi, reset, irq), expected_vectors)

    def test_builds_valid_minimal_nrom_image(self) -> None:
        self._assert_valid_nrom_image("minimal")

    def test_builds_valid_arithmetic_nrom_image(self) -> None:
        self._assert_valid_nrom_image("arithmetic")

    def test_builds_valid_boolean_expressions_nrom_image(self) -> None:
        self._assert_valid_nrom_image("boolean_expressions")

    def test_builds_valid_conditionals_nrom_image(self) -> None:
        self._assert_valid_nrom_image("conditionals")

    def test_loop_example_builds_valid_nrom_image(self) -> None:
        self._assert_valid_nrom_image("loops")

    def test_counting_example_builds_valid_nrom_image(self) -> None:
        self._assert_valid_nrom_image("counting")

    def test_procedure_example_builds_valid_nrom_image(self) -> None:
        self._assert_valid_nrom_image("procedures")

    def test_procedure_parameter_example_builds_valid_nrom_image(self) -> None:
        self._assert_valid_nrom_image("procedure_parameters")

    def test_memory_layout_example_builds_valid_nrom_image(self) -> None:
        self._assert_valid_nrom_image("memory_layout")

    def test_zero_page_example_builds_valid_nrom_image(self) -> None:
        self._assert_valid_nrom_image("zero_page")

    def test_frame_synchronization_example_builds_valid_nrom_image(self) -> None:
        self._assert_valid_nrom_image("frame_synchronization")

    def test_frame_callbacks_example_builds_valid_nrom_image(self) -> None:
        self._assert_valid_nrom_image(
            "frame_callbacks",
            expected_vectors=(0x8000, 0x8015, 0x8014),
        )

    def test_slow_update_callback_example_builds_valid_nrom_image(self) -> None:
        self._assert_valid_nrom_image("slow_update_callback")

    def test_controller_input_example_builds_with_player_chr_asset(self) -> None:
        self._assert_valid_nrom_image(
            "controller_input",
            expected_vectors=(0x8000, 0x803E, 0x803D),
            expected_empty_chr=False,
        )

    def test_configured_chr_asset_is_included_unchanged_and_reproducibly(self) -> None:
        source = """program ChrAsset;
begin
    nes.set_background_color($21);
    nes.run;
end.
"""
        expected_chr = bytes(range(256)) * 32
        with tempfile.TemporaryDirectory() as temporary_directory:
            project = Path(temporary_directory) / "project"
            source_directory = project / "source"
            asset_directory = project / "assets"
            output_directory = project / "build"
            unrelated_cwd = Path(temporary_directory) / "unrelated"
            source_directory.mkdir(parents=True)
            asset_directory.mkdir()
            unrelated_cwd.mkdir()
            source_path = source_directory / "main.nsp"
            source_path.write_text(source, encoding="utf-8")
            (asset_directory / "tiles.chr").write_bytes(expected_chr)
            first_rom = output_directory / "first.nes"
            second_rom = output_directory / "second.nes"

            previous_cwd = Path.cwd()
            try:
                os.chdir(unrelated_cwd)
                compile_source(
                    source_path,
                    first_rom,
                    chr_path="../assets/./tiles.chr",
                )
                compile_source(
                    source_path,
                    second_rom,
                    chr_path="../assets/./tiles.chr",
                )
            finally:
                os.chdir(previous_cwd)

            first_bytes = first_rom.read_bytes()
            second_bytes = second_rom.read_bytes()
            first_config = first_rom.with_suffix(".cfg").read_bytes()
            second_config = second_rom.with_suffix(".cfg").read_bytes()

        self.assertEqual(first_bytes, second_bytes)
        self.assertEqual(first_config, second_config)
        self.assertEqual(first_bytes[5], 1)
        self.assertEqual(first_bytes[-NROM_CHR_ROM_SIZE:], expected_chr)

    def test_chr_asset_example_builds_with_its_project_relative_asset(self) -> None:
        expected_chr = (ROOT / "examples" / "assets" / "chr_asset.chr").read_bytes()
        with tempfile.TemporaryDirectory() as temporary_directory:
            rom_path = Path(temporary_directory) / "chr_asset.nes"
            compile_source(
                ROOT / "examples" / "chr_asset.nsp",
                rom_path,
                chr_path="assets/chr_asset.chr",
            )
            rom = rom_path.read_bytes()

        self.assertEqual(len(expected_chr), NROM_CHR_ROM_SIZE)
        self.assertEqual(rom[-NROM_CHR_ROM_SIZE:], expected_chr)

    def test_palette_example_builds_with_custom_chr_and_runtime_palette_state(self) -> None:
        expected_chr = (ROOT / "examples" / "assets" / "chr_asset.chr").read_bytes()
        with tempfile.TemporaryDirectory() as temporary_directory:
            rom_path = Path(temporary_directory) / "palette_support.nes"
            compile_source(
                ROOT / "examples" / "palette_support.nsp",
                rom_path,
                chr_path="assets/chr_asset.chr",
            )
            rom = rom_path.read_bytes()
            memory_map = rom_path.with_suffix(".map").read_text(encoding="utf-8")

        self.assertEqual(len(rom), 16 + 32 * 1024 + 8 * 1024)
        self.assertEqual(rom[-NROM_CHR_ROM_SIZE:], expected_chr)
        self.assertIn("runtime_palette_shadow", memory_map)
        self.assertIn("runtime_palette_universal_dirty", memory_map)
        self.assertIn("runtime_ppuctrl_shadow", memory_map)
        self.assertIn("runtime_scroll_x_shadow", memory_map)
        self.assertIn("runtime_scroll_y_shadow", memory_map)

    def test_nametable_example_embeds_and_builds_complete_background(self) -> None:
        expected = (
            ROOT / "examples" / "assets" / "nametable_loading.nam"
        ).read_bytes()
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            first_rom = directory / "first.nes"
            second_rom = directory / "second.nes"
            arguments = {
                "chr_path": "assets/chr_asset.chr",
                "nametable_path": "assets/nametable_loading.nam",
            }
            first_assembly, _ = compile_source(
                ROOT / "examples" / "nametable_loading.nsp",
                first_rom,
                **arguments,
            )
            second_assembly, _ = compile_source(
                ROOT / "examples" / "nametable_loading.nsp",
                second_rom,
                **arguments,
            )
            first_bytes = first_rom.read_bytes()
            second_bytes = second_rom.read_bytes()
            first_assembly_bytes = first_assembly.read_bytes()
            second_assembly_bytes = second_assembly.read_bytes()

        prg = first_bytes[16 : 16 + 32 * 1024]
        self.assertEqual(prg.count(expected), 1)
        self.assertEqual(first_bytes, second_bytes)
        self.assertEqual(first_assembly_bytes, second_assembly_bytes)
        self.assertEqual(len(first_bytes), 16 + 32 * 1024 + 8 * 1024)

    def test_split_nametable_assets_build_as_one_complete_asset(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project = Path(temporary_directory)
            source_path = project / "main.nsp"
            source_path.write_text(
                """program SplitBackground;
begin
    nes.load_background();
    nes.set_background_color($0F);
    nes.run;
end.
""",
                encoding="utf-8",
            )
            tiles = bytes([0x12]) * NAMETABLE_TILE_SIZE
            attributes = bytes([0xE4]) * ATTRIBUTE_TABLE_SIZE
            (project / "tiles.bin").write_bytes(tiles)
            (project / "attributes.bin").write_bytes(attributes)
            rom_path = project / "main.nes"
            compile_source(
                source_path,
                rom_path,
                nametable_tiles_path="tiles.bin",
                nametable_attributes_path="attributes.bin",
            )
            prg = rom_path.read_bytes()[16 : 16 + 32 * 1024]

        self.assertEqual(prg.count(tiles + attributes), 1)

    def test_optional_promotion_fallback_builds_the_same_valid_rom_format(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            rom_path = Path(temporary_directory) / "zero_page_fallback.nes"
            compile_source(
                ROOT / "examples" / "zero_page.nsp",
                rom_path,
                MemoryLayoutSettings(zero_page_automatic_size=0),
            )
            rom = rom_path.read_bytes()
            memory_map = rom_path.with_suffix(".map").read_text(encoding="utf-8")

        self.assertEqual(rom[:4], b"NES\x1a")
        self.assertEqual(len(rom), 16 + 32 * 1024 + 8 * 1024)
        self.assertNotIn("Zero Page   byte       Counter", memory_map)
        self.assertIn("Regular RAM byte       Counter", memory_map)

    def test_ca65_uses_zero_page_opcodes_for_selected_symbols(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            rom_path = directory / "memory_layout.nes"
            assembly_path, _ = compile_source(
                ROOT / "examples" / "memory_layout.nsp",
                rom_path,
            )
            listing_path = directory / "memory_layout.lst"
            listing_object = directory / "memory_layout_listing.o"
            result = subprocess.run(
                [
                    str(shutil.which("ca65")),
                    str(assembly_path),
                    "-o",
                    str(listing_object),
                    "-l",
                    str(listing_path),
                ],
                capture_output=True,
                check=False,
                text=True,
            )
            listing = listing_path.read_text(encoding="utf-8")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertRegex(
            listing,
            r"85 rr\s+sta expression_temporary_0",
        )
        self.assertRegex(
            listing,
            r"A5 rr\s+lda variable_BackgroundColor",
        )
        self.assertRegex(
            listing,
            r"AD rr rr\s+lda variable_RenderingEnabled",
        )
        self.assertRegex(
            listing,
            r"E6 rr\s+inc runtime_frame_counter",
        )
        self.assertRegex(
            listing,
            r"85 rr\s+sta runtime_frame_ready",
        )

    def test_update_frame_state_uses_zero_page_opcodes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            rom_path = directory / "frame_callbacks.nes"
            assembly_path, _ = compile_source(
                ROOT / "examples" / "frame_callbacks.nsp",
                rom_path,
            )
            listing_path = directory / "frame_callbacks.lst"
            listing_object = directory / "frame_callbacks_listing.o"
            result = subprocess.run(
                [
                    str(shutil.which("ca65")),
                    str(assembly_path),
                    "-o",
                    str(listing_object),
                    "-l",
                    str(listing_path),
                ],
                capture_output=True,
                check=False,
                text=True,
            )
            listing = listing_path.read_text(encoding="utf-8")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertRegex(
            listing,
            r"85 rr\s+sta runtime_last_processed_frame",
        )
        self.assertRegex(
            listing,
            r"C5 rr\s+cmp runtime_last_processed_frame",
        )

    def test_controller_runtime_state_uses_zero_page_opcodes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            rom_path = directory / "controller_input.nes"
            assembly_path, _ = compile_source(
                ROOT / "examples" / "controller_input.nsp",
                rom_path,
            )
            listing_path = directory / "controller_input.lst"
            listing_object = directory / "controller_input_listing.o"
            result = subprocess.run(
                [
                    str(shutil.which("ca65")),
                    str(assembly_path),
                    "-o",
                    str(listing_object),
                    "-l",
                    str(listing_path),
                ],
                capture_output=True,
                check=False,
                text=True,
            )
            listing = listing_path.read_text(encoding="utf-8")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertRegex(
            listing,
            r"A5 rr\s+lda runtime_controller_1_current",
        )
        self.assertRegex(
            listing,
            r"66 rr\s+ror runtime_controller_2_current",
        )
        self.assertRegex(
            listing,
            r"C5 rr\s+cmp runtime_controller_polled_frame",
        )

    def test_generated_memory_artifacts_are_complete_and_reproducible(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            first_rom = directory / "first.nes"
            second_rom = directory / "second.nes"
            source_path = ROOT / "examples" / "memory_layout.nsp"

            compile_source(source_path, first_rom)
            compile_source(source_path, second_rom)

            first_config = first_rom.with_suffix(".cfg").read_text(encoding="utf-8")
            second_config = second_rom.with_suffix(".cfg").read_text(encoding="utf-8")
            first_map = first_rom.with_suffix(".map").read_text(encoding="utf-8")
            second_map = second_rom.with_suffix(".map").read_text(encoding="utf-8")

        self.assertEqual(first_config, second_config)
        self.assertEqual(first_map, second_map)
        self.assertIn("OAM:     start = $0200, size = $0100", first_config)
        self.assertIn("runtime_oam_shadow", first_map)
        self.assertIn("variable_BackgroundColor", first_map)

    def test_conditional_branch_larger_than_relative_branch_range(self) -> None:
        assignments = "\n".join(
            "        Counter := Counter + $01;" for _ in range(80)
        )
        source = f"""program LongBranch;
var
    Enabled: boolean;
    Counter: byte;
begin
    Enabled := true;
    Counter := $00;
    if Enabled then
    begin
{assignments}
    end;
    nes.set_background_color($21);
    nes.run;
end.
"""
        with tempfile.TemporaryDirectory() as temporary_directory:
            source_path = Path(temporary_directory) / "long_branch.nsp"
            rom_path = Path(temporary_directory) / "long_branch.nes"
            source_path.write_text(source, encoding="utf-8")
            compile_source(source_path, rom_path)
            rom = rom_path.read_bytes()
        self.assertEqual(len(rom), 16 + 32 * 1024 + 8 * 1024)

    def test_for_body_larger_than_relative_branch_range(self) -> None:
        updates = "\n".join("        inc(Total);" for _ in range(80))
        source = f"""program LongFor;
var
    Index: byte;
    Total: byte;
begin
    Total := $00;
    for Index := $00 to $01 do
    begin
{updates}
    end;
    nes.set_background_color($21);
    nes.run;
end.
"""
        with tempfile.TemporaryDirectory() as temporary_directory:
            source_path = Path(temporary_directory) / "long_for.nsp"
            rom_path = Path(temporary_directory) / "long_for.nes"
            source_path.write_text(source, encoding="utf-8")
            compile_source(source_path, rom_path)
            rom = rom_path.read_bytes()
        self.assertEqual(len(rom), 16 + 32 * 1024 + 8 * 1024)


@unittest.skipUnless(
    TOOLCHAIN_AVAILABLE and MESEN_EXECUTABLE is not None,
    "emulator integration skipped: ca65, ld65, and a valid MESEN_PATH are required",
)
class MesenIntegrationTests(unittest.TestCase):
    def _run_mesen_test(
        self,
        example_name: str,
        script_name: str,
        memory_settings: MemoryLayoutSettings | None = None,
        chr_path: str | Path | None = None,
        nametable_path: str | Path | None = None,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            rom_path = Path(temporary_directory) / f"{example_name}.nes"
            source_path = ROOT / "examples" / f"{example_name}.nsp"
            if memory_settings is None:
                compile_source(
                    source_path,
                    rom_path,
                    chr_path=chr_path,
                    nametable_path=nametable_path,
                )
            else:
                compile_source(
                    source_path,
                    rom_path,
                    memory_settings,
                    chr_path=chr_path,
                    nametable_path=nametable_path,
                )
            result = subprocess.run(
                [
                    str(MESEN_EXECUTABLE),
                    "--testRunner",
                    str(rom_path),
                    str(ROOT / "tests" / "mesen" / script_name),
                ],
                capture_output=True,
                check=False,
                text=True,
                timeout=30,
            )

        self.assertEqual(
            result.returncode,
            0,
            f"Mesen runtime validation failed:\n{result.stdout}\n{result.stderr}",
        )

    def test_loop_example_reaches_expected_runtime_state(self) -> None:
        self._run_mesen_test("loops", "verify_loops.lua")

    def test_counting_example_reaches_expected_runtime_state(self) -> None:
        self._run_mesen_test(
            "counting",
            "verify_counting.lua",
        )

    def test_procedure_example_reaches_expected_runtime_state(self) -> None:
        self._run_mesen_test(
            "procedures",
            "verify_procedures.lua",
        )

    def test_procedure_parameters_reach_expected_runtime_state(self) -> None:
        self._run_mesen_test(
            "procedure_parameters",
            "verify_procedure_parameters.lua",
        )

    def test_memory_layout_example_reaches_expected_runtime_state(self) -> None:
        self._run_mesen_test("memory_layout", "verify_memory_layout.lua")

    def test_zero_page_example_reaches_expected_runtime_state(self) -> None:
        self._run_mesen_test("zero_page", "verify_zero_page.lua")

    def test_zero_page_fallback_preserves_runtime_state(self) -> None:
        self._run_mesen_test(
            "zero_page",
            "verify_zero_page_fallback.lua",
            MemoryLayoutSettings(zero_page_automatic_size=0),
        )

    def test_frame_synchronization_waits_for_distinct_nmis(self) -> None:
        self._run_mesen_test(
            "frame_synchronization",
            "verify_frame_synchronization.lua",
        )

    def test_callbacks_advance_once_per_frame_across_counter_wrap(self) -> None:
        self._run_mesen_test(
            "frame_callbacks",
            "verify_frame_callbacks.lua",
        )

    def test_slow_update_processes_newest_pending_frame_without_nesting(self) -> None:
        self._run_mesen_test(
            "slow_update_callback",
            "verify_slow_update_callback.lua",
        )

    def test_controller_example_validates_input_and_oam_across_wrap(self) -> None:
        self._run_mesen_test(
            "controller_input",
            "verify_controller_input.lua",
        )

    def test_palette_example_uploads_initial_and_runtime_palettes(self) -> None:
        self._run_mesen_test(
            "palette_support",
            "verify_palette_support.lua",
            chr_path="assets/chr_asset.chr",
        )

    def test_nametable_example_uploads_tiles_and_attributes(self) -> None:
        self._run_mesen_test(
            "nametable_loading",
            "verify_nametable_loading.lua",
            chr_path="assets/chr_asset.chr",
            nametable_path="assets/nametable_loading.nam",
        )


if __name__ == "__main__":
    unittest.main()
