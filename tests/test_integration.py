from pathlib import Path
import shutil
import tempfile
import unittest

from nes_pascal.cli import compile_source


ROOT = Path(__file__).resolve().parents[1]
TOOLCHAIN_AVAILABLE = shutil.which("ca65") is not None and shutil.which("ld65") is not None


@unittest.skipUnless(
    TOOLCHAIN_AVAILABLE,
    "integration skipped: ca65 and/or ld65 are not installed",
)
class ToolchainIntegrationTests(unittest.TestCase):
    def test_builds_valid_nrom_image(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            rom_path = Path(temporary_directory) / "minimal.nes"
            compile_source(ROOT / "examples" / "minimal.nsp", rom_path)
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


if __name__ == "__main__":
    unittest.main()
