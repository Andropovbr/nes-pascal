import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from nes_pascal.cli import compile_source
from nes_pascal.memory_layout import MemoryLayoutSettings


ROOT = Path(__file__).resolve().parents[1]
TOOLCHAIN_AVAILABLE = (
    shutil.which("ca65") is not None
    and shutil.which("ld65") is not None
)
MESEN_PATH = os.environ.get("MESEN_PATH")


@unittest.skipUnless(
    TOOLCHAIN_AVAILABLE,
    "integration skipped: ca65 and/or ld65 are not installed",
)
class ToolchainIntegrationTests(unittest.TestCase):
    def _assert_valid_nrom_image(self, example_name: str) -> None:
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
        self.assertEqual(rom[-8 * 1024 :], bytes(8 * 1024))

        vector_offset = 16 + 0x7FFA
        nmi = int.from_bytes(rom[vector_offset : vector_offset + 2], "little")
        reset = int.from_bytes(rom[vector_offset + 2 : vector_offset + 4], "little")
        irq = int.from_bytes(rom[vector_offset + 4 : vector_offset + 6], "little")
        self.assertEqual((nmi, reset, irq), (0x8000, 0x8002, 0x8001))

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
    TOOLCHAIN_AVAILABLE and MESEN_PATH is not None,
    "emulator integration skipped: ca65, ld65, and MESEN_PATH are required",
)
class MesenIntegrationTests(unittest.TestCase):
    def _run_mesen_test(
        self,
        example_name: str,
        script_name: str,
        memory_settings: MemoryLayoutSettings | None = None,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            rom_path = Path(temporary_directory) / f"{example_name}.nes"
            source_path = ROOT / "examples" / f"{example_name}.nsp"
            if memory_settings is None:
                compile_source(source_path, rom_path)
            else:
                compile_source(source_path, rom_path, memory_settings)
            result = subprocess.run(
                [
                    str(MESEN_PATH),
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


if __name__ == "__main__":
    unittest.main()
