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


if __name__ == "__main__":
    unittest.main()
